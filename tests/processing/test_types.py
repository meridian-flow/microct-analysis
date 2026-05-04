from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from microct_analysis.processing.types import LabelVolume, ScanVolume, SegmentationResult, Thresholds


def test_threshold_defaults_are_scanco_equivalents():
    thresholds = Thresholds()

    assert thresholds.bone_soft_tissue == 220
    assert thresholds.subchondral_cortical == 270
    assert thresholds.surface_3d == 320
    assert thresholds.marrow_bone == 270


def test_scan_and_label_dataclasses_can_be_created():
    scan = ScanVolume(
        data=np.zeros((2, 3, 4), dtype=np.float32),
        spacing=(0.01, 0.02, 0.03),
        affine=np.eye(4),
        provenance={"slice_count": 2},
    )
    labels = LabelVolume(data=np.zeros((2, 3, 4), dtype=np.uint8), spacing=scan.spacing, label_map={"tibia": 1})
    result = SegmentationResult(labels=labels, structure_assignments={"tibia": 1}, threshold_observations=[], confidence="high")

    assert scan.data.dtype == np.float32
    assert scan.spacing == (0.01, 0.02, 0.03)
    assert result.labels.label_map == {"tibia": 1}


def test_processing_dataclasses_are_frozen():
    thresholds = Thresholds()

    with pytest.raises(FrozenInstanceError):
        thresholds.bone_soft_tissue = 221  # type: ignore[misc]
