"""Focused release parsing checks; actual preparation also compares white covariance with PINT."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import tpa_batch as tpa


def test_noise_units_and_backend_selector():
    text = "TNEF -be MKBF 1.2\nTNEQ -be MKBF -6\nTNECORR -be MKBF 5\nTNRedAmp -12\nTNRedGam 4\nTNRedC 100\n"
    n = tpa.noise_parameters(text)
    c = tpa.mpta.white_covariance(np.array([1e-6, 2e-6]), np.array([0, 0]), n)
    np.testing.assert_allclose(c / 1e-12, [[27.44, 25], [25, 31.76]])
    assert n["red_modes"] == 100
    with pytest.raises(ValueError):
        tpa.noise_parameters(text.replace("-be MKBF", "-fe OTHER", 1))


def test_catalogue_resolves_b_alias_without_losing_binary_flag(tmp_path):
    p = tmp_path / "cat.db"
    p.write_text("#CATALOGUE fixture\nPSRJ J1234+5678 ref\nPSRB B1231+57 ref\nBINARY BT\n@---\nPSRJ J0000-0000 ref\n")
    records, aliases = tpa.catalogue(p)
    assert aliases["B1231+57"] == "J1234+5678"
    assert "BINARY" in records[aliases["B1231+57"]]
    assert "BINARY" not in records["J0000-0000"]


def test_ecorr_singleton_epoch_matches_pint():
    from pint.models.noise_model import create_ecorr_quantization_matrix

    noise = {"efac": 1.2, "log10_equad": -6, "log10_ecorr": np.log10(5e-6)}
    errors = np.array([1e-6, 2e-6, 3e-6])
    seconds = np.array([0.0, 0.01, 100.0])
    basis = create_ecorr_quantization_matrix(seconds)
    expected = np.diag((1.2 * errors) ** 2 + 1e-12) + (basis @ basis.T) * 25e-12
    np.testing.assert_allclose(tpa.white_covariance(errors, seconds, noise), expected)


def test_ecorr_splits_long_observation_without_chaining():
    from pint.models.noise_model import create_ecorr_quantization_matrix

    seconds = np.array([2.0, 0.9, 1.0, 0.0, 1.8])
    noise = {"efac": 1.0, "log10_equad": None, "log10_ecorr": 0.0}
    covariance = tpa.white_covariance(np.ones(5), seconds, noise)
    expected = np.eye(5)
    expected[np.ix_([1, 3], [1, 3])] += 1
    expected[np.ix_([2, 4], [2, 4])] += 1
    np.testing.assert_array_equal(covariance, expected)
    basis = create_ecorr_quantization_matrix(seconds)
    np.testing.assert_array_equal(covariance, np.eye(5) + basis @ basis.T)


def test_tim_pulse_numbers_and_unknown_directives():
    r = tpa.timing_rows("FORMAT 1\nx 1400 59000.2 3 meerkat -be MKBF -pn 123456 -chan 2\n")
    assert r[0][4]["-pn"] == "123456"
    with pytest.raises(ValueError):
        tpa.timing_rows("INCLUDE other.tim\n")
