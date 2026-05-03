from __future__ import annotations

import pytest

from microct_analysis.domain.artifact_contracts import screenshot_path


def test_screenshot_path_zero_pads_index() -> None:
    assert screenshot_path("segmentation", 1) == "segmentation/screenshot_001.png"
    assert screenshot_path("measurements", 12) == "measurements/screenshot_012.png"


def test_screenshot_path_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        screenshot_path("", 1)
    with pytest.raises(ValueError):
        screenshot_path("segmentation/nested", 1)
    with pytest.raises(ValueError):
        screenshot_path("segmentation", 0)
