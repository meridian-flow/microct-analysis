"""Workflow planning helpers shared by analyst and workflow-creator."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from microct_analysis.workflows.loading import load_workflow, validate_workflow

STAGE_FIELDS: dict[str, tuple[str, ...]] = {
    "intake": ("workflow_id", "modality", "species", "anatomy", "study_type", "sources"),
    "segmentation": ("thresholds", "acceptance_checks", "reference_images"),
    "landmarks-orientation": ("landmarks", "orientation_protocol", "acceptance_checks", "reference_images"),
    "roi": ("roi_definitions", "orientation_protocol", "acceptance_checks", "reference_images"),
    "measurement": ("measurements", "roi_definitions", "acceptance_checks", "sources"),
}


@dataclass(frozen=True)
class OverrideFingerprint:
    """Normalized override identity for promotion detection."""

    workflow_id: str
    stage: str
    field: str
    canonical_value: str
    override_value: str


@dataclass(frozen=True)
class RunRecord:
    """Summary of a completed analysis run for override history."""

    completed_at: str
    session_id: str
    workflow_id: str
    override_fingerprints: list[OverrideFingerprint]


def override_fingerprint_from_record(workflow_id: str, override: dict[str, Any]) -> OverrideFingerprint:
    """Create a normalized fingerprint from a run override record."""

    return OverrideFingerprint(
        workflow_id=workflow_id,
        stage=str(override["stage"]),
        field=str(override["field"]),
        canonical_value=normalize_override_value(override.get("canonical_value")),
        override_value=normalize_override_value(override.get("override_value")),
    )


def normalize_override_value(value: Any) -> str:
    """Normalize an override value for stable history comparison."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def append_run_record(runs_jsonl_path: Path, record: RunRecord) -> None:
    """Append a run record to the workflow's runs.jsonl."""

    runs_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    existing = runs_jsonl_path.read_text(encoding="utf-8") if runs_jsonl_path.exists() else ""
    tmp_path = runs_jsonl_path.with_suffix(runs_jsonl_path.suffix + ".tmp")
    tmp_path.write_text(existing + json.dumps(_run_record_to_json(record), sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(runs_jsonl_path)


def load_run_history(runs_jsonl_path: Path) -> list[RunRecord]:
    """Load run history from runs.jsonl."""

    if not runs_jsonl_path.exists():
        return []

    records: list[RunRecord] = []
    with runs_jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            records.append(_run_record_from_json(json.loads(stripped)))
    return records


def detect_promotion_candidates(
    current_fingerprints: list[OverrideFingerprint],
    history: list[RunRecord],
    streak_threshold: int = 3,
) -> list[OverrideFingerprint]:
    """Detect overrides that appear in streak_threshold consecutive runs.

    M7.2: Same override in 3+ consecutive runs → suggest workflow update.
    Walks runs in descending completed_at order. Only counts the current run plus
    preceding completed runs. Runs without the fingerprint break the streak.
    """

    if streak_threshold <= 1:
        return sorted(set(current_fingerprints), key=_fingerprint_sort_key)

    ordered_history = sorted(history, key=lambda record: record.completed_at, reverse=True)
    candidates: list[OverrideFingerprint] = []
    for fingerprint in sorted(set(current_fingerprints), key=_fingerprint_sort_key):
        streak = 1
        for record in ordered_history:
            if record.workflow_id != fingerprint.workflow_id:
                continue
            if fingerprint not in set(record.override_fingerprints):
                break
            streak += 1
            if streak >= streak_threshold:
                candidates.append(fingerprint)
                break
    return candidates


def list_available_workflows(kb_workflows_dir: Path) -> list[dict[str, Any]]:
    """List workflow files in the KB workflows directory with summary metadata."""

    workflows: list[dict[str, Any]] = []
    if not kb_workflows_dir.exists():
        return workflows

    for workflow_path in sorted(kb_workflows_dir.rglob("workflow.md")):
        try:
            workflow = load_workflow(workflow_path)
        except (OSError, ValueError):
            continue
        if validate_workflow(workflow):
            continue
        workflows.append(
            {
                "workflow_id": workflow.get("workflow_id", ""),
                "study_type": workflow.get("study_type", ""),
                "description": workflow.get("description", workflow.get("protocol_identity", "")),
                "path": workflow_path,
            }
        )
    return workflows


def workflow_covers_stage(workflow: dict[str, Any], stage: str) -> bool:
    """Check if a workflow has the required fields for a given stage."""

    required_fields = STAGE_FIELDS.get(stage)
    if required_fields is None:
        return False
    for field in required_fields:
        value = workflow.get(field)
        if field == "reference_images":
            continue
        if value is None or value == "" or value == [] or value == {}:
            return False
    return True


def extract_stage_workflow(workflow: dict[str, Any], stage: str) -> dict[str, Any]:
    """Extract stage-relevant workflow sections for passing to a specialist."""

    fields = STAGE_FIELDS.get(stage)
    if fields is None:
        raise ValueError(f"unknown workflow stage: {stage}")

    stage_workflow = {
        "workflow_id": workflow.get("workflow_id"),
        "study_type": workflow.get("study_type"),
        "stage": stage,
    }
    for field in fields:
        if field in workflow:
            stage_workflow[field] = workflow[field]
    if "field_provenance" in workflow:
        stage_workflow["field_provenance"] = workflow["field_provenance"]
    return stage_workflow


def _run_record_to_json(record: RunRecord) -> dict[str, Any]:
    return {
        "completed_at": record.completed_at,
        "session_id": record.session_id,
        "workflow_id": record.workflow_id,
        "override_fingerprints": [asdict(fingerprint) for fingerprint in record.override_fingerprints],
    }


def _run_record_from_json(payload: dict[str, Any]) -> RunRecord:
    return RunRecord(
        completed_at=str(payload["completed_at"]),
        session_id=str(payload["session_id"]),
        workflow_id=str(payload["workflow_id"]),
        override_fingerprints=[OverrideFingerprint(**item) for item in payload.get("override_fingerprints", [])],
    )


def _fingerprint_sort_key(fingerprint: OverrideFingerprint) -> tuple[str, str, str, str, str]:
    return (
        fingerprint.workflow_id,
        fingerprint.stage,
        fingerprint.field,
        fingerprint.canonical_value,
        fingerprint.override_value,
    )
