"""Trabecular ROI metric primitives (BV/TV, Tb.Th, Tb.N, Tb.Sp)."""

from __future__ import annotations

import math

import numpy as np

from .models import MeasurementResult, MeasurementSpec


def compute_bv_tv(bone_mask: np.ndarray, roi_mask: np.ndarray) -> float:
    """Compute bone volume fraction (BV/TV)."""

    roi = np.asarray(roi_mask, dtype=bool)
    total = int(np.count_nonzero(roi))
    if total == 0:
        raise ValueError("ROI mask is empty")
    bone = np.asarray(bone_mask, dtype=bool) & roi
    return float(np.count_nonzero(bone) / total)


def compute_tb_th(bone_mask: np.ndarray, spacing: tuple[float, ...]) -> float:
    """Compute mean trabecular thickness using distance transform."""

    mask = np.asarray(bone_mask, dtype=bool)
    values = _distance_transform(mask, spacing)[mask] * 2.0
    return float(values.mean()) if values.size else 0.0


def compute_tb_sp(bone_mask: np.ndarray, spacing: tuple[float, ...]) -> float:
    """Compute mean trabecular separation using distance transform on inverted mask."""

    mask = ~np.asarray(bone_mask, dtype=bool)
    values = _distance_transform(mask, spacing)[mask] * 2.0
    return float(values.mean()) if values.size else 0.0


def compute_tb_n(bv_tv: float, tb_th: float) -> float:
    """Compute trabecular number: BV/TV / Tb.Th."""

    return 0.0 if tb_th == 0 else float(bv_tv / tb_th)


def compute_trabecular_metrics(
    spec: MeasurementSpec,
    bone_mask: np.ndarray,
    roi_mask: np.ndarray,
    spacing: tuple[float, ...],
    threshold: float,
) -> list[MeasurementResult]:
    """Compute all trabecular metrics for a specified ROI."""

    roi = np.asarray(roi_mask, dtype=bool)
    bone = np.asarray(bone_mask, dtype=bool) & roi
    bv_tv = compute_bv_tv(bone, roi)
    tb_th = compute_tb_th(bone, spacing)
    tb_sp = compute_tb_sp(bone, spacing)
    tb_n = compute_tb_n(bv_tv, tb_th)
    values = {"BV/TV": (bv_tv, "dimensionless"), "Tb.Th": (tb_th, "mm"), "Tb.N": (tb_n, "1/mm"), "Tb.Sp": (tb_sp, "mm")}
    return [
        MeasurementResult(
            f"{spec.name}_{metric}",
            value,
            unit,
            spec,
            {"roi": spec.roi, "threshold": threshold, "spacing": list(spacing), "algorithm": spec.algorithm},
            f"measurements/qc/{spec.name}_{metric}.json",
        )
        for metric, (value, unit) in values.items()
    ]


def _distance_transform(mask: np.ndarray, spacing: tuple[float, ...]) -> np.ndarray:
    try:
        from scipy.ndimage import distance_transform_edt  # type: ignore[import-untyped]

        return np.asarray(distance_transform_edt(mask, sampling=spacing), dtype=float)
    except Exception:
        return _brute_distance_transform(mask, spacing)


def _brute_distance_transform(mask: np.ndarray, spacing: tuple[float, ...]) -> np.ndarray:
    true_coords = np.argwhere(mask)
    false_coords = np.argwhere(~mask)
    result = np.zeros(mask.shape, dtype=float)
    if true_coords.size == 0 or false_coords.size == 0:
        return result
    scale = np.asarray([float(spacing[index]) if index < len(spacing) else 1.0 for index in range(mask.ndim)])
    for coord in true_coords:
        deltas = (false_coords - coord) * scale
        distances = np.sqrt(np.sum(deltas * deltas, axis=1))
        result[tuple(coord)] = float(distances.min()) if distances.size else math.inf
    return result
