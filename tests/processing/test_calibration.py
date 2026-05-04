import numpy as np

from microct_analysis.processing.calibration import analyze_histogram, derive_thresholds
from microct_analysis.processing.types import Thresholds


def test_analyze_histogram_detects_synthetic_air_soft_and_bone_peaks():
    rng = np.random.default_rng(42)
    volume = np.concatenate([
        rng.normal(-900, 8, 4_000),
        rng.normal(50, 8, 4_000),
        rng.normal(320, 8, 4_000),
    ])

    result = analyze_histogram(volume)

    assert result["air_peak"] is not None
    assert result["soft_tissue_peak"] is not None
    assert result["bone_peak"] is not None
    assert abs(result["air_peak"] - -900) < 25
    assert abs(result["soft_tissue_peak"] - 50) < 25
    assert abs(result["bone_peak"] - 320) < 25


def test_derive_thresholds_returns_scanco_defaults():
    thresholds = derive_thresholds(np.array([0, 1, 2]), scanner="scanco")

    assert thresholds == Thresholds()


def test_derive_thresholds_unknown_scanner_uses_histogram_peaks():
    rng = np.random.default_rng(7)
    volume = np.concatenate([rng.normal(-800, 5, 2_000), rng.normal(40, 5, 2_000), rng.normal(300, 5, 2_000)])

    thresholds = derive_thresholds(volume, scanner="unknown")

    assert thresholds.bone_soft_tissue > 100
    assert thresholds.subchondral_cortical >= thresholds.bone_soft_tissue
    assert thresholds.surface_3d >= thresholds.subchondral_cortical
