"""The nonlinear statistic on a toy orbit: exact polynomial fit, linear limit and brute-force agreement."""

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import nonlinear_statistic as ns

N, D = 120, 3
RNG = np.random.default_rng(7)
TIMES = np.sort(RNG.uniform(0, 3000, N))
PHASE = 2 * np.pi * TIMES / 12.3
BASIS = np.column_stack([np.sin(PHASE), np.cos(PHASE), np.sin(2 * PHASE)])
NUISANCE = np.column_stack([np.ones(N), TIMES, TIMES**2])
COVARIANCE = np.diag(RNG.uniform(0.5, 2.0, N)) + 0.2 * np.exp(-np.abs(TIMES[:, None] - TIMES) / 400)
LOWER, UPPER = -np.full(D, 3.0), np.full(D, 3.0)
FREQUENCIES = 1 / np.array([150.0, 300.0, 600.0, 1200.0])
TEMPLATES = ns.periodic_templates(TIMES, FREQUENCIES, 0.0, N)


def quadratic(x):
    return BASIS @ x * 0.4 + 0.05 * BASIS[:, 0] * x[0] * x[1] + 0.03 * BASIS[:, 2] * x[2] ** 2


def curved(x):
    """Not a polynomial: a logarithmic, Shapiro-like term."""
    return BASIS @ x * 0.4 - 0.6 * np.log1p(0.25 * (1 + 0.2 * x[2]) * np.sin(PHASE) * 0.9) * (1 + 0.1 * x[1]) \
        + 0.6 * np.log1p(0.25 * np.sin(PHASE) * 0.9)


def brute(delay, data, template=None):
    scan = ns.NonlinearScan(COVARIANCE, NUISANCE, ns.PolynomialDelay(np.zeros((N, D)), np.eye(D, dtype=int), LOWER, UPPER),
                            TEMPLATES)
    design = NUISANCE if template is None else np.column_stack([NUISANCE, template])
    q, _ = np.linalg.qr(scan.white(design / np.linalg.norm(design, axis=0)))

    def residual(x):
        w = scan.white(data - delay(x))
        return w - q @ (q.T @ w)

    best = min((least_squares(residual, start, bounds=(LOWER, UPPER), xtol=1e-12, ftol=1e-12, gtol=1e-12)
                for start in (np.zeros(D), np.full(D, 1.0), np.full(D, -1.0))), key=lambda s: s.cost)
    return 2 * best.cost


def test_polynomial_fit_reproduces_a_quadratic_exactly():
    fit = ns.PolynomialDelay.fit(quadratic, LOWER, UPPER, 2, ns.sample_domain(LOWER, UPPER, 40, 1))
    for point in ns.sample_domain(LOWER, UPPER, 10, 2):
        np.testing.assert_allclose(fit(point), quadratic(point), atol=1e-10)


def test_fit_rejects_too_few_points():
    with pytest.raises(AssertionError, match="Too few"):
        ns.PolynomialDelay.fit(quadratic, LOWER, UPPER, 2, ns.sample_domain(LOWER, UPPER, 10, 1))


def test_linear_orbit_matches_generalised_least_squares():
    linear = ns.PolynomialDelay(BASIS * 0.4, np.eye(D, dtype=int), -np.full(D, 1e6), np.full(D, 1e6))
    scan = ns.NonlinearScan(COVARIANCE, NUISANCE, linear, TEMPLATES)
    data = np.linalg.cholesky(COVARIANCE) @ RNG.standard_normal(N) + 1.5 * np.sin(2 * np.pi * TIMES / 300 + 0.4)
    result = scan.scan(data)
    design = np.column_stack([NUISANCE, BASIS])
    for k in range(len(FREQUENCIES)):
        chi2 = []
        for columns in (design, np.column_stack([design, TEMPLATES[:, k]])):
            w, y = scan.white(columns), scan.white(data)
            chi2.append(float(y @ y - y @ w @ np.linalg.lstsq(w, y, rcond=None)[0]))
        assert result["delta_chi2"][k] == pytest.approx(chi2[0] - chi2[1], abs=1e-8)
    assert not result["unconverged"].any()


@pytest.mark.parametrize("signal", [0.0, 1.5])
def test_nonlinear_orbit_matches_brute_force(signal):
    surrogate = ns.PolynomialDelay.fit(curved, LOWER, UPPER, 4, ns.sample_domain(LOWER, UPPER, 200, 3))
    scan = ns.NonlinearScan(COVARIANCE, NUISANCE, surrogate, TEMPLATES)
    truth = np.array([0.7, -1.1, 0.9])
    data = (np.linalg.cholesky(COVARIANCE) @ np.random.default_rng(11).standard_normal(N) + curved(truth)
            + signal * np.sin(2 * np.pi * TIMES / 600 + 1.0))
    result = scan.scan(data)
    null = brute(curved, data)
    assert result["null_chi2"] == pytest.approx(null, abs=2e-3)
    for k in range(len(FREQUENCIES)):
        assert result["delta_chi2"][k] == pytest.approx(null - brute(curved, data, TEMPLATES[:, k]), abs=4e-3)
    assert not result["unconverged"].any()
    if signal:
        assert np.argmax(result["delta_chi2"]) == 2
        amplitude = np.hypot(*result["template_coefficients"][2])
        assert amplitude == pytest.approx(signal, rel=0.3)


def test_statistic_is_never_negative_and_flags_the_boundary():
    surrogate = ns.PolynomialDelay.fit(quadratic, LOWER, UPPER, 2, ns.sample_domain(LOWER, UPPER, 40, 1))
    scan = ns.NonlinearScan(COVARIANCE, NUISANCE, surrogate, TEMPLATES)
    data = np.linalg.cholesky(COVARIANCE) @ RNG.standard_normal(N) + quadratic(np.array([8.0, 0.0, 0.0]))
    result = scan.scan(data)
    assert result["delta_chi2"].min() > -1e-8
    assert result["null_on_boundary"]


def test_extended_exponents_lead_with_the_linear_terms_and_add_pair_powers():
    rows = ns.extended_exponents(3, 2, [1, 2], 4)
    np.testing.assert_array_equal(rows[:3], np.eye(3, dtype=int))
    assert len(rows) == len(np.unique(rows, axis=0)) == 9 + (14 - 5)
    assert [0, 3, 1] in rows.tolist() and [1, 2, 0] not in rows.tolist()
