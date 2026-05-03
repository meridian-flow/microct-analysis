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
        "explanation_payload",
        "confirmed_assignments",
        "landmark-decision",
        "component-reassignment",
        "threshold-adjustment",
        "next-look-guidance",
    )
    for index, cell in enumerate(cells):
        text = _source_text(cell)
        outputs_text = " ".join(_output_text(output) for output in cell.get("outputs", []))
        combined = f"{text}\n{outputs_text}"
        if any(marker in combined for marker in markers):
            review_cells.append(index)
    return review_cells


def _source_text(cell: dict[str, Any]) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(str(part) for part in source)
    return str(source)


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
