"""Thresholding helpers for micro-CT volumes."""

from __future__ import annotations

import numpy as np


def binary_mask(volume: np.ndarray, lower_bound: int, upper_bound: int | None = None) -> np.ndarray:
    """Create a boolean mask for values within the requested intensity range."""

    mask = np.asarray(volume) >= lower_bound
    if upper_bound is not None:
        mask &= np.asarray(volume) <= upper_bound
    return mask.astype(bool, copy=False)
