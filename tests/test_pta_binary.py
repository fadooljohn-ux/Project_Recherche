"""Parkes/European binary adapter: text handling and selection guards (no observations read)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import pta_binary as pb
import target_calibration as cal

T2_KEPLER = ("PSRJ J0000+0000\nF0 100 1\nPEPOCH 56000\nRAJ 00:00:00\nDECJ 00:00:00\nBINARY T2\nPB 11.05 1 2e-10\n"
             "T0 56030.84 1 0.047\nA1 9.93 1 1e-6\nOM 117.9 1 1.5\nECC 7.15e-07 1 3.7e-8\nM2 0.25 1 0.02\n"
             "SINI 0.9 1 0.01\nNTOA 100\nCHI2R 1.0 50\n")


def ppta_intake(tmp_path, par=T2_KEPLER):
    intake, tims = tmp_path / "intake", tmp_path / "tims"
    (intake / "ppta").mkdir(parents=True)
    tims.mkdir()
    (intake / "ppta/J0000+0000_singlePsrNoise_fit.par").write_text(par)
    (tims / "J0000+0000.tim").write_text("FORMAT 1\n")
    return intake, tims


def test_model_text_drops_report_lines_and_merges_repeated_chromatic_settings(tmp_path):
    text = pb.model_text("F0 100 1\nNTOA 5\nTNChromIdx 4\nTNChromIdx 4\nTRES 1.0\n", "ppta", tmp_path, "J0000+0000")
    assert text == "F0 100 1\nTNChromIdx 4\n"
    with pytest.raises(ValueError, match="Conflicting"):
        pb.model_text("TNChromIdx 4\nTNChromIdx 3\n", "ppta", tmp_path, "J0000+0000")


def test_select_records_translation_then_reexpression_and_shapiro(tmp_path):
    intake, tims = ppta_intake(tmp_path)
    pb.select(tmp_path / "root", "ppta", intake, ["J0000+0000"], "test", reexpressed=True, shapiro_basis=True,
              tims=tims, development=True)
    selection = cal.read(tmp_path / "root/selection.json")
    row, = selection["rows"]
    assert row["binary_model"] == "T2" and row["translation"]["to"] == "DD"
    assert row["reexpression"]["from"] == "DD" and row["reexpression"]["to"] == "ELL1"
    assert row["shapiro_basis"] == ["M2", "SINI"] and selection["development"] is True
    assert set(row["input_hashes"]) == {"J0000+0000.par", "J0000+0000.tim"}
    # The same steps are reproduced from the selection at preparation.
    text = pb.model_text((tmp_path / "root/J0000+0000/original/J0000+0000.par").read_text(), "ppta", tmp_path, "J0000+0000")
    searched, steps = pb.searched_text(text, row)
    assert "BINARY ELL1" in searched and "TASC" in searched and steps["translation"]["to"] == "DD"
    with pytest.raises(ValueError, match="Development root"):
        pb.calibrate(tmp_path / "root")


def test_select_refusals(tmp_path):
    intake, tims = ppta_intake(tmp_path, par=T2_KEPLER + "KOM 90 1 1\nKIN 70 1 1\n")
    with pytest.raises(ValueError, match="does not cover: KOM KIN"):
        pb.select(tmp_path / "a", "ppta", intake, ["J0000+0000"], "test", tims=tims)
    intake, tims = ppta_intake(tmp_path / "x", par="PSRJ J0000+0000\nF0 100 1\n")
    with pytest.raises(ValueError, match="Not a binary"):
        pb.select(tmp_path / "b", "ppta", intake, ["J0000+0000"], "test", tims=tims)
    with pytest.raises(ValueError, match="need --tims"):
        pb.select(tmp_path / "c", "ppta", intake, ["J0000+0000"], "test")
    with pytest.raises(ValueError, match="Unknown source"):
        pb.select(tmp_path / "d", "inpta", intake, ["J0000+0000"], "test")


def test_code_binding_names_every_module():
    assert {"adapter", "orbit_translate", "orbit_reexpress", "shapiro_basis", "pta_campaign", "mpta_binary"} <= set(pb.code())


def test_missing_uncertainties_are_filled_from_the_search_covariance_and_given_ones_kept():
    import numpy as np

    class Parameter:
        def __init__(self, uncertainty):
            self.uncertainty_value = uncertainty

    class Model:
        free_params = ["PB", "A1", "F0"]
        PB, A1, F0 = Parameter(None), Parameter(2e-7), Parameter(None)

    class Component:
        params = ["PB", "A1", "M2"]

    rng = np.random.default_rng(0)
    design = rng.standard_normal((40, 3))
    covariance = np.eye(40) * 4.0
    model = Model()
    filled = pb.fill_missing_uncertainties(model, Component(), design, ["PB", "A1", "F0"], covariance)
    expected = np.sqrt(np.diag(np.linalg.inv(design.T @ design / 4.0)))
    assert set(filled) == {"PB"} and abs(filled["PB"] - expected[0]) < 1e-12
    assert model.PB.uncertainty_value == filled["PB"] and model.A1.uncertainty_value == 2e-7
    assert model.F0.uncertainty_value is None                      # not an orbital parameter


def test_terms_the_library_would_drop_are_reported():
    base = "PSRJ J0000+0000\nF0 100 1\nPEPOCH 56000\nRAJ 00:00:00\nDECJ 00:00:00\nDM 10\n"
    assert pb.unimplemented_terms(base + "DM_SERIES TAYLOR\n") == []
    assert pb.unimplemented_terms(base + "DM_SERIES POLY\n") == ["DM_SERIES"]
    assert pb.unimplemented_terms(base + "GAUSEP_1 53913.1\nGAUSAMP_1 -5.7e-06\nGAUSSIG_1 94\nGAUSINDEX_1 -2\n") == [
        "GAUSAMP_1", "GAUSEP_1", "GAUSINDEX_1", "GAUSSIG_1"]
