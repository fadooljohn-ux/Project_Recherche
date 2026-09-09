import hashlib
from pathlib import Path

from pulsar_pilot.config import load_yaml
from pulsar_pilot.pilot1_benchmark import (
    benchmark50_plan,
    build_benchmark50_order,
    verify_execution_freeze,
)


def _plan() -> dict:
    return load_yaml(Path(__file__).resolve().parents[1] / "config/pilot1.yaml")


def test_benchmark50_order_is_deterministic_representative_and_sealed() -> None:
    first = build_benchmark50_order(_plan())
    second = build_benchmark50_order(_plan())
    assert first == second
    assert len(first) == 50
    assert [item["sequence"] for item in first] == list(range(1, 51))
    assert len({item["case_id"] for item in first}) == 50
    assert not any(item.get("family") == "sealed_evaluation" for item in first)

    roles = [item["benchmark_role"] for item in first]
    assert roles.count("calibration_null") == 10
    assert roles.count("full_covariance_audit") == 4
    assert roles.count("main_matrix") == 28
    assert roles.count("annual_identifiability") == 4
    assert roles.count("search_boundary") == 4
    assert sum(item["full_covariance_audit"] for item in first) == 4

    injection_cases = [item for item in first if item["benchmark_role"] != "calibration_null"]
    main_cases = [item for item in first if item["benchmark_role"] == "main_matrix"]
    annual_cases = [
        item for item in first if item["benchmark_role"] == "annual_identifiability"
    ]
    boundary_cases = [item for item in first if item["benchmark_role"] == "search_boundary"]
    assert len(injection_cases) == 40
    assert {item["period_days"] for item in main_cases} == {50.0, 100.0, 200.0, 500.0, 1000.0}
    assert {item["amplitude_microseconds"] for item in main_cases} == {0.5, 1.0, 2.0, 5.0}
    assert len({item["phase_radians"] for item in main_cases}) == 4
    assert {item["noise_realization_index"] for item in main_cases} == {0, 1, 2}
    assert len(annual_cases) == 4
    assert {item["period_days"] for item in annual_cases} == {365.25}
    assert len({item["phase_radians"] for item in annual_cases}) == 4
    assert {
        (item["period_days"], item["amplitude_microseconds"]) for item in boundary_cases
    } == {(30.0, 1.0), (30.0, 5.0), (2000.0, 1.0), (2000.0, 5.0)}


def test_benchmark50_plan_hashes_the_exact_order() -> None:
    result = benchmark50_plan(_plan())
    assert result["execution_authorized"] is False
    assert result["benchmark_id"] == "pilot1-first-50-corrective-replay-v0.2"
    assert result["sealed_evaluation_cases"] == 0
    assert result["case_count"] == 50
    assert result["full_covariance_audits"] == 4
    canonical = __import__("json").dumps(
        result["case_order"], sort_keys=True, separators=(",", ":")
    ).encode()
    assert result["order_sha256"] == hashlib.sha256(canonical).hexdigest()


def test_execution_freeze_hashes_and_authorization() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = (
        (root / "protocol/execution_freezes.sha256")
        .read_text()
        .strip()
        .splitlines()[-1]
    )
    expected, relative = manifest.split("  ", 1)
    assert relative == "protocol/PILOT1_EXECUTION_FREEZE_v0.2.json"
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
    result = verify_execution_freeze()
    assert result["status"] == "pass"
    assert result["failures"] == []


def test_corrective_replay_preserves_the_original_case_order() -> None:
    root = Path(__file__).resolve().parents[1]
    original = __import__("json").loads(
        (root / "results/pilot1/benchmark50_plan.json").read_text()
    )
    corrective = benchmark50_plan(_plan())
    assert corrective["order_sha256"] == original["order_sha256"]
    assert [item["case_id"] for item in corrective["case_order"]] == [
        item["case_id"] for item in original["case_order"]
    ]
