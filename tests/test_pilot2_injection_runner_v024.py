import json
from pathlib import Path

import pytest

from pulsar_pilot.config import load_yaml
from pulsar_pilot.paths import initialize_data_root, repository_root
from pulsar_pilot.pilot2_injection_remediation_v023 import build_v023_inventory
from pulsar_pilot.pilot2_injection_runner_v024 import (
    EXPECTED_AUTHORIZED_CASE_COUNTS,
    RUNNER_CONFIG_PATH,
    STAGE,
    V024Ledger,
    _record_path,
    execute,
    implementation_sha256,
    recover_active_attempt,
    verify_execution_gate,
    verify_readiness_freeze,
    verify_repository_execution_authorization,
)
from pulsar_pilot.provenance import hash_file

INVENTORY_SHA256 = "811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b"


def _ledger(tmp_path: Path) -> V024Ledger:
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    inventory = build_v023_inventory()
    ledger = V024Ledger(
        data_root,
        inventory["inventory_sha256"],
        implementation_sha256(),
    )
    ledger.save(ledger.empty())
    return ledger


def _first_case() -> dict[str, object]:
    return build_v023_inventory()["cases"][0]


def _fake_gate() -> dict[str, object]:
    return {
        "status": "pass",
        "failures": [],
        "predecessors": {"threshold_delta_chi2": 1.0},
        "freeze_sha256": "f" * 64,
    }


def test_v024_reuses_never_executed_v023_inventory_without_seed_churn() -> None:
    inventory = build_v023_inventory()
    assert inventory["inventory_sha256"] == INVENTORY_SHA256
    assert len(inventory["cases"]) == 344


@pytest.mark.parametrize("semantic", [None, "fail"])
def test_readiness_semantic_must_explicitly_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    semantic: str | None,
) -> None:
    freeze_path = tmp_path / "readiness.json"
    freeze_path.write_text(json.dumps({"execution_readiness": semantic}))
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.READINESS_FREEZE_PATH",
        str(freeze_path),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024._verify_freeze",
        lambda *_: {
            "status": "pass",
            "failures": [],
            "freeze_sha256": "r" * 64,
        },
    )
    result = verify_readiness_freeze()
    assert result["status"] == "fail"
    assert any("readiness semantic is not pass" in item for item in result["failures"])


def test_readiness_semantic_pass_is_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    freeze_path = tmp_path / "readiness.json"
    freeze_path.write_text(json.dumps({"execution_readiness": "pass"}))
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.READINESS_FREEZE_PATH",
        str(freeze_path),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024._verify_freeze",
        lambda *_: {
            "status": "pass",
            "failures": [],
            "freeze_sha256": "r" * 64,
        },
    )
    assert verify_readiness_freeze()["status"] == "pass"


def test_malformed_present_execution_freeze_stops_before_predecessor_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    freeze_path = tmp_path / "execution-freeze.json"
    freeze_path.write_text("{not-json")
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.EXECUTION_FREEZE_PATH",
        str(freeze_path),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.verify_implementation_freeze",
        lambda: {"status": "pass", "failures": [], "freeze_sha256": "i" * 64},
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.verify_readiness_freeze",
        lambda: {"status": "pass", "failures": [], "freeze_sha256": "r" * 64},
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.verify_predecessor_bindings",
        lambda *_: pytest.fail("predecessors loaded for malformed authorization"),
    )
    result = verify_execution_gate(tmp_path / "must-not-be-read")
    assert result["status"] == "fail"
    assert result["predecessors_loaded"] is False


def test_execution_freeze_full_contract_is_required_and_hash_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    implementation_freeze_sha = "i" * 64
    readiness_freeze_sha = "r" * 64
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.verify_implementation_freeze",
        lambda: {
            "status": "pass",
            "failures": [],
            "freeze_sha256": implementation_freeze_sha,
        },
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.verify_readiness_freeze",
        lambda: {
            "status": "pass",
            "failures": [],
            "freeze_sha256": readiness_freeze_sha,
        },
    )
    root = repository_root()
    runner = load_yaml(root / RUNNER_CONFIG_PATH)
    predecessors = {
        key: binding["sha256"] for key, binding in runner["predecessor_bindings"].items()
    }
    frozen_path = "config/pilot2_injection_runner_v0.2.4.yaml"
    freeze = {
        "schema_version": 1,
        "freeze_id": "pilot2-b1937-injection-execution-freeze-v0.2.4",
        "status": "frozen_before_first_v0.2.4_injection_case",
        "user_authorization": "test-only contract validation",
        "execution_authorized": True,
        "authorized_case_counts": EXPECTED_AUTHORIZED_CASE_COUNTS,
        "authorized_primary_fits": 688,
        "no_reroll": True,
        "threshold_retuning_authorized": False,
        "v0.2.1_injection_acceptance_reuse_authorized": False,
        "observed_residual_access_authorized": False,
        "observed_periodic_search_authorized": False,
        "promotion_grade_authorized": False,
        "discovery_claim_authorized": False,
        "inventory_sha256": INVENTORY_SHA256,
        "implementation_sha256": implementation_sha256(),
        "implementation_freeze_sha256": implementation_freeze_sha,
        "readiness_freeze_sha256": readiness_freeze_sha,
        "predecessor_sha256": predecessors,
        "threshold_lock_sha256": predecessors["threshold_lock"],
        "supervision_policy": {
            "heartbeat_interval_seconds": 30,
            "stale_after_seconds": 90,
            "checkpoint_case_interval": 25,
            "passive_review_interval_seconds": 1800,
            "scientific_outcomes_in_health_record": False,
        },
        "stop_rule": (
            "any_gate_failure_stops_before_or_during_execution_without_reroll_retune_or_promotion"
        ),
        "frozen_sha256": {
            frozen_path: hash_file(root / frozen_path, "sha256"),
        },
    }
    freeze_path = tmp_path / "execution-freeze.json"
    freeze_path.write_text(json.dumps(freeze))
    assert verify_repository_execution_authorization(freeze_path)["status"] == "pass"
    freeze["authorized_primary_fits"] = 687
    freeze_path.write_text(json.dumps(freeze))
    result = verify_repository_execution_authorization(freeze_path)
    assert result["status"] == "fail"
    assert any("primary-fit count is invalid" in item for item in result["failures"])


def test_attempt_journal_precedes_execution_and_health_remains_outcome_free(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    case = _first_case()
    path = _record_path(ledger.data_root, 1, case)
    ledger.begin_attempt(1, case, "b" * 64, path)
    state = ledger.load()
    assert state["active_attempt"]["case_id"] == case["case_id"]
    assert state["active_attempt"]["seed"] == case["seed"]
    assert state["active_attempt"]["status"] == "started_seed_consumed"
    health = ledger.write_health(state)
    serialized = json.dumps(health)
    assert health["attempt_active"] is True
    for forbidden in (
        str(case["case_id"]),
        str(case["seed"]),
        "candidate_metric",
        "fit_result",
        "trigger_statistic",
    ):
        assert forbidden not in serialized


def test_consumed_attempt_without_artifact_terminally_stops(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    case = _first_case()
    result_path = ledger.data_root / "run_records/pilot2/failure.json"
    ledger.begin_attempt(
        1,
        case,
        "b" * 64,
        _record_path(ledger.data_root, 1, case),
    )
    with pytest.raises(RuntimeError, match="lacks a verified adoptable artifact"):
        recover_active_attempt(ledger, [case], "b" * 64, result_path)
    state = ledger.load()
    result = json.loads(result_path.read_text())
    assert state["stage_status"][STAGE] == "fail"
    assert state["hard_stop"] is not None
    assert state["active_attempt"]["case_id"] == case["case_id"]
    assert result["failure_class"] == ("interrupted_consumed_attempt_without_verified_artifact")
    assert result["partial_scientific_metrics_recorded"] is False


def test_verified_attempt_artifact_is_adopted_without_recomputation(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    case = _first_case()
    binding = "b" * 64
    path = _record_path(ledger.data_root, 1, case)
    ledger.begin_attempt(1, case, binding, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"case": case, "execution_binding_sha256": binding}))
    record = recover_active_attempt(
        ledger,
        [case],
        binding,
        ledger.data_root / "run_records/pilot2/failure.json",
    )
    state = ledger.load()
    assert record is not None
    assert case["case_id"] in state["completed_cases"]
    assert state["active_attempt"] is None
    assert state["attempt_history"][-1]["status"] == (
        "verified_artifact_adopted_without_recomputation"
    )


def test_recorded_attempt_is_reconciled_without_recomputation(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    case = _first_case()
    binding = "b" * 64
    path = _record_path(ledger.data_root, 1, case)
    ledger.begin_attempt(1, case, binding, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"case": case, "execution_binding_sha256": binding}))
    ledger.record_case(STAGE, str(case["case_id"]), path)
    recover_active_attempt(
        ledger,
        [case],
        binding,
        ledger.data_root / "run_records/pilot2/failure.json",
    )
    state = ledger.load()
    assert state["active_attempt"] is None
    assert state["attempt_history"][-1]["status"] == (
        "verified_ledger_record_reconciled_without_recomputation"
    )


def test_keyboard_interrupt_leaves_durable_consumed_attempt_for_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _ledger(tmp_path)
    runner = load_yaml(repository_root() / RUNNER_CONFIG_PATH)
    lock_path = ledger.data_root / runner["predecessor_bindings"]["threshold_lock"]["logical_path"]
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("{}")
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.verify_execution_gate",
        lambda *_: _fake_gate(),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.prepare_context",
        lambda *_: object(),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.execute_injection_case",
        lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    with pytest.raises(KeyboardInterrupt):
        execute(ledger.data_root)
    state = ledger.load()
    assert state["stage_status"][STAGE] == "running"
    assert state["hard_stop"] is None
    assert state["active_attempt"]["status"] == "started_seed_consumed"
    assert len(state["completed_cases"]) == 0


def test_post_begin_failure_is_terminalized_by_execute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _ledger(tmp_path)
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.verify_execution_gate",
        lambda *_: _fake_gate(),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.prepare_context",
        lambda *_: pytest.fail("context loaded after threshold binding failure"),
    )
    with pytest.raises(FileNotFoundError):
        execute(ledger.data_root)
    state = ledger.load()
    result_path = ledger.data_root / "run_records/pilot2/injection-evaluation-v0.2.4.json"
    result = json.loads(result_path.read_text())
    assert state["stage_status"][STAGE] == "fail"
    assert state["hard_stop"] is not None
    assert result["failure_class"] == "unexpected_execution_exception"
    assert result["partial_scientific_metrics_recorded"] is False


def test_absent_execution_freeze_never_loads_predecessors_or_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _ledger(tmp_path)
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.verify_predecessor_bindings",
        lambda *_: pytest.fail("predecessors loaded before authorization"),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v024.prepare_context",
        lambda *_: pytest.fail("context loaded before authorization"),
    )
    gate = verify_execution_gate(ledger.data_root)
    assert gate["status"] in {"locked", "fail"}
    assert gate["predecessors_loaded"] is False
    with pytest.raises(RuntimeError, match="execution is locked"):
        execute(ledger.data_root)
