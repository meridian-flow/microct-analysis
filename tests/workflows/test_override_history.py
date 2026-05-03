from __future__ import annotations

from microct_analysis.workflows.planning import (
    OverrideFingerprint,
    RunRecord,
    append_run_record,
    detect_promotion_candidates,
    load_run_history,
    override_fingerprint_from_record,
)


def test_override_fingerprint_excludes_rationale_confidence_and_approver() -> None:
    first = override_fingerprint_from_record(
        "mouse-knee",
        {
            "stage": "segmentation",
            "field": "thresholds.bone.value",
            "canonical_value": 220,
            "override_value": 235,
            "rationale": "noisy",
            "confidence": "medium",
            "approver": "user",
        },
    )
    second = override_fingerprint_from_record(
        "mouse-knee",
        {
            "stage": "segmentation",
            "field": "thresholds.bone.value",
            "canonical_value": 220,
            "override_value": 235,
            "rationale": "different words",
            "confidence": "high",
            "approver": "analyst",
        },
    )

    assert first == second


def test_append_and_load_run_history_round_trips_records(tmp_path) -> None:
    path = tmp_path / "workflows" / "mouse-knee" / "runs.jsonl"
    fingerprint = OverrideFingerprint("mouse-knee", "roi", "roi.height_um", "500", "550")
    record = RunRecord("2026-05-03T10:00:00Z", "session-1", "mouse-knee", [fingerprint])

    append_run_record(path, record)

    assert load_run_history(path) == [record]


def test_detect_promotion_candidates_requires_current_plus_two_immediately_preceding_runs() -> None:
    fingerprint = OverrideFingerprint("mouse-knee", "segmentation", "threshold", "220", "235")
    history = [
        RunRecord("2026-05-02T10:00:00Z", "session-2", "mouse-knee", [fingerprint]),
        RunRecord("2026-05-01T10:00:00Z", "session-1", "mouse-knee", [fingerprint]),
    ]

    assert detect_promotion_candidates([fingerprint], history) == [fingerprint]


def test_detect_promotion_candidates_breaks_streak_when_prior_run_lacks_fingerprint() -> None:
    fingerprint = OverrideFingerprint("mouse-knee", "segmentation", "threshold", "220", "235")
    other = OverrideFingerprint("mouse-knee", "roi", "height", "500", "550")
    history = [
        RunRecord("2026-05-02T10:00:00Z", "session-2", "mouse-knee", [other]),
        RunRecord("2026-05-01T10:00:00Z", "session-1", "mouse-knee", [fingerprint]),
    ]

    assert detect_promotion_candidates([fingerprint], history) == []
