from __future__ import annotations

import copy
import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from pulsar_pilot import pilot2_runtime_core
from pulsar_pilot.pilot2_durable_ledger import (
    EXPECTED_GATE_NAMES,
    STAGE,
    SingleWriterLock,
    V028Ledger,
    durable_atomic_json,
    validate_terminal_result,
)
from pulsar_pilot.pilot2_injection_runner_v028 import (
    TEMPORARY_GENERATION,
    candidate_science_control_sha256,
    initialize_temporary_validation_root,
    zero_case_dry_run,
)
from pulsar_pilot.pilot2_offline_resources import (
    NetworkDeniedError,
    NetworkDeny,
    ResourceOpenTracer,
    validate_environment_manifest,
    validate_resource_manifest,
)
from pulsar_pilot.pilot2_release_contract import (
    BASE_CONFIG_PATH,
    EXECUTION_FREEZE_KEYS,
    EXPECTED_CASE_COUNTS,
    INVENTORY_SHA256,
    REMEDIATION_CONFIG_PATH,
    RUNNER_CONFIG_PATH,
    _validate_execution_freeze,
    verify_repository_execution_authorization,
)
from pulsar_pilot.pilot2_runtime_core import (
    _load_or_recover_active_attempt,
    append_annual_period,
    validate_annual_mask,
)
from pulsar_pilot.pilot2_trusted_data import (
    TrustedDataError,
    loads_json,
    loads_yaml,
)
from pulsar_pilot.provenance import hash_file

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def _ledger(data_root: Path) -> V028Ledger:
    return V028Ledger(
        data_root,
        inventory_sha256=INVENTORY_SHA256,
        implementation_sha256=SHA_A,
        science_control_sha256=SHA_B,
        environment_manifest_sha256=SHA_C,
        resource_manifest_sha256=SHA_D,
    )


@pytest.mark.parametrize(
    "payload",
    [
        '{"execution_authorized":false,"execution_authorized":true}',
        '{"audit":{"status":"hold","status":"pass"}}',
        '{"value":NaN}',
        '{"value":Infinity}',
    ],
)
def test_trusted_json_rejects_ambiguous_or_nonfinite_payloads(payload: str) -> None:
    with pytest.raises(TrustedDataError):
        loads_json(payload)


@pytest.mark.parametrize(
    "payload",
    [
        "execution_authorized: false\nexecution_authorized: true\n",
        "audit:\n  status: hold\n  status: pass\n",
        "value: .nan\n",
        "true: forbidden_non_string_mapping_key\n",
    ],
)
def test_trusted_yaml_rejects_ambiguous_or_nonfinite_payloads(payload: str) -> None:
    with pytest.raises(TrustedDataError):
        loads_yaml(payload)


def test_single_writer_lock_excludes_a_second_writer_and_releases(tmp_path: Path) -> None:
    first = SingleWriterLock(tmp_path)
    second = SingleWriterLock(tmp_path)
    first.acquire()
    try:
        with pytest.raises(RuntimeError, match="another live"):
            second.acquire()
    finally:
        first.release()
    with second:
        assert second.held
    assert not second.held


def test_process_death_releases_lock_without_deleting_lock_file(tmp_path: Path) -> None:
    code = """
import sys
import time
from pathlib import Path
from pulsar_pilot.pilot2_durable_ledger import SingleWriterLock
lock = SingleWriterLock(Path(sys.argv[1]))
lock.acquire()
print('LOCKED', flush=True)
time.sleep(60)
"""
    child = subprocess.Popen(
        [sys.executable, "-c", code, str(tmp_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert child.stdout is not None
    try:
        assert child.stdout.readline().strip() == "LOCKED"
        with pytest.raises(RuntimeError, match="another live"):
            SingleWriterLock(tmp_path).acquire()
    finally:
        child.terminate()
        child.wait(timeout=10)
    lock_file = tmp_path / "run_records/pilot2/locks/pilot2-v0.2.8.lock"
    assert lock_file.is_file()
    with SingleWriterLock(tmp_path):
        pass


def test_durable_json_replaces_atomically_without_fixed_tmp_files(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "record.json"
    durable_atomic_json(target, {"sequence": 1})
    durable_atomic_json(target, {"sequence": 2})
    assert json.loads(target.read_text(encoding="utf-8")) == {"sequence": 2}
    assert not list(target.parent.glob("*.tmp"))


def test_pending_ledger_and_health_are_outcome_free(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    state = ledger.load()
    health = json.loads(ledger.health_path.read_text(encoding="utf-8"))
    assert state["stage_status"][STAGE] == "pending"
    assert state["completed_cases"] == {}
    assert health["scientific_outcomes_in_health_record"] is False
    assert "payload" not in health
    assert "candidate" not in health


def test_ledger_rejects_extra_fields_and_false_pass(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    state = ledger.empty()
    state["extra"] = True
    with pytest.raises(TrustedDataError, match="member mismatch"):
        ledger.validate(state)

    state = ledger.empty()
    state["stage_status"][STAGE] = "pass"
    with pytest.raises(TrustedDataError, match="PASS lacks 344"):
        ledger.validate(state)


def test_ledger_rejects_duplicate_case_sequence(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    state = ledger.empty()
    state["stage_status"][STAGE] = "running"
    state["active_stage"] = STAGE
    state["active_stage_started_utc"] = "2026-08-11T00:00:00Z"
    state["execution_binding_sha256"] = SHA_A
    state["runtime_active"] = True
    state["runner_pid"] = 123
    artifact = {
        "sequence": 1,
        "family": "main",
        "logical_path": "derived/case.json",
        "bytes": 1,
        "sha256": SHA_A,
    }
    state["completed_cases"] = {"case-a": artifact, "case-b": copy.deepcopy(artifact)}
    with pytest.raises(TrustedDataError, match="duplicate sequence"):
        ledger.validate(state)


def _passing_terminal_result() -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": "pilot2-b1937-injection-remediation-v0.2.8",
        "status": "pass",
        "inventory_sha256": INVENTORY_SHA256,
        "execution_binding_sha256": SHA_A,
        "completed_case_count": 344,
        "authorized_primary_fits": 688,
        "solver_audits": 35,
        "annual_mask_sha256": SHA_B,
        "threshold_lock_sha256": SHA_C,
        "threshold_retuned": False,
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
        "promotion_grade_executed": False,
        "science_cases_executed_this_invocation": 344,
        "payload": {
            "schema_version": 1,
            "stage": STAGE,
            "status": "pass",
            "gates": [
                {
                    "name": name,
                    "observed": 0,
                    "comparator": "==",
                    "limit": 0,
                    "status": "pass",
                }
                for name in sorted(EXPECTED_GATE_NAMES)
            ],
            "diagnostics": {
                "all_triggered_main_phase_error_role": "diagnostic_not_hard_gate",
                "all_triggered_main_phase_error_p90_radians": 0.0,
                "phase_reference_error_p90_radians": 0.0,
                "strong_control_minimum_recovery": 1.0,
                "frequency_recovery_rate": 1.0,
                "median_amplitude_bias_fraction": 0.0,
                "monotonic_periods": 5,
                "bracketed_periods": 5,
            },
            "observed_residual_vector_used": False,
            "observed_periodic_scan_executed": False,
        },
    }


def test_terminal_result_requires_exact_all_pass_gate_set() -> None:
    result = _passing_terminal_result()
    assert (
        validate_terminal_result(
            result,
            inventory_sha256=INVENTORY_SHA256,
            execution_binding_sha256=SHA_A,
            annual_mask_sha256=SHA_B,
        )
        == result
    )
    result["payload"]["gates"].pop()
    with pytest.raises(TrustedDataError, match="gate set is not exact"):
        validate_terminal_result(
            result,
            inventory_sha256=INVENTORY_SHA256,
            execution_binding_sha256=SHA_A,
            annual_mask_sha256=SHA_B,
        )


def test_terminal_result_rejects_unknown_top_level_member() -> None:
    result = _passing_terminal_result()
    result["unknown"] = True
    with pytest.raises(TrustedDataError, match="member mismatch"):
        validate_terminal_result(
            result,
            inventory_sha256=INVENTORY_SHA256,
            execution_binding_sha256=SHA_A,
            annual_mask_sha256=SHA_B,
        )


def test_artifact_verification_detects_tampering(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    ledger.begin_stage(SHA_A)
    case_path = tmp_path / "derived" / "case.json"
    durable_atomic_json(case_path, {"value": 1})
    ledger.begin_attempt(
        case_id="case-a",
        sequence=1,
        seed=1,
        family="main",
        artifact_path=case_path,
        execution_binding_sha256=SHA_A,
        input_binding_sha256=SHA_B,
    )
    ledger.record_case("case-a", 1, "main", case_path)
    ledger.clear_attempt("committed_without_interruption")
    assert ledger.verify_artifacts()["status"] == "pass"
    durable_atomic_json(case_path, {"value": 2})
    assert ledger.verify_artifacts()["failures"] == ["completed_case:case-a"]


def _interrupted_case() -> dict[str, object]:
    return {"case_id": "case-a", "seed": 17, "family": "main"}


def _begin_interrupted_attempt(ledger: V028Ledger, artifact_path: Path) -> None:
    ledger.save(ledger.empty())
    ledger.begin_stage(SHA_A)
    ledger.begin_attempt(
        case_id="case-a",
        sequence=1,
        seed=17,
        family="main",
        artifact_path=artifact_path,
        execution_binding_sha256=SHA_A,
        input_binding_sha256=SHA_B,
    )


def test_interrupted_attempt_without_artifact_is_consumed_terminal_stop(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path)
    artifact = tmp_path / "derived/missing-case.json"
    _begin_interrupted_attempt(ledger, artifact)
    with pytest.raises(RuntimeError, match="consumed attempt lacks"):
        _load_or_recover_active_attempt(
            ledger=ledger,
            cases=[_interrupted_case()],
            execution_binding=SHA_A,
            input_binding_sha256=SHA_B,
            trusted_input_binding={},
            threshold=1.0,
            audit_ids=set(),
        )
    state = ledger.load()
    assert state["stage_status"][STAGE] == "fail"
    assert state["hard_stop"]["reason"] == "interrupted_consumed_attempt_without_verified_artifact"
    assert state["attempt_history"][0]["disposition"] == "consumed_terminal_hard_stop"


def test_interrupted_attempt_adopts_verified_artifact_without_recomputation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _ledger(tmp_path)
    artifact = tmp_path / "derived/completed-case.json"
    durable_atomic_json(artifact, {"record": "complete"})
    _begin_interrupted_attempt(ledger, artifact)
    monkeypatch.setattr(
        pilot2_runtime_core,
        "validate_complete_case_record",
        lambda value, **_kwargs: value,
    )
    record = _load_or_recover_active_attempt(
        ledger=ledger,
        cases=[_interrupted_case()],
        execution_binding=SHA_A,
        input_binding_sha256=SHA_B,
        trusted_input_binding={},
        threshold=1.0,
        audit_ids=set(),
    )
    state = ledger.load()
    assert record == {"record": "complete"}
    assert "case-a" in state["completed_cases"]
    assert state["active_attempt"] is None
    assert state["attempt_history"][0]["disposition"] == (
        "verified_artifact_adopted_without_recomputation"
    )


def _resource_manifest(data_root: Path) -> dict[str, object]:
    repository = data_root / "controlled" / "offline-resources"
    clocks = data_root / "controlled" / "clock-overrides"
    repository.mkdir(parents=True)
    clocks.mkdir(parents=True)
    resource = repository / "index.txt"
    resource.write_text("index\n", encoding="utf-8")
    return {
        "schema_version": 1,
        "manifest_id": "test-resource-manifest",
        "status": "frozen_local_only",
        "local_repository_relative_path": "controlled/offline-resources",
        "clock_override_relative_path": "controlled/clock-overrides",
        "entries": [
            {
                "logical_name": "clock-index",
                "controlled_relative_path": "controlled/offline-resources/index.txt",
                "source_url_or_publication": "test fixture",
                "license_or_redistribution_status": "test-only",
                "bytes": resource.stat().st_size,
                "sha256": hash_file(resource, "sha256"),
                "consumer": "PINT",
                "resolution_role": "global_clock_index",
            }
        ],
        "required_resource_classes": ["global_clock_index"],
    }


def test_resource_manifest_hashes_every_local_resource(tmp_path: Path) -> None:
    manifest = _resource_manifest(tmp_path)
    assert validate_resource_manifest(manifest, data_root=tmp_path) == manifest
    (tmp_path / "controlled/offline-resources/index.txt").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(TrustedDataError, match="identity mismatch"):
        validate_resource_manifest(manifest, data_root=tmp_path)


def test_resource_manifest_rejects_duplicate_identity(tmp_path: Path) -> None:
    manifest = _resource_manifest(tmp_path)
    manifest["entries"] = [manifest["entries"][0], copy.deepcopy(manifest["entries"][0])]
    with pytest.raises(TrustedDataError, match="duplicate identity"):
        validate_resource_manifest(manifest)


def test_resource_manifest_rejects_untraceable_path(tmp_path: Path) -> None:
    manifest = _resource_manifest(tmp_path)
    manifest["entries"][0]["controlled_relative_path"] = "uncontrolled/index.txt"
    with pytest.raises(TrustedDataError, match="outside its controlled repositories"):
        validate_resource_manifest(manifest)


def test_network_deny_counts_and_blocks_connections() -> None:
    with NetworkDeny() as boundary, pytest.raises(NetworkDeniedError):
        socket.getaddrinfo("example.invalid", 443)
    assert boundary.attempts == ["socket.getaddrinfo"]


def test_resource_open_tracer_records_confined_reads(tmp_path: Path) -> None:
    controlled = tmp_path / "controlled"
    controlled.mkdir()
    resource = controlled / "index.txt"
    resource.write_text("index", encoding="utf-8")
    with ResourceOpenTracer(controlled) as tracer:
        resource.read_text(encoding="utf-8")
        (tmp_path / "outside.txt").write_text("outside", encoding="utf-8")
    assert tracer.opened == {"index.txt"}


def test_resource_open_tracer_covers_repository_and_clock_override(tmp_path: Path) -> None:
    repository = tmp_path / "controlled/repository"
    override = tmp_path / "controlled/override"
    repository.mkdir(parents=True)
    override.mkdir(parents=True)
    (repository / "index.txt").write_text("index", encoding="utf-8")
    (override / "time_ao.dat").write_text("clock", encoding="utf-8")
    with ResourceOpenTracer(tmp_path, (repository, override)) as tracer:
        (repository / "index.txt").read_text(encoding="utf-8")
        (override / "time_ao.dat").read_text(encoding="utf-8")
    assert tracer.opened == {
        "controlled/repository/index.txt",
        "controlled/override/time_ao.dat",
    }


def _environment_manifest(repository_root: Path, resource_sha: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "manifest_id": "test-environment",
        "status": "frozen_exact_environment",
        "repository_files": {
            name: hash_file(repository_root / name, "sha256")
            for name in ("pixi.lock", "pixi.toml", "pyproject.toml")
        },
        "python": {"version": "3.11.0", "executable_sha256": SHA_A},
        "platform": {
            "macos": "test",
            "kernel_machine": "x86_64",
            "process_machine": "x86_64",
            "pointer_bits": 64,
        },
        "precision": {
            "gate_g1_precision": "pass",
            "extended_precision": True,
            "float64_mantissa_bits": 52,
            "longdouble_mantissa_bits": 63,
        },
        "packages": [
            {
                "name": name,
                "version": "1",
                "build": "test",
                "channel": "test",
                "sha256": SHA_A,
            }
            for name in ("python", "pint-pulsar", "astropy-base", "numpy", "scipy")
        ],
        "critical_modules": {"pint": SHA_A},
        "environment_policy": {"allowed": [], "values_sha256": SHA_A},
        "resource_manifest_sha256": resource_sha,
    }


def test_environment_manifest_binds_lockfiles_and_resource_manifest(
    tmp_path: Path,
) -> None:
    for name in ("pixi.lock", "pixi.toml", "pyproject.toml"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    manifest = _environment_manifest(tmp_path, SHA_B)
    assert (
        validate_environment_manifest(
            manifest,
            repository_root=tmp_path,
            resource_manifest_sha256=SHA_B,
            verify_live=False,
        )
        == manifest
    )
    manifest["resource_manifest_sha256"] = SHA_C
    with pytest.raises(TrustedDataError, match="resource-manifest binding"):
        validate_environment_manifest(
            manifest,
            repository_root=tmp_path,
            resource_manifest_sha256=SHA_B,
            verify_live=False,
        )


def test_environment_manifest_checks_live_runtime_when_enabled(
    tmp_path: Path,
) -> None:
    for name in ("pixi.lock", "pixi.toml", "pyproject.toml"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    manifest = _environment_manifest(tmp_path, SHA_B)
    with pytest.raises(TrustedDataError, match="live Python version"):
        validate_environment_manifest(
            manifest,
            repository_root=tmp_path,
            resource_manifest_sha256=SHA_B,
        )


def test_repository_execution_gate_is_locked_before_execution_freeze() -> None:
    gate = verify_repository_execution_authorization()
    assert gate["status"] == "locked"
    assert gate["predecessors_loaded"] is False
    assert any("execution freeze is absent" in item for item in gate["failures"])


def test_every_science_control_file_changes_the_candidate_binding(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    paths = (BASE_CONFIG_PATH, REMEDIATION_CONFIG_PATH, RUNNER_CONFIG_PATH)
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repository / relative, target)
    baseline = candidate_science_control_sha256(tmp_path)
    for relative in paths:
        isolated = tmp_path / relative
        original = isolated.read_text(encoding="utf-8")
        isolated.write_text(original + "\n# controlled mutation\n", encoding="utf-8")
        assert candidate_science_control_sha256(tmp_path) != baseline
        isolated.write_text(original, encoding="utf-8")


def _execution_freeze_fixture(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    artifacts: dict[str, dict[str, str]] = {}
    for name in ("resource", "environment", "audit-record", "audit-disposition", "audit-report"):
        path = tmp_path / f"{name}.json"
        path.write_text(f"{name}\n", encoding="utf-8")
        artifacts[name] = {"path": path.name, "sha256": hash_file(path, "sha256")}
    predecessor_sha = {"threshold_lock": SHA_A, "prior_terminal": SHA_B}
    freeze: dict[str, object] = {
        "schema_version": 1,
        "freeze_id": "pilot2-b1937-injection-execution-freeze-v0.2.8",
        "recorded_utc": "2026-08-11T00:00:00Z",
        "status": "frozen_before_first_v0.2.8_injection_case",
        "scope": "one synthetic 344-case run",
        "user_authorization": "separate exact authorization",
        "execution_authorized": True,
        "authorized_case_counts": EXPECTED_CASE_COUNTS,
        "authorized_primary_fits": 688,
        "inventory_sha256": INVENTORY_SHA256,
        "implementation_sha256": SHA_A,
        "science_control_sha256": SHA_B,
        "environment_manifest_sha256": artifacts["environment"]["sha256"],
        "resource_manifest_sha256": artifacts["resource"]["sha256"],
        "design_freeze_sha256": SHA_C,
        "remediation_freeze_sha256": SHA_D,
        "implementation_freeze_sha256": SHA_A,
        "readiness_freeze_sha256": SHA_B,
        "audit": {
            "status": "pass",
            "record_path": artifacts["audit-record"]["path"],
            "record_sha256": artifacts["audit-record"]["sha256"],
            "disposition_path": artifacts["audit-disposition"]["path"],
            "disposition_sha256": artifacts["audit-disposition"]["sha256"],
            "report_path": artifacts["audit-report"]["path"],
            "report_sha256": artifacts["audit-report"]["sha256"],
        },
        "data_root": {"data_root_id": "controlled-v028", "marker_sha256": SHA_C},
        "predecessor_sha256": predecessor_sha,
        "threshold_lock_sha256": SHA_A,
        "launch_contract": {
            "session": "managed_persistent_exec_session",
            "detached_background_launch": False,
            "module": "pulsar_pilot.pilot2_injection_runner_v028",
            "command": "run",
        },
        "supervision_policy": {
            "heartbeat_interval_seconds": 30,
            "stale_after_seconds": 90,
            "checkpoint_case_interval": 25,
            "passive_review_interval_seconds": 1800,
            "scientific_outcomes_in_health_record": False,
        },
        "no_reroll": True,
        "threshold_retuning_authorized": False,
        "observed_residual_access_authorized": False,
        "observed_periodic_search_authorized": False,
        "promotion_grade_authorized": False,
        "discovery_claim_authorized": False,
        "stop_rule": "any_failure_terminally_closes_v0.2.8_without_rerun_retune_or_promotion",
        "frozen_sha256": {},
        "next_gate_if_pass": "terminal_closeout",
        "next_gate_if_fail": "preserve_terminal_failure",
    }
    assert set(freeze) == EXECUTION_FREEZE_KEYS
    runner = {
        "manifests": {
            "resource": artifacts["resource"]["path"],
            "environment": artifacts["environment"]["path"],
        },
        "predecessor_bindings": {
            "threshold_lock": {"sha256": SHA_A},
            "prior_terminal": {"sha256": SHA_B},
        },
    }
    return freeze, runner


def test_execution_freeze_checks_audit_artifacts_and_exact_predecessors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    freeze, runner = _execution_freeze_fixture(tmp_path)
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_release_contract.implementation_sha256", lambda _root: SHA_A
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_release_contract.science_control_sha256", lambda _root: SHA_B
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_release_contract.verify_design_freeze",
        lambda _root: {"freeze_sha256": SHA_C},
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_release_contract.verify_v023_remediation_freeze",
        lambda _root: {"freeze_sha256": SHA_D},
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_release_contract.load_science_controls",
        lambda _root: ({}, {}, runner),
    )
    implementation = {"freeze_sha256": SHA_A}
    readiness = {"freeze_sha256": SHA_B}
    assert not _validate_execution_freeze(
        freeze, root=tmp_path, implementation=implementation, readiness=readiness
    )

    altered = copy.deepcopy(freeze)
    altered["predecessor_sha256"]["unfrozen_extra"] = SHA_C
    failures = _validate_execution_freeze(
        altered, root=tmp_path, implementation=implementation, readiness=readiness
    )
    assert "v0.2.8 execution predecessor binding set differs" in failures

    altered = copy.deepcopy(freeze)
    altered["audit"]["status"] = "hold"
    failures = _validate_execution_freeze(
        altered, root=tmp_path, implementation=implementation, readiness=readiness
    )
    assert "v0.2.8 execution audit is not PASS" in failures

    (tmp_path / freeze["audit"]["report_path"]).write_text("tampered\n", encoding="utf-8")
    failures = _validate_execution_freeze(
        freeze, root=tmp_path, implementation=implementation, readiness=readiness
    )
    assert any("execution audit report_path hash mismatch" in item for item in failures)


def test_execution_freeze_rejects_unknown_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    freeze, runner = _execution_freeze_fixture(tmp_path)
    freeze["unexpected"] = True
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_release_contract.load_science_controls",
        lambda _root: ({}, {}, runner),
    )
    failures = _validate_execution_freeze(
        freeze,
        root=tmp_path,
        implementation={"freeze_sha256": SHA_A},
        readiness={"freeze_sha256": SHA_B},
    )
    assert any("member mismatch" in item for item in failures)


def test_zero_case_dry_run_uses_only_temporary_root(tmp_path: Path) -> None:
    data_root = tmp_path / "v028-zero-science"
    initialize_temporary_validation_root(data_root)
    result = zero_case_dry_run(data_root)
    marker = json.loads(
        (data_root / ".project-recherche-data-root.json").read_text(encoding="utf-8")
    )
    assert marker["generation"] == TEMPORARY_GENERATION
    assert result["status"] == "pass"
    assert result["science_cases_executed"] == 0
    assert result["random_draws_generated"] == 0
    assert result["model_fits_executed"] == 0
    assert result["periodic_scans_executed"] == 0
    assert result["external_data_root_accessed"] is False
    assert result["predecessor_artifacts_loaded"] == 0
    assert not (data_root / "derived/pilot2/calibration-v0.2.8/injections").exists()


def test_annual_mask_requires_complete_exact_period_set() -> None:
    mask = {
        "schema_version": 1,
        "run_id": "pilot2-b1937-injection-remediation-v0.2.8",
        "status": "complete",
        "inventory_sha256": INVENTORY_SHA256,
        "execution_binding_sha256": SHA_A,
        "periods": [],
        "updated_utc": "2026-08-11T00:00:00Z",
    }
    with pytest.raises(TrustedDataError, match="lacks an authorized period"):
        validate_annual_mask(mask, execution_binding=SHA_A, allowed_periods=[365.25])


def test_annual_mask_incremental_commit_is_idempotent(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    ledger.begin_stage(SHA_A)
    mask_path = tmp_path / "run_records/pilot2/annual-mask.json"
    kwargs = {
        "mask_path": mask_path,
        "ledger": ledger,
        "execution_binding": SHA_A,
        "allowed_periods": [365.25],
        "period": 365.25,
        "records": [
            {
                "case": {"case_id": "annual-a"},
                "signal_astrometry_correlation": 0.1,
                "ordinary_absorption_fraction": 0.2,
            }
        ],
        "record_artifacts": [{"sha256": SHA_B}],
        "correlation_limit": 0.8,
        "absorption_limit": 0.8,
    }
    first, first_eligible = append_annual_period(**kwargs)
    second, second_eligible = append_annual_period(**kwargs)
    assert first_eligible is second_eligible is True
    assert first["periods"] == second["periods"]
    assert second["status"] == "complete"
    assert ledger.load()["stage_results"]["annual_mask"]["logical_path"] == (
        "run_records/pilot2/annual-mask.json"
    )
