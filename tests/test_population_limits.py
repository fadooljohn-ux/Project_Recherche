"""Population-limit arithmetic on synthetic curves."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import population_limits as pl


def curve(target, mass, disposition="NO_TRIGGER", low=30.0, high=400.0, record=None):
    period = 1 / np.linspace(1 / high, 1 / low, 60)
    return {"record_id": record or target, "target": target, "disposition": disposition,
            "period_days": period.tolist(), "eligible": [True] * 60, "worst_minimum_mass_earth": [mass] * 60}


def test_upper_limit_matches_the_closed_form_for_identical_pulsars():
    n = 40
    expected = (1 - 0.05 ** (1 / n)) / 0.95
    assert abs(pl.upper_limit(np.ones(n)) - expected) < 1e-9
    assert pl.upper_limit(np.array([0.5])) is None       # one half-covered pulsar cannot exclude anything
    assert pl.upper_limit(np.zeros(5)) is None


def test_table_counts_coverage_margin_and_left_out_candidates():
    curves = [curve("A", 1.0), curve("A", 0.2, record="A2"), curve("B", 5.0),
              curve("C", 0.01, disposition="PERIODIC_SIGNAL_CANDIDATE")]
    t = pl.table(curves, 1.0, bins=[30, 60, 400, 1000], masses=[0.5, 10])
    assert t["pulsars"] == 2 and t["datasets_left_out"] == ["C"]
    cell = {(c["period_min_days"], c["minimum_mass_earth"]): c for c in t["cells"]}
    assert cell[(30, 0.5)]["effective_pulsars"] == 1.0   # A through its better dataset; B too coarse
    assert cell[(30, 10)]["effective_pulsars"] == 2.0
    assert cell[(400, 10)]["effective_pulsars"] == 0.0   # beyond every searched period
    assert pl.table(curves, 3.0, bins=[30, 60], masses=[0.5])["cells"][0]["effective_pulsars"] == 0.0


def test_masked_stretch_is_not_bridged():
    c = curve("A", 1.0)
    for i in range(20, 40):
        c["eligible"][i] = False
    period = np.array(c["period_days"])
    best = pl.best_mass(pl.pulsar_curves([c])[0]["A"], np.array([period[5], period[30], period[50]]))
    assert np.isfinite(best[0]) and np.isinf(best[1]) and np.isfinite(best[2])


def test_extra_curve_files_are_combined_and_also_reported_alone(tmp_path, monkeypatch):
    import json
    atlas = {"host_mass_solar": 1.4, "definition": "d", "curves": [curve("A", 1.0), curve("B", 1.0)]}
    extra = {"host_mass_solar": 1.6, "definition": "e", "curves": [curve("C", 0.01)]}
    (tmp_path / "atlas.json").write_text(json.dumps(atlas))
    (tmp_path / "extra.json").write_text(json.dumps(extra))
    monkeypatch.setattr(sys, "argv", ["x", "--atlas", str(tmp_path / "atlas.json"), "--extra",
                                      str(tmp_path / "extra.json"), "--out", str(tmp_path / "out.json"),
                                      "--margins", "1"])
    pl.main()
    out = json.loads((tmp_path / "out.json").read_text())
    assert [out[k][0]["pulsars"] for k in ("tables", "tables_atlas_only", "tables_extra_only")] == [3, 2, 1]
    assert out["extra"][0]["curves"] == 1 and out["extra"][0]["host_mass_solar"] == 1.6
