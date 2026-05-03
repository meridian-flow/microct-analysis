"""Workflow file YAML frontmatter schema parsing."""

from __future__ import annotations

from typing import Any

import yaml


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content."""

    if not content.startswith("---"):
        raise ValueError("workflow file is missing YAML frontmatter")

    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("workflow file is missing YAML frontmatter")

    end_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        raise ValueError("workflow YAML frontmatter is not closed")

    yaml_text = "".join(lines[1:end_index])
    body = "".join(lines[end_index + 1 :])
    try:
        parsed = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"workflow YAML frontmatter is malformed: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("workflow YAML frontmatter must be a mapping")

    return parsed, body


def extract_thresholds(workflow: dict[str, Any]) -> dict[str, Any]:
    """Extract threshold definitions from parsed workflow data."""

    thresholds = workflow.get("thresholds", {})
    return thresholds if isinstance(thresholds, dict) else {}


def extract_landmarks(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract landmark definitions from parsed workflow data."""

    landmarks = workflow.get("landmarks", [])
    return [item for item in landmarks if isinstance(item, dict)] if isinstance(landmarks, list) else []


def extract_measurements(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract measurement definitions from parsed workflow data."""

    measurements = workflow.get("measurements", [])
    return [item for item in measurements if isinstance(item, dict)] if isinstance(measurements, list) else []


def extract_acceptance_checks(workflow: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Extract acceptance checks grouped by stage."""

    checks = workflow.get("acceptance_checks", {})
    if not isinstance(checks, dict):
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for stage, stage_checks in checks.items():
        if isinstance(stage, str) and isinstance(stage_checks, list):
            grouped[stage] = [item for item in stage_checks if isinstance(item, dict)]
    return grouped


def extract_reference_images(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract reference image entries from parsed workflow data."""

    references = workflow.get("reference_images", [])
    return [item for item in references if isinstance(item, dict)] if isinstance(references, list) else []
