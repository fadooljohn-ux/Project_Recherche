"""Binary-search sensitivity curves from saved results (synthetic files only)."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import binary_curves
import detection_limits


def make(directory):
    directory.mkdir(parents=True)
    np.savez(directory / "periodogram.npz", frequencies=np.array([1 / 400, 1 / 100, 1 / 30]),
             statistic=np.zeros(3), eligible=np.array([False, True, True]),
             best_phase_amplitude_us=np.ones(3), worst_phase_amplitude_us=np.array([np.nan, 1.0, 2.0]))
    sha = hashlib.sha256((directory / "periodogram.npz").read_bytes()).hexdigest()
    (directory / "result.json").write_text(json.dumps(
        {"target": "J0000+0000", "status": "NO_TRIGGER", "threshold": 20.0, "periodogram_sha256": sha}))


def test_curve_converts_eligible_cells_only(tmp_path):
    make(tmp_path / "mpta-binary01" / "J0000+0000")
    c = binary_curves.curve(tmp_path / "mpta-binary01" / "J0000+0000")
    assert c["target"] == "J0000+0000" and c["disposition"] == "NO_TRIGGER" and c["eligible"] == [False, True, True]
    assert c["worst_minimum_mass_earth"][0] is None
    assert c["worst_minimum_mass_earth"][2] == detection_limits.minimum_mass_earth(2.0, 30.0, 1.6)
    assert np.allclose(c["period_days"], [400, 100, 30])


def test_curve_refuses_a_periodogram_that_does_not_match_its_result(tmp_path):
    make(tmp_path / "mpta-binary01" / "J0000+0000")
    result = tmp_path / "mpta-binary01" / "J0000+0000" / "result.json"
    result.write_text(result.read_text().replace('"periodogram_sha256": "', '"periodogram_sha256": "0'))
    with pytest.raises(ValueError, match="does not match"):
        binary_curves.curve(tmp_path / "mpta-binary01" / "J0000+0000")


def test_dataset_label_follows_the_release_and_a_pulsar_may_appear_in_two(tmp_path, monkeypatch):
    make(tmp_path / "ppta-binary01-x" / "J0000+0000")
    make(tmp_path / "epta-binary01-x" / "J0000+0000")
    monkeypatch.setattr(sys, "argv", ["x", str(tmp_path / "ppta-binary01-x"), str(tmp_path / "epta-binary01-x"),
                                      "--out", str(tmp_path / "curves.json")])
    binary_curves.main()
    out = json.loads((tmp_path / "curves.json").read_text())
    assert [c["dataset"].split(";")[0] for c in out["curves"]] == ["PPTA DR3", "EPTA DR2full"]
    assert out["pulsars"] == 1 and len({c["record_id"] for c in out["curves"]}) == 2
