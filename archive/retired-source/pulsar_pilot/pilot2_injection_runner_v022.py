from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import defaultdict
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_yaml
from .injection_integrity import (
    classify_injection_warning_lines,
    toa_adjustment_gate_value,
)
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _directory_size_gib, _peak_rss_gib
from .pilot1_runtime import build_search_frequency_grid, prepare_covariance_gls_scanner
from .pilot2_calibration_runtime import (
    CalibrationLedger,
    HeartbeatService,
    _atomic_json,
    _utc_now,
)
from .pilot2_injection_executor import (
    HEARTBEAT_INTERVAL_SECONDS,
    InjectionContext,
    _execute_injection_case,
)
from .pilot2_injection_remediation import (
    BASE_CONFIG_PATH,
    build_remediation_inventory,
    verify_remediation_freeze,
)
from .pilot2_injection_remediation import CONFIG_PATH as REMEDIATION_CONFIG_PATH
from .pilot2_preflight import _load_release, _network_disabled
from .provenance import hash_file, logical_path

RUNNER_CONFIG_PATH = "config/pilot2_injection_runner_v0.2.2.yaml"
IMPLEMENTATION_FREEZE_PATH = "protocol/PILOT2_INJECTION_RUNNER_FREEZE_v0.2.2.json"
READINESS_FREEZE_PATH = (
    "protocol/PILOT2_INJECTION_EXECUTION_READINESS_FREEZE_v0.2.2.json"
)
EXECUTION_FREEZE_PATH = "protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.2.json"
STAGE = "injection_remediation_evaluation"
RUN_ID = "pilot2-b1937-injection-remediation-v0.2.2"
IMPLEMENTATION_PATHS = (
    "src/pulsar_pilot/pilot2_injection_runner_v022.py",
    "src/pulsar_pilot/pilot2_injection_executor.py",
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
    base, remediation, _ = _configs()
    return build_remediation_inventory(base, remediation)


def verify_implementation_freeze() -> dict[str, Any]:
    root = repository_root()
    path = root / IMPLEMENTATION_FREEZE_PATH
    if not path.is_file():
        return {"status": "locked", "failures": ["v0.2.2 runner freeze is absent"]}
    freeze = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "implementation_frozen_execution_not_authorized":
        failures.append("v0.2.2 runner freeze status is invalid")
    if freeze.get("execution_authorized") is not False:
        failures.append("v0.2.2 runner freeze authorizes execution")
    if freeze.get("science_cases_executed_during_validation") != 0:
        failures.append("v0.2.2 runner validation was not zero-case")
    remediation = verify_remediation_freeze()
    if remediation["status"] != "pass":
        failures.append("Remediation freeze verification failed")
    inventory = _inventory()
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("v0.2.2 runner inventory mismatch")
    if freeze.get("implementation_sha256") != implementation_sha256():
        failures.append("v0.2.2 aggregate implementation mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"v0.2.2 runner hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "implementation_sha256": implementation_sha256(),
        "inventory_sha256": inventory["inventory_sha256"],
        "freeze_sha256": hash_file(path, "sha256"),
        "execution_authorized": False,
    }


def verify_predecessor_bindings(data_root: Path) -> dict[str, Any]:
    require_initialized_data_root(data_root)
    _, _, runner = _configs()
    failures: list[str] = []
    bindings = runner["predecessor_bindings"]
    for key in (
        "threshold_lock",
        "sealed_gaussian_result",
        "structured_tail_result",
        "v0.2.1_terminal_result",
        "v0.2.1_final_ledger",
    ):
        binding = bindings[key]
        path = data_root / str(binding["logical_path"])
        if not path.is_file() or hash_file(path, "sha256") != binding["sha256"]:
            failures.append(f"Predecessor binding mismatch: {key}")
    if failures:
        return {"status": "fail", "failures": failures}
    ledger_binding = bindings["v0.2.1_final_ledger"]
    ledger = json.loads(
        (data_root / ledger_binding["logical_path"]).read_text(encoding="utf-8")
    )
    if ledger["stage_status"].get("injection_recovery_and_annual_map") != "fail":
        failures.append("v0.2.1 injection terminal failure changed")
    if ledger.get("hard_stop", {}).get("reason") != "stage_gate_failure":
        failures.append("v0.2.1 hard stop changed")
    for stage in (
        "gaussian_threshold_calibration",
        "commit_threshold_lock",
        "sealed_gaussian_evaluation",
        "structured_tail_evaluation",
    ):
        if ledger["stage_status"].get(stage) != "pass":
            failures.append(f"Passed predecessor changed: {stage}")
    lock_binding = bindings["threshold_lock"]
    lock = json.loads(
        (data_root / lock_binding["logical_path"]).read_text(encoding="utf-8")
    )
    if lock.get("status") != "locked_before_sealed_evaluation":
        failures.append("Predecessor threshold-lock status changed")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "threshold_delta_chi2": float(lock["value_delta_chi2"]),
        "threshold_lock_sha256": lock_binding["sha256"],
        "v0.2.1_hard_stop_preserved": not any(
            failure.startswith("v0.2.1") for failure in failures
        ),
    }


def verify_readiness_freeze() -> dict[str, Any]:
    root = repository_root()
    path = root / READINESS_FREEZE_PATH
    if not path.is_file():
        return {"status": "locked", "failures": ["v0.2.2 readiness freeze is absent"]}
    freeze = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "execution_readiness_frozen_execution_not_authorized":
        failures.append("v0.2.2 readiness freeze status is invalid")
    if freeze.get("execution_readiness") != "pass":
        failures.append("v0.2.2 readiness did not pass")
    if freeze.get("execution_authorized") is not False:
        failures.append("v0.2.2 readiness freeze authorizes execution")
    inventory = _inventory()
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("v0.2.2 readiness inventory mismatch")
    if freeze.get("implementation_sha256") != implementation_sha256():
        failures.append("v0.2.2 readiness implementation mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"v0.2.2 readiness hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "execution_authorized": False,
        "inventory_sha256": inventory["inventory_sha256"],
        "implementation_sha256": implementation_sha256(),
        "freeze_sha256": hash_file(path, "sha256"),
    }


def verify_execution_gate(data_root: Path | None = None) -> dict[str, Any]:
    root = repository_root()
    implementation = verify_implementation_freeze()
    readiness = verify_readiness_freeze()
    failures = list(implementation["failures"]) + list(readiness["failures"])
    path = root / EXECUTION_FREEZE_PATH
    if not path.is_file():
        return {
            "status": "locked",
            "failures": failures + ["Separate v0.2.2 execution freeze is absent"],
            "implementation": implementation,
            "readiness": readiness,
            "predecessors_loaded": False,
        }
    freeze = json.loads(path.read_text(encoding="utf-8"))
    if freeze.get("status") != "frozen_before_first_v0.2.2_injection_case":
        failures.append("v0.2.2 execution freeze status is invalid")
    if freeze.get("execution_authorized") is not True:
        failures.append("v0.2.2 execution authorization is absent")
    for key in (
        "observed_residual_access_authorized",
        "observed_periodic_search_authorized",
        "promotion_grade_authorized",
        "discovery_claim_authorized",
    ):
        if freeze.get(key) is not False:
            failures.append(f"v0.2.2 execution boundary invalid: {key}")
    inventory = _inventory()
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("v0.2.2 execution inventory mismatch")
    if freeze.get("implementation_sha256") != implementation_sha256():
        failures.append("v0.2.2 execution implementation mismatch")
    if freeze.get("readiness_freeze_sha256") != readiness.get("freeze_sha256"):
        failures.append("v0.2.2 execution readiness-freeze mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"v0.2.2 execution hash mismatch: {relative}")
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


class V022Ledger(CalibrationLedger):
    def __init__(self, data_root: Path, inventory_sha256: str, implementation_hash: str):
        super().__init__(data_root, inventory_sha256, implementation_hash)
        self.path = data_root / "run_records/pilot2/calibration-v0.2.2-ledger.json"
        self.health_path = data_root / "run_records/pilot2/calibration-v0.2.2-health.json"
        self.dashboard_path = (
            data_root / "derived/pilot2/calibration-v0.2.2-dashboard/index.html"
        )

    def empty(self) -> dict[str, Any]:
        state = super().empty()
        state["run_id"] = RUN_ID
        state["stage_status"] = {STAGE: "pending", "promotion_grade": "pending"}
        state["predecessor_results_reused"] = True
        state["v0.2.1_injection_acceptance_reused"] = False
        return state

    def begin_stage(self, stage: str) -> dict[str, Any]:
        if stage != STAGE:
            raise ValueError(f"Unknown v0.2.2 runner stage: {stage}")
        state = self.load()
        if state["hard_stop"] is not None:
            raise RuntimeError("v0.2.2 ledger contains a hard stop")
        if state["stage_status"][STAGE] == "pass":
            raise RuntimeError("v0.2.2 injection stage is already complete")
        if state["active_stage"] not in {None, STAGE}:
            raise RuntimeError("A different v0.2.2 stage is active")
        if state["active_stage"] is None:
            state["active_stage_started_utc"] = _utc_now()
        state["active_stage"] = STAGE
        state["stage_status"][STAGE] = "running"
        self.save(state)
        return state

    def health(self, state: dict[str, Any]) -> dict[str, Any]:
        health = super().health(state)
        completed = sum(
            item["stage"] == STAGE for item in state["completed_cases"].values()
        )
        health.update(
            completed_injection_cases=completed,
            total_injection_cases=344,
            scientific_outcomes_sealed=state["stage_status"][STAGE]
            not in {"pass", "fail"},
            manual_refresh_command=(
                "PYTHONPATH=src pixi run python -m "
                "pulsar_pilot.pilot2_injection_runner_v022 health --data-root <PATH>"
            ),
        )
        return health


def prepare_context(data_root: Path, cases: list[dict[str, Any]]) -> InjectionContext:
    log_path = data_root / "run_records/pilot2/injection-v0.2.2-setup.log"
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
            raise RuntimeError(f"v0.2.2 injection setup mismatch: {key}")
    return InjectionContext(
        model=model,
        toas=toas,
        scanner=scanner,
        exact_scanners=exact_scanners,
        times=times,
        reference_epoch=reference_epoch,
        input_binding=binding,
    )


def _gate(
    name: str, observed: Any, comparator: str, limit: Any, passed: bool
) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "comparator": comparator,
        "limit": limit,
        "status": "pass" if passed else "fail",
    }


def _nearest_rank(values: list[float], quantile: float) -> float:
    if not values:
        return math.inf
    ordered = sorted(values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


def grade_records(
    records: list[dict[str, Any]],
    base_config: dict[str, Any],
    remediation: dict[str, Any],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["family"])].append(record)
    expected = {"main": 240, "phase_reference": 60, "annual": 28, "boundary": 16}
    gates = [
        _gate(
            f"{family}_case_count",
            len(grouped[family]),
            "==",
            count,
            len(grouped[family]) == count,
        )
        for family, count in expected.items()
    ]
    canonical_failures = 0
    adjustment_values: list[float] = []
    for record in records:
        try:
            adjustment_values.append(toa_adjustment_gate_value(record))
        except (TypeError, ValueError):
            canonical_failures += 1
    maximum_adjustment = max(adjustment_values, default=math.inf)
    adjustment_limit = float(
        remediation["application_integrity"]["toa_adjustment_maximum_microseconds"]
    )
    gates.extend(
        [
            _gate(
                "canonical_toa_metrics",
                canonical_failures,
                "==",
                0,
                canonical_failures == 0 and len(adjustment_values) == len(records),
            ),
            _gate(
                "toa_application_error",
                maximum_adjustment,
                "<=",
                adjustment_limit,
                maximum_adjustment <= adjustment_limit,
            ),
        ]
    )
    all_converged = bool(records) and all(
        bool(item["ordinary_fit_converged"]) and bool(item["joint_fit_converged"])
        for item in records
    )
    audited = [item for item in records if bool(item.get("solver_audit_required"))]
    audit_failures = sum(not bool(item.get("solver_audit_pass")) for item in audited)
    gates.extend(
        [
            _gate("fit_convergence", all_converged, "is", True, all_converged),
            _gate("solver_audit_count", len(audited), "==", 35, len(audited) == 35),
            _gate(
                "solver_audit_failures",
                audit_failures,
                "==",
                0,
                audit_failures == 0,
            ),
        ]
    )
    main = grouped["main"]
    periods: dict[float, dict[float, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for item in main:
        periods[float(item["period_days"])][float(item["amplitude_microseconds"])].append(
            item
        )
    monotonic = 0
    bracketed = 0
    strong_rates: list[float] = []
    for cells in periods.values():
        rates = [
            sum(bool(item["triggered"]) for item in cells[amplitude])
            / len(cells[amplitude])
            for amplitude in sorted(cells)
        ]
        monotonic += all(left <= right for left, right in pairwise(rates))
        bracketed += min(rates) <= 0.5 <= max(rates) and min(rates) <= 0.9 <= max(rates)
        strong_rates.append(rates[-1])
    triggered = [item for item in main if bool(item["triggered"])]
    frequency_rate = (
        sum(bool(item["frequency_recovered"]) for item in triggered) / len(triggered)
        if triggered
        else 0.0
    )
    median_bias = (
        float(np.median([abs(float(item["amplitude_bias_fraction"])) for item in triggered]))
        if triggered
        else math.inf
    )
    main_phase_p90 = _nearest_rank(
        [abs(float(item["phase_error_radians"])) for item in triggered], 0.9
    )
    limits = base_config["injection_gates"]
    gates.extend(
        [
            _gate(
                "strong_control_recovery",
                min(strong_rates, default=0.0),
                ">=",
                limits["strong_control_recovery_rate_minimum"],
                bool(strong_rates)
                and min(strong_rates)
                >= float(limits["strong_control_recovery_rate_minimum"]),
            ),
            _gate(
                "frequency_recovery",
                frequency_rate,
                ">=",
                limits["injected_frequency_recovery_rate_minimum"],
                frequency_rate
                >= float(limits["injected_frequency_recovery_rate_minimum"]),
            ),
            _gate(
                "median_amplitude_bias",
                median_bias,
                "<=",
                limits["median_amplitude_bias_fraction_maximum"],
                median_bias <= float(limits["median_amplitude_bias_fraction_maximum"]),
            ),
            _gate(
                "monotonic_periods",
                monotonic,
                ">=",
                limits["minimum_main_periods_with_monotonic_detection_fraction"],
                monotonic
                >= int(limits["minimum_main_periods_with_monotonic_detection_fraction"]),
            ),
            _gate(
                "bracketed_periods",
                bracketed,
                ">=",
                limits["minimum_main_periods_bracketing_50_and_90_percent_recovery"],
                bracketed
                >= int(
                    limits[
                        "minimum_main_periods_bracketing_50_and_90_percent_recovery"
                    ]
                ),
            ),
        ]
    )
    phase_reference = grouped["phase_reference"]
    reference_p90 = _nearest_rank(
        [abs(float(item["phase_error_radians"])) for item in phase_reference], 0.9
    )
    reference_limit = float(
        remediation["phase_reference_controls"]["phase_error_p90_maximum_radians"]
    )
    all_reference_triggered = len(phase_reference) == 60 and all(
        bool(item["triggered"]) for item in phase_reference
    )
    gates.extend(
        [
            _gate(
                "phase_reference_trigger_recovery",
                sum(bool(item["triggered"]) for item in phase_reference),
                "==",
                60,
                all_reference_triggered,
            ),
            _gate(
                "phase_reference_error_p90",
                reference_p90,
                "<=",
                reference_limit,
                reference_p90 <= reference_limit,
            ),
        ]
    )
    correlation_limit = float(
        base_config["candidate_eligibility"]["maximum_signal_astrometry_correlation"]
    )
    absorption_limit = float(
        base_config["candidate_eligibility"][
            "maximum_ordinary_model_absorption_fraction"
        ]
    )
    annual_by_period: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for item in grouped["annual"]:
        annual_by_period[float(item["period_days"])].append(item)
    annual_eligible = {
        period: max(float(item["signal_astrometry_correlation"]) for item in items)
        < correlation_limit
        and max(float(item["ordinary_absorption_fraction"]) for item in items)
        < absorption_limit
        for period, items in annual_by_period.items()
    }
    annual_violations = sum(
        bool(item.get("candidate_eligible"))
        and not annual_eligible[float(item["period_days"])]
        for item in grouped["annual"]
    )
    gates.append(
        _gate(
            "annual_eligibility_violations",
            annual_violations,
            "==",
            0,
            annual_violations == 0,
        )
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "status": "pass" if all(gate["status"] == "pass" for gate in gates) else "fail",
        "gates": gates,
        "diagnostics": {
            "all_triggered_main_phase_error_role": "diagnostic_not_hard_gate",
            "all_triggered_main_phase_error_p90_radians": main_phase_p90,
            "phase_reference_error_p90_radians": reference_p90,
            "strong_control_minimum_recovery": min(strong_rates, default=0.0),
            "frequency_recovery_rate": frequency_rate,
            "median_amplitude_bias_fraction": median_bias,
            "monotonic_periods": monotonic,
            "bracketed_periods": bracketed,
        },
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
    }


def _record_path(data_root: Path, sequence: int, case: dict[str, Any]) -> Path:
    return (
        data_root
        / "derived/pilot2/calibration-v0.2.2/injections"
        / str(case["family"])
        / f"{sequence:04d}-{case['case_id']}.json"
    )


def _resource_gate(name: str, observed: float, limit: float) -> dict[str, Any]:
    return _gate(name, observed, "<=", limit, observed <= limit)


def execute(data_root: Path) -> dict[str, Any]:
    gate = verify_execution_gate(data_root)
    if gate["status"] != "pass":
        raise RuntimeError(f"v0.2.2 injection execution is locked: {gate['failures']}")
    require_initialized_data_root(data_root)
    base, remediation, runner = _configs()
    inventory = build_remediation_inventory(base, remediation)
    cases = inventory["cases"]
    audit_ids = set(inventory["solver_audit_case_ids"])
    ledger = V022Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())
    integrity = ledger.verify_artifacts()
    if integrity["status"] != "pass":
        raise RuntimeError("v0.2.2 recorded artifact integrity failure")
    state = ledger.load()
    if state["stage_status"][STAGE] == "pass":
        return {"status": "already_complete", "science_cases_executed_this_invocation": 0}
    if state["active_stage"] is None:
        ledger.begin_stage(STAGE)
    predecessor = gate["predecessors"]
    lock_binding = runner["predecessor_bindings"]["threshold_lock"]
    lock_path = data_root / lock_binding["logical_path"]
    lock_sha = hash_file(lock_path, "sha256")
    execution_binding = hashlib.sha256(
        (
            f"{implementation_sha256()}:{gate['freeze_sha256']}:"
            f"{lock_sha}:{inventory['inventory_sha256']}"
        ).encode()
    ).hexdigest()
    context = prepare_context(data_root, cases)
    started = time.perf_counter()
    records_by_id: dict[str, dict[str, Any]] = {}
    executed = 0

    def enforce_runtime_cap() -> None:
        if time.perf_counter() - started > float(
            runner["resource_caps"]["wall_hours_maximum"]
        ) * 3600.0:
            raise RuntimeError("v0.2.2 injection stage exceeded the six-hour cap")

    def load_or_execute(
        sequence: int, case: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        path = _record_path(data_root, sequence, case)
        if case["case_id"] in ledger.load()["completed_cases"]:
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["case"] != case or record["execution_binding_sha256"] != execution_binding:
                raise RuntimeError("Resumed v0.2.2 case binding differs")
            return record, False
        record = _execute_injection_case(
            context,
            case,
            float(predecessor["threshold_delta_chi2"]),
            case["case_id"] in audit_ids,
            base,
            execution_binding,
        )
        if record.get("run_id") != "pilot2-b1937-calibration-v0.2.1":
            raise RuntimeError("Unexpected inherited injection record version")
        record["run_id"] = RUN_ID
        record["schema_version"] = 2
        record["v0.2.1_injection_acceptance_reused"] = False
        return record, True

    def process_nonannual(family: str) -> None:
        nonlocal executed
        family_cases = [
            (sequence, case)
            for sequence, case in enumerate(cases, 1)
            if case["family"] == family
        ]
        for sequence, case in family_cases:
            record, is_new = load_or_execute(sequence, case)
            if is_new:
                record["candidate_eligible"] = True
                path = _record_path(data_root, sequence, case)
                _atomic_json(path, record)
                ledger.record_case(STAGE, case["case_id"], path)
                executed += 1
            records_by_id[case["case_id"]] = record
            print(f"PILOT2R2_INJECTION_PROGRESS {len(records_by_id)}/344", flush=True)
            enforce_runtime_cap()

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
            base["candidate_eligibility"][
                "maximum_ordinary_model_absorption_fraction"
            ]
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
                    raise RuntimeError("Resumed v0.2.2 annual eligibility differs")
                record["candidate_eligible"] = eligible
            for sequence, case, record in pending:
                path = _record_path(data_root, sequence, case)
                _atomic_json(path, record)
                ledger.record_case(STAGE, case["case_id"], path)
                executed += 1
            records_by_id.update({item["case"]["case_id"]: item for item in group_records})
            print(f"PILOT2R2_INJECTION_PROGRESS {len(records_by_id)}/344", flush=True)
            enforce_runtime_cap()
        process_nonannual("boundary")
    records = [records_by_id[case["case_id"]] for case in cases]
    if hash_file(lock_path, "sha256") != lock_sha:
        raise RuntimeError("Predecessor threshold lock changed during v0.2.2 execution")
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
            _resource_gate(
                "injection_wall_hours",
                elapsed_hours,
                float(runner["resource_caps"]["wall_hours_maximum"]),
            ),
            _resource_gate(
                "peak_memory_gib",
                peak_memory,
                float(runner["resource_caps"]["peak_memory_gib_maximum"]),
            ),
            _resource_gate(
                "complete_data_root_gib",
                data_root_size,
                float(runner["resource_caps"]["complete_data_root_gib_maximum"]),
            ),
            _gate(
                "unexpected_material_warnings",
                warnings["status"],
                "==",
                "pass",
                warnings["status"] == "pass",
            ),
        ]
    )
    result["status"] = (
        "pass" if all(item["status"] == "pass" for item in result["gates"]) else "fail"
    )
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
    result_path = data_root / runner["paths"]["result"]
    _atomic_json(result_path, result)
    ledger.complete_stage(STAGE, result_path, result["status"] == "pass")
    return {
        "status": result["status"],
        "completed_injection_cases": len(records),
        "science_cases_executed_this_invocation": executed,
        "threshold_lock_unchanged": hash_file(lock_path, "sha256") == lock_sha,
        "ledger_verification": ledger.verify_artifacts(),
        "promotion_grade_executed": False,
    }


def supervision_snapshot(data_root: Path, now_utc: str | None = None) -> dict[str, Any]:
    inventory = _inventory()
    ledger = V022Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())
    state = ledger.load()
    health = json.loads(ledger.health_path.read_text()) if ledger.health_path.is_file() else {}
    status = state["stage_status"][STAGE]
    event = "locked_idle"
    attention = False
    heartbeat_age: float | None = None
    if status in {"pass", "fail"}:
        event = f"terminal_{status}"
        attention = True
    elif status == "running":
        heartbeat = health.get("last_heartbeat_utc")
        if heartbeat:
            from datetime import UTC, datetime

            now = datetime.fromisoformat(now_utc) if now_utc else datetime.now(UTC)
            heartbeat_age = max(0.0, (now - datetime.fromisoformat(heartbeat)).total_seconds())
        if not state.get("runtime_active") or heartbeat_age is None:
            event = "paused_or_interrupted"
            attention = True
        elif heartbeat_age > 90.0:
            event = "stale_attention_required"
            attention = True
        else:
            event = "healthy_no_action"
    completed = sum(item["stage"] == STAGE for item in state["completed_cases"].values())
    return {
        "schema_version": 1,
        "event": event,
        "codex_check_required": attention,
        "heartbeat_age_seconds": heartbeat_age,
        "heartbeat_interval_seconds": 30,
        "stale_after_seconds": 90,
        "passive_review_interval_seconds": 1800,
        "injection_cases_completed": completed,
        "injection_cases_total": 344,
        "checkpoint_count": len(state["checkpoints"]),
        "hard_stop_present": state["hard_stop"] is not None,
        "scientific_outcomes_sealed": status == "running",
        "policy": "health_only_no_scientific_outcomes_before_terminal",
    }


def zero_case_dry_run(data_root: Path) -> dict[str, Any]:
    require_initialized_data_root(data_root)
    inventory = _inventory()
    ledger = V022Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())
    state = ledger.load()
    ledger.save(state)
    gate = verify_execution_gate()
    snapshot = supervision_snapshot(data_root)
    criteria = {
        "remediation_freeze_passes": verify_remediation_freeze()["status"] == "pass",
        "runner_implementation_freeze_passes": verify_implementation_freeze()["status"]
        == "pass",
        "execution_gate_locked": gate["status"] == "locked",
        "predecessors_not_loaded_before_authorization": gate["predecessors_loaded"] is False,
        "zero_cases_recorded": len(state["completed_cases"]) == 0,
        "stage_pending": state["stage_status"][STAGE] == "pending",
        "promotion_pending": state["stage_status"]["promotion_grade"] == "pending",
        "artifact_verification_passes": ledger.verify_artifacts()["status"] == "pass",
        "health_record_written": ledger.health_path.is_file(),
        "dashboard_written": ledger.dashboard_path.is_file(),
        "heartbeat_interval_30_seconds": snapshot["heartbeat_interval_seconds"] == 30,
        "manual_refresh_recorded": bool(
            json.loads(ledger.health_path.read_text())["manual_refresh_command"]
        ),
    }
    return {
        "schema_version": 1,
        "status": "pass" if all(criteria.values()) else "fail",
        "operation": "v0.2.2_runner_zero_case_integrity_dry_run",
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
    parser = argparse.ArgumentParser(prog="pilot2-injection-runner-v022")
    parser.add_argument(
        "command",
        choices=("verify-implementation", "verify-gate", "dry-run", "health", "run"),
    )
    parser.add_argument("--data-root")
    args = parser.parse_args()
    if args.command == "verify-implementation":
        result = verify_implementation_freeze()
    elif args.command == "verify-gate":
        result = verify_execution_gate()
    else:
        data_root = configured_data_root(args.data_root)
        if args.command == "dry-run":
            result = zero_case_dry_run(data_root)
        elif args.command == "health":
            inventory = _inventory()
            ledger = V022Ledger(
                data_root, inventory["inventory_sha256"], implementation_sha256()
            )
            result = ledger.write_health(ledger.load())
        else:
            result = execute(data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status", "pass") not in {"fail"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
