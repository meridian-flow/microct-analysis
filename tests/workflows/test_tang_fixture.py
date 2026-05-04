from __future__ import annotations

from pathlib import Path

from microct_analysis.workflows.loading import get_uncertain_fields, validate_workflow
from microct_analysis.workflows.schema import (
    extract_acceptance_checks,
    extract_landmarks,
    extract_measurements,
    extract_thresholds,
    parse_frontmatter,
)

FIXTURE = Path("tests/fixtures/workflows/mouse-knee-oa-geometric-indices/workflow.md")


def test_tang_workflow_fixture_validates() -> None:
    workflow, body = parse_frontmatter(FIXTURE.read_text(encoding="utf-8"))

    assert "Protocol identity" in body
    assert validate_workflow(workflow) == []

    thresholds = extract_thresholds(workflow)
    assert thresholds["bone_soft_tissue"]["value"] == 220
    assert thresholds["subchondral_plate"]["value"] == 270
    assert thresholds["segmentation_3d"]["value"] == 320

    landmark_names = {landmark["name"] for landmark in extract_landmarks(workflow)}
    assert landmark_names == {
        "intercondylar_groove_midpoint",
        "intercondylar_notch",
        "lateral_condylar_edge",
        "medial_condylar_edge",
        "articular_surface_proximal",
        "growth_plate_proximal",
        "medial_tibial_condyle_edge",
        "lateral_tibial_condyle_edge",
    }
    landmark_domains = {landmark["name"]: landmark["domain"] for landmark in extract_landmarks(workflow)}
    assert landmark_domains["intercondylar_groove_midpoint"] == "femoral_3d_surface"
    assert landmark_domains["articular_surface_proximal"] == "tibial_2d_slice"

    measurement_names = {measurement["name"] for measurement in extract_measurements(workflow)}
    assert measurement_names == {
        "distal_femoral_length",
        "distal_femoral_width",
        "distal_femoral_ratio",
        "tibial_iioc_height",
        "tibial_width",
        "tibial_iioc_ratio",
        "medial_trabecular_morphometry",
        "lateral_trabecular_morphometry",
        "total_iioc_bone_volume",
    }

    checks = extract_acceptance_checks(workflow)
    assert set(checks) == {"segmentation", "landmarks", "roi", "measurement"}

    assert get_uncertain_fields(workflow) == []
