"""Orientation helpers for SOP-matched micro-CT measurements."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import affine_transform


def _validate_3d(volume: np.ndarray, spacing: tuple[float, ...]) -> np.ndarray:
    source = np.asarray(volume)
    if source.ndim != 3:
        raise ValueError("volume must be a 3D array")
    if len(spacing) != 3:
        raise ValueError("spacing must contain three values in (z, y, x) order")
    if any(axis_spacing <= 0 for axis_spacing in spacing):
        raise ValueError("spacing values must be positive")
    return source


def center_volume(
    volume: np.ndarray, spacing: tuple[float, ...]
) -> tuple[np.ndarray, np.ndarray]:
    """Compute bounding-box center translation for non-zero voxels.

    SOP: ``translate = -1 × (LL + UR) / 2``. Coordinates are computed in
    physical space using ``spacing`` in ``(z, y, x)`` order.

    Returns:
        ``(translation_vector, center_physical)``. ``translation_vector`` is the
        physical vector to add to coordinates to center the object on origin.
    """

    source = _validate_3d(volume, spacing)
    nonzero = np.argwhere(source != 0)
    if nonzero.size == 0:
        raise ValueError("volume must contain at least one non-zero voxel")

    spacing_array = np.asarray(spacing, dtype=np.float64)
    lower_left = nonzero.min(axis=0).astype(np.float64) * spacing_array
    upper_right = nonzero.max(axis=0).astype(np.float64) * spacing_array
    center_physical = (lower_left + upper_right) / 2.0
    translation_vector = -center_physical
    return translation_vector, center_physical


def pca_orient(
    label_mask: np.ndarray,
    intensity: np.ndarray,
    spacing: tuple[float, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Orient a tibia label/intensity pair using PCA in physical coordinates.

    The label mask is resampled with nearest-neighbor interpolation and the
    intensity volume with linear interpolation. Voxel spacing is preserved by
    keeping the output shape equal to the input shape and rotating in physical
    coordinate space.
    """

    labels = _validate_3d(label_mask, spacing)
    intensities = _validate_3d(intensity, spacing)
    if labels.shape != intensities.shape:
        raise ValueError("label_mask and intensity must have the same shape")

    _, center_physical = center_volume(labels, spacing)
    voxel_indices = np.argwhere(labels != 0).astype(np.float64)
    if voxel_indices.shape[0] < 3:
        raise ValueError("label_mask must contain at least three non-zero voxels")

    spacing_array = np.asarray(spacing, dtype=np.float64)
    physical_positions = voxel_indices * spacing_array
    centered_positions = physical_positions - center_physical

    covariance = np.cov(centered_positions, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    principal_axes = eigenvectors[:, np.argsort(eigenvalues)[::-1]]

    # Stabilize signs so equivalent masks do not flip arbitrarily.
    for axis_index in range(principal_axes.shape[1]):
        axis = principal_axes[:, axis_index]
        largest_component = np.argmax(np.abs(axis))
        if axis[largest_component] < 0:
            principal_axes[:, axis_index] = -axis

    # Target axis order is array-coordinate physical (z, y, x): PC1 -> z/SI,
    # PC2 -> x/ML, PC3 -> y/AP to complete a right-handed orthonormal basis.
    target_axes = np.column_stack(
        (
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([0.0, 1.0, 0.0]),
        )
    )
    rotation = target_axes @ principal_axes.T
    if np.linalg.det(rotation) < 0:
        target_axes[:, 2] *= -1
        rotation = target_axes @ principal_axes.T

    oriented_label = apply_rotation(labels, rotation, order=0, spacing=spacing)
    oriented_intensity = apply_rotation(intensities, rotation, order=1, spacing=spacing)
    return oriented_label.astype(labels.dtype, copy=False), oriented_intensity, rotation


def apply_rotation(
    volume: np.ndarray,
    rotation: np.ndarray,
    order: int,
    spacing: tuple[float, ...],
) -> np.ndarray:
    """Apply a rigid rotation while preserving shape and voxel spacing.

    ``rotation`` is a 3×3 physical-space matrix. The center of rotation is the
    volume center. The returned array has the same shape as ``volume``.
    """

    source = _validate_3d(volume, spacing)
    rotation_array = np.asarray(rotation, dtype=np.float64)
    if rotation_array.shape != (3, 3):
        raise ValueError("rotation must be a 3x3 matrix")

    spacing_array = np.asarray(spacing, dtype=np.float64)
    scale = np.diag(spacing_array)
    inverse_scale = np.diag(1.0 / spacing_array)
    center_index = (np.asarray(source.shape, dtype=np.float64) - 1.0) / 2.0
    center_physical = center_index * spacing_array

    # scipy maps output indices to input indices. In physical coordinates:
    # input = R.T @ (output - center) + center.
    matrix = inverse_scale @ rotation_array.T @ scale
    offset_physical = center_physical - rotation_array.T @ center_physical
    offset = inverse_scale @ offset_physical

    return affine_transform(
        source,
        matrix=matrix,
        offset=offset,
        output_shape=source.shape,
        order=order,
        mode="constant",
        cval=0,
        prefilter=order > 1,
    )
