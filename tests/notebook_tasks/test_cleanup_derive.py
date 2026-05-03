from __future__ import annotations

from microct_analysis.notebook_tasks.cleanup import build_derive_spec, validate_derived_notebook


def test_build_derive_spec_removes_dead_ends_and_preserves_accepted_evidence() -> None:
    cells = [
        {"cell_type": "markdown", "source": "dead end abandoned threshold branch"},
        {"cell_type": "code", "source": "explanation_payload = {'why': 'fix threshold'}", "outputs": []},
        {"cell_type": "code", "source": "capture_screenshot('segmentation/screenshot_001.png')", "outputs": []},
        {"cell_type": "markdown", "source": "Measurement summary measurements/results.json"},
    ]

    spec = build_derive_spec(cells, measurement_artifacts={"results": "measurements/results.json"})

    assert spec.remove_cells == [0]
    assert spec.keep_cells == [1, 2, 3]
    assert spec.preserve_screenshots == ["segmentation/screenshot_001.png"]
    assert spec.preserve_measurements is True
    assert spec.preserve_explanations is True


def test_build_derive_spec_preserves_review_cell_even_with_dead_end_marker() -> None:
    cells = [
        {"cell_type": "markdown", "source": "dead end but decision point: user rejected first ROI"},
        {"cell_type": "markdown", "source": "accepted ROI"},
    ]

    spec = build_derive_spec(cells)

    assert spec.remove_cells == []
    assert spec.keep_cells == [0, 1]


def test_validate_derived_notebook_reports_missing_artifact_references() -> None:
    cells = [
        {"cell_type": "markdown", "source": "Kept measurements/results.json and segmentation/screenshot_001.png"},
    ]

    missing = validate_derived_notebook(
        cells,
        ["measurements/results.json", "segmentation/screenshot_001.png", "overrides.json"],
    )

    assert missing == ["overrides.json"]
