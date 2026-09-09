import hashlib
import json
from pathlib import Path

import pytest

from pulsar_pilot.config import load_yaml
from pulsar_pilot.pilot1_evaluation import (
    THRESHOLD_LOCK_PATH,
    build_evaluation_order,
    evaluation_plan,
    verify_evaluation_freeze,
    wilson_interval_95,
)
from pulsar_pilot.pilot1_runtime import build_pilot1_case_inventory


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _plan() -> dict:
    return load_yaml(_root() / "config/pilot1.yaml")


def _threshold() -> dict:
    return json.loads((_root() / THRESHOLD_LOCK_PATH).read_text())


def test_evaluation_order_is_exact_disjoint_and_deterministic() -> None:
    order = build_evaluation_order(_plan())
    inventory = build_pilot1_case_inventory(_plan())
    calibration = [case for case in inventory["null_cases"] if case["family"] == "calibration"]
    assert len(order) == 500
    assert [case["index"] for case in order] == list(range(500))
    assert all(case["family"] == "sealed_evaluation" for case in order)
    assert {case["case_id"] for case in order}.isdisjoint(
        {case["case_id"] for case in calibration}
    )
    assert {case["seed"] for case in order}.isdisjoint({case["seed"] for case in calibration})


def test_evaluation_plan_binds_order_and_threshold() -> None:
    plan = evaluation_plan(_plan(), _threshold())
    order = build_evaluation_order(_plan())
    canonical = json.dumps(order, sort_keys=True, separators=(",", ":")).encode()
    assert plan["execution_authorized"] is False
    assert plan["case_count"] == 500
    assert plan["case_order_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert plan["locked_threshold_delta_chi2"] == pytest.approx(23.33426855482562)
    assert plan["threshold_retuning_authorized"] is False


def test_wilson_interval_known_counts() -> None:
    zero = wilson_interval_95(0, 500)
    five = wilson_interval_95(5, 500)
    assert zero["proportion"] == 0.0
    assert zero["upper"] == pytest.approx(0.007624340461552241)
    assert five["proportion"] == 0.01
    assert five["upper"] == pytest.approx(0.023193099755730702)


def test_evaluation_freeze_hashes_and_authorization() -> None:
    root = _root()
    relative = "protocol/PILOT1_EVALUATION_FREEZE_v0.1.json"
    manifest = (root / "protocol/execution_freezes.sha256").read_text().strip().splitlines()
    expected = next(line.split("  ", 1)[0] for line in manifest if line.endswith(relative))
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
    result = verify_evaluation_freeze()
    assert result["status"] == "pass"
    assert result["failures"] == []
