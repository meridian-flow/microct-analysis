"""Seeded segmentation primitives for micro-CT volumes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

import numpy as np
from scipy import ndimage
from skimage.segmentation import watershed


def seed_from_region(
    filtered: np.ndarray,
    mask: np.ndarray,
    label_assignments: Mapping[str, Sequence[int]],
) -> np.ndarray:
    """Create marker seeds by flood filling masked components from centroids.

    Each assignment receives a stable 1-based marker ID in insertion order.  A
    seed point must lie inside ``mask``; the marker is expanded to the connected
    masked component containing that point, approximating Amira's Magic Wand / All
    Slices behavior.
    """

    volume_shape = np.asarray(filtered).shape
    mask_array = np.asarray(mask, dtype=bool)
    if mask_array.shape != volume_shape:
        raise ValueError("mask shape must match filtered volume shape")

    markers = np.zeros(volume_shape, dtype=np.int32)
    components, _ = cast(tuple[np.ndarray, int], ndimage.label(mask_array))
    for label_id, seed in enumerate(label_assignments.values(), start=1):
        if len(seed) != len(volume_shape):
            raise ValueError("seed dimensionality must match volume")
        seed_index = tuple(int(coord) for coord in seed[: len(volume_shape)])
        if any(coord < 0 or coord >= limit for coord, limit in zip(seed_index, volume_shape, strict=True)):
            raise ValueError(f"seed {seed_index} is outside volume bounds")
        component_id = int(components[seed_index])
        if component_id == 0:
            raise ValueError(f"seed {seed_index} is outside mask")
        markers[components == component_id] = label_id
    return markers


def watershed_segment(filtered: np.ndarray, seeds: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Run marker-based watershed inside ``mask`` on raw intensity values."""

    filtered_array = np.asarray(filtered)
    seeds_array = np.asarray(seeds, dtype=np.int32)
    mask_array = np.asarray(mask, dtype=bool)
    if filtered_array.shape != seeds_array.shape or filtered_array.shape != mask_array.shape:
        raise ValueError("filtered, seeds, and mask must have matching shapes")
    return watershed(filtered_array, markers=seeds_array, mask=mask_array)


def extract_label(grown: np.ndarray, label_id: int) -> np.ndarray:
    """Extract one integer label as a boolean mask."""

    return np.asarray(grown) == label_id
