"""tempo2 comparison arithmetic on synthetic residuals (tempo2 itself is not run)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import tempo2_compare as t2


def setup(n=200):
    rng = np.random.default_rng(4)
    times = np.sort(rng.uniform(55000, 58000, n))
    design = np.column_stack([np.ones(n), times - times.mean(), np.sin(2 * np.pi * times / 5.7)])
    covariance = np.eye(n) * 1e-14
    tempo2 = {"residuals": rng.standard_normal(n) * 1e-7, "site_times": times - 69.0 / 86400, "deleted": np.zeros(n, bool)}
    return times, design, covariance, tempo2


def test_a_difference_inside_the_projected_columns_agrees():
    times, design, covariance, tempo2 = setup()
    prepared = tempo2["residuals"] + design @ np.array([3e-7, 1e-10, 2e-7])
    result = t2.compare(prepared, tempo2, design, covariance, times)
    assert result["status"] == "AGREES_WITH_TEMPO2" and result["maximum_difference_in_TOA_sigma"] < 1e-6
    assert result["rms_difference_seconds_before_projection"] > 1e-7


def test_a_difference_the_search_would_not_remove_is_flagged():
    times, design, covariance, tempo2 = setup()
    prepared = tempo2["residuals"] + 5e-8 * np.sin(2 * np.pi * times / 91.0)
    assert t2.compare(prepared, tempo2, design, covariance, times)["status"] == "DIFFERS_FROM_TEMPO2"


def test_count_and_order_guards():
    times, design, covariance, tempo2 = setup()
    with pytest.raises(ValueError, match="count differs"):
        t2.compare(tempo2["residuals"][:-1], tempo2, design, covariance, times)
    shuffled = {**tempo2, "site_times": tempo2["site_times"][::-1].copy()}
    with pytest.raises(ValueError, match="same order"):
        t2.compare(tempo2["residuals"], shuffled, design, covariance, times)
    deleted = {**tempo2, "deleted": np.r_[True, np.zeros(199, bool)]}
    with pytest.raises(ValueError, match="count differs"):
        t2.compare(tempo2["residuals"], deleted, design, covariance, times)
