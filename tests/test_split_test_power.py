"""Split-test power arithmetic on a small synthetic data set."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import split_test_power as power


def setup():
    rng = np.random.default_rng(1)
    t = np.sort(rng.uniform(0, 1000, 300))
    design = np.column_stack([np.ones(300), t - 500, (t - 500) ** 2])
    template = np.column_stack([np.cos(2 * np.pi * t / 37.0), np.sin(2 * np.pi * t / 37.0)])
    return t, design, template, np.eye(300) * 1e-14, rng.uniform(size=300) < 0.5


def test_estimator_recovers_split_coefficients_exactly_without_noise():
    t, design, template, covariance, part = setup()
    split = np.column_stack([template * part[:, None], template * ~part[:, None]])
    e, s = power.estimator(covariance, design, split)
    truth = np.array([1e-7, -2e-7, 3e-7, 4e-7])
    assert np.allclose(e @ (split @ truth + design @ [1e-6, 1e-9, 1e-12]), truth, rtol=1e-8, atol=1e-16)
    assert np.allclose(s, e @ covariance @ e.T)


def test_planet_and_fluke_pass_at_the_nominal_rate_and_one_part_signals_are_caught():
    t, design, template, covariance, part = setup()
    r = power.evaluate({"white": covariance}, covariance, design, template, part, 6e-8, 4000, 5)
    row = r["generators"]["white"]
    assert abs(r["limit"] - 9.2103) < 1e-3
    for label in ("planet", "noise_fluke", "noise_unconditional"):
        assert row[label]["rejected_fraction"] < 0.02
    assert row["part_a_only"]["rejected_fraction"] > 0.9 and row["part_b_only"]["rejected_fraction"] > 0.9
    # Every scenario is built to show the declared amplitude in the whole-data fit.
    assert abs(row["noise_fluke"]["whole_data_amplitude_us"] - 0.06) < 1e-9
    assert abs(row["part_a_only"]["whole_data_amplitude_us"] - 0.06) < 0.01


def test_misspecified_red_noise_changes_the_rejection_rate():
    t, design, template, covariance, part = setup()
    lag = abs(t[:, None] - t[None])
    red = covariance + 4e-14 * np.exp(-(lag / 60.0) ** 2)
    half = t < 500
    r = power.evaluate({"red": red}, covariance, design, template, half, 6e-8, 4000, 5)
    assert r["generators"]["red"]["noise_unconditional"]["rejected_fraction"] > 0.05
