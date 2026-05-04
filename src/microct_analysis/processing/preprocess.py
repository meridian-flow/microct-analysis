"""Preprocessing filters for micro-CT volumes."""

from __future__ import annotations

import numpy as np
from scipy import ndimage


def median_filter(volume: np.ndarray, *, iterations: int = 3, size: int = 3) -> np.ndarray:
    """Apply an iterative XY-plane median filter slice-by-slice.

    The Amira SOP uses a 3-iteration median filter in the XY plane.  The
    first axis is treated as slice/depth, so no median window spans adjacent
    slices.
    """

    if iterations < 0:
        raise ValueError("iterations must be non-negative")
    if size < 1:
        raise ValueError("size must be positive")

    filtered = np.asarray(volume).copy()
    for _ in range(iterations):
        filtered = ndimage.median_filter(filtered, size=(1, size, size))
    return filtered
