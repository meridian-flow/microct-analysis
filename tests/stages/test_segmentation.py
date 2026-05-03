from __future__ import annotations

import ast
from pathlib import Path

from mouse_ct.types import Component, Thresholds

from microct_analysis.stages import segmentation


ALLOWED_MOUSE_CT_IMPORTS = {
    "mouse_ct.io.calibration",
    "mouse_ct.io.output",
    "mouse_ct.processing.markers",
    "mouse_ct.processing.preprocess",
    "mouse_ct.processing.threshold",
    "mouse_ct.processing.watershed",
    "mouse_ct.types",
    "mouse_ct.verify.sanity",
}


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    return names


def test_segmentation_driver_imports_only_allowed_mouse_ct_surface(microct_src: Path) -> None:
    imports = [name for name in _imports(microct_src / "stages" / "segmentation.py") if name.startswith("mouse_ct")]
    assert set(imports) <= ALLOWED_MOUSE_CT_IMPORTS
    assert all(not name.startswith(("mouse_ct.picker", "mouse_ct.seed_editor", "mouse_ct.cli", "mouse_ct.qc")) for name in imports)


def test_stage_report_structure(tmp_path: Path) -> None:
    report = segmentation._report(
        status="ready",
        confidence="high",
        evidence="ok",
        output_root=tmp_path / "segmentation",
        flags=[],
        structure_assignments={"femur": 1},
        threshold_observations=[],
        confounders=[],
    )

    assert report["stage"] == "segmentation"
    assert report["status"] == "ready"
    assert report["recommended_action"] == "proceed"
    assert report["artifacts"]["labels"].endswith("segmentation/labels.nii.gz")
    assert report["artifacts"]["structure_assignments"].endswith("segmentation/structure_assignments.json")
    assert report["artifacts"]["seeds"].endswith("segmentation/seeds.json")
    assert report["artifacts"]["screenshots"] == ["segmentation/screenshot_001.png"]


def test_threshold_comparison_flags_workflow_discrepancy() -> None:
    observations = segmentation.compare_thresholds(
        Thresholds(mask=240.0, marker=410.0, method="histogram-otsu"),
        {"mask": {"value": 200.0}, "marker": {"value": 400.0}, "tolerance_fraction": 0.10},
    )

    assert len(observations) == 1
    assert "mask threshold derived" in observations[0]


def test_confounder_detection_flags_boundary_extra_and_bridge_components() -> None:
    components = [
        Component(1, 1000, (5.0, 5.0, 5.0), (0.1, 0.1, 0.1), ((0, 21), (2, 8), (2, 8)), ("z_min",)),
        Component(2, 900, (25.0, 5.0, 5.0), (0.5, 0.1, 0.1), ((20, 28), (2, 8), (2, 8)), ()),
        Component(3, 400, (15.0, 1.0, 5.0), (0.3, 0.02, 0.1), ((14, 18), (0, 2), (4, 7)), ()),
        Component(4, 300, (15.0, 9.0, 5.0), (0.3, 0.18, 0.1), ((14, 18), (8, 10), (4, 7)), ()),
        Component(5, 250, (15.0, 7.0, 9.0), (0.3, 0.14, 0.18), ((14, 18), (6, 8), (8, 10)), ()),
    ]

    observations = segmentation.detect_confounders(components, [], (30, 10, 10))

    assert any("Partial bones" in item for item in observations)
    assert any("Sesamoid" in item for item in observations)
    assert any("Osteophytes" in item for item in observations)
