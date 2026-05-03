from pathlib import Path

from microct_analysis.measurements.workflow_binding import compile_measurement_specs
from microct_analysis.workflows.loading import load_workflow


def test_compile_tang_fixture_measurements():
    workflow = load_workflow(Path("tests/fixtures/workflows/mouse-knee-oa-geometric-indices/workflow.md"))
    specs = compile_measurement_specs(workflow)
    by_name = {spec.name: spec for spec in specs}
    assert by_name["distal_femoral_length"].points == ["intercondylar_groove_midpoint", "intercondylar_notch"]
    assert by_name["distal_femoral_ratio"].acceptance == {"normal_range": [1.0, 1.28], "oa_threshold": 1.245}
    assert by_name["tibial_iioc_height"].boundaries == ["most_proximal_articular_surface", "most_proximal_growth_plate"]
