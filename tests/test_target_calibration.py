"""Focused contract, cache and statistical checks for reusable calibration."""

import importlib
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def calibration(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "tools"))
    return importlib.import_module("target_calibration")


def arrays():
    times = np.linspace(0, 500, 60)
    design = np.column_stack([np.ones(len(times)), times / 500])
    return {
        "times": times,
        "covariance": np.eye(len(times)) * 1e-10,
        "design": design,
        "baseline_design": design[:, :1],
    }


def test_cache_reuse_and_policy_covariance_invalidation(calibration, tmp_path):
    profile = calibration.create_profile(
        tmp_path / "profile",
        "unseen-target",
        arrays(),
        {"timing_model": "linear spin", "noise_model": "fixed Gaussian"},
        {"null_count": 1024, "minimum_period_days": 20.0},
    )
    first = calibration.run(profile, tmp_path / "cache")
    assert not first["cache_hit"]
    assert calibration.run(profile, tmp_path / "cache")["cache_hit"]
    data = calibration.read(profile)
    data["policy"]["maximum_period_days"] = 300.0
    calibration.write(profile, data)
    changed = calibration.run(profile, tmp_path / "cache")
    assert changed["cache_key"] != first["cache_key"]
    assert not changed["cache_hit"]
    revised = arrays()
    revised["covariance"] *= 4
    second_profile = calibration.create_profile(
        tmp_path / "revised", "unseen-target", revised, data["provenance"], data["policy"]
    )
    second = calibration.run(second_profile, tmp_path / "cache")
    assert second["cache_key"] != changed["cache_key"]
    assert second["median_worst_phase_amplitude_us"] == pytest.approx(
        2 * changed["median_worst_phase_amplitude_us"], rel=1e-8
    )
    artifact = Path(second["path"]) / "null-maxima.npy"
    artifact.write_bytes(b"damaged")
    with pytest.raises(ValueError, match="Cached calibration changed"):
        calibration.run(second_profile, tmp_path / "cache")


def test_ingestion_drops_observed_residuals_and_rejects_changed_arrays(calibration, tmp_path):
    from argparse import Namespace

    source = tmp_path / "input.npz"
    np.savez(source, **arrays(), residuals=np.ones(60) * 99)
    profile = calibration.import_npz(
        Namespace(
            context=source,
            output=tmp_path / "profile",
            target="new-pulsar",
            baseline_columns=None,
            timing_model="spin",
            noise_model="Gaussian",
            minimum_period=20,
            maximum_period=400,
        )
    )
    _, saved = calibration.load_profile(profile)
    assert "residuals" not in saved
    saved["covariance"] *= 2
    np.savez(profile.parent / "arrays.npz", **saved)
    with pytest.raises(ValueError, match="Profile arrays changed"):
        calibration.load_profile(profile)


def test_invalid_covariance_and_nonnested_baseline(calibration):
    a = arrays()
    a["covariance"][0, 0] = -1
    with pytest.raises(np.linalg.LinAlgError):
        calibration.validate_arrays(a)
    a = arrays()
    make = calibration.prepare_covariance_gls_scanner
    frequencies = np.array([1 / 70, 1 / 100])
    full = make(a["covariance"], a["design"], a["times"], frequencies, 0)
    base = make(a["covariance"], np.sin(a["times"])[:, None], a["times"], frequencies, 0)
    with pytest.raises(ValueError, match="not contained"):
        calibration.projection_map(full, base, calibration.DEFAULT_POLICY)


def test_wideband_auxiliary_rows_and_annual_exclusion(calibration):
    times = np.linspace(0, 1000, 100)
    # Auxiliary DM rows have no planetary timing signal, but constrain epoch dispersion.
    dm = np.vstack([np.eye(100), np.eye(100)])
    offset = np.r_[np.ones(100), np.zeros(100)]
    base = np.column_stack([offset, dm])
    annual = np.zeros((200, 2))
    annual[:100] = np.column_stack(
        [np.sin(2 * np.pi * times / 365.25), np.cos(2 * np.pi * times / 365.25)]
    )
    full = np.column_stack([base, annual])
    make = calibration.prepare_covariance_gls_scanner
    frequencies = np.array([1 / 66.54, 1 / 365.25])
    scanner = make(np.eye(200), full, times, frequencies, 0)
    baseline = make(np.eye(200), base, times, frequencies, 0)
    mask, _ = calibration.projection_map(scanner, baseline, calibration.DEFAULT_POLICY)
    assert mask.tolist() == [True, False]


def test_sensitivity_matches_independent_noisy_signal_trials(calibration):
    a = arrays()
    scanner = calibration.prepare_covariance_gls_scanner(
        a["covariance"], a["design"], a["times"], np.array([1 / 70]), 0
    )
    _, worst = calibration.sensitivity(scanner, np.array([True]), 20, 0.95)
    templates = scanner.projected_whitened_templates[:, 0, :]
    _, eigenvectors = np.linalg.eigh(templates.T @ templates)
    coefficients = eigenvectors[:, 0] * worst[0] * 1e-6
    # Independent least-squares projection of white noise plus the injected signal.
    noise = np.random.default_rng(726).normal(size=(60, 12000))
    samples = noise + (templates @ coefficients)[:, None]
    q, _ = np.linalg.qr(templates)
    statistics = np.sum((q.T @ samples) ** 2, axis=0)
    assert np.mean(statistics > 20) == pytest.approx(0.95, abs=0.01)
