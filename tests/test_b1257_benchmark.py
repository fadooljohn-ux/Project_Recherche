"""Numerical checks for the narrowband benchmark's new orbit adapter."""

import importlib
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def benchmark(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "tools"))
    return importlib.import_module("b1257_benchmark")


def test_phase_arc_recovers_signal_across_zero(benchmark):
    phase = np.array([0.98, 0.01, 0.03, 0.95])
    recovered, width = benchmark.unwrap_cluster(phase)
    np.testing.assert_allclose(recovered, np.array([-0.02, 0.01, 0.03, -0.05]) + 0.0075)
    assert width == pytest.approx(0.08)


def test_joint_eccentric_orbits_recover_independent_roemer_data(benchmark):
    from scipy.optimize import newton

    rng = np.random.default_rng(615)
    times = np.sort(rng.uniform(0, 730, 100))
    periods = [66.54, 98.21]
    eccentricities = [0.0186, 0.0252]
    amplitudes = [0.0013106, 0.0014134]
    values = np.zeros(len(times))
    for period, eccentricity, amplitude, omega in zip(
        periods, eccentricities, amplitudes, [0.7, 1.4], strict=True
    ):
        mean = 2 * np.pi * times / period + 0.3
        anomaly = newton(
            lambda e, ecc=eccentricity, mean=mean: e - ecc * np.sin(e) - mean,
            mean,
            fprime=lambda e, ecc=eccentricity: 1 - ecc * np.cos(e),
        )
        values += amplitude * (
            np.sin(omega) * (np.cos(anomaly) - eccentricity)
            + np.cos(omega) * np.sqrt(1 - eccentricity**2) * np.sin(anomaly)
        )
    design = np.column_stack([np.ones(len(times)), times / 730])
    scanner = benchmark.prepare_covariance_gls_scanner(
        np.eye(len(times)) * 1e-10, design, times, np.array([1 / periods[0], 1 / periods[1]]), 0.0
    )
    fit, _, _ = benchmark.fit_orbits(
        scanner, times, values + 1e-5 * times / 730, [1 / 66.6, 1 / 102.76], 0.0, 1 / (5 * 730)
    )
    np.testing.assert_allclose(fit["periods_days"], periods, atol=1e-5)
    np.testing.assert_allclose(fit["amplitudes_us"], np.array(amplitudes) * 1e6, atol=0.01)
    np.testing.assert_allclose(fit["eccentricities"], eccentricities, atol=1e-5)


def test_annual_mask_separates_dispersion_cost_from_astrometric_loss(benchmark):
    times = np.repeat(np.linspace(0, 735, 37), 10)
    radio = np.tile(np.linspace(110, 190, 10), 37)
    dm = np.zeros((len(times), 37))
    dm[np.arange(len(times)), np.repeat(np.arange(37), 10)] = radio**-2
    base = np.column_stack([np.ones(len(times)), dm])
    design = np.column_stack(
        [base, np.sin(2 * np.pi * times / 365.25), np.cos(2 * np.pi * times / 365.25)]
    )
    frequencies = np.array([1 / 66.54, 1 / 365.25])
    covariance = np.eye(len(times))
    make = benchmark.prepare_covariance_gls_scanner
    dispersion = make(covariance, base, times, frequencies, 0.0)
    timing = make(covariance, design, times, frequencies, 0.0)
    mask, _ = benchmark.eligible_mask(timing, dispersion)
    assert mask.tolist() == [True, False]
