"""Core processing-layer data contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class Thresholds:
    """SCANCO-equivalent processing thresholds."""

    bone_soft_tissue: int = 220
    subchondral_cortical: int = 270
    surface_3d: int = 320
    marrow_bone: int = 270


@dataclass(frozen=True)
class ScanVolume:
    """Loaded scan data with physical spacing and provenance."""

    data: NDArray[np.float32]
    spacing: tuple[float, ...]
    affine: NDArray[np.float64]
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LabelVolume:
    """Discrete labels with 0 reserved for background."""

    data: NDArray[np.uint8] | NDArray[np.uint16]
    spacing: tuple[float, ...]
    label_map: dict[str, int]


@dataclass(frozen=True)
class SegmentationResult:
    """Result of assigning segmented structures to labels."""

    labels: LabelVolume
    structure_assignments: dict[str, int]
    threshold_observations: list[str]
    confidence: Confidence
