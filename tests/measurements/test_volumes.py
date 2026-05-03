import numpy as np
import pytest

from microct_analysis.measurements.models import MeasurementSpec
from microct_analysis.measurements.volumes import compute_labeled_volume


def test_labeled_volume_counts_label_voxels_times_voxel_volume():
    labels = np.array([[[1, 2], [2, 2]], [[0, 2], [1, 1]]])
    result = compute_labeled_volume(MeasurementSpec("patella_volume", "volume", unit="mm^3"), labels, 2, (0.5, 0.5, 2.0))
    assert result.value == pytest.approx(4 * 0.5)
