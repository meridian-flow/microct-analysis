from __future__ import annotations

import pytest

from microct_analysis.workflows.explain import (
    correction_code,
    explain_assignment_change,
    explain_correction,
    explain_landmark_decision,
    explain_threshold_change,
)


def test_explain_threshold_change_raise_direction() -> None:
    record = explain_threshold_change(110.0, 145.0, "Noise dominated the edges.")

    assert record.what_changed == "The threshold will raise from 110 to 145."
    assert "Noise dominated the edges." in record.why
    assert "removes faint noise" in record.why
    assert record.domain_context["explanation_payload"]["details"]["direction"] == "raise"


def test_explain_threshold_change_lower_and_keep_directions() -> None:
    lowered = explain_threshold_change(145.0, 110.0, "Bone was clipped.")
    kept = explain_threshold_change(145.0, 145.0, "Only the review note changes.")

    assert lowered.what_changed == "The threshold will lower from 145 to 110."
    assert "includes fainter bone" in lowered.why
    assert kept.what_changed == "The threshold will keep from 145 to 145."
    assert "numeric threshold is unchanged" in kept.why


def test_explain_assignment_change_variants() -> None:
    moved = explain_assignment_change("component-1", "femur", "tibia")
    unassigned = explain_assignment_change("component-2", "tibia", "unassigned")
    fresh = explain_assignment_change("component-3", None, "fibula")

    assert moved.what_changed == "Component component-1 will move from femur to tibia."
    assert "clears the earlier assignment" in moved.why
    assert unassigned.what_changed == "Component component-2 will be left unassigned."
    assert "will not be used as a seed" in unassigned.why
    assert fresh.what_changed == "Component component-3 will be assigned to fibula."


def test_explain_landmark_decision_accept_and_reject() -> None:
    accepted = explain_landmark_decision("femur", True, "The highlighted candidate matches the expected anatomy.")
    rejected = explain_landmark_decision("tibia", False, "The candidate sits outside the expected cortex.")

    assert accepted.what_changed == "The femur landmark candidate will be accepted."
    assert "accepted" in accepted.why.lower()
    assert rejected.what_changed == "The tibia landmark candidate will be rejected."
    assert "rejected" in rejected.why.lower()


def test_explain_correction_uses_generic_fallback_for_unknown_operation() -> None:
    record = explain_correction(
        "custom_cleanup",
        parameters={"summary": "Remove abandoned scratch cells.", "reason": "They are superseded by the accepted workflow."},
        before_state={"status": "messy"},
        after_state={"status": "compacted"},
    )

    assert record.what_changed == "Remove abandoned scratch cells."
    assert record.why == "They are superseded by the accepted workflow."
    assert record.domain_context["operation_type"] == "custom_cleanup"


def test_correction_code_captures_explanation_before_exec(compile_snippet) -> None:
    record = explain_correction(
        "adjust_threshold",
        parameters={"reason": "The mask missed thin cortex."},
        before_state={"threshold": 140},
        after_state={"threshold": 120},
    )

    snippet = correction_code(record, "result = {'status': 'ok'}\nprint(result)")
    compile_snippet(snippet, filename="correction_code.py")

    explanation_idx = snippet.index("correction_explanations.append")
    exec_idx = snippet.index("result = {'status': 'ok'}")
    assert explanation_idx < exec_idx
    assert "display(Markdown(" in snippet
    assert "correction_explanations" in snippet


@pytest.mark.parametrize(
    ("operation_type", "parameters", "before_state", "after_state", "expected_text"),
    [
        (
            "threshold_adjustment",
            {"reason": "More cortex should be included."},
            {"threshold": 140},
            {"threshold": 120},
            "threshold will lower",
        ),
        (
            "component_reassignment",
            {"component_id": "component-7", "old_label": "femur", "new_label": "tibia"},
            {},
            {},
            "Component component-7 will move from femur to tibia.",
        ),
        (
            "add_landmark",
            {"landmark_name": "femur", "accepted": True, "reason": "Matches the expected anatomy."},
            {},
            {},
            "landmark candidate will be accepted",
        ),
        (
            "remove_landmark",
            {"landmark_name": "tibia", "accepted": False, "reason": "The point is off cortex."},
            {},
            {},
            "landmark candidate will be rejected",
        ),
    ],
)
def test_explain_correction_supports_operation_aliases(
    operation_type: str,
    parameters: dict[str, object],
    before_state: dict[str, object],
    after_state: dict[str, object],
    expected_text: str,
) -> None:
    record = explain_correction(operation_type, parameters, before_state, after_state)

    assert expected_text in record.what_changed
