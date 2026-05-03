"""Confidence gating for the semi-HITL analysis loop."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(Enum):
    """Stage-boundary confidence levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class AcceptanceCheckResult:
    """Result of evaluating one acceptance check from a workflow file."""

    check_name: str
    rule: str
    passed: bool
    confidence_if_violated: ConfidenceLevel
    detail: str


@dataclass(frozen=True)
class ConfidenceAssessment:
    """Result of a confidence assessment at a stage boundary."""

    level: ConfidenceLevel
    evidence: str
    observations: list[str]
    acceptance_check_results: list[AcceptanceCheckResult]


def assess_confidence(
    acceptance_results: list[AcceptanceCheckResult],
    visual_observations: list[str] | None = None,
) -> ConfidenceAssessment:
    """Compute overall confidence from acceptance checks and visual observations."""

    observations = list(visual_observations or [])
    failed = [result for result in acceptance_results if not result.passed]

    if any(result.confidence_if_violated is ConfidenceLevel.LOW for result in failed):
        level = ConfidenceLevel.LOW
    elif any(result.confidence_if_violated is ConfidenceLevel.MEDIUM for result in failed):
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.HIGH

    evidence_parts: list[str] = []
    if failed:
        evidence_parts.extend(f"{result.check_name}: {result.detail}" for result in failed)
    else:
        evidence_parts.append("All acceptance checks passed.")

    if observations:
        evidence_parts.append("Visual observations: " + "; ".join(observations))
    else:
        evidence_parts.append("No concerning visual observations recorded.")

    return ConfidenceAssessment(
        level=level,
        evidence=" ".join(evidence_parts),
        observations=observations,
        acceptance_check_results=list(acceptance_results),
    )
