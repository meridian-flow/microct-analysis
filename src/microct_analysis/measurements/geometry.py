"""Geometric distance, ratio, and slice-count measurement primitives."""

from __future__ import annotations

import math
from typing import Any

from .models import MeasurementResult, MeasurementSpec


def compute_distance(spec: MeasurementSpec, landmarks: dict[str, Any], spacing: tuple[float, ...]) -> MeasurementResult:
    """Compute Euclidean distance between two landmark points."""

    if not spec.points or len(spec.points) != 2:
        raise ValueError(f"distance measurement {spec.name} requires exactly two points")
    first_name, second_name = spec.points
    first = _point(landmarks, first_name)
    second = _point(landmarks, second_name)
    value = math.sqrt(sum(((second[i] - first[i]) * _axis_spacing(spacing, i)) ** 2 for i in range(len(first))))
    return MeasurementResult(spec.name, value, spec.unit, spec, {"points": {first_name: first, second_name: second}, "spacing": list(spacing)}, f"measurements/qc/{spec.name}.json")


def compute_ratio(spec: MeasurementSpec, component_results: dict[str, MeasurementResult]) -> MeasurementResult:
    """Compute ratio from two component measurements."""

    if not spec.numerator or not spec.denominator:
        raise ValueError(f"ratio measurement {spec.name} requires numerator and denominator")
    numerator = component_results[spec.numerator]
    denominator = component_results[spec.denominator]
    if denominator.value == 0:
        raise ValueError(f"ratio measurement {spec.name} denominator is zero")
    return MeasurementResult(spec.name, numerator.value / denominator.value, spec.unit, spec, {"numerator": spec.numerator, "denominator": spec.denominator}, f"measurements/qc/{spec.name}.json")


def compute_slice_count(spec: MeasurementSpec, landmarks: dict[str, Any], spacing: tuple[float, ...]) -> MeasurementResult:
    """Compute distance from slice count × slice thickness."""

    if not spec.boundaries or len(spec.boundaries) != 2:
        raise ValueError(f"slice-count measurement {spec.name} requires exactly two boundaries")
    start_name, end_name = spec.boundaries
    start = _point(landmarks, start_name)
    end = _point(landmarks, end_name)
    axis = max(range(len(start)), key=lambda index: abs(end[index] - start[index]))
    value = abs(end[axis] - start[axis]) * _axis_spacing(spacing, axis)
    return MeasurementResult(spec.name, value, spec.unit, spec, {"boundaries": {start_name: start, end_name: end}, "axis": axis, "spacing": list(spacing)}, f"measurements/qc/{spec.name}.json")


def _point(landmarks: dict[str, Any], name: str) -> tuple[float, ...]:
    raw = landmarks.get(name)
    if raw is None and "landmarks" in landmarks:
        for item in landmarks["landmarks"]:
            if isinstance(item, dict) and item.get("id") == name:
                raw = item.get("physical") or item.get("voxel")
                break
    if raw is None:
        raise KeyError(f"missing landmark {name!r}")
    values = list(raw)
    if not values:
        raise ValueError(f"landmark {name!r} is empty")
    return tuple(float(value) for value in values)


def _axis_spacing(spacing: tuple[float, ...], axis: int) -> float:
    return float(spacing[axis]) if axis < len(spacing) else 1.0
