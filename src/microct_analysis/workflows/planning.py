"""Workflow planning helpers shared by analyst and workflow-creator."""

from __future__ import annotations

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
