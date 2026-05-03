import numpy as np
import pytest

from microct_analysis.measurements.models import MeasurementSpec
from microct_analysis.measurements.trabecular import compute_bv_tv, compute_tb_n, compute_tb_sp, compute_tb_th, compute_trabecular_metrics


def test_bv_tv_counts_bone_inside_roi():
    bone = np.array([[1, 0], [1, 0]], dtype=bool)
    roi = np.array([[1, 1], [1, 0]], dtype=bool)
    assert compute_bv_tv(bone, roi) == pytest.approx(2 / 3)


def test_thickness_separation_and_number_are_positive_for_mixed_mask():
    bone = np.zeros((3, 3, 3), dtype=bool)
    bone[1, 1, 1] = True
    tb_th = compute_tb_th(bone, (1, 1, 1))
    tb_sp = compute_tb_sp(bone, (1, 1, 1))
    assert tb_th > 0
    assert tb_sp > 0
    assert compute_tb_n(0.5, tb_th) == pytest.approx(0.5 / tb_th)


def test_compute_trabecular_metrics_returns_named_results():
    bone = np.ones((2, 2, 2), dtype=bool)
    roi = np.ones((2, 2, 2), dtype=bool)
    spec = MeasurementSpec("trab", "roi_stat", roi="proximal_tibia", algorithm="edt")
    results = compute_trabecular_metrics(spec, bone, roi, (1, 1, 1), threshold=220)
    assert {r.name for r in results} == {"trab_BV/TV", "trab_Tb.Th", "trab_Tb.N", "trab_Tb.Sp"}
