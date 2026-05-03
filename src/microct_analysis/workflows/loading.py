"""Workflow file loading and matching."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from microct_analysis.workflows.schema import FieldProvenance, extract_field_provenance, parse_frontmatter

REQUIRED_WORKFLOW_FIELDS = (
    "workflow_id",
    "thresholds",
    "landmarks",
    "roi_definitions",
    "measurements",
    "orientation_protocol",
    "acceptance_checks",
    "sources",
)


def find_workflow(workflow_name: str, kb_workflows_dir: Path) -> Path | None:
    """Find a workflow file by name or study type in the KB workflows directory."""

    exact = kb_workflows_dir / workflow_name / "workflow.md"
    if exact.is_file():
        return exact

    direct = kb_workflows_dir / f"{workflow_name}.md"
    if direct.is_file():
        return direct

    for workflow_path in sorted(kb_workflows_dir.rglob("workflow.md")):
        try:
            data = load_workflow(workflow_path)
        except (OSError, ValueError):
            continue
        if data.get("workflow_id") == workflow_name or data.get("study_type") == workflow_name:
            return workflow_path
    return None


def load_workflow(workflow_path: Path) -> dict[str, Any]:
    """Load a markdown workflow file and return its YAML frontmatter mapping."""

    frontmatter, _body = parse_frontmatter(workflow_path.read_text(encoding="utf-8"))
    return frontmatter


def validate_workflow(workflow_data: dict[str, Any]) -> list[str]:
    """Validate that a workflow dict has all required executable sections."""

    missing: list[str] = []
    for field in REQUIRED_WORKFLOW_FIELDS:
        value = workflow_data.get(field)
        if value is None or value == "" or value == [] or value == {}:
            missing.append(field)
    return missing


def get_uncertain_fields(workflow: dict[str, Any]) -> list[tuple[str, FieldProvenance]]:
    """Return provenance fields requiring user review before first workflow use."""

    uncertain: list[tuple[str, FieldProvenance]] = []
    for field, provenance in extract_field_provenance(workflow).items():
        if provenance.confidence in {"medium", "low"} or provenance.source == "inferred":
            uncertain.append((field, provenance))
    return uncertain
