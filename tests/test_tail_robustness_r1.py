import inspect
from pathlib import Path

from pulsar_pilot.config import load_yaml
from pulsar_pilot.tail_robustness_r1 import (
    CONFIG_PATH,
    build_null_orders,
    run_gate,
    verify_freeze,
)


def test_r1_nulls_are_exact_unique_and_disjoint() -> None:
    config = load_yaml(Path(__file__).resolve().parents[1] / CONFIG_PATH)
    orders = build_null_orders(config)
    cases = orders["calibration"] + orders["evaluation"]
    assert len(orders["calibration"]) == 2000
    assert len(orders["evaluation"]) == 1000
    assert len({case["case_id"] for case in cases}) == 3000
    assert len({case["seed"] for case in cases}) == 3000


def test_r1_run_has_no_observed_residual_path() -> None:
    source = inspect.getsource(run_gate)
    assert "WidebandTOAResiduals" not in source
    assert "calc_wideband_resids" not in source
    assert "observed_residual_accessed" in source


def test_r1_freeze_verifies() -> None:
    result = verify_freeze()
    assert result["status"] == "pass"
    assert result["failures"] == []
