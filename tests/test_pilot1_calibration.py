import hashlib
import json
from pathlib import Path

from pulsar_pilot.config import load_yaml
from pulsar_pilot.pilot1_calibration import (
    build_calibration_order,
    calibration_plan,
    verify_calibration_freeze,
)


def _plan() -> dict:
    return load_yaml(Path(__file__).resolve().parents[1] / "config/pilot1.yaml")


def test_calibration_order_is_exact_disjoint_and_sealed() -> None:
    order = build_calibration_order(_plan())
    assert len(order["all"]) == 1000
    assert len(order["reused"]) == 10
    assert len(order["remaining"]) == 990
    assert {case["case_id"] for case in order["reused"]}.isdisjoint(
        {case["case_id"] for case in order["remaining"]}
    )
    assert [case["index"] for case in order["all"]] == list(range(1000))
    assert all(case["family"] == "calibration" for case in order["all"])
    assert not any("sealed" in case["case_id"] for case in order["all"])


def test_calibration_plan_hashes_all_three_exact_orders() -> None:
    plan = calibration_plan(_plan())
    order = build_calibration_order(_plan())
    assert plan["execution_authorized"] is False
    assert plan["calibration_case_count"] == 1000
    assert plan["reused_benchmark_case_count"] == 10
    assert plan["new_scan_case_count"] == 990
    assert plan["sealed_evaluation_case_count"] == 0
    for key, cases in (
        ("all_case_order_sha256", order["all"]),
        ("reused_case_order_sha256", order["reused"]),
        ("remaining_case_order_sha256", order["remaining"]),
    ):
        canonical = json.dumps(cases, sort_keys=True, separators=(",", ":")).encode()
        assert plan[key] == hashlib.sha256(canonical).hexdigest()


def test_calibration_freeze_hashes_and_authorization() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = (root / "protocol/execution_freezes.sha256").read_text().strip().splitlines()
    relative = "protocol/PILOT1_CALIBRATION_FREEZE_v0.1.json"
    expected = next(line.split("  ", 1)[0] for line in manifest if line.endswith(relative))
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
    result = verify_calibration_freeze()
    assert result["status"] == "pass"
    assert result["failures"] == []
