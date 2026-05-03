"""Cheap-agent notebook cleanup helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CleanupPlan:
    """Plan for notebook cleanup."""

    cells_to_keep: list[int]
    cells_to_remove: list[int]
    reason: str


@dataclass(frozen=True)
class DeriveSpec:
    """Specification for what to preserve in a derived notebook."""

    keep_cells: list[int]
    remove_cells: list[int]
    preserve_screenshots: list[str]
    preserve_measurements: bool
    preserve_explanations: bool


def build_derive_spec(cells: list[dict[str, Any]], measurement_artifacts: dict[str, Any] | None = None) -> DeriveSpec:
    """Build a derivation spec that preserves the accepted analysis path.

    M6.1: Produce clean derived notebook without dead ends.
    M6.3: Preserve decision points, explanations, screenshots, measurements.
    """

    remove_cells = identify_dead_ends(cells)
    review_cells = set(identify_review_cells(cells))
    measurement_cells = _measurement_cells(cells, measurement_artifacts)
    explanation_cells = _explanation_cells(cells)
    keep_cells = sorted((set(range(len(cells))) - set(remove_cells)) | review_cells | measurement_cells | explanation_cells)
    screenshots = sorted(_referenced_screenshots(cells[index]) for index in keep_cells)
    return DeriveSpec(
        keep_cells=keep_cells,
        remove_cells=sorted(index for index in remove_cells if index not in review_cells),
        preserve_screenshots=[path for paths in screenshots for path in paths],
        preserve_measurements=bool(measurement_cells or measurement_artifacts),
        preserve_explanations=bool(explanation_cells),
    )


def validate_derived_notebook(cells: list[dict[str, Any]], expected_artifacts: list[str]) -> list[str]:
    """Validate that a derived notebook still references expected durable artifacts.

    Returns expected artifact paths that are not referenced by any cell source or output.
    """

    notebook_text = "\n".join(_cell_text(cell) for cell in cells)
    return [artifact for artifact in expected_artifacts if artifact not in notebook_text]


def identify_dead_ends(cells: list[dict[str, Any]]) -> list[int]:
    """Identify cell indices that are dead-end explorations."""
    review_cells = set(identify_review_cells(cells))
    recoverable_error_cells = _recoverable_error_cells(cells)
    dead_ends: list[int] = []
    markers = ("dead end", "abandoned", "discard", "do not use", "failed attempt")
    for index, cell in enumerate(cells):
        if index in review_cells:
            continue
        cell_type = str(cell.get("cell_type", ""))
        source = _source_text(cell).lower()
        outputs = cell.get("outputs", [])
        has_error = any(isinstance(output, dict) and output.get("output_type") == "error" for output in outputs)
        has_marker = any(marker in source for marker in markers)
        if index in recoverable_error_cells:
            dead_ends.append(index)
        elif has_marker and (cell_type != "code" or not has_error):
            dead_ends.append(index)
    return dead_ends


def identify_review_cells(cells: list[dict[str, Any]]) -> list[int]:
    """Identify cells that document review decisions, screenshots, or explanations."""
    review_cells: list[int] = []
    markers = (
        "capture_screenshot",
        "visualizations/screenshots",
        "screenshot_",
        "explanation_payload",
        "confirmed_assignments",
        "landmark-decision",
        "component-reassignment",
        "threshold-adjustment",
        "next-look-guidance",
        "override",
        "decision point",
    )
    for index, cell in enumerate(cells):
        combined = _cell_text(cell)
        if any(marker in combined for marker in markers):
            review_cells.append(index)
    return review_cells


def _source_text(cell: dict[str, Any]) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(str(part) for part in source)
    return str(source)


def _cell_text(cell: dict[str, Any]) -> str:
    text = _source_text(cell)
    outputs_text = " ".join(_output_text(output) for output in cell.get("outputs", []))
    metadata_text = _stringify(cell.get("metadata", {}))
    return f"{text}\n{outputs_text}\n{metadata_text}"


def _measurement_cells(cells: list[dict[str, Any]], measurement_artifacts: dict[str, Any] | None) -> set[int]:
    artifact_text = _stringify(measurement_artifacts or {})
    markers = ("measurement", "measurements/results.json", "qc_overlays", "results.json")
    return {index for index, cell in enumerate(cells) if any(marker in _cell_text(cell) for marker in markers) or (artifact_text and artifact_text in _cell_text(cell))}


def _explanation_cells(cells: list[dict[str, Any]]) -> set[int]:
    markers = ("explanation_payload", "explain-then-apply", "rationale", "why it addresses")
    return {index for index, cell in enumerate(cells) if any(marker in _cell_text(cell) for marker in markers)}


def _referenced_screenshots(cell: dict[str, Any]) -> list[str]:
    words = _cell_text(cell).replace("'", ' ').replace('"', ' ').replace(")", " ").replace("(", " ").split()
    return [word.strip(",.;:]") for word in words if ".png" in word and ("screenshot" in word or "visualizations/" in word)]


def _recoverable_error_cells(cells: list[dict[str, Any]]) -> set[int]:
    code_indexes = [index for index, cell in enumerate(cells) if cell.get("cell_type") == "code"]
    successful_code_after: set[int] = set()
    seen_success = False

    for index in reversed(code_indexes):
        if seen_success:
            successful_code_after.add(index)
        outputs = cells[index].get("outputs", [])
        has_error = any(isinstance(output, dict) and output.get("output_type") == "error" for output in outputs)
        if not has_error:
            seen_success = True

    return {
        index
        for index in code_indexes
        if any(
            isinstance(output, dict) and output.get("output_type") == "error"
            for output in cells[index].get("outputs", [])
        )
        and index in successful_code_after
    }


def _output_text(output: Any) -> str:
    if not isinstance(output, dict):
        return str(output)
    chunks: list[str] = []
    for key in ("text", "ename", "evalue"):
        value = output.get(key)
        if isinstance(value, list):
            chunks.extend(str(part) for part in value)
        elif value is not None:
            chunks.append(str(value))
    data = output.get("data")
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                chunks.extend(str(part) for part in value)
            else:
                chunks.append(str(value))
    return " ".join(chunks)


def _stringify(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_stringify(item)}" for key, item in sorted(value.items()))
    if isinstance(value, list):
        return " ".join(_stringify(item) for item in value)
    return "" if value is None else str(value)
