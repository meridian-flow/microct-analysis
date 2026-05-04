"""Morphology helpers for SOP growth-plate separation."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import binary_closing as scipy_binary_closing
from scipy.ndimage import binary_erosion

from microct_analysis.processing.types import Thresholds

BoolArray = NDArray[np.bool_]


def morphological_closing(binary: np.ndarray, structure: np.ndarray | None = None) -> BoolArray:
    """Close gaps in a binary cortical shell.

    Mirrors the SOP's Cortical & Trabecular Isolation recipe closing step.
    """
    return scipy_binary_closing(np.asarray(binary, dtype=bool), structure=structure).astype(bool, copy=False)


def shrink_interior(label_closing: np.ndarray, iterations: int = 3) -> BoolArray:
    """Shrink the closed label interior by repeated binary erosion.

    The SOP applies Shrink three times to the selected inside part of bone.
    """
    if iterations < 0:
        msg = "iterations must be non-negative"
        raise ValueError(msg)
    closed = np.asarray(label_closing, dtype=bool)
    if iterations == 0:
        return closed.copy()
    return binary_erosion(closed, iterations=iterations).astype(bool, copy=False)


def lock_exterior_threshold(
    filtered: np.ndarray,
    interior_mask: np.ndarray,
    lower_bound: int = 1000,
    upper_bound: int = 1500,
) -> tuple[BoolArray, BoolArray]:
    """Threshold only unlocked interior voxels into subchondral bone and marrow."""
    if lower_bound > upper_bound:
        msg = "lower_bound must be <= upper_bound"
        raise ValueError(msg)

    intensity = np.asarray(filtered)
    interior = np.asarray(interior_mask, dtype=bool)
    if intensity.shape != interior.shape:
        msg = "filtered and interior_mask must have the same shape"
        raise ValueError(msg)

    subchondral_bone = interior & (intensity >= lower_bound) & (intensity <= upper_bound)
    marrow = interior & ~subchondral_bone
    return subchondral_bone.astype(bool, copy=False), marrow.astype(bool, copy=False)


def crop_growth_plate_region(label: np.ndarray, start_slice: int, n_slices: int = 22) -> BoolArray:
    """Crop a z-slice slab beginning at the growth-plate boundary."""
    if start_slice < 0:
        msg = "start_slice must be non-negative"
        raise ValueError(msg)
    if n_slices <= 0:
        msg = "n_slices must be positive"
        raise ValueError(msg)

    binary = np.asarray(label, dtype=bool)
    if binary.ndim < 1:
        msg = "label must have at least one dimension"
        raise ValueError(msg)
    stop_slice = min(start_slice + n_slices, binary.shape[0])
    return binary[start_slice:stop_slice].copy()


def isolate_trabecular_roi(
    tibia_label: np.ndarray,
    intensity: np.ndarray,
    thresholds: Thresholds,
    compartment: str,
) -> BoolArray:
    """Run the SOP trabecular-isolation morphology pipeline.

    ``compartment`` accepts ``"total"``. The medial/lateral split is a manual
    operator decision in the SOP, so callers must provide that boundary outside
    this helper rather than relying on an invented anatomical split.
    """
    normalized_compartment = compartment.lower()
    if normalized_compartment not in {"medial", "lateral", "total"}:
        msg = "compartment must be 'medial', 'lateral', or 'total'"
        raise ValueError(msg)
    if normalized_compartment in {"medial", "lateral"}:
        msg = (
            'Medial/lateral compartment split requires operator-provided boundary mask. '
            'Pass compartment="total" or provide a boundary_mask argument.'
        )
        raise ValueError(msg)

    label = np.asarray(tibia_label, dtype=bool)
    if label.shape != np.asarray(intensity).shape:
        msg = "tibia_label and intensity must have the same shape"
        raise ValueError(msg)

    closed = morphological_closing(label)
    interior = shrink_interior(closed, iterations=3)
    subchondral_bone, _marrow = lock_exterior_threshold(intensity, interior, lower_bound=thresholds.marrow_bone)

    occupied_slices = np.flatnonzero(np.any(subchondral_bone, axis=tuple(range(1, subchondral_bone.ndim))))
    start_slice = int(occupied_slices[0]) if occupied_slices.size else 0
    return crop_growth_plate_region(subchondral_bone, start_slice=start_slice, n_slices=22)
