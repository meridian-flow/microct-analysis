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
