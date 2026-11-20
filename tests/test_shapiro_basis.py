"""Nonlinear Shapiro treatment on simulated Shapiro delays only (no observations read)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import shapiro_basis as shapiro

RNG = np.random.default_rng(11)
N = 600
PHASE = RNG.uniform(0, 2 * np.pi, N)
TIME = np.sort(RNG.uniform(0, 1600, N))
SIGMA = 1e-7
COVARIANCE = np.eye(N) * SIGMA ** 2
# Offset, slope and the orbital terms a Roemer fit absorbs.
DESIGN = np.column_stack([np.ones(N), TIME - 800, np.sin(PHASE), np.cos(PHASE), np.sin(2 * PHASE), np.cos(2 * PHASE)])
T_SUN = 4.925490947e-6


def family(m2, sini):
    return -2 * T_SUN * m2 * np.log(1 - sini * np.sin(PHASE))


def changer(m2, sini):
    def change(values):
        return family(values.get("M2", m2), values.get("SINI", sini)) - family(m2, sini)
    return change


def unremoved(columns, delta):
    full = np.column_stack([DESIGN, columns]) if columns.shape[1] else DESIGN
    return np.max(abs(delta - full @ np.linalg.lstsq(full, delta, rcond=None)[0])) / SIGMA


def expected_change(delta):
    """Chi-square change of an arrival-time change after projecting the design (white noise)."""
    rest = delta - DESIGN @ np.linalg.lstsq(DESIGN, delta, rcond=None)[0]
    return float(rest @ rest) / SIGMA ** 2


@pytest.mark.parametrize("m2, sini, dm2, dsini", [(0.3, 0.90, 0.03, 0.01), (0.5, 0.9990, 0.02, 1e-4), (0.2, 0.6, 0.05, 0.05),
                                                  (0.2, 0.6, 0.15, 0.2)])
def test_basis_removes_shapiro_changes_anywhere_in_the_neighbourhood(m2, sini, dm2, dsini):
    start = {"M2": (m2, dm2), "SINI": (sini, dsini)}
    columns, report = shapiro.build(changer(m2, sini), start, DESIGN, COVARIANCE, RNG.standard_normal(N) * SIGMA, seed=1)
    assert report["largest_unremoved_at_test_points_in_TOA_sigma"] <= shapiro.LIMIT
    assert columns.shape == (N, report["components"]) and report["components"] <= shapiro.MAX_COMPONENTS
    # Fresh points the builder never saw, checked by ordinary least squares.
    generator, checked = np.random.default_rng(99), 0
    while checked < 40:
        m, s = (generator.uniform(*report["sampled_range"][k]) for k in ("M2", "SINI"))
        delta = family(m, s) - family(m2, sini)
        if expected_change(delta) <= shapiro.REGION:
            assert unremoved(columns, delta) <= 1.5 * shapiro.LIMIT
            checked += 1
    assert report["sampled_range"]["SINI"][1] <= shapiro.BOUNDS["SINI"][1]


def test_neighbourhood_is_three_sigma_for_a_linear_parameter():
    def change(values):
        return (values["H3"] - 1e-7) * np.sin(3 * PHASE)
    columns, report = shapiro.build(change, {"H3": (1e-7, 1e-12)}, DESIGN, COVARIANCE, np.zeros(N), seed=2)
    own = report["uncertainty_under_search_covariance"]["H3"]
    low, high = report["neighbourhood_range"]["H3"]
    assert abs(high - 1e-7 - 3 * own) < 0.16 * own and abs(1e-7 - low - 3 * own) < 0.16 * own
    assert report["components"] == 1


def test_linear_family_needs_no_more_columns_than_parameters():
    def change(values):
        return (values.get("H3", 1e-7) - 1e-7) * np.sin(3 * PHASE) + (values.get("H4", 5e-8) - 5e-8) * np.cos(4 * PHASE)
    columns, report = shapiro.build(change, {"H3": (1e-7, 5e-8), "H4": (5e-8, 5e-8)}, DESIGN, COVARIANCE,
                                    RNG.standard_normal(N) * SIGMA, seed=2)
    assert report["components"] <= 2


def test_too_few_components_is_a_hold_not_a_pass():
    with pytest.raises(ValueError, match="unremoved"):
        shapiro.build(changer(0.5, 0.999), {"M2": (0.5, 0.1), "SINI": (0.999, 3e-4)}, DESIGN, COVARIANCE,
                      np.zeros(N), seed=3, max_components=0)


def test_data_preferring_values_outside_the_neighbourhood_is_a_hold():
    m2, sini = 0.3, 0.9
    start = {"M2": (m2, 0.03), "SINI": (sini, 0.01)}
    probe = shapiro.build(changer(m2, sini), start, DESIGN, COVARIANCE, np.zeros(N), seed=4)[1]
    m_far = probe["sampled_range"]["M2"][1]
    residuals = family(m_far, sini) - family(m2, sini)
    assert expected_change(residuals) > shapiro.REGION
    with pytest.raises(ValueError, match="outside the checked neighbourhood"):
        shapiro.build(changer(m2, sini), start, DESIGN, COVARIANCE, residuals, seed=4)


def test_data_inside_the_neighbourhood_is_located():
    m2, sini = 0.5, 0.999
    start = {"M2": (m2, 0.02), "SINI": (sini, 1e-4)}
    truth = (m2 + 0.001, sini)
    residuals = family(*truth) - family(m2, sini)
    assert expected_change(residuals) < shapiro.REGION
    report = shapiro.build(changer(m2, sini), start, DESIGN, COVARIANCE, residuals, seed=5)[1]
    assert report["data_preferred_expected_chi2_change"] <= shapiro.REGION
    assert report["chi2_released_minus_preferred"] > 0.5 * expected_change(residuals)   # grid resolution


def test_missing_uncertainty_and_unphysical_value_are_refused():
    with pytest.raises(ValueError, match="uncertainty missing"):
        shapiro.build(changer(0.3, 0.9), {"M2": (0.3, None)}, DESIGN, COVARIANCE, np.zeros(N), seed=6)
    with pytest.raises(ValueError, match="physical range"):
        shapiro.build(changer(0.3, 0.9), {"SINI": (1.2, 0.1)}, DESIGN, COVARIANCE, np.zeros(N), seed=6)
