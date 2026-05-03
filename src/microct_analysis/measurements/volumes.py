"""Labeled volume measurement primitives."""

from __future__ import annotations

import numpy as np

from .models import MeasurementResult, MeasurementSpec


def compute_labeled_volume(
    spec: MeasurementSpec, labels: np.ndarray, label_index: int, spacing: tuple[float, ...]
) -> MeasurementResult:
    """Compute volume of a labeled structure from voxel count × voxel volume."""

    voxel_count = int(np.count_nonzero(labels == label_index))
    voxel_volume = float(np.prod(np.asarray(spacing, dtype=float)))
    return MeasurementResult(
        spec.name,
        voxel_count * voxel_volume,
        spec.unit,
        spec,
        {"label_index": label_index, "voxel_count": voxel_count, "spacing": list(spacing)},
        f"measurements/qc/{spec.name}.json",
    )
