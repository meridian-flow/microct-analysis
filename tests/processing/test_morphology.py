from __future__ import annotations

import numpy as np

from microct_analysis.processing.morphology import (
    crop_growth_plate_region,
    isolate_trabecular_roi,
    lock_exterior_threshold,
    morphological_closing,
    shrink_interior,
)
from microct_analysis.processing.types import Thresholds


def _sphere(shape: tuple[int, int, int], radius: float) -> np.ndarray:
    z, y, x = np.indices(shape)
    center = (np.array(shape) - 1) / 2
    distance = np.sqrt((z - center[0]) ** 2 + (y - center[1]) ** 2 + (x - center[2]) ** 2)
    return distance <= radius


def test_morphological_closing_closes_synthetic_hollow_sphere_gap() -> None:
    sphere = _sphere((9, 9, 9), radius=3.0)
    hollow = sphere & ~_sphere((9, 9, 9), radius=1.2)
    hollow[4, 4, 3] = False

    closed = morphological_closing(hollow, structure=np.ones((3, 3, 3), dtype=bool))

    assert closed[4, 4, 3]
    assert closed.sum() >= hollow.sum()


def test_shrink_interior_reduces_interior_region() -> None:
    label = np.ones((7, 7, 7), dtype=bool)

    shrunk = shrink_interior(label, iterations=2)

    assert shrunk.sum() < label.sum()
    assert shrunk[3, 3, 3]
    assert not shrunk[0, 3, 3]


def test_lock_exterior_threshold_classifies_only_interior_voxels() -> None:
    filtered = np.array([[[900, 1200], [1600, 1300]]])
    interior = np.array([[[True, True], [True, False]]])

    subchondral, marrow = lock_exterior_threshold(filtered, interior, lower_bound=1000, upper_bound=1500)

    np.testing.assert_array_equal(subchondral, np.array([[[False, True], [False, False]]]))
    np.testing.assert_array_equal(marrow, np.array([[[True, False], [True, False]]]))


def test_crop_growth_plate_region_extracts_slice_range() -> None:
    label = np.zeros((10, 3, 3), dtype=bool)
    label[3:8] = True

    cropped = crop_growth_plate_region(label, start_slice=3, n_slices=4)

    assert cropped.shape == (4, 3, 3)
    assert cropped.all()


def test_isolate_trabecular_roi_runs_full_pipeline_for_total_compartment() -> None:
    tibia = np.zeros((30, 15, 15), dtype=bool)
    tibia[5:28, 3:12, 3:12] = True
    intensity = np.zeros_like(tibia, dtype=np.float32)
    intensity[tibia] = 1200

    roi = isolate_trabecular_roi(tibia, intensity, Thresholds(marrow_bone=270), compartment="total")

    assert roi.dtype == np.bool_
    assert roi.shape[0] <= 22
    assert roi.any()


def test_isolate_trabecular_roi_rejects_medial_lateral_without_operator_boundary() -> None:
    tibia = np.ones((7, 7, 7), dtype=bool)
    intensity = np.ones_like(tibia, dtype=np.float32) * 1200

    for compartment in ("medial", "lateral"):
        try:
            isolate_trabecular_roi(tibia, intensity, Thresholds(marrow_bone=270), compartment=compartment)
        except ValueError as exc:
            assert "operator-provided boundary mask" in str(exc)
        else:
            raise AssertionError(f"expected {compartment} to require an operator boundary")


def test_isolate_trabecular_roi_uses_thresholds_marrow_bone_as_lower_bound() -> None:
    tibia = np.ones((15, 15, 15), dtype=bool)
    intensity = np.ones_like(tibia, dtype=np.float32) * 800
    intensity[7, 7, 7] = 1200

    high_threshold_roi = isolate_trabecular_roi(tibia, intensity, Thresholds(marrow_bone=1000), compartment="total")
    low_threshold_roi = isolate_trabecular_roi(tibia, intensity, Thresholds(marrow_bone=700), compartment="total")

    assert high_threshold_roi.sum() < low_threshold_roi.sum()
