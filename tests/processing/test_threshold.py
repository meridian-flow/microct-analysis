import numpy as np

from microct_analysis.processing.threshold import binary_mask


def test_binary_mask_uses_lower_bound_only():
    volume = np.array([[100, 220, 221]])

    mask = binary_mask(volume, 220)

    assert mask.dtype == np.bool_
    np.testing.assert_array_equal(mask, np.array([[False, True, True]]))


def test_binary_mask_uses_inclusive_upper_bound_when_given():
    volume = np.array([[219, 220, 270, 271]])

    mask = binary_mask(volume, 220, 270)

    assert mask.dtype == np.bool_
    np.testing.assert_array_equal(mask, np.array([[False, True, True, False]]))
