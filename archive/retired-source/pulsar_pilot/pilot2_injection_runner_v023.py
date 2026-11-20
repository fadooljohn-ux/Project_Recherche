from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_yaml
from .injection_integrity import classify_injection_warning_lines
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _directory_size_gib, _peak_rss_gib
from .pilot1_runtime import build_search_frequency_grid, prepare_covariance_gls_scanner
from .pilot2_calibration_runtime import (
    CalibrationLedger,
    HeartbeatService,
    _atomic_json,
    _utc_now,
)
from .pilot2_injection_executor import HEARTBEAT_INTERVAL_SECONDS, InjectionContext
from .pilot2_injection_executor_v023 import execute_injection_case
from .pilot2_injection_remediation import BASE_CONFIG_PATH
from .pilot2_injection_remediation_v023 import (
    CONFIG_PATH as REMEDIATION_CONFIG_PATH,
)
from .pilot2_injection_remediation_v023 import (
    build_v023_inventory,
    verify_remediation_freeze,
)
from .pilot2_injection_runner_v022 import _gate, grade_records
from .pilot2_preflight import _load_release, _network_disabled
from .provenance import hash_file, logical_path

RUNNER_CONFIG_PATH = "config/pilot2_injection_runner_v0.2.3.yaml"
IMPLEMENTATION_FREEZE_PATH = "protocol/PILOT2_INJECTION_RUNNER_FREEZE_v0.2.3.json"
READINESS_FREEZE_PATH = "protocol/PILOT2_INJECTION_EXECUTION_READINESS_FREEZE_v0.2.3.json"
EXECUTION_FREEZE_PATH = "protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.3.json"
STAGE = "injection_remediation_evaluation"
RUN_ID = "pilot2-b1937-injection-remediation-v0.2.3"
IMPLEMENTATION_PATHS = (
    "src/pulsar_pilot/pilot2_injection_runner_v023.py",
    "src/pulsar_pilot/pilot2_injection_executor_v023.py",
    "src/pulsar_pilot/pilot2_injection_remediation_v023.py",
    "src/pulsar_pilot/pilot2_injection_runner_v022.py",
    "src/pulsar_pilot/pilot2_injection_remediation.py",
    "src/pulsar_pilot/injection_integrity.py",
    "src/pulsar_pilot/c1.py",
    "src/pulsar_pilot/c1r1.py",
    "src/pulsar_pilot/c3.py",
    "src/pulsar_pilot/pilot1_benchmark.py",
    "src/pulsar_pilot/pilot1_runtime.py",
    "src/pulsar_pilot/pilot2_preflight.py",
    "src/pulsar_pilot/pilot2_calibration_runtime.py",
)


def _aggregate_sha256(paths: tuple[str, ...]) -> str:
    root = repository_root()
    digest = hashlib.sha256()
    for relative in paths:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def implementation_sha256() -> str:
    return _aggregate_sha256(IMPLEMENTATION_PATHS)


def _configs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = repository_root()
    return (
        load_yaml(root / BASE_CONFIG_PATH),
        load_yaml(root / REMEDIATION_CONFIG_PATH),
        load_yaml(root / RUNNER_CONFIG_PATH),
    )


def _inventory() -> dict[str, Any]:
    return build_v023_inventory()


def _verify_freeze(path_name: str, expected_status: str, label: str) -> dict[str, Any]:
    root = repository_root()
    path = root / path_name
    if not path.is_file():
        return {"status": "locked", "failures": [f"v0.2.3 {label} freeze is absent"]}
    freeze = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != expected_status:
        failures.append(f"v0.2.3 {label} freeze status is invalid")
    if freeze.get("execution_authorized") is not False:
        failures.append(f"v0.2.3 {label} freeze authorizes execution")
    if freeze.get("science_cases_executed_during_validation") != 0:
        failures.append(f"v0.2.3 {label} validation was not zero-science")
    inventory = _inventory()
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append(f"v0.2.3 {label} inventory mismatch")
    if freeze.get("implementation_sha256") != implementation_sha256():
        failures.append(f"v0.2.3 {label} implementation mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"v0.2.3 {label} hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "execution_authorized": False,
        "inventory_sha256": inventory["inventory_sha256"],
        "implementation_sha256": implementation_sha256(),
        "freeze_sha256": hash_file(path, "sha256"),
    }


def verify_implementation_freeze() -> dict[str, Any]:
    return _verify_freeze(
        IMPLEMENTATION_FREEZE_PATH,
        "implementation_frozen_execution_not_authorized",
        "implementation",
    )


def verify_readiness_freeze() -> dict[str, Any]:
    return _verify_freeze(
        READINESS_FREEZE_PATH,
        "execution_readiness_frozen_execution_not_authorized",
        "readiness",
    )


def verify_predecessor_bindings(data_root: Path) -> dict[str, Any]:
    require_initialized_data_root(data_root)
    root = repository_root()
    _, remediation, runner = _configs()
    failures: list[str] = []
    bindings = runner["predecessor_bindings"]
    repository_keys = {"v0.2.2_execution_freeze", "v0.2.2_crash_audit"}
    for key, binding in bindings.items():
        base = root if key in repository_keys else data_root
        path = base / str(binding["logical_path"])
        if not path.is_file() or hash_file(path, "sha256") != binding["sha256"]:
            failures.append(f"Predecessor binding mismatch: {key}")
    if failures:
        return {"status": "fail", "failures": failures}
    v022_ledger = json.loads(
        (data_root / bindings["v0.2.2_ledger"]["logical_path"]).read_text()
    )
    if len(v022_ledger.get("completed_cases", {})) != 0:
        failures.append("v0.2.2 completed-case count changed")
    if v022_ledger.get("runtime_active") is not False:
        failures.append("v0.2.2 crash ledger is unexpectedly active")
    if v022_ledger.get("stage_status", {}).get(STAGE) != "running":
        failures.append("v0.2.2 crash ledger state changed")
    if v022_ledger.get("hard_stop") is not None:
        failures.append("v0.2.2 crash ledger was retrospectively terminalized")
    crash = json.loads((root / bindings["v0.2.2_crash_audit"]["logical_path"]).read_text())
    consumed = remediation["consumed_v0.2.2_case"]
    if crash.get("attempted_case", {}).get("case_id") != consumed["case_id"]:
        failures.append("Consumed v0.2.2 case binding changed")
    lock = json.loads((data_root / bindings["threshold_lock"]["logical_path"]).read_text())
    if lock.get("status") != "locked_before_sealed_evaluation":
        failures.append("Threshold-lock status changed")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "threshold_delta_chi2": float(lock["value_delta_chi2"]),
        "threshold_lock_sha256": bindings["threshold_lock"]["sha256"],
        "v0.2.2_crash_preserved": not failures,
        "consumed_v0.2.2_case_id": consumed["case_id"],
        "consumed_v0.2.2_seed": int(consumed["seed"]),
    }


def verify_execution_gate(data_root: Path | None = None) -> dict[str, Any]:
    root = repository_root()
    implementation = verify_implementation_freeze()
    readiness = verify_readiness_freeze()
    failures = list(implementation["failures"]) + list(readiness["failures"])
    path = root / EXECUTION_FREEZE_PATH
    if not path.is_file():
        return {
            "status": "locked" if not failures else "fail",
            "failures": failures + ["Separate v0.2.3 execution freeze is absent"],
            "implementation": implementation,
            "readiness": readiness,
            "predecessors_loaded": False,
        }
    freeze = json.loads(path.read_text(encoding="utf-8"))
    if freeze.get("status") != "frozen_before_first_v0.2.3_injection_case":
        failures.append("v0.2.3 execution freeze status is invalid")
    if freeze.get("execution_authorized") is not True:
        failures.append("v0.2.3 execution authorization is absent")
    for key in (
        "observed_residual_access_authorized",
        "observed_periodic_search_authorized",
        "promotion_grade_authorized",
        "discovery_claim_authorized",
    ):
        if freeze.get(key) is not False:
            failures.append(f"v0.2.3 execution boundary invalid: {key}")
    inventory = _inventory()
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("v0.2.3 execution inventory mismatch")
    if freeze.get("implementation_sha256") != implementation_sha256():
        failures.append("v0.2.3 execution implementation mismatch")
    if freeze.get("readiness_freeze_sha256") != readiness.get("freeze_sha256"):
        failures.append("v0.2.3 execution readiness-freeze mismatch")
    if data_root is None:
        failures.append("Authorized execution requires an explicit data root")
        predecessors = {"status": "not_loaded", "failures": []}
    else:
        predecessors = verify_predecessor_bindings(data_root)
        failures.extend(predecessors["failures"])
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "implementation": implementation,
        "readiness": readiness,
        "predecessors": predecessors,
        "predecessors_loaded": data_root is not None,
        "freeze_sha256": hash_file(path, "sha256"),
    }


class V023Ledger(CalibrationLedger):
    def __init__(self, data_root: Path, inventory_sha256: str, implementation_hash: str):
        super().__init__(data_root, inventory_sha256, implementation_hash)
        self.path = data_root / "run_records/pilot2/calibration-v0.2.3-ledger.json"
        self.health_path = data_root / "run_records/pilot2/calibration-v0.2.3-health.json"
        self.dashboard_path = data_root / "derived/pilot2/calibration-v0.2.3-dashboard/index.html"

    def empty(self) -> dict[str, Any]:
        state = super().empty()
        state["run_id"] = RUN_ID
        state["stage_status"] = {STAGE: "pending", "promotion_grade": "pending"}
        state["v0.2.2_resume_authorized"] = False
        state["consumed_v0.2.2_case_reused"] = False
        return state

    def begin_stage(self, stage: str) -> dict[str, Any]:
        if stage != STAGE:
            raise ValueError(f"Unknown v0.2.3 runner stage: {stage}")
        state = self.load()
        if state["hard_stop"] is not None:
            raise RuntimeError("v0.2.3 ledger contains a hard stop")
        if state["stage_status"][STAGE] == "pass":
            raise RuntimeError("v0.2.3 injection stage is already complete")
        if state["active_stage"] not in {None, STAGE}:
            raise RuntimeError("A different v0.2.3 stage is active")
        if state["active_stage"] is None:
            state["active_stage_started_utc"] = _utc_now()
        state["active_stage"] = STAGE
        state["stage_status"][STAGE] = "running"
        self.save(state)
        return state

    def health(self, state: dict[str, Any]) -> dict[str, Any]:
        health = super().health(state)
        completed = sum(item["stage"] == STAGE for item in state["completed_cases"].values())
        health.update(
            completed_injection_cases=completed,
            total_injection_cases=344,
            scientific_outcomes_sealed=state["stage_status"][STAGE] not in {"pass", "fail"},
            manual_refresh_command=(
                "PYTHONPATH=src pixi run python -m "
                "pulsar_pilot.pilot2_injection_runner_v023 health --data-root <PATH>"
            ),
        )
        return health


def prepare_context(data_root: Path, cases: list[dict[str, Any]]) -> InjectionContext:
    log_path = data_root / "run_records/pilot2/injection-v0.2.3-setup.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with _network_disabled():
        model, toas = _load_release(data_root, log_path)
    from pint.fitter import WidebandTOAFitter

    fitter = WidebandTOAFitter(toas, model)
    covariance = fitter.get_noise_covariancematrix().matrix
    design = fitter.get_designmatrix().matrix
    times = np.asarray(toas.table["tdbld"].data, dtype=float)
    frequencies, grid = build_search_frequency_grid(times, 30.0, 2000.0, 5)
    reference_epoch = float(model.PEPOCH.value)
    scanner = prepare_covariance_gls_scanner(
        covariance, design, times, frequencies, reference_epoch
    )
    exact_scanners = {
        period: prepare_covariance_gls_scanner(
            covariance, design, times, np.asarray([1.0 / period]), reference_epoch
        )
        for period in sorted({float(case["period_days"]) for case in cases})
    }
    binding = {
        "target": "B1937+21",
        "active_toas": len(toas),
        "covariance_shape": list(covariance.shape),
        "timing_design_shape": list(design.shape),
        "timing_design_rank": scanner.timing_design_rank,
        "frequency_grid": grid,
        "reference_epoch_mjd_tdb": reference_epoch,
        "observed_residual_vector_loaded": False,
        "observed_periodic_scan_executed": False,
        "network_access_enabled": False,
    }
    expected = {
        "active_toas": 660,
        "covariance_shape": [1320, 1320],
        "timing_design_shape": [1320, 284],
        "timing_design_rank": 284,
    }
    for key, value in expected.items():
        if binding[key] != value:
            raise RuntimeError(f"v0.2.3 injection setup mismatch: {key}")
    return InjectionContext(
        model=model,
        toas=toas,
        scanner=scanner,
        exact_scanners=exact_scanners,
        times=times,
        reference_epoch=reference_epoch,
        input_binding=binding,
    )


def _record_path(data_root: Path, sequence: int, case: dict[str, Any]) -> Path:
    return (
        data_root
        / "derived/pilot2/calibration-v0.2.3/injections"
        / str(case["family"])
        / f"{sequence:04d}-{case['case_id']}.json"
    )


def _resource_gate(name: str, observed: float, limit: float) -> dict[str, Any]:
    return _gate(name, observed, "<=", limit, observed <= limit)


def terminalize_unexpected_exception(
    ledger: V023Ledger,
    result_path: Path,
    error: Exception,
    active_case_id: str | None,
) -> dict[str, Any]:
    state = ledger.load()
    result = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "stage": STAGE,
        "status": "fail",
        "failure_class": "unexpected_execution_exception",
        "exception_type": type(error).__name__,
        "exception_message": str(error),
        "active_case_id": active_case_id,
        "completed_case_records": len(state["completed_cases"]),
        "partial_scientific_metrics_recorded": False,
        "threshold_retuned": False,
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
        "promotion_grade_executed": False,
    }
    _atomic_json(result_path, result)
    ledger.complete_stage(STAGE, result_path, False)
    return result


def execute(data_root: Path) -> dict[str, Any]:
    gate = verify_execution_gate(data_root)
    if gate["status"] != "pass":
        raise RuntimeError(f"v0.2.3 injection execution is locked: {gate['failures']}")
    require_initialized_data_root(data_root)
    base, remediation, runner = _configs()
    inventory = _inventory()
    cases = inventory["cases"]
    audit_ids = set(inventory["solver_audit_case_ids"])
    ledger = V023Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())
    if ledger.verify_artifacts()["status"] != "pass":
        raise RuntimeError("v0.2.3 recorded artifact integrity failure")
    state = ledger.load()
    if state["stage_status"][STAGE] == "pass":
        return {"status": "already_complete", "science_cases_executed_this_invocation": 0}
    if state["active_stage"] is None:
        ledger.begin_stage(STAGE)
    predecessor = gate["predecessors"]
    lock_path = data_root / runner["predecessor_bindings"]["threshold_lock"]["logical_path"]
    lock_sha = hash_file(lock_path, "sha256")
    execution_binding = hashlib.sha256(
        (
            f"{implementation_sha256()}:{gate['freeze_sha256']}:"
            f"{lock_sha}:{inventory['inventory_sha256']}"
        ).encode()
    ).hexdigest()
    result_path = data_root / runner["paths"]["result"]
    current_case_id: str | None = None
    started = time.perf_counter()
    records_by_id: dict[str, dict[str, Any]] = {}
    executed = 0

    def enforce_runtime_cap() -> None:
        if time.perf_counter() - started > float(runner["resource_caps"]["wall_hours_maximum"]) * 3600:
            raise RuntimeError("v0.2.3 injection stage exceeded the six-hour cap")

    def load_or_execute(sequence: int, case: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        nonlocal current_case_id
        current_case_id = str(case["case_id"])
        path = _record_path(data_root, sequence, case)
        if current_case_id in ledger.load()["completed_cases"]:
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["case"] != case or record["execution_binding_sha256"] != execution_binding:
                raise RuntimeError("Resumed v0.2.3 case binding differs")
            return record, False
        record = execute_injection_case(
            prepare_context_result,
            case,
            float(predecessor["threshold_delta_chi2"]),
            current_case_id in audit_ids,
            base,
            execution_binding,
        )
        return record, True

    def process_nonannual(family: str) -> None:
        nonlocal executed
        for sequence, case in (
            (sequence, case)
            for sequence, case in enumerate(cases, 1)
            if case["family"] == family
        ):
            record, is_new = load_or_execute(sequence, case)
            if is_new:
                record["candidate_eligible"] = True
                path = _record_path(data_root, sequence, case)
                _atomic_json(path, record)
                ledger.record_case(STAGE, case["case_id"], path)
                executed += 1
            records_by_id[case["case_id"]] = record
            print(f"PILOT2R3_INJECTION_PROGRESS {len(records_by_id)}/344", flush=True)
            enforce_runtime_cap()

    try:
        prepare_context_result = prepare_context(data_root, cases)
        with HeartbeatService(ledger, HEARTBEAT_INTERVAL_SECONDS):
            process_nonannual("main")
            process_nonannual("phase_reference")
            annual_periods = sorted(
                {float(case["period_days"]) for case in cases if case["family"] == "annual"}
            )
            correlation_limit = float(
                base["candidate_eligibility"]["maximum_signal_astrometry_correlation"]
            )
            absorption_limit = float(
                base["candidate_eligibility"]["maximum_ordinary_model_absorption_fraction"]
            )
            for period in annual_periods:
                group = [
                    (sequence, case)
                    for sequence, case in enumerate(cases, 1)
                    if case["family"] == "annual" and float(case["period_days"]) == period
                ]
                pending: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
                group_records: list[dict[str, Any]] = []
                for sequence, case in group:
                    record, is_new = load_or_execute(sequence, case)
                    group_records.append(record)
                    if is_new:
                        pending.append((sequence, case, record))
                eligible = max(
                    float(item["signal_astrometry_correlation"]) for item in group_records
                ) < correlation_limit and max(
                    float(item["ordinary_absorption_fraction"]) for item in group_records
                ) < absorption_limit
                for record in group_records:
                    if "candidate_eligible" in record and bool(record["candidate_eligible"]) != eligible:
                        raise RuntimeError("Resumed v0.2.3 annual eligibility differs")
                    record["candidate_eligible"] = eligible
                for sequence, case, record in pending:
                    path = _record_path(data_root, sequence, case)
                    _atomic_json(path, record)
                    ledger.record_case(STAGE, case["case_id"], path)
                    executed += 1
                records_by_id.update({item["case"]["case_id"]: item for item in group_records})
                enforce_runtime_cap()
            process_nonannual("boundary")
        records = [records_by_id[case["case_id"]] for case in cases]
        if hash_file(lock_path, "sha256") != lock_sha:
            raise RuntimeError("Predecessor threshold lock changed during v0.2.3 execution")
        result = grade_records(records, base, remediation)
        elapsed_hours = (time.perf_counter() - started) / 3600.0
        peak_memory = _peak_rss_gib()
        data_root_size = _directory_size_gib(data_root)
        setup_log = data_root / runner["paths"]["setup_log"]
        sanitized = [
            line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
            for line in setup_log.read_text(encoding="utf-8").splitlines()
        ]
        warnings = classify_injection_warning_lines(sanitized)
        result["gates"].extend(
            [
                _resource_gate("injection_wall_hours", elapsed_hours, float(runner["resource_caps"]["wall_hours_maximum"])),
                _resource_gate("peak_memory_gib", peak_memory, float(runner["resource_caps"]["peak_memory_gib_maximum"])),
                _resource_gate("complete_data_root_gib", data_root_size, float(runner["resource_caps"]["complete_data_root_gib_maximum"])),
                _gate("unexpected_material_warnings", warnings["status"], "==", "pass", warnings["status"] == "pass"),
            ]
        )
        result["status"] = "pass" if all(item["status"] == "pass" for item in result["gates"]) else "fail"
        result.update(
            threshold_lock_sha256=lock_sha,
            threshold_retuned=False,
            science_cases_executed_this_invocation=executed,
            execution_binding_sha256=execution_binding,
            wall_hours=elapsed_hours,
            peak_memory_gib=peak_memory,
            complete_data_root_gib=data_root_size,
            warnings=warnings,
            observed_residual_vector_used=False,
            observed_periodic_scan_executed=False,
            promotion_grade_executed=False,
        )
        _atomic_json(result_path, result)
        ledger.complete_stage(STAGE, result_path, result["status"] == "pass")
        return {
            "status": result["status"],
            "completed_injection_cases": len(records),
            "science_cases_executed_this_invocation": executed,
            "ledger_verification": ledger.verify_artifacts(),
            "promotion_grade_executed": False,
        }
    except Exception as error:
        state = ledger.load()
        if state["active_stage"] == STAGE and state["stage_status"][STAGE] == "running":
            terminalize_unexpected_exception(ledger, result_path, error, current_case_id)
        raise


def supervision_snapshot(data_root: Path) -> dict[str, Any]:
    inventory = _inventory()
    ledger = V023Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())
    state = ledger.load()
    status = state["stage_status"][STAGE]
    return {
        "schema_version": 1,
        "event": f"terminal_{status}" if status in {"pass", "fail"} else "locked_idle",
        "injection_cases_completed": len(state["completed_cases"]),
        "injection_cases_total": 344,
        "checkpoint_count": len(state["checkpoints"]),
        "hard_stop_present": state["hard_stop"] is not None,
        "heartbeat_interval_seconds": 30,
        "stale_after_seconds": 90,
        "passive_review_interval_seconds": 1800,
        "scientific_outcomes_sealed": status not in {"pass", "fail"},
    }


def zero_case_dry_run(data_root: Path) -> dict[str, Any]:
    require_initialized_data_root(data_root)
    inventory = _inventory()
    ledger = V023Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())
    state = ledger.load()
    ledger.save(state)
    gate = verify_execution_gate()
    allowed_lock_failures = {
        "v0.2.3 readiness freeze is absent",
        "Separate v0.2.3 execution freeze is absent",
    }
    criteria = {
        "remediation_freeze_passes": verify_remediation_freeze()["status"] == "pass",
        "implementation_freeze_passes": verify_implementation_freeze()["status"] == "pass",
        "execution_gate_fail_closed": (
            gate["status"] in {"locked", "fail"}
            and "Separate v0.2.3 execution freeze is absent" in gate["failures"]
            and set(gate["failures"]) <= allowed_lock_failures
        ),
        "predecessors_not_loaded": gate["predecessors_loaded"] is False,
        "zero_cases_recorded": len(state["completed_cases"]) == 0,
        "stage_pending": state["stage_status"][STAGE] == "pending",
        "hard_stop_absent": state["hard_stop"] is None,
        "artifact_verification_passes": ledger.verify_artifacts()["status"] == "pass",
    }
    return {
        "schema_version": 1,
        "status": "pass" if all(criteria.values()) else "fail",
        "operation": "v0.2.3_runner_zero_science_integrity_dry_run",
        "criteria": criteria,
        "science_cases_executed": 0,
        "random_draws_generated": 0,
        "model_fits_executed": 0,
        "periodic_scans_executed": 0,
        "predecessor_artifacts_loaded": 0,
        "execution_gate_status": gate["status"],
        "health_record": logical_path(ledger.health_path, data_root),
        "dashboard": logical_path(ledger.dashboard_path, data_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-injection-runner-v023")
    parser.add_argument("command", choices=("verify-implementation", "verify-gate", "dry-run", "health", "run"))
    parser.add_argument("--data-root")
    args = parser.parse_args()
    if args.command == "verify-implementation":
        result = verify_implementation_freeze()
    elif args.command == "verify-gate":
        root = configured_data_root(args.data_root) if args.data_root else None
        result = verify_execution_gate(root)
    else:
        data_root = configured_data_root(args.data_root)
        if args.command == "dry-run":
            result = zero_case_dry_run(data_root)
        elif args.command == "health":
            inventory = _inventory()
            ledger = V023Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())
            result = ledger.write_health(ledger.load())
        else:
            result = execute(data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status", "pass") not in {"fail"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
