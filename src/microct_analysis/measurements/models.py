"""Typed measurement models and specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MeasurementSpec:
    """Compiled measurement specification from workflow YAML."""

    name: str
    kind: str
    domain: str | None = None
    frame: str | None = None
    projection: str | None = None
    points: list[str] | None = None
    boundaries: list[str] | None = None
    slice_selection: str | None = None
    slice_thickness_mm: float | None = None
    numerator: str | None = None
    denominator: str | None = None
    roi: str | None = None
    algorithm: str | None = None
    unit: str = "mm"
    acceptance: dict[str, Any] | None = None


@dataclass(frozen=True)
class MeasurementResult:
    """Result of computing one measurement."""

    name: str
    value: float
    unit: str
    spec: MeasurementSpec
    inputs: dict[str, Any] = field(default_factory=dict)
    qc_evidence: str | None = None


@dataclass(frozen=True)
class OverrideRecord:
    """Per-run deviation from canonical workflow values."""

    stage: str
    field: str
    canonical_value: Any
    override_value: Any
    rationale: str
    confidence: str
    approver: str = "agent"
