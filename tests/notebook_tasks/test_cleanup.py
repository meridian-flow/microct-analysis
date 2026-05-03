from __future__ import annotations

from microct_analysis.notebook_tasks.cleanup import identify_dead_ends, identify_review_cells


def test_identify_dead_ends_flags_explicit_markers_and_error_outputs() -> None:
    cells = [
        {"cell_type": "markdown", "source": "Dead end; abandon this branch."},
        {"cell_type": "code", "source": "segment()", "outputs": [{"output_type": "error", "ename": "ValueError", "evalue": "bad threshold"}]},
        {"cell_type": "code", "source": "accepted workflow", "outputs": [{"output_type": "stream", "text": "ok"}]},
    ]

    assert identify_dead_ends(cells) == [0, 1]


def test_identify_review_cells_detects_markers_in_source_and_outputs() -> None:
    cells = [
        {"cell_type": "code", "source": "capture_screenshot('review-1')", "outputs": []},
        {"cell_type": "code", "source": "print('done')", "outputs": [{"output_type": "display_data", "data": {"text/plain": ["component-reassignment"]}}]},
        {"cell_type": "markdown", "source": "ordinary note", "outputs": []},
    ]

    assert identify_review_cells(cells) == [0, 1]


def test_identify_dead_ends_aligns_with_compaction_by_removing_only_recovered_failures() -> None:
    cells = [
        {"cell_type": "code", "source": "first failed attempt", "outputs": [{"output_type": "error", "ename": "ValueError", "evalue": "bad threshold"}]},
        {"cell_type": "code", "source": "recovered path", "outputs": [{"output_type": "stream", "text": "ok"}]},
        {"cell_type": "code", "source": "terminal failed attempt", "outputs": [{"output_type": "error", "ename": "RuntimeError", "evalue": "still broken"}]},
    ]

    assert identify_dead_ends(cells) == [0]


def test_review_and_explanation_cells_are_preserved_even_if_they_mention_dead_end_signals() -> None:
    cells = [
        {
            "cell_type": "code",
            "source": "# dead end note\nexplanation_payload = {'status': 'kept'}",
            "outputs": [{"output_type": "error", "ename": "ValueError", "evalue": "documented failed attempt"}],
        },
        {
            "cell_type": "code",
            "source": "capture_screenshot('scene-1.png')",
            "outputs": [{"output_type": "stream", "text": "saved visualizations/screenshots/scene-1.png"}],
        },
    ]

    assert identify_review_cells(cells) == [0, 1]
    assert identify_dead_ends(cells) == []


def test_review_detection_handles_list_source_and_display_payload_text() -> None:
    cells = [
        {
            "cell_type": "markdown",
            "source": ["Review note: ", "capture_screenshot('shot')"],
            "outputs": [],
        },
        {
            "cell_type": "code",
            "source": "print('done')",
            "outputs": [
                {
                    "output_type": "display_data",
                    "data": {"text/plain": ["threshold-adjustment", "kept for review"]},
                }
            ],
        },
    ]

    assert identify_review_cells(cells) == [0, 1]
    assert identify_dead_ends(cells) == []
