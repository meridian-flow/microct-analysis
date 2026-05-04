"""Workflow file YAML frontmatter schema parsing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

LANDMARK_DOMAINS = {"femoral_3d_surface", "tibial_2d_slice"}


@dataclass(frozen=True)
class FieldProvenance:
    """Source and confidence metadata for an executable workflow field."""

    source: str
    confidence: str
    note: str = ""


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
    return [_normalize_landmark(item) for item in landmarks if isinstance(item, dict)] if isinstance(landmarks, list) else []


def _normalize_landmark(item: dict[str, Any]) -> dict[str, Any]:
    """Return a landmark mapping with validated optional domain metadata."""

    domain = item.get("domain")
    if domain is not None and str(domain) not in LANDMARK_DOMAINS:
        name = item.get("id") or item.get("name") or "<unknown>"
        raise ValueError(f"unsupported landmark domain for {name}: {domain}")
    return item


def extract_roi_definitions(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract ROI definitions from parsed workflow data."""

    rois = workflow.get("roi_definitions", [])
    return [item for item in rois if isinstance(item, dict)] if isinstance(rois, list) else []


def extract_measurements(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract measurement definitions from parsed workflow data."""

    measurements = workflow.get("measurements", [])
    return [item for item in measurements if isinstance(item, dict)] if isinstance(measurements, list) else []


def extract_orientation_protocol(workflow: dict[str, Any]) -> dict[str, Any]:
    """Extract the orientation protocol from parsed workflow data."""

    protocol = workflow.get("orientation_protocol", {})
    return protocol if isinstance(protocol, dict) else {}


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


def extract_sources(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract source citation entries from parsed workflow data."""

    sources = workflow.get("sources", [])
    return [item for item in sources if isinstance(item, dict)] if isinstance(sources, list) else []


def extract_field_provenance(workflow: dict[str, Any]) -> dict[str, FieldProvenance]:
    """Extract field_provenance section into typed objects."""

    provenance = workflow.get("field_provenance", {})
    if not isinstance(provenance, dict):
        return {}

    typed: dict[str, FieldProvenance] = {}
    for field, data in provenance.items():
        if not isinstance(field, str) or not isinstance(data, dict):
            continue
        source = data.get("source", "")
        confidence = data.get("confidence", "")
        note = data.get("note", "")
        typed[field] = FieldProvenance(
            source=str(source),
            confidence=str(confidence),
            note=str(note) if note is not None else "",
        )
    return typed
