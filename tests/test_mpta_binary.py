"""MeerKAT binary adapter: input parsing and selection guards (no observations read)."""
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import mpta_binary as mb
import target_calibration as cal


def test_inner_period_from_pb_or_orbital_frequency():
    assert mb.inner_period_days(mb.par_fields("BINARY ELL1\nPB 7.25D0 1 1e-9\n")) == 7.25
    fields = mb.par_fields("BINARY ELL1\nFB0 7.9e-05 1 1e-15\n")
    assert abs(mb.inner_period_days(fields) - 1 / 7.9e-05 / 86400) < 1e-12


def make_source(tmp_path, monkeypatch, reasons, par=b"BINARY ELL1\nPB 4.0 1 1e-9\n"):
    source = tmp_path / "source"
    (source / "original").mkdir(parents=True)
    files = {"J0000+0000.par": par, "J0000+0000.tim": b"FORMAT 1\n"}
    with tarfile.open(source / "original/mpta-partim.tar.gz", "w:gz") as archive:
        for name, payload in files.items():
            info = tarfile.TarInfo("partim/" + name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    for name in ("mk2utc_observatory.clk", "tai2tt_bipm2020.clk"):
        (source / "original" / name).write_text("clock\n")
    for name, payload in files.items():
        (tmp_path / name).write_bytes(payload)
    row = {"target": "J0000+0000", "exclusion_reasons": reasons, "noise": {}, "toas": 10, "epochs": 5,
           "span_days": 1500.0, "precision_proxy_us": 0.1,
           "par_sha256": cal.digest(tmp_path / "J0000+0000.par"), "tim_sha256": cal.digest(tmp_path / "J0000+0000.tim")}
    (source / "selection.json").write_text(json.dumps({"rows": [row]}))
    monkeypatch.setattr(mb, "ARCHIVE_SHA256", cal.digest(source / "original/mpta-partim.tar.gz"))
    return source


def test_select_records_the_approved_list_and_counts_every_target(tmp_path, monkeypatch):
    source = make_source(tmp_path, monkeypatch, ["supplied_binary_model"])
    data = tmp_path / "batch"
    mb.select(data, source, ["J0000+0000"], "owner words")
    selection = json.loads((data / "selection.json").read_text())
    assert selection["selected"] == ["J0000+0000"] and selection["policy"]["search_count"] == 1
    assert selection["rows"][0]["binary_period_days"] == 4.0 and selection["owner_instruction"] == "owner words"
    assert selection["observed_periodograms_inspected"] is False
    with pytest.raises(FileExistsError):
        mb.select(data, source, ["J0000+0000"], "again")


def test_select_refuses_a_target_with_another_exclusion(tmp_path, monkeypatch):
    source = make_source(tmp_path, monkeypatch, ["supplied_binary_model", "published_scattering"])
    with pytest.raises(ValueError, match="Not a binary-only exclusion"):
        mb.select(tmp_path / "batch", source, ["J0000+0000"], "owner words")


def test_select_records_the_reexpression_or_refuses_before_reading_observations(tmp_path, monkeypatch):
    par = b"BINARY DD\nPB 4.0 1 1e-9\nT0 55000.5 1 0.01\nA1 2.0 1 1e-7\nOM 90 1 1\nECC 1e-6 1 1e-8\n"
    source = make_source(tmp_path, monkeypatch, ["supplied_binary_model"], par)
    mb.select(tmp_path / "batch", source, ["J0000+0000"], "owner words", reexpressed=True)
    row = json.loads((tmp_path / "batch/selection.json").read_text())["rows"][0]
    assert row["binary_model"] == "DD" and row["reexpression"]["to"] == "ELL1"
    assert abs(float(row["reexpression"]["tasc_mjd"]) - 54999.5) < 1e-12 and abs(row["reexpression"]["eps1"] - 1e-6) < 1e-18
    other = tmp_path / "other"
    other.mkdir()
    source = make_source(other, monkeypatch, ["supplied_binary_model"])
    with pytest.raises(ValueError, match="DD and DDH only"):
        mb.select(other / "batch", source, ["J0000+0000"], "owner words", reexpressed=True)


def test_select_records_free_shapiro_parameters_for_the_basis_treatment(tmp_path, monkeypatch):
    par = b"BINARY ELL1H\nPB 4.0 1 1e-9\nH3 1e-7 1 1e-8\nSTIG 0.5 1 0.1\nM2 0.3\n"
    source = make_source(tmp_path, monkeypatch, ["supplied_binary_model"], par)
    mb.select(tmp_path / "batch", source, ["J0000+0000"], "owner words", shapiro_basis=["J0000+0000"])
    row = json.loads((tmp_path / "batch/selection.json").read_text())["rows"][0]
    assert row["shapiro_basis"] == ["H3", "STIGMA"] and "reexpression" not in row
    other = tmp_path / "other"
    other.mkdir()
    source = make_source(other, monkeypatch, ["supplied_binary_model"])
    with pytest.raises(ValueError, match="No free Shapiro parameter"):
        mb.select(other / "batch", source, ["J0000+0000"], "owner words", shapiro_basis=True)
