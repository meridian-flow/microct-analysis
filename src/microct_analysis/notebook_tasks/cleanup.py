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
    dead_ends: list[int] = []
    markers = ("dead end", "abandoned", "discard", "do not use", "failed attempt")
    for index, cell in enumerate(cells):
        source = _source_text(cell).lower()
        outputs = cell.get("outputs", [])
        has_error = any(isinstance(output, dict) and output.get("output_type") == "error" for output in outputs)
        if any(marker in source for marker in markers) or has_error:
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
