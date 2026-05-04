from __future__ import annotations

import math

from microct_analysis.measurements.geometry import (
    compute_boundary_slice_count,
    compute_frontal_projected_width,
    compute_ratio,
    compute_slice_distance,
    compute_surface_distance,
)
from microct_analysis.measurements.models import MeasurementSpec
from microct_analysis.measurements.reporting import build_qc_payload


def _within_pct(value: float, expected: float, pct: float = 0.10) -> bool:
    return expected * (1 - pct) <= value <= expected * (1 + pct)


def test_oa6_femoral_surface_measurements_and_ratio_match_published_acceptance() -> None:
    landmarks = {
        "intercondylar_groove_midpoint": [0.0, 0.0, 0.0],
        "intercondylar_notch": [2.29, 0.0, 0.0],
        "lateral_condylar_edge": [0.0, 2.0, 3.48],
        "medial_condylar_edge": [0.0, -4.0, 0.0],
    }
    length_spec = MeasurementSpec(
        name="distal_femoral_length",
        domain="femoral_3d_surface",
        kind="surface_distance",
        points=["intercondylar_groove_midpoint", "intercondylar_notch"],
    )
    width_spec = MeasurementSpec(
        name="distal_femoral_width",
        domain="femoral_3d_surface",
        kind="frontal_projected_width",
        projection="frontal",
        points=["lateral_condylar_edge", "medial_condylar_edge"],
    )
    ratio_spec = MeasurementSpec(
        name="distal_femoral_ratio",
        domain="derived",
        kind="ratio",
        numerator="distal_femoral_width",
        denominator="distal_femoral_length",
        unit="dimensionless",
    )

    length = compute_surface_distance(length_spec, landmarks, (1.0, 1.0, 1.0))
    width = compute_frontal_projected_width(width_spec, landmarks, (1.0, 1.0, 1.0))
    ratio = compute_ratio(ratio_spec, {length.name: length, width.name: width})

    assert _within_pct(length.value, 2.29)
    assert _within_pct(width.value, 3.48)
    assert _within_pct(ratio.value, 1.520)
    assert width.inputs["method"] == "frontal_projected_width"
    assert width.inputs["projection_axis"] == 2


def test_oa6_tibial_slice_measurements_are_domain_routed_and_exact_slice_multiple() -> None:
    landmarks = {
        "articular_surface_proximal": {"slice_index": 661},
        "growth_plate_proximal": {"slice_index": 732},
        "medial_tibial_condyle_edge": [700.0, 0.0, 100.0],
        "lateral_tibial_condyle_edge": [700.0, 0.0, 380.9523809524],
    }
    height_spec = MeasurementSpec(
        name="tibial_iioc_height",
        domain="tibial_2d_slice",
        kind="boundary_slice_count",
        boundaries=["articular_surface_proximal", "growth_plate_proximal"],
    )
    width_spec = MeasurementSpec(
        name="tibial_width",
        domain="tibial_2d_slice",
        kind="slice_distance",
        projection="frontal",
        points=["medial_tibial_condyle_edge", "lateral_tibial_condyle_edge"],
    )
    ratio_spec = MeasurementSpec(
        name="tibial_iioc_ratio",
        domain="derived",
        kind="ratio",
        numerator="tibial_iioc_height",
        denominator="tibial_width",
        unit="dimensionless",
    )

    spacing = (0.0105, 0.0105, 0.0105)
    height = compute_boundary_slice_count(height_spec, landmarks, spacing)
    width = compute_slice_distance(width_spec, landmarks, spacing)
    ratio = compute_ratio(ratio_spec, {height.name: height, width.name: width})
    qc = build_qc_payload([height, width, ratio])["qc_overlays"]

    assert height.inputs["slice_count"] == 71
    assert height.value == 71 * 0.0105
    assert math.isclose(height.value / 0.0105, round(height.value / 0.0105))
    assert height.inputs["exact_multiple"] is True
    assert _within_pct(width.value, 2.95)
    assert _within_pct(ratio.value, 0.253)
    assert qc[0]["domain"] == "tibial_2d_slice"
    assert qc[0]["method"] == "boundary_slice_count"
    assert qc[0]["slice_count"] == 71
    assert qc[0]["exact_multiple"] is True
