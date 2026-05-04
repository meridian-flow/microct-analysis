from pathlib import Path

from microct_analysis.measurements.workflow_binding import compile_measurement_specs
from microct_analysis.workflows.loading import load_workflow


def test_compile_tang_fixture_measurements():
    workflow = load_workflow(Path("tests/fixtures/workflows/mouse-knee-oa-geometric-indices/workflow.md"))
    specs = compile_measurement_specs(workflow)
    by_name = {spec.name: spec for spec in specs}
    assert by_name["distal_femoral_length"].domain == "femoral_3d_surface"
    assert by_name["distal_femoral_length"].kind == "surface_distance"
    assert by_name["distal_femoral_length"].points == ["intercondylar_groove_midpoint", "intercondylar_notch"]
    assert by_name["distal_femoral_ratio"].domain == "derived"
    assert by_name["distal_femoral_ratio"].acceptance["normal_threshold"] == 1.28
    assert by_name["distal_femoral_ratio"].acceptance["oa_threshold"] == 1.30
    assert by_name["tibial_iioc_height"].kind == "boundary_slice_count"
    assert by_name["tibial_iioc_height"].domain == "tibial_2d_slice"
    assert by_name["tibial_iioc_height"].boundaries == ["articular_surface_proximal", "growth_plate_proximal"]
