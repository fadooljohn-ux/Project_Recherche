import hashlib
import json
from pathlib import Path

from pulsar_pilot.pilot2_selection import (
    _combined_key,
    _noise_inventory_has_red_noise,
    _parse_par,
    _parse_tim,
    _score,
)


def test_split_variants_are_excluded() -> None:
    assert _combined_key("J1909-3744_PINT_20230131.wb.par", ["gbt", "ao"]) == (
        "J1909-3744"
    )
    assert _combined_key("J1909-3744gbt_PINT_20230131.wb.par", ["gbt", "ao"]) is None
    assert _combined_key("B1937+21ao_PINT_20230131.wb.par", ["gbt", "ao"]) is None


def test_metadata_parsers_ignore_commented_toas() -> None:
    par = _parse_par(
        """PSR JTEST+0000
NTOA 2
START 55000
FINISH 55100
ELAT 30
BINARY ELL1
PLRedNoise 1"""
    )
    tim = _parse_tim(
        """FORMAT 1
C ignored 1400 55000 0.1 gbt
a 1400 55000.1 0.2 gbt
b 1400 55100.1 0.4 ao"""
    )
    assert par["binary_model"] is True
    assert par["released_red_noise"] is True
    assert tim["active_toa_count"] == 2
    assert tim["unique_floor_mjd_days"] == 2
    assert abs(tim["median_toa_uncertainty_microseconds"] - 0.3) < 1e-15


def test_noise_inventory_detects_released_red_noise_terms() -> None:
    assert _noise_inventory_has_red_noise(
        "B1937+21_red_noise_gamma\nB1937+21_red_noise_log10_A\n"
    )
    assert not _noise_inventory_has_red_noise(
        "JTEST_L-wide_PUPPI_efac\nJTEST_L-wide_PUPPI_log10_t2equad\n"
    )


def test_score_is_capped_and_penalizes_complexity() -> None:
    ranking = {
        "precision": {"weight": 0.35, "best_microseconds": 0.05, "floor_microseconds": 1.5},
        "span": {"weight": 0.2, "floor_days": 4500, "best_days": 5800},
        "unique_days": {"weight": 0.15, "floor": 150, "best": 400},
        "active_toas": {"weight": 0.1, "floor": 300, "best": 700},
        "annual_geometry": {
            "weight": 0.1,
            "floor_absolute_degrees": 10,
            "best_absolute_degrees": 60,
        },
        "no_released_red_noise": {"weight": 0.05},
        "isolated_timing_model": {"weight": 0.05},
    }
    record = {
        "median_toa_uncertainty_microseconds": 0.05,
        "span_days": 6000,
        "unique_floor_mjd_days": 500,
        "active_toa_count": 800,
        "ecliptic_latitude_degrees": 80,
        "released_red_noise": True,
        "binary_model": True,
    }
    score = _score(record, ranking)
    assert score["precision"] == 0.35
    assert score["span"] == 0.2
    assert score["unique_days"] == 0.15
    assert score["active_toas"] == 0.1
    assert score["annual_geometry"] == 0.1
    assert score["no_released_red_noise"] == 0.0
    assert score["isolated_timing_model"] == 0.0
    assert abs(score["total"] - 0.9) < 1e-12


def test_selection_module_has_no_residual_path() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/pulsar_pilot/pilot2_selection.py").read_text(
        encoding="utf-8"
    )
    assert "WidebandTOAResiduals" not in source
    assert "calc_wideband_resids" not in source
    assert "get_noise_covariancematrix" not in source
    assert "periodogram" not in source.lower()


def test_pilot2_selection_and_preflight_freeze_is_self_consistent() -> None:
    root = Path(__file__).resolve().parents[1]
    freeze = json.loads(
        (root / "protocol/PILOT2_SELECTION_AND_PREFLIGHT_FREEZE_v0.2.json")
        .read_text(encoding="utf-8")
    )
    assert freeze["selection_status"] == "complete_metadata_only"
    assert freeze["preflight_status"] == "frozen_design_execution_not_authorized"
    assert not any(freeze["authorization"].values())
    for relative, expected in freeze["frozen_sha256"].items():
        actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        assert actual == expected, relative
