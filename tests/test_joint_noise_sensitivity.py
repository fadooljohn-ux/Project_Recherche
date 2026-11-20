"""The second-stage sensitivity curve, on synthetic data."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import j1453_review as common
import joint_noise
import joint_noise_sensitivity as sensitivity
from test_joint_noise_stage import problem


def test_half_detection_interpolates_in_log_amplitude():
    assert abs(sensitivity.half_detection([1.0, 2.0, 4.0], [0.0, 0.25, 0.75]) - 2 * 2 ** 0.5) < 1e-12
    assert sensitivity.half_detection([1.0, 2.0], [0.6, 1.0]) == 1.0
    assert sensitivity.half_detection([1.0, 2.0], [0.0, 0.4]) is None


def test_spread_picks_distinct_cells_including_both_ends():
    periods = np.geomspace(30, 3000, 200)
    cells = sensitivity.spread(periods, 12)
    assert len(cells) == 12 and cells[0] == 0 and cells[-1] == 199


def test_a_family_holding_only_the_true_noise_matches_the_ideal_test():
    arrays, _ = problem()
    rows = 75
    contrast = joint_noise.Contrast(arrays["base_covariance"], arrays["design"], 60)
    common.REFERENCE = 56000.0
    arrays["periods"] = np.geomspace(40.0, 400.0, 30)
    full = common.template(arrays["times"], arrays["periods"], rows)
    templates = (contrast.B @ full.reshape(rows, -1)).reshape(contrast.dimension, -1, 2)
    truth = {"log10_amplitude": -12.6, "gamma": 3.0, "white_scale": 1.0}
    scope = {"coverage": {"selected_modes": 8}, "alpha": 0.01, "family": [truth],
             "generators": [{"name": "truth", **truth}]}
    cells = sensitivity.spread(arrays["periods"], 4)
    rng = np.random.default_rng(3)
    covariance = contrast.covariance(sensitivity.stage.variable_covariance(arrays, 8, truth))
    threshold, amplitude = sensitivity.ideal(contrast, [covariance], templates, cells, rng, 2048, 0.01)
    # Red noise makes the longest period harder than the shortest.
    assert amplitude[-1] > amplitude[0]
    out = sensitivity.curves(scope, arrays, contrast, templates, threshold, cells, count=96, seed=5)
    ratios = [row["joint_over_ideal"] for row in out[0]["cells"]]
    # With the noise known, the joint test is the ideal test: half detection near the ideal amplitude.
    assert all(0.8 <= r <= 1.3 for r in ratios), ratios
    rows_ = sensitivity.summary(out)
    assert rows_[0]["reference_generator"] == "truth" and rows_[0]["largest_joint_over_ideal"] == ratios[0]
