"""Histogram-based calibration and threshold defaults."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.signal import find_peaks

from microct_analysis.processing.types import Thresholds


def analyze_histogram(volume: np.ndarray) -> dict[str, Any]:
    """Detect air, soft-tissue, and bone peaks in an intensity histogram."""

    values = np.asarray(volume, dtype=np.float64).ravel()
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"air_peak": None, "soft_tissue_peak": None, "bone_peak": None, "peaks": []}

    counts, edges = np.histogram(values, bins=256)
    centers = (edges[:-1] + edges[1:]) / 2.0
    if counts.max() == 0:
        return {"air_peak": None, "soft_tissue_peak": None, "bone_peak": None, "peaks": []}

    normalized = counts / counts.max()
    peak_indices, properties = find_peaks(normalized, prominence=0.01)
    peaks = sorted(float(centers[index]) for index in peak_indices)

    return {
        "air_peak": peaks[0] if len(peaks) > 0 else None,
        "soft_tissue_peak": peaks[1] if len(peaks) > 1 else None,
        "bone_peak": peaks[-1] if len(peaks) > 0 else None,
        "peaks": peaks,
        "histogram": {"counts": counts.tolist(), "bin_centers": centers.tolist()},
        "prominences": properties.get("prominences", np.array([], dtype=float)).tolist(),
    }


def derive_thresholds(volume: np.ndarray, scanner: str = "scanco") -> Thresholds:
    """Derive processing thresholds, using fixed SCANCO defaults when requested."""

    if scanner.lower() == "scanco":
        return Thresholds()

    observations = analyze_histogram(volume)
    soft = observations.get("soft_tissue_peak")
    bone = observations.get("bone_peak")
    if soft is None or bone is None or bone <= soft:
        return Thresholds()

    bone_soft_tissue = int(round((float(soft) + float(bone)) / 2.0))
    subchondral_cortical = int(round(float(bone) * 0.9 + bone_soft_tissue * 0.1))
    surface_3d = int(round(float(bone) * 1.05))
    return Thresholds(
        bone_soft_tissue=bone_soft_tissue,
        subchondral_cortical=max(subchondral_cortical, bone_soft_tissue),
        surface_3d=max(surface_3d, subchondral_cortical),
        marrow_bone=max(subchondral_cortical, bone_soft_tissue),
    )
