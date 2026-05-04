"""Volume resampling helpers for micro-CT processing."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import zoom


def to_isotropic(
    volume: np.ndarray,
    spacing: tuple[float, ...],
    target_spacing: float | None = None,
    order: int = 1,
) -> tuple[np.ndarray, tuple[float, ...]]:
    """Resample a 3D volume to isotropic voxel spacing.

    Args:
        volume: 3D array.
        spacing: Source voxel spacing in ``(z, y, x)`` order, in mm.
        target_spacing: Target isotropic spacing. If omitted, the smallest
            source spacing is used so the highest input resolution is preserved.
        order: Interpolation order passed to ``scipy.ndimage.zoom``. Use
            ``0`` for labels and ``1`` for intensity volumes.

    Returns:
        ``(resampled_volume, new_spacing)`` where ``new_spacing`` repeats the
        isotropic target spacing for each input dimension.
    """

    if len(spacing) != 3:
        raise ValueError("spacing must contain three values in (z, y, x) order")
    if any(axis_spacing <= 0 for axis_spacing in spacing):
        raise ValueError("spacing values must be positive")

    resolved_target = min(spacing) if target_spacing is None else target_spacing
    if resolved_target <= 0:
        raise ValueError("target_spacing must be positive")

    source = np.asarray(volume)
    if source.ndim != 3:
        raise ValueError("volume must be a 3D array")

    zoom_factors = tuple(axis_spacing / resolved_target for axis_spacing in spacing)
    resampled = np.asarray(zoom(source, zoom=zoom_factors, order=order))
    new_spacing = (resolved_target, resolved_target, resolved_target)
    return resampled, new_spacing
