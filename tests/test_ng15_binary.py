"""NANOGrav binary adapter: selection guards and vector helpers (no observations read)."""
import io
import json
import sys
import tarfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ng15_binary as nb
import target_calibration as cal

DD = (b"PSR J0000+0000\nBINARY DD\nPB 11.05 1 2e-10\nT0 56030.84 1 0.047\nA1 9.93 1 1e-6\nOM 117.9 1 1.5\n"
      b"ECC 7.15e-07 1 3.7e-8\nM2 0.25 1 0.02\nSINI 0.9 1 0.01\n")


def make(tmp_path, par=DD, name="B0000+00"):
    files = {"release/wideband/par/x.par": par, "release/wideband/tim/x.tim": b"FORMAT 1\n",
             "release/clock/vla2gps.clk": b"clock\n"}
    with tarfile.open(tmp_path / "release.tar.gz", "w:gz") as archive:
        for member, payload in files.items():
            info = tarfile.TarInfo(member)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    digest = {}
    for member, payload in files.items():
        (tmp_path / "scratch").write_bytes(payload)
        digest[member] = cal.digest(tmp_path / "scratch")
    row = {"target": name, "release_name": name, "par_member": "release/wideband/par/x.par",
           "tim_member": "release/wideband/tim/x.tim", "par_sha256": digest["release/wideband/par/x.par"],
           "tim_sha256": digest["release/wideband/tim/x.tim"]}
    (tmp_path / "inventory.json").write_text(json.dumps([row]))
    return tmp_path / "release.tar.gz", tmp_path / "inventory.json"


def test_select_records_both_treatments_and_the_clock(tmp_path, monkeypatch):
    monkeypatch.setitem(nb.observed.ALIASES, "B0000+00", "J0000+0000")
    archive, inventory = make(tmp_path)
    nb.select(tmp_path / "root", archive, inventory, ["J0000+0000"], "test", reexpressed=True, shapiro_basis=True)
    selection = cal.read(tmp_path / "root/selection.json")
    row, = selection["rows"]
    assert row["shapiro_basis"] == ["M2", "SINI"] and row["reexpression"]["to"] == "ELL1"
    assert row["binary_model"] == "DD" and row["binary_period_days"] == 11.05 and row["release_name"] == "B0000+00"
    assert selection["policy"]["search_count"] == 1 and selection["policy"]["maximum_period_days"] == 2000.0
    assert cal.read(tmp_path / "root/resources/binding.json")["filename"] == "vla2gps.clk"
    assert (tmp_path / "root/J0000+0000/original/J0000+0000.par").read_bytes() == DD


def test_select_refuses_what_the_treatments_do_not_cover(tmp_path):
    archive, inventory = make(tmp_path, par=b"BINARY ELL1\nPB 4.0 1 1e-9\n", name="J0000+0000")
    with pytest.raises(ValueError, match="No free Shapiro parameter"):
        nb.select(tmp_path / "a", archive, inventory, ["J0000+0000"], "test", shapiro_basis=["J0000+0000"])
    with pytest.raises(ValueError, match="DD and DDH only"):
        nb.select(tmp_path / "b", archive, inventory, ["J0000+0000"], "test", reexpressed=True)
    with pytest.raises(ValueError, match="Inventory is missing"):
        nb.select(tmp_path / "c", archive, inventory, ["J1111+1111"], "test")


def test_development_roots_cannot_be_calibrated_or_frozen(tmp_path):
    archive, inventory = make(tmp_path, name="J0000+0000")
    nb.select(tmp_path / "root", archive, inventory, ["J0000+0000"], "test")
    selection = cal.read(tmp_path / "root/selection.json")
    cal.write(tmp_path / "root/selection.json", {**selection, "development": True})
    with pytest.raises(ValueError, match="Development root"):
        nb.calibrate(tmp_path / "root")


def test_padding_and_residual_sign():
    change = np.sin(np.linspace(0, 20, 200)) * 1e-7
    assert np.array_equal(nb.padded(change, 400)[200:], np.zeros(200)) and np.array_equal(nb.padded(change, 400)[:200], change)
    assert nb.signature_sign(change + 3e-6, change) == 1.0          # a constant offset is the removed mean
    assert nb.signature_sign(-change - 1e-6, change) == -1.0
    with pytest.raises(ValueError, match="do not follow"):
        nb.signature_sign(np.cos(np.linspace(0, 20, 200)) * 1e-7, change)


def test_zero_unfitted_terms_are_dropped_and_real_ones_kept():
    text, dropped = nb.drop_inert("BINARY DD\nOMDOT 0.0\nPBDOT 0.0 0\nGAMMA 0.0\nA1DOT 1e-14 1 1e-15\nEDOT 0 1\n")
    assert dropped == ["OMDOT", "PBDOT", "GAMMA"] and "EDOT 0 1" in text and "A1DOT" in text
    assert nb.drop_inert("OMDOT 0.01\n") == ("OMDOT 0.01\n", [])


def test_select_reexpresses_a_release_that_lists_unused_terms(tmp_path):
    archive, inventory = make(tmp_path, par=DD + b"OMDOT 0.0\nGAMMA 0.0\n", name="J0000+0000")
    nb.select(tmp_path / "root", archive, inventory, ["J0000+0000"], "test", reexpressed=True)
    row, = cal.read(tmp_path / "root/selection.json")["rows"]
    assert row["zero_unfitted_terms_dropped"] == ["OMDOT", "GAMMA"] and row["reexpression"]["to"] == "ELL1"
    archive, inventory = make(tmp_path, par=DD + b"OMDOT 0.01 1 0.001\n", name="J0000+0000")
    with pytest.raises(ValueError, match="does not map: OMDOT"):
        nb.select(tmp_path / "other", archive, inventory, ["J0000+0000"], "test", reexpressed=True)


def test_free_shapiro_names():
    fields = nb.par_fields("H3 1e-7 1 1e-8\nSTIG 0.5 1 0.1\nM2 0.2 0\nSINI 0.9\n")
    assert nb.free_shapiro(fields) == ["H3", "STIGMA"]


def test_a_target_with_no_searchable_period_is_held_at_calibration(tmp_path, monkeypatch):
    archive, inventory = make(tmp_path, name="J0000+0000")
    nb.select(tmp_path / "root", archive, inventory, ["J0000+0000"], "test")
    (tmp_path / "root/J0000+0000/profile").mkdir()
    monkeypatch.setattr(nb, "verify", lambda data, target: ({}, {}))

    def no_frequency(*args):
        raise ValueError("No identifiable frequency remains")

    monkeypatch.setattr(nb.cal, "run", no_frequency)
    with pytest.raises(ValueError, match="No compatible preparation"):       # the only target is held, not a crash
        nb.calibrate(tmp_path / "root")


def test_refinement_is_recorded_only_for_a_reexpressed_orbit(tmp_path):
    archive, inventory = make(tmp_path, name="J0000+0000")
    nb.select(tmp_path / "root", archive, inventory, ["J0000+0000"], "test", reexpressed=True, refined=True)
    assert cal.read(tmp_path / "root/selection.json")["rows"][0]["refine"] is True
    with pytest.raises(ValueError, match="applies to a re-expressed orbit"):
        nb.select(tmp_path / "other", archive, inventory, ["J0000+0000"], "test", refined=True)
