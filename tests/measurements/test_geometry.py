import pytest

from microct_analysis.measurements.geometry import compute_distance, compute_ratio, compute_slice_count
from microct_analysis.measurements.models import MeasurementSpec


def test_distance_uses_spacing():
    spec = MeasurementSpec(name="length", kind="distance", points=["a", "b"])
    result = compute_distance(spec, {"a": [0, 0, 0], "b": [3, 4, 0]}, (2.0, 1.0, 1.0))
    assert result.value == pytest.approx((6**2 + 4**2) ** 0.5)


def test_ratio_uses_component_results():
    a = compute_distance(MeasurementSpec("a", "distance", points=["p1", "p2"]), {"p1": [0, 0, 0], "p2": [2, 0, 0]}, (1, 1, 1))
    b = compute_distance(MeasurementSpec("b", "distance", points=["p1", "p2"]), {"p1": [0, 0, 0], "p2": [4, 0, 0]}, (1, 1, 1))
    result = compute_ratio(MeasurementSpec("r", "ratio", numerator="b", denominator="a", unit="dimensionless"), {"a": a, "b": b})
    assert result.value == pytest.approx(2.0)


def test_slice_count_uses_dominant_axis_spacing():
    spec = MeasurementSpec(name="height", kind="slice_count", boundaries=["top", "bottom"])
    result = compute_slice_count(spec, {"top": [2, 0, 0], "bottom": [7, 1, 0]}, (0.01, 1, 1))
    assert result.value == pytest.approx(0.05)
