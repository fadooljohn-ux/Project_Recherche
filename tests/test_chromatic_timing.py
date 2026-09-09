"""Physical scaling and signal-separation checks for optional chromatic support."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import chromatic_timing as chromatic
import mpta_batch as batch


def test_scattering_scales_cross_frequency_covariance_and_preserves_psd():
    c = np.array([[4.0, 1.0], [1.0, 9.0]])
    actual = chromatic.scattering_covariance(c, [700, 1400], 4)
    np.testing.assert_array_equal(actual, [[1024, 16], [16, 9]])
    assert np.linalg.eigvalsh(actual).min() > 0
    with pytest.raises(ValueError):
        chromatic.scattering_covariance(c, [0, 1400], 4)


def test_gaussian_is_localized_and_annual_basis_contains_arbitrary_phase():
    t = np.array([58900, 59000, 59100], dtype=float)
    event = {"kind": "gaussian", "index": 3, "center_mjd": 59000, "width_days": 100}
    result = chromatic.event_design(t, [1400, 700, 1400], event)
    np.testing.assert_allclose(result[:, 0], [np.exp(-0.5), 8, np.exp(-0.5)])
    annual = chromatic.event_design(t, [1400, 700, 1400], {"kind": "annual", "index": 3})
    phase = 2 * np.pi * (t - t.min()) / 365.25
    np.testing.assert_allclose(annual @ [np.cos(0.7), np.sin(0.7)],
                               np.sin(phase + 0.7) * [1, 8, 1])


def test_optional_covariance_preserves_legacy_and_requires_explicit_radio():
    t = np.array([59000, 59100, 59400.0])
    errors, groups = np.ones(3) * 1e-6, np.arange(3)
    noise = {"efac": 1, "log10_equad": None, "log10_ecorr": None,
             "red_amplitude": -14, "red_gamma": 3, "common_amplitude": -15,
             "chrom_amplitude": None}
    legacy = (batch.white_covariance(errors, groups, noise)
              + batch.red_covariance(t, -14, 3) + batch.red_covariance(t, -15, 13 / 3))
    np.testing.assert_array_equal(batch.published_covariance(t, errors, groups, noise), legacy)
    np.testing.assert_array_equal(
        batch.published_covariance(t, errors, groups, noise, radio=[900, 1200, 1600]), legacy)
    noise.update(chrom_amplitude=-13, chrom_gamma=2, chrom_index=4)
    with pytest.raises(ValueError):
        batch.published_covariance(t, errors, groups, noise)
    extended = batch.published_covariance(t, errors, groups, noise, radio=[900, 1200, 1600])
    np.testing.assert_allclose(extended - legacy, chromatic.scattering_covariance(
        batch.red_covariance(t, -13, 2), [900, 1200, 1600], 4))
