"""Numerical checks for the additional MPTA fixed-noise adapter."""

import sys
from pathlib import Path

import numpy as np
from scipy.stats import chi2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import mpta_batch as batch

from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner


def test_wideband_observed_audit_keeps_orbit_out_of_dispersion_rows(tmp_path):
    """Exercise the full saved-result path with correlated TOA and auxiliary DM rows."""
    import target_calibration as cal
    times = np.linspace(59000, 59600, 80)
    n = len(times)
    # Deliberately different units/scales and nonzero cross-covariance.
    covariance = np.kron(np.array([[1e-12, 2e-10], [2e-10, 1e-6]]), np.eye(n))
    design = np.column_stack([np.r_[np.ones(n), np.zeros(n)],
                              np.r_[np.zeros(n), np.ones(n)]])
    policy = {**cal.DEFAULT_POLICY, "minimum_period_days": 30.0, "maximum_period_days": 150.0}
    root = tmp_path / "fixture"
    root.mkdir()
    cal.create_profile(root / "profile", "fixture", {"times": times, "covariance": covariance,
                        "design": design, "baseline_design": design},
                       {"timing_model": "synthetic joint TOA/DM", "noise_model": "known block covariance"},
                       policy, reference_epoch=59000.0)
    template = batch.circular_template(times, 59000.0, 0.01, 2 * n)
    assert np.all(template[n:] == 0)
    np.testing.assert_array_equal(template[:n], batch.circular_template(times, 59000.0, 0.01, n))
    residuals = template @ np.array([30e-6, 40e-6]) + design @ np.array([2e-6, 0.003])
    (root / "prepared").mkdir()
    np.savez(root / "prepared/observed.npz", residuals=residuals)
    cal.write(tmp_path / "selection.json", {"selected": ["fixture"], "rows": [], "policy": policy})
    batch.freeze(tmp_path)
    batch.run(tmp_path, "fixture")
    result = cal.read(root / "run01/result.json")
    assert result["candidate"] and not result["new_discovery"]
    np.testing.assert_allclose(result["peak_period_days"], 100, atol=1e-9)
    np.testing.assert_allclose(result["peak_amplitude_us"], 50, atol=1e-6)
    assert result["post_peak_chi2"] < 1e-12


def test_white_noise_units_and_epoch_correlations():
    n = {"efac": 2.0, "log10_equad": -6.0, "log10_ecorr": -5.0}
    c = batch.white_covariance(np.array([1.0, 2.0, 3.0]) * 1e-6, np.array([0, 0, 1]), n)
    np.testing.assert_allclose(c / 1e-12, [[105, 100, 0], [100, 117, 0], [0, 0, 137]])


def test_red_covariance_against_stationary_kernel_in_seconds():
    t = np.array([0.0, 21.0, 183.0, 365.25]) + 59000
    amplitude = -14.0
    gamma = 13 / 3
    c = batch.red_covariance(t, amplitude, gamma, modes=7)
    year = 31557600.0
    variance = 10.0 ** (2 * amplitude) * year**2 / (12 * np.pi**2)
    expected = np.array(
        [
            [
                sum(
                    variance * k ** (-gamma) * np.cos(2 * np.pi * k * (a - b) / 365.25)
                    for k in range(1, 8)
                )
                for b in t
            ]
            for a in t
        ]
    )
    np.testing.assert_allclose(c, expected, rtol=1e-12, atol=1e-28)
    np.testing.assert_allclose(batch.red_covariance(t + 1000, amplitude, gamma, modes=7), c)


def test_epoch_dm_projection_absorbs_correlated_dispersion_without_removing_orbit():
    rng = np.random.default_rng(42)
    t = np.repeat(np.linspace(59000, 60000, 30), 3)
    radio = np.tile([900.0, 1200.0, 1600.0], 30)
    epoch = np.repeat(np.arange(30), 3)
    dm = np.zeros((90, 30))
    dm[np.arange(90), epoch] = (1400 / radio) ** 2
    design = np.column_stack([np.ones(90), t - t.mean(), dm])
    covariance = np.eye(90) * 1e-12
    r = 4e-6 * np.sin(2 * np.pi * (t - 59000) / 100) + dm @ rng.normal(0, 1e-4, 30)
    args = (design, t, np.array([0.009, 0.01, 0.011]), 59000.0)
    plain = prepare_covariance_gls_scanner(covariance, *args).scan(r)["all_delta_chi2"]
    with_dm = prepare_covariance_gls_scanner(covariance + dm @ dm.T * 1e-9, *args).scan(r)[
        "all_delta_chi2"
    ]
    np.testing.assert_allclose(plain, with_dm, rtol=1e-6)
    assert np.argmax(plain) == 1 and plain[1] > 100


def test_batch_union_bound_counts_ten_full_grids():
    for grid_size in [186, 254, 300]:
        threshold = 2 * np.log(
            batch.POLICY["search_count"] * grid_size / batch.POLICY["false_alarm_probability"]
        )
        assert 10 * grid_size * chi2.sf(threshold, 2) <= 0.01000000001


def test_next_inventory_excludes_all_prior_selections_and_preserves_inputs(tmp_path):
    import hashlib
    import io
    import json
    import tarfile

    previous = tmp_path / "previous"
    original = previous / "original"
    original.mkdir(parents=True)
    rows = []
    archive_path = original / "mpta-partim.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for index, target in enumerate(["J0000+0001", "J0000+0002", "J0000+0003"]):
            row = {"target": target, "selected": index == 1, "exclusion_reasons": [],
                   "rank_key": [index], "batch_index": index}
            for suffix, key in ((".par", "par_sha256"), (".tim", "tim_sha256")):
                payload = (target + suffix).encode()
                info = tarfile.TarInfo(target + suffix)
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
                row[key] = hashlib.sha256(payload).hexdigest()
            rows.append(row)
    prior = {"selected": ["J0000+0002"], "previously_selected": ["J0000+0001"],
             "rows": rows, "policy": batch.POLICY,
             "original_hashes": {archive_path.name: batch.cal.digest(archive_path)},
             "source_hashes": {}, "prior_membership_scope": "fixture"}
    (previous / "selection.json").write_text(json.dumps(prior))
    before = batch.cal.digest(previous / "selection.json")
    destination = tmp_path / "next"
    batch.inventory_next(destination, previous)
    result = batch.cal.read(destination / "selection.json")
    assert result["selected"] == ["J0000+0003"]
    assert result["policy"]["search_count"] == 1
    assert result["policy"]["seed"] == batch.POLICY["seed"] + 100
    assert batch.cal.digest(previous / "selection.json") == before
    assert (destination / "J0000+0003/original/J0000+0003.tim").read_bytes() == b"J0000+0003.tim"
