import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from pulsar_pilot import pilot2_injection_runner_v027 as runner_module
from pulsar_pilot.config import load_yaml
from pulsar_pilot.paths import initialize_data_root, repository_root
from pulsar_pilot.pilot2_injection_remediation_v023 import build_v023_inventory
from pulsar_pilot.pilot2_injection_runner_v027 import (
    EXPECTED_AUTHORIZED_CASE_COUNTS,
    RUNNER_CONFIG_PATH,
    STAGE,
    TrustedJSONError,
    V027Ledger,
    _durable_atomic_json,
    _durable_mkdirs,
    _execution_binding_sha256,
    _input_binding_sha256,
    _loads_trusted_json,
    _record_path,
    _require_initialized_data_root,
    _verify_exact_repository_hashes,
    execute,
    implementation_sha256,
    prepare_case_directories,
    recover_active_attempt,
    validate_complete_case_record,
    verify_execution_gate,
    verify_readiness_freeze,
    verify_repository_execution_authorization,
)
from pulsar_pilot.provenance import hash_file

INVENTORY_SHA256 = "811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b"


def _ledger(tmp_path: Path) -> V027Ledger:
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    inventory = build_v023_inventory()
    ledger = V027Ledger(
        data_root,
        inventory["inventory_sha256"],
        implementation_sha256(),
    )
    ledger.save(ledger.empty())
    return ledger


def _first_case() -> dict[str, object]:
    return build_v023_inventory()["cases"][0]


def _first_family_case(family: str) -> dict[str, object]:
    return next(case for case in build_v023_inventory()["cases"] if case["family"] == family)


def _input_binding() -> dict[str, object]:
    return {
        "target": "B1937+21",
        "active_toas": 660,
        "covariance_shape": [1320, 1320],
        "timing_design_shape": [1320, 284],
        "timing_design_rank": 284,
        "frequency_grid": {
            "algorithm": "linear_frequency_independent_bin_oversampling",
            "oversampling": 5,
            "span_days": 1000.0,
            "minimum_period_days": 30.0,
            "maximum_period_days": 2000.0,
            "minimum_frequency_per_day": 0.0005,
            "maximum_frequency_per_day": 0.03333333333333333,
            "frequency_step_per_day": 0.0002,
            "frequency_count": 166,
        },
        "reference_epoch_mjd_tdb": 50000.0,
        "observed_residual_vector_loaded": False,
        "observed_periodic_scan_executed": False,
        "network_access_enabled": False,
    }


def _input_binding_sha() -> str:
    return _input_binding_sha256(_input_binding())


def _context() -> SimpleNamespace:
    return SimpleNamespace(input_binding=_input_binding())


def _complete_record(
    case: dict[str, object],
    binding: str,
    threshold: float = 1.0,
    audit_required: bool = False,
) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_version": 3,
        "run_id": "pilot2-b1937-injection-remediation-v0.2.7",
        "execution_binding_sha256": binding,
        "case": case,
        "family": case["family"],
        "period_days": float(case["period_days"]),
        "amplitude_microseconds": float(case["amplitude_microseconds"]),
        "phase_radians": float(case["phase_radians"]),
        "locked_threshold_delta_chi2": threshold,
        "global_maximum_delta_chi2": 0.0,
        "triggered": False,
        "frequency_recovered": False,
        "frequency_recovery_tolerance_per_day": 0.001,
        "amplitude_bias_fraction": 0.0,
        "phase_error_radians": 0.0,
        "recovered_sine_microseconds": 0.1,
        "recovered_cosine_microseconds": 0.1,
        "sine_uncertainty_microseconds": 0.01,
        "cosine_uncertainty_microseconds": 0.01,
        "sine_cosine_correlation": 0.0,
        "sine_cosine_covariance_microseconds_squared": 0.0,
        "recovered_phase_radians": 0.0,
        "phase_standard_error_radians": 0.01,
        "signed_wrapped_phase_error_radians": 0.0,
        "toa_adjustment_error_microseconds": 0.0,
        "toa_adjustment_maximum_absolute_error_microseconds": 0.0,
        "uncentered_toa_residual_target_maximum_absolute_error_microseconds": 0.0,
        "dm_maximum_absolute_error": 0.0,
        "ordinary_fit_converged": True,
        "joint_fit_converged": True,
        "ordinary_absorption_fraction": 0.0,
        "signal_astrometry_correlation": 0.0,
        "solver_audit_required": audit_required,
        "solver_audit_pass": True,
        "solver_comparison": None,
        "full_covariance_solver": None,
        "input_binding": _input_binding(),
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
    }
    if case["family"] != "annual":
        record["candidate_eligible"] = True
    if audit_required:
        record["solver_comparison"] = {
            "amplitude_difference_microseconds": 0.0,
            "phase_difference_radians": 0.0,
            "chi2_difference": 0.0,
        }
        record["full_covariance_solver"] = {
            "solver": "WidebandTOAFitter_explicit_full_covariance",
            "completed": True,
            "returned_chi2": 1.0,
            "sine_us": 0.1,
            "cosine_us": 0.1,
            "amplitude_us": 0.14,
            "phase_radians": 0.0,
            "sine_uncertainty_us": 0.01,
            "cosine_uncertainty_us": 0.01,
            "chi2": 1.0,
            "reduced_chi2": 1.0,
            "weighted_rms_us": 1.0,
            "free_parameter_count": 284,
            "release_red_noise_preserved": True,
            "wavex_absent": True,
        }
    return record


def _fake_gate() -> dict[str, object]:
    return {
        "status": "pass",
        "failures": [],
        "predecessors": {"threshold_delta_chi2": 1.0},
        "freeze_sha256": "f" * 64,
    }


def test_v027_reuses_never_executed_v023_inventory_without_seed_churn() -> None:
    inventory = build_v023_inventory()
    assert inventory["inventory_sha256"] == INVENTORY_SHA256
    assert len(inventory["cases"]) == 344


@pytest.mark.parametrize(
    "payload",
    [
        '{"execution_authorized":false,"execution_authorized":true}',
        '{"input_binding":{"active_toas":0,"active_toas":660}}',
    ],
)
def test_trusted_json_rejects_top_level_and_nested_duplicate_members(
    payload: str,
) -> None:
    with pytest.raises(TrustedJSONError, match="duplicate JSON member"):
        _loads_trusted_json(payload, "test payload")


def test_runner_contains_no_ordinary_trusted_json_reads() -> None:
    source = Path(runner_module.__file__).read_text(encoding="utf-8")
    assert source.count("json.loads(") == 1
    assert "object_pairs_hook=_reject_duplicate_members" in source


@pytest.mark.parametrize("semantic", [None, "fail"])
def test_readiness_semantic_must_explicitly_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    semantic: str | None,
) -> None:
    freeze_path = tmp_path / "readiness.json"
    freeze_path.write_text(json.dumps({"execution_readiness": semantic}))
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.READINESS_FREEZE_PATH",
        str(freeze_path),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027._verify_freeze",
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
        "pulsar_pilot.pilot2_injection_runner_v027.READINESS_FREEZE_PATH",
        str(freeze_path),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027._verify_freeze",
        lambda *_: {
            "status": "pass",
            "failures": [],
            "freeze_sha256": "r" * 64,
        },
    )
    assert verify_readiness_freeze()["status"] == "pass"


def test_readiness_freeze_rejects_duplicate_member_before_semantic_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    freeze_path = tmp_path / "readiness.json"
    freeze_path.write_text('{"execution_readiness":"hold","execution_readiness":"pass"}')
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.READINESS_FREEZE_PATH",
        str(freeze_path),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027._verify_freeze",
        lambda *_: {
            "status": "pass",
            "failures": [],
            "freeze_sha256": "r" * 64,
        },
    )
    result = verify_readiness_freeze()
    assert result["status"] == "fail"
    assert any("duplicate JSON member" in item for item in result["failures"])


def test_malformed_present_execution_freeze_stops_before_predecessor_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    freeze_path = tmp_path / "protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.7.json"
    freeze_path.parent.mkdir(parents=True)
    freeze_path.write_text("{not-json")
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.repository_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.verify_implementation_freeze",
        lambda: {"status": "pass", "failures": [], "freeze_sha256": "i" * 64},
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.verify_readiness_freeze",
        lambda: {"status": "pass", "failures": [], "freeze_sha256": "r" * 64},
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.verify_predecessor_bindings",
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
        "pulsar_pilot.pilot2_injection_runner_v027.verify_implementation_freeze",
        lambda: {
            "status": "pass",
            "failures": [],
            "freeze_sha256": implementation_freeze_sha,
        },
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.verify_readiness_freeze",
        lambda: {
            "status": "pass",
            "failures": [],
            "freeze_sha256": readiness_freeze_sha,
        },
    )
    runner = load_yaml(repository_root() / RUNNER_CONFIG_PATH)
    predecessors = {
        key: binding["sha256"] for key, binding in runner["predecessor_bindings"].items()
    }
    frozen_path = "frozen.txt"
    (tmp_path / frozen_path).write_text("frozen\n")
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.repository_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.implementation_sha256",
        lambda: "m" * 64,
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027._configs",
        lambda: ({}, {}, runner),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.EXECUTION_FREEZE_FROZEN_PATHS",
        (frozen_path,),
    )
    freeze = {
        "schema_version": 1,
        "freeze_id": "pilot2-b1937-injection-execution-freeze-v0.2.7",
        "status": "frozen_before_first_v0.2.7_injection_case",
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
        "implementation_sha256": "m" * 64,
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
            frozen_path: hash_file(tmp_path / frozen_path, "sha256"),
        },
    }
    freeze_path = tmp_path / "protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.7.json"
    freeze_path.parent.mkdir(parents=True)
    freeze_path.write_text(json.dumps(freeze))
    assert verify_repository_execution_authorization()["status"] == "pass"
    duplicate_authorization = json.dumps(freeze).replace(
        '"execution_authorized": true',
        '"execution_authorized": false, "execution_authorized": true',
    )
    freeze_path.write_text(duplicate_authorization)
    duplicate_result = verify_repository_execution_authorization()
    assert duplicate_result["status"] == "fail"
    assert duplicate_result["predecessors_loaded"] is False
    assert any("duplicate JSON member" in item for item in duplicate_result["failures"])
    freeze["authorized_primary_fits"] = 687
    freeze_path.write_text(json.dumps(freeze))
    result = verify_repository_execution_authorization()
    assert result["status"] == "fail"
    assert any("primary-fit count is invalid" in item for item in result["failures"])


@pytest.mark.parametrize("unsafe_path", ["../outside.json", "/tmp/outside.json"])
def test_frozen_hash_path_escape_fails_before_hash_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_path: str,
) -> None:
    monkeypatch.setattr(
        runner_module,
        "hash_file",
        lambda *_: pytest.fail("unsafe hash target was accessed"),
    )
    failures = _verify_exact_repository_hashes(
        tmp_path,
        {unsafe_path: "0" * 64},
        ("expected.json",),
        "execution",
    )
    assert failures
    assert "path set is not exact" in failures[0]


def test_frozen_hash_contract_requires_exact_complete_path_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runner_module,
        "hash_file",
        lambda *_: pytest.fail("hashing began before exact-set validation"),
    )
    failures = _verify_exact_repository_hashes(
        tmp_path,
        {"one.json": "0" * 64},
        ("one.json", "two.json"),
        "execution",
    )
    assert failures
    assert "missing=['two.json']" in failures[0]


def test_symlinked_hash_target_cannot_escape_repository(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.json"
    outside.write_text("outside\n")
    (tmp_path / "link.json").symlink_to(outside)
    failures = _verify_exact_repository_hashes(
        tmp_path,
        {"link.json": hash_file(outside, "sha256")},
        ("link.json",),
        "execution",
    )
    assert failures == ["v0.2.7 execution hash path escapes repository: link.json"]


def test_attempt_journal_precedes_execution_and_health_remains_outcome_free(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    case = _first_case()
    path = _record_path(ledger.data_root, 1, case)
    ledger.begin_attempt(1, case, "b" * 64, _input_binding_sha(), path)
    state = ledger.load()
    assert state["active_attempt"]["case_id"] == case["case_id"]
    assert state["active_attempt"]["seed"] == case["seed"]
    assert state["active_attempt"]["status"] == "started_seed_consumed"
    assert state["active_attempt"]["input_binding_sha256"] == _input_binding_sha()
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


def test_durable_json_syncs_file_before_replace_and_directory_after(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    original_fsync = os.fsync
    original_replace = os.replace
    original_fcntl = runner_module.fcntl.fcntl

    def tracked_fsync(file_descriptor: int) -> None:
        kind = (
            "directory_fsync" if stat.S_ISDIR(os.fstat(file_descriptor).st_mode) else "file_fsync"
        )
        events.append(kind)
        original_fsync(file_descriptor)

    def tracked_fullfsync(file_descriptor: int, operation: int) -> int:
        events.append("file_fullfsync")
        return original_fcntl(file_descriptor, operation)

    def tracked_replace(source: Path, destination: Path) -> None:
        events.append("replace")
        original_replace(source, destination)

    monkeypatch.setattr(runner_module.os, "fsync", tracked_fsync)
    monkeypatch.setattr(runner_module.os, "replace", tracked_replace)
    if runner_module.sys.platform == "darwin":
        monkeypatch.setattr(runner_module.fcntl, "fcntl", tracked_fullfsync)
    path = tmp_path / "durable.json"
    _durable_atomic_json(path, {"durable": True})
    assert json.loads(path.read_text()) == {"durable": True}
    assert events.index("file_fsync") < events.index("replace")
    if runner_module.sys.platform == "darwin":
        assert events.index("file_fsync") < events.index("file_fullfsync")
        assert events.index("file_fullfsync") < events.index("replace")
    assert events.index("replace") < events.index("directory_fsync")


def test_nested_directory_entries_are_each_synced_in_their_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[tuple[str, str]] = []
    original_mkdir = os.mkdir
    original_sync_directory = runner_module._sync_directory

    def relative(path: Path) -> str:
        return str(Path(path).relative_to(tmp_path)) or "."

    def tracked_mkdir(path: Path, *args: object, **kwargs: object) -> None:
        events.append(("mkdir", relative(Path(path))))
        original_mkdir(path, *args, **kwargs)

    def tracked_sync(path: Path) -> None:
        events.append(("sync", relative(path)))
        original_sync_directory(path)

    monkeypatch.setattr(runner_module.os, "mkdir", tracked_mkdir)
    monkeypatch.setattr(runner_module, "_sync_directory", tracked_sync)
    _durable_mkdirs(tmp_path / "a/b/c")
    assert events == [
        ("mkdir", "a"),
        ("sync", "."),
        ("mkdir", "a/b"),
        ("sync", "a"),
        ("mkdir", "a/b/c"),
        ("sync", "a/b"),
    ]


def test_case_directories_are_durably_precreated(tmp_path: Path) -> None:
    prepare_case_directories(tmp_path)
    case_root = tmp_path / "derived/pilot2/calibration-v0.2.7/injections"
    assert case_root.is_dir()
    assert {path.name for path in case_root.iterdir()} == {
        "main",
        "phase_reference",
        "annual",
        "boundary",
    }


def test_attempt_durability_failure_stops_before_executor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    runner = load_yaml(repository_root() / RUNNER_CONFIG_PATH)
    lock_path = ledger.data_root / runner["predecessor_bindings"]["threshold_lock"]["logical_path"]
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("{}")
    monkeypatch.setattr(runner_module, "verify_execution_gate", lambda *_: _fake_gate())
    monkeypatch.setattr(runner_module, "prepare_context", lambda *_: _context())

    class NoHeartbeat:
        def __enter__(self) -> object:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr(runner_module, "HeartbeatService", lambda *_: NoHeartbeat())
    monkeypatch.setattr(
        runner_module,
        "execute_injection_case",
        lambda *_: pytest.fail("executor called after failed durable attempt commit"),
    )
    original_sync = runner_module._sync_regular_file
    calls = 0

    def fail_first_sync(file_descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("simulated attempt-journal sync failure")
        original_sync(file_descriptor)

    monkeypatch.setattr(runner_module, "_sync_regular_file", fail_first_sync)
    with pytest.raises(OSError, match="attempt-journal sync failure"):
        execute(ledger.data_root)
    state = ledger.load()
    assert state["stage_status"][STAGE] == "fail"
    assert state["hard_stop"] is not None
    assert len(state["completed_cases"]) == 0


def test_case_directory_sync_failure_stops_before_executor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    runner = load_yaml(repository_root() / RUNNER_CONFIG_PATH)
    lock_path = ledger.data_root / runner["predecessor_bindings"]["threshold_lock"]["logical_path"]
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("{}")
    monkeypatch.setattr(runner_module, "verify_execution_gate", lambda *_: _fake_gate())
    monkeypatch.setattr(runner_module, "prepare_context", lambda *_: _context())

    class NoHeartbeat:
        def __enter__(self) -> object:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr(runner_module, "HeartbeatService", lambda *_: NoHeartbeat())
    monkeypatch.setattr(
        runner_module,
        "execute_injection_case",
        lambda *_: pytest.fail("executor called after failed case-directory sync"),
    )
    original_fsync = os.fsync
    failed = False

    def fail_first_directory_sync(file_descriptor: int) -> None:
        nonlocal failed
        if stat.S_ISDIR(os.fstat(file_descriptor).st_mode) and not failed:
            failed = True
            raise OSError("simulated case-directory sync failure")
        original_fsync(file_descriptor)

    monkeypatch.setattr(runner_module.os, "fsync", fail_first_directory_sync)
    with pytest.raises(OSError, match="case-directory sync failure"):
        execute(ledger.data_root)
    state = ledger.load()
    assert state["stage_status"][STAGE] == "fail"
    assert state["hard_stop"] is not None
    assert len(state["completed_cases"]) == 0


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
        _input_binding_sha(),
        _record_path(ledger.data_root, 1, case),
    )
    with pytest.raises(RuntimeError, match="lacks a verified adoptable artifact"):
        recover_active_attempt(
            ledger,
            [case],
            "b" * 64,
            _input_binding_sha(),
            _input_binding(),
            1.0,
            set(),
            result_path,
        )
    state = ledger.load()
    result = json.loads(result_path.read_text())
    assert state["stage_status"][STAGE] == "fail"
    assert state["hard_stop"] is not None
    assert state["active_attempt"]["case_id"] == case["case_id"]
    assert result["failure_class"] == ("interrupted_consumed_attempt_without_verified_artifact")
    assert result["partial_scientific_metrics_recorded"] is False


def test_incomplete_attempt_artifact_is_rejected_and_terminally_consumed(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    case = _first_case()
    binding = "b" * 64
    path = _record_path(ledger.data_root, 1, case)
    ledger.begin_attempt(1, case, binding, _input_binding_sha(), path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"case": case, "execution_binding_sha256": binding}))
    result_path = ledger.data_root / "run_records/pilot2/failure.json"
    with pytest.raises(RuntimeError, match="lacks a verified adoptable artifact"):
        recover_active_attempt(
            ledger,
            [case],
            binding,
            _input_binding_sha(),
            _input_binding(),
            1.0,
            set(),
            result_path,
        )
    state = ledger.load()
    assert case["case_id"] not in state["completed_cases"]
    assert state["stage_status"][STAGE] == "fail"
    assert state["hard_stop"] is not None


def test_complete_attempt_artifact_is_adopted_without_recomputation(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    case = _first_case()
    binding = "b" * 64
    path = _record_path(ledger.data_root, 1, case)
    ledger.begin_attempt(1, case, binding, _input_binding_sha(), path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_complete_record(case, binding)))
    record = recover_active_attempt(
        ledger,
        [case],
        binding,
        _input_binding_sha(),
        _input_binding(),
        1.0,
        set(),
        ledger.data_root / "run_records/pilot2/failure.json",
    )
    state = ledger.load()
    assert record is not None
    assert case["case_id"] in state["completed_cases"]
    assert state["active_attempt"] is None
    assert state["attempt_history"][-1]["status"] == (
        "verified_artifact_adopted_without_recomputation"
    )


def test_interrupted_artifact_rejects_nested_duplicate_binding_member(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    case = _first_case()
    binding = "b" * 64
    path = _record_path(ledger.data_root, 1, case)
    ledger.begin_attempt(1, case, binding, _input_binding_sha(), path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_complete_record(case, binding)).replace(
        '"active_toas": 660',
        '"active_toas": 0, "active_toas": 660',
    )
    path.write_text(payload)
    with pytest.raises(RuntimeError, match="lacks a verified adoptable artifact"):
        recover_active_attempt(
            ledger,
            [case],
            binding,
            _input_binding_sha(),
            _input_binding(),
            1.0,
            set(),
            ledger.data_root / "run_records/pilot2/failure.json",
        )
    state = ledger.load()
    assert state["stage_status"][STAGE] == "fail"
    assert state["hard_stop"] is not None


def test_version_ledger_rejects_duplicate_members(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    payload = ledger.path.read_text().replace(
        '"hard_stop": null',
        '"hard_stop": {"reason": "concealed"}, "hard_stop": null',
    )
    ledger.path.write_text(payload)
    with pytest.raises(RuntimeError, match="duplicate JSON member"):
        ledger.load()


def test_data_root_marker_rejects_duplicate_members(tmp_path: Path) -> None:
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    marker = data_root / ".project-recherche-data-root.json"
    marker.write_text(
        '{"schema_version":1,"project":"wrong","project":"project-recherche-pulsar-pilot"}'
    )
    with pytest.raises(RuntimeError, match="duplicate JSON member"):
        _require_initialized_data_root(data_root)


def test_recorded_attempt_is_reconciled_without_recomputation(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    case = _first_case()
    binding = "b" * 64
    path = _record_path(ledger.data_root, 1, case)
    ledger.begin_attempt(1, case, binding, _input_binding_sha(), path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_complete_record(case, binding)))
    ledger.record_case(STAGE, str(case["case_id"]), path)
    recover_active_attempt(
        ledger,
        [case],
        binding,
        _input_binding_sha(),
        _input_binding(),
        1.0,
        set(),
        ledger.data_root / "run_records/pilot2/failure.json",
    )
    state = ledger.load()
    assert state["active_attempt"] is None
    assert state["attempt_history"][-1]["status"] == (
        "verified_ledger_record_reconciled_without_recomputation"
    )


def test_annual_interrupted_artifact_is_adopted_before_group_grading(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    case = _first_family_case("annual")
    binding = "b" * 64
    sequence = next(
        index
        for index, item in enumerate(build_v023_inventory()["cases"], 1)
        if item["case_id"] == case["case_id"]
    )
    path = _record_path(ledger.data_root, sequence, case)
    ledger.begin_attempt(sequence, case, binding, _input_binding_sha(), path)
    path.parent.mkdir(parents=True, exist_ok=True)
    annual_record = _complete_record(case, binding)
    assert "candidate_eligible" not in annual_record
    path.write_text(json.dumps(annual_record))
    recovered = recover_active_attempt(
        ledger,
        [case],
        binding,
        _input_binding_sha(),
        _input_binding(),
        1.0,
        set(),
        ledger.data_root / "run_records/pilot2/failure.json",
    )
    assert recovered == annual_record
    assert ledger.load()["active_attempt"] is None


def test_nonannual_recovery_requires_candidate_eligibility_field() -> None:
    case = _first_case()
    record = _complete_record(case, "b" * 64)
    record.pop("candidate_eligible")
    with pytest.raises(RuntimeError, match="schema differs"):
        validate_complete_case_record(record, case, "b" * 64, 1.0, False, _input_binding())


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("observed_residual_vector_loaded",), 0),
        (("active_toas",), 660.0),
        (("covariance_shape",), [1320.0, 1320]),
        (("reference_epoch_mjd_tdb",), 50001.0),
        (("frequency_grid", "span_days"), 1001.0),
        (("frequency_grid", "frequency_count"), 167),
    ],
)
def test_complete_record_requires_exact_typed_trusted_input_binding(
    path: tuple[str, ...], replacement: object
) -> None:
    case = _first_case()
    record = _complete_record(case, "b" * 64)
    cursor = record["input_binding"]
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = replacement
    with pytest.raises(RuntimeError, match="input binding"):
        validate_complete_case_record(record, case, "b" * 64, 1.0, False, _input_binding())


def test_execution_binding_commits_to_trusted_input_binding() -> None:
    original = _input_binding()
    changed = _input_binding()
    changed["reference_epoch_mjd_tdb"] = 50001.0
    common = ("a" * 64, "b" * 64, "c" * 64, "d" * 64)
    assert _execution_binding_sha256(*common, _input_binding_sha256(original)) != (
        _execution_binding_sha256(*common, _input_binding_sha256(changed))
    )


def test_solver_audit_recovery_requires_complete_nested_schema() -> None:
    inventory = build_v023_inventory()
    audit_id = inventory["solver_audit_case_ids"][0]
    case = next(item for item in inventory["cases"] if item["case_id"] == audit_id)
    record = _complete_record(case, "b" * 64, audit_required=True)
    assert (
        validate_complete_case_record(record, case, "b" * 64, 1.0, True, _input_binding()) == record
    )
    record["full_covariance_solver"].pop("returned_chi2")
    with pytest.raises(RuntimeError, match="full-covariance solver schema differs"):
        validate_complete_case_record(record, case, "b" * 64, 1.0, True, _input_binding())


def test_keyboard_interrupt_leaves_durable_consumed_attempt_for_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _ledger(tmp_path)
    runner = load_yaml(repository_root() / RUNNER_CONFIG_PATH)
    lock_path = ledger.data_root / runner["predecessor_bindings"]["threshold_lock"]["logical_path"]
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("{}")
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.verify_execution_gate",
        lambda *_: _fake_gate(),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.prepare_context",
        lambda *_: _context(),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.execute_injection_case",
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
        "pulsar_pilot.pilot2_injection_runner_v027.verify_execution_gate",
        lambda *_: _fake_gate(),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.prepare_context",
        lambda *_: pytest.fail("context loaded after threshold binding failure"),
    )
    with pytest.raises(FileNotFoundError):
        execute(ledger.data_root)
    state = ledger.load()
    result_path = ledger.data_root / "run_records/pilot2/injection-evaluation-v0.2.7.json"
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
        "pulsar_pilot.pilot2_injection_runner_v027.verify_predecessor_bindings",
        lambda *_: pytest.fail("predecessors loaded before authorization"),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v027.prepare_context",
        lambda *_: pytest.fail("context loaded before authorization"),
    )
    gate = verify_execution_gate(ledger.data_root)
    assert gate["status"] in {"locked", "fail"}
    assert gate["predecessors_loaded"] is False
    with pytest.raises(RuntimeError, match="execution is locked"):
        execute(ledger.data_root)
