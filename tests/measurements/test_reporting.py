from microct_analysis.measurements.models import MeasurementResult, MeasurementSpec
from microct_analysis.measurements.reporting import build_qc_payload, results_to_json, results_to_markdown


def test_results_to_json_and_markdown_include_values_and_qc():
    spec = MeasurementSpec("length", "distance", unit="mm", frame="oriented_frontal")
    result = MeasurementResult("length", 1.25, "mm", spec, {"points": ["a", "b"]}, "qc.json")
    payload = results_to_json([result], "workflow", "session")
    assert payload["workflow_id"] == "workflow"
    assert payload["results"][0]["value"] == 1.25
    assert "| length | 1.25 | mm |" in results_to_markdown([result])
    assert build_qc_payload([result])["qc_overlays"][0]["evidence"] == "qc.json"


def test_results_to_markdown_includes_method_inputs_formulas_and_slice_counts():
    length_spec = MeasurementSpec(
        "distal_femoral_length",
        "surface_distance",
        domain="femoral_3d_surface",
        points=["intercondylar_groove_midpoint", "intercondylar_notch"],
    )
    height_spec = MeasurementSpec(
        "tibial_iioc_height",
        "boundary_slice_count",
        domain="tibial_2d_slice",
        boundaries=["articular_surface_proximal", "growth_plate_proximal"],
    )
    ratio_spec = MeasurementSpec(
        "tibial_iioc_ratio",
        "ratio",
        domain="derived",
        numerator="tibial_iioc_height",
        denominator="tibial_width",
        unit="dimensionless",
    )
    markdown = results_to_markdown(
        [
            MeasurementResult(
                "distal_femoral_length",
                2.29,
                "mm",
                length_spec,
                {
                    "method": "euclidean_3d",
                    "points": {
                        "intercondylar_groove_midpoint": [0, 0, 0],
                        "intercondylar_notch": [2.29, 0, 0],
                    },
                },
                "length-qc.json",
            ),
            MeasurementResult(
                "tibial_iioc_height",
                0.7455,
                "mm",
                height_spec,
                {
                    "method": "boundary_slice_count",
                    "boundaries": {"articular_surface_proximal": 661, "growth_plate_proximal": 732},
                    "slice_count": 71,
                    "slice_thickness": 0.0105,
                },
                "height-qc.json",
            ),
            MeasurementResult(
                "tibial_iioc_ratio",
                0.253,
                "dimensionless",
                ratio_spec,
                {"numerator": "tibial_iioc_height", "denominator": "tibial_width"},
                "ratio-qc.json",
            ),
        ]
    )

    assert "Method" in markdown
    assert "euclidean_3d" in markdown
    assert "landmarks: intercondylar_groove_midpoint, intercondylar_notch" in markdown
    assert "boundary_slice_count" in markdown
    assert "slice_count: 71" in markdown
    assert "71 slices × 0.0105 mm" in markdown
    assert "tibial_iioc_height / tibial_width" in markdown
