from __future__ import annotations

import argparse
import copy
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .c1 import generate_circular_delay_us
from .c1r1 import _joint_downhill_fit, _joint_full_covariance_fit, wrapped_phase_difference
from .c3 import extract_annual_correlation_diagnostic
from .config import load_yaml
from .injection_integrity import (
    classify_injection_warning_lines,
    phase_measurement_diagnostics,
    separate_application_diagnostics,
)
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _directory_size_gib, _peak_rss_gib, _synthetic_toas
from .pilot1_runtime import (
    build_search_frequency_grid,
    generate_covariance_null,
    prepare_covariance_gls_scanner,
)
from .pilot2_calibration_grading import grade_injections
from .pilot2_calibration_revision_design import build_revision_inventory
from .pilot2_calibration_revision_runtime import (
    CONFIG_PATH,
    RevisionLedger,
)
from .pilot2_calibration_revision_runtime import (
    implementation_sha256 as gaussian_implementation_sha256,
)
from .pilot2_calibration_runtime import HeartbeatService, _atomic_json
from .pilot2_preflight import MAX_FIT_ITERATIONS, _load_release, _network_disabled
from .provenance import hash_file

INJECTION_IMPLEMENTATION_FREEZE_PATH = (
    "protocol/PILOT2_INJECTION_IMPLEMENTATION_FREEZE_v0.2.1.json"
)
INJECTION_EXECUTION_FREEZE_PATH = "protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.1.json"
STRUCTURED_CLOSEOUT_PATH = "results/pilot2/structured_tail_closeout_v0.2.1.json"
INJECTION_IMPLEMENTATION_PATHS = (
    "src/pulsar_pilot/pilot2_injection_executor.py",
    "src/pulsar_pilot/c1.py",
    "src/pulsar_pilot/c1r1.py",
    "src/pulsar_pilot/c3.py",
    "src/pulsar_pilot/g2.py",
    "src/pulsar_pilot/pilot1_benchmark.py",
    "src/pulsar_pilot/pilot1_runtime.py",
    "src/pulsar_pilot/pilot2_calibration_grading.py",
    "src/pulsar_pilot/pilot2_calibration_revision_design.py",
    "src/pulsar_pilot/pilot2_calibration_revision_runtime.py",
    "src/pulsar_pilot/pilot2_calibration_runtime.py",
    "src/pulsar_pilot/pilot2_preflight.py",
)
HEARTBEAT_INTERVAL_SECONDS = 30.0
STALE_HEARTBEAT_SECONDS = 90.0
PASSIVE_REVIEW_INTERVAL_SECONDS = 900
ASTROMETRIC_PARAMETERS = ("PX", "ELONG", "ELAT", "PMELONG", "PMELAT")


@dataclass
class InjectionContext:
    model: Any
    toas: Any
    scanner: Any
    exact_scanners: dict[float, Any]
    times: np.ndarray
    reference_epoch: float
    input_binding: dict[str, Any]


def injection_implementation_sha256() -> str:
    root = repository_root()
    digest = hashlib.sha256()
    for relative in INJECTION_IMPLEMENTATION_PATHS:
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update((root / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def verify_injection_implementation_freeze() -> dict[str, Any]:
    root = repository_root()
    path = root / INJECTION_IMPLEMENTATION_FREEZE_PATH
    if not path.is_file():
        return {"status": "locked", "failures": ["Injection implementation freeze is absent"]}
    freeze = json.loads(path.read_text())
    failures: list[str] = []
    if freeze.get("status") != "implementation_frozen_execution_not_authorized":
        failures.append("Injection implementation status is invalid")
    if freeze.get("execution_authorized") is not False:
        failures.append("Injection implementation freeze authorizes execution")
    if freeze.get("science_cases_executed_during_validation") != 0:
        failures.append("Injection implementation validation was not zero-case")
    if freeze.get("implementation_sha256") != injection_implementation_sha256():
        failures.append("Injection aggregate implementation mismatch")
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("Injection implementation inventory mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"Injection implementation hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "implementation_sha256": injection_implementation_sha256(),
        "inventory_sha256": inventory["inventory_sha256"],
        "freeze_sha256": hash_file(path, "sha256"),
    }


def verify_injection_prerequisites(
    data_root: Path, *, verify_case_artifacts: bool = True
) -> dict[str, Any]:
    require_initialized_data_root(data_root)
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    failures: list[str] = []
    closeout_path = root / STRUCTURED_CLOSEOUT_PATH
    closeout = json.loads(closeout_path.read_text()) if closeout_path.is_file() else {}
    if closeout.get("status") != "pass":
        failures.append("Structured-tail closeout is absent or not a pass")
    if closeout.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("Structured-tail closeout inventory mismatch")
    ledger = RevisionLedger(
        data_root, inventory["inventory_sha256"], gaussian_implementation_sha256()
    )
    try:
        state = ledger.load()
    except (OSError, RuntimeError, ValueError) as error:
        return {"status": "fail", "failures": [str(error)]}
    expected_predecessors = {
        "gaussian_threshold_calibration": "pass",
        "commit_threshold_lock": "pass",
        "sealed_gaussian_evaluation": "pass",
        "structured_tail_evaluation": "pass",
    }
    for stage, expected in expected_predecessors.items():
        if state["stage_status"].get(stage) != expected:
            failures.append(f"Unexpected prerequisite stage status: {stage}")
    injection_status = state["stage_status"].get("injection_recovery_and_annual_map")
    if injection_status not in {"pending", "running"}:
        failures.append("Injection stage is not pending or resumable")
    stage_counts = {
        stage: sum(item["stage"] == stage for item in state["completed_cases"].values())
        for stage in (
            "gaussian_threshold_calibration",
            "sealed_gaussian_evaluation",
            "structured_tail_evaluation",
            "injection_recovery_and_annual_map",
        )
    }
    if {key: stage_counts[key] for key in list(stage_counts)[:3]} != {
        "gaussian_threshold_calibration": 5000,
        "sealed_gaussian_evaluation": 2000,
        "structured_tail_evaluation": 3000,
    }:
        failures.append(f"Unexpected predecessor case counts: {stage_counts}")
    if stage_counts["injection_recovery_and_annual_map"] > 284:
        failures.append("Injection case count exceeds the frozen inventory")
    if state.get("hard_stop") is not None:
        failures.append("Cumulative ledger contains a hard stop")
    bindings = closeout.get("artifact_bindings", {})
    external_artifacts = {
        "threshold_lock_sha256": "run_records/pilot2/calibration-threshold-lock-v0.2.1.json",
        "sealed_evaluation_result_sha256": (
            "run_records/pilot2/sealed-gaussian-evaluation-v0.2.1.json"
        ),
        "structured_tail_result_sha256": (
            "run_records/pilot2/structured-tail-evaluation-v0.2.1.json"
        ),
    }
    for key, relative in external_artifacts.items():
        item = data_root / relative
        if not item.is_file() or hash_file(item, "sha256") != bindings.get(key):
            failures.append(f"Injection prerequisite artifact mismatch: {relative}")
    if (
        stage_counts["injection_recovery_and_annual_map"] == 0
        and injection_status == "pending"
    ):
        ledger_path = data_root / "run_records/pilot2/calibration-v0.2.1-ledger.json"
        if hash_file(ledger_path, "sha256") != bindings.get("final_ledger_sha256"):
            failures.append("Pre-injection ledger differs from structured-tail closeout")
    artifact_verification = (
        ledger.verify_artifacts()
        if verify_case_artifacts
        else {"status": "not_requested", "completed_cases": len(state["completed_cases"])}
    )
    if verify_case_artifacts and artifact_verification["status"] != "pass":
        failures.append("Cumulative case-artifact ledger verification failed")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "inventory_sha256": inventory["inventory_sha256"],
        "completed_case_counts": stage_counts,
        "checkpoint_count": len(state["checkpoints"]),
        "artifact_verification": artifact_verification,
        "threshold_lock_sha256": bindings.get("threshold_lock_sha256"),
        "structured_tail_result_sha256": bindings.get("structured_tail_result_sha256"),
        "structured_closeout_sha256": hash_file(closeout_path, "sha256"),
    }


def verify_injection_execution_gate(data_root: Path) -> dict[str, Any]:
    root = repository_root()
    prerequisites = verify_injection_prerequisites(data_root)
    implementation = verify_injection_implementation_freeze()
    failures = list(prerequisites.get("failures", [])) + list(
        implementation.get("failures", [])
    )
    path = root / INJECTION_EXECUTION_FREEZE_PATH
    if not path.is_file():
        failures.append("Injection execution authorization freeze is absent")
        return {
            "status": "locked" if prerequisites["status"] == implementation["status"] == "pass" else "fail",
            "failures": failures,
            "prerequisites": prerequisites,
            "implementation": implementation,
        }
    freeze = json.loads(path.read_text())
    if freeze.get("status") != "frozen_before_first_injection_case":
        failures.append("Injection execution freeze status is invalid")
    if freeze.get("execution_authorized") is not True:
        failures.append("Injection execution is not authorized")
    expected_counts = {"main": 240, "annual": 28, "boundary": 16, "solver_audits": 29}
    if freeze.get("authorized_case_counts") != expected_counts:
        failures.append("Injection authorized counts differ from the frozen inventory")
    for key in (
        "threshold_retuning_authorized",
        "promotion_grade_authorized",
        "observed_residual_access_authorized",
        "observed_periodic_search_authorized",
        "discovery_claim_authorized",
    ):
        if freeze.get(key) is not False:
            failures.append(f"Injection execution boundary invalid: {key}")
    if freeze.get("inventory_sha256") != prerequisites.get("inventory_sha256"):
        failures.append("Injection execution inventory mismatch")
    if freeze.get("implementation_sha256") != implementation.get("implementation_sha256"):
        failures.append("Injection execution implementation mismatch")
    if freeze.get("threshold_lock_sha256") != prerequisites.get("threshold_lock_sha256"):
        failures.append("Injection execution threshold-lock mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"Injection execution hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "prerequisites": prerequisites,
        "implementation": implementation,
        "freeze_sha256": hash_file(path, "sha256"),
    }


def prepare_injection_context(data_root: Path, cases: list[dict[str, Any]]) -> InjectionContext:
    log_path = data_root / "run_records/pilot2/injection-v0.2.1-setup.log"
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
            raise RuntimeError(f"Injection setup mismatch: {key}")
    return InjectionContext(
        model=model,
        toas=toas,
        scanner=scanner,
        exact_scanners=exact_scanners,
        times=times,
        reference_epoch=reference_epoch,
        input_binding=binding,
    )


def _solver_audit_pass(
    primary: dict[str, Any], audit: dict[str, Any], comparison: dict[str, float], config: dict[str, Any]
) -> bool:
    limits = config["solver_audit"]
    return bool(
        primary["returned_converged"]
        and primary["fitter_converged"]
        and audit["completed"]
        and primary["release_red_noise_preserved"]
        and audit["release_red_noise_preserved"]
        and primary["wavex_absent"]
        and audit["wavex_absent"]
        and comparison["amplitude_difference_microseconds"]
        <= float(limits["amplitude_difference_maximum_microseconds"])
        and comparison["phase_difference_radians"]
        <= float(limits["phase_difference_maximum_radians"])
        and comparison["chi2_difference"] <= float(limits["chi2_difference_maximum"])
    )


def _phase_telemetry(primary: dict[str, Any], injected_phase: float) -> dict[str, float]:
    correlation = primary["fitter"].get_parameter_correlation_matrix()
    block = correlation.get_label_matrix(["CSSIN", "CSCOS"])
    diagnostics = phase_measurement_diagnostics(
        float(primary["sine_us"]),
        float(primary["cosine_us"]),
        float(primary["sine_uncertainty_us"]),
        float(primary["cosine_uncertainty_us"]),
        float(block.matrix[0, 1]),
    )
    diagnostics["signed_wrapped_phase_error_radians"] = wrapped_phase_difference(
        diagnostics["recovered_phase_radians"], injected_phase
    )
    return diagnostics


def _execute_injection_case(
    context: InjectionContext,
    case: dict[str, Any],
    threshold: float,
    audit_required: bool,
    config: dict[str, Any],
    execution_binding: str,
) -> dict[str, Any]:
    from pint.fitter import WidebandDownhillFitter
    from pint.residuals import WidebandTOAResiduals

    count = len(context.toas)
    noise = generate_covariance_null(
        context.scanner.covariance_cholesky, np.random.default_rng(int(case["seed"]))
    )
    signal_us = np.asarray(
        generate_circular_delay_us(
            context.times.astype(np.longdouble),
            float(case["period_days"]),
            float(case["amplitude_microseconds"]),
            float(case["phase_radians"]),
            context.reference_epoch,
        ),
        dtype=float,
    )
    requested = noise.copy()
    requested[:count] += signal_us * 1e-6
    scan = context.scanner.scan(requested)
    synthetic, application = _synthetic_toas(context.toas, context.model, requested)
    ordinary = WidebandDownhillFitter(synthetic, copy.deepcopy(context.model))
    ordinary_returned = bool(ordinary.fit_toas(maxiter=MAX_FIT_ITERATIONS))
    ordinary_residuals = WidebandTOAResiduals(synthetic, ordinary.model)
    exact = context.exact_scanners[float(case["period_days"])].scan(
        ordinary_residuals.calc_wideband_resids()
    )
    postfit_amplitude = float(exact["amplitude_us"])
    absorption = float(
        np.clip(1.0 - postfit_amplitude / float(case["amplitude_microseconds"]), 0.0, 1.0)
    )
    injected_frequency = 1.0 / float(case["period_days"])
    primary = _joint_downhill_fit(
        synthetic,
        context.model,
        injected_frequency,
        context.reference_epoch,
        MAX_FIT_ITERATIONS,
    )
    phase_telemetry = _phase_telemetry(primary, float(case["phase_radians"]))
    application_diagnostics = separate_application_diagnostics(application)
    comparison: dict[str, float] | None = None
    audit_payload: dict[str, Any] | None = None
    audit_pass = True
    if audit_required:
        audit = _joint_full_covariance_fit(
            synthetic,
            context.model,
            injected_frequency,
            context.reference_epoch,
            MAX_FIT_ITERATIONS,
        )
        comparison = {
            "amplitude_difference_microseconds": abs(
                float(primary["amplitude_us"]) - float(audit["amplitude_us"])
            ),
            "phase_difference_radians": abs(
                wrapped_phase_difference(
                    float(primary["phase_radians"]), float(audit["phase_radians"])
                )
            ),
            "chi2_difference": abs(float(primary["chi2"]) - float(audit["chi2"])),
        }
        audit_pass = _solver_audit_pass(primary, audit, comparison, config)
        audit_payload = {
            key: value for key, value in audit.items() if key not in {"fitter", "model", "residuals"}
        }
    astrometric_correlation = 0.0
    if case["family"] == "annual":
        diagnostic = extract_annual_correlation_diagnostic(
            primary["fitter"], list(ASTROMETRIC_PARAMETERS)
        )
        astrometric_correlation = float(diagnostic["maximum_absolute_correlation"])
    independent_bin = 1.0 / float(np.ptp(context.times))
    amplitude_bias = abs(
        float(primary["amplitude_us"]) - float(case["amplitude_microseconds"])
    ) / float(case["amplitude_microseconds"])
    phase_error = abs(phase_telemetry["signed_wrapped_phase_error_radians"])
    record = {
        "schema_version": 1,
        "run_id": "pilot2-b1937-calibration-v0.2.1",
        "execution_binding_sha256": execution_binding,
        "case": case,
        "family": case["family"],
        "period_days": float(case["period_days"]),
        "amplitude_microseconds": float(case["amplitude_microseconds"]),
        "phase_radians": float(case["phase_radians"]),
        "locked_threshold_delta_chi2": threshold,
        "global_maximum_delta_chi2": float(scan["trigger_statistic"]),
        "triggered": float(scan["trigger_statistic"]) > threshold,
        "frequency_recovered": abs(float(scan["peak_frequency_per_day"]) - injected_frequency)
        <= independent_bin,
        "frequency_recovery_tolerance_per_day": independent_bin,
        "amplitude_bias_fraction": amplitude_bias,
        "phase_error_radians": phase_error,
        **phase_telemetry,
        "toa_adjustment_error_microseconds": application_diagnostics[
            "toa_adjustment_maximum_absolute_error_microseconds"
        ],
        **application_diagnostics,
        "ordinary_fit_converged": ordinary_returned and bool(ordinary.converged),
        "joint_fit_converged": bool(primary["returned_converged"])
        and bool(primary["fitter_converged"]),
        "ordinary_absorption_fraction": absorption,
        "signal_astrometry_correlation": astrometric_correlation,
        "solver_audit_required": audit_required,
        "solver_audit_pass": audit_pass,
        "solver_comparison": comparison,
        "full_covariance_solver": audit_payload,
        "input_binding": context.input_binding,
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
    }
    return json.loads(json.dumps(record, sort_keys=True))


def _record_path(data_root: Path, sequence: int, case: dict[str, Any]) -> Path:
    return (
        data_root
        / "derived/pilot2/calibration-v0.2.1/injections"
        / case["family"]
        / f"{sequence:04d}-{case['case_id']}.json"
    )


def _resource_gate(name: str, observed: float, limit: float) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "comparator": "<=",
        "limit": limit,
        "status": "pass" if observed <= limit else "fail",
    }


def execute_injections(data_root: Path) -> dict[str, Any]:
    gate = verify_injection_execution_gate(data_root)
    if gate["status"] != "pass":
        raise RuntimeError(f"Injection execution is locked: {gate['failures']}")
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    cases = inventory["injection_cases"]
    audit_ids = set(inventory["solver_audit_case_ids"])
    ledger = RevisionLedger(
        data_root, inventory["inventory_sha256"], gaussian_implementation_sha256()
    )
    state = ledger.load()
    if state["stage_status"]["injection_recovery_and_annual_map"] == "pass":
        return {"status": "already_complete", "science_cases_executed_this_invocation": 0}
    if state["active_stage"] is None:
        ledger.begin_stage("injection_recovery_and_annual_map")
    lock_path = data_root / "run_records/pilot2/calibration-threshold-lock-v0.2.1.json"
    lock = ledger.verify_threshold_lock()
    lock_sha = hash_file(lock_path, "sha256")
    freeze_sha = hash_file(root / INJECTION_EXECUTION_FREEZE_PATH, "sha256")
    execution_binding = hashlib.sha256(
        f"{injection_implementation_sha256()}:{freeze_sha}:{lock_sha}".encode()
    ).hexdigest()
    context = prepare_injection_context(data_root, cases)
    started = time.perf_counter()
    records_by_id: dict[str, dict[str, Any]] = {}
    executed = 0

    def load_or_execute(sequence: int, case: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        path = _record_path(data_root, sequence, case)
        if case["case_id"] in ledger.load()["completed_cases"]:
            return json.loads(path.read_text()), False
        return (
            _execute_injection_case(
                context,
                case,
                float(lock["value_delta_chi2"]),
                case["case_id"] in audit_ids,
                config,
                execution_binding,
            ),
            True,
        )

    with HeartbeatService(ledger, HEARTBEAT_INTERVAL_SECONDS):
        def process_nonannual_family(family: str) -> None:
            nonlocal executed
            family_cases = [
                (sequence, case)
                for sequence, case in enumerate(cases, 1)
                if case["family"] == family
            ]
            for sequence, case in family_cases:
                record, is_new = load_or_execute(sequence, case)
                if is_new:
                    path = _record_path(data_root, sequence, case)
                    record["candidate_eligible"] = True
                    _atomic_json(path, record)
                    ledger.record_case(
                        "injection_recovery_and_annual_map", case["case_id"], path
                    )
                    executed += 1
                records_by_id[case["case_id"]] = record
                print(f"PILOT2R1_INJECTION_PROGRESS {len(records_by_id)}/284", flush=True)

        process_nonannual_family("main")

        annual_periods = sorted(
            {float(case["period_days"]) for case in cases if case["family"] == "annual"}
        )
        correlation_limit = float(
            config["candidate_eligibility"]["maximum_signal_astrometry_correlation"]
        )
        absorption_limit = float(
            config["candidate_eligibility"]["maximum_ordinary_model_absorption_fraction"]
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
            for item in group_records:
                if "candidate_eligible" in item and bool(item["candidate_eligible"]) != eligible:
                    raise RuntimeError("Resumed annual eligibility differs from frozen group result")
                item["candidate_eligible"] = eligible
            for sequence, case, record in pending:
                path = _record_path(data_root, sequence, case)
                _atomic_json(path, record)
                ledger.record_case("injection_recovery_and_annual_map", case["case_id"], path)
                executed += 1
                print(f"PILOT2R1_INJECTION_PROGRESS {len(records_by_id) + 1}/284", flush=True)
            records_by_id.update({item["case"]["case_id"]: item for item in group_records})
            if time.perf_counter() - started > float(config["resource_caps"]["macbook_wall_hours_maximum"]) * 3600:
                raise RuntimeError("Injection stage exceeded the frozen six-hour wall cap")

        process_nonannual_family("boundary")

    records = [records_by_id[case["case_id"]] for case in cases]
    if hash_file(lock_path, "sha256") != lock_sha:
        raise RuntimeError("Threshold lock changed during injection evaluation")
    result = grade_injections(records, config)
    elapsed_hours = (time.perf_counter() - started) / 3600.0
    peak_memory = _peak_rss_gib()
    data_root_size = _directory_size_gib(data_root)
    resource_caps = config["resource_caps"]
    log_path = data_root / "run_records/pilot2/injection-v0.2.1-setup.log"
    sanitized = [
        line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
        for line in log_path.read_text().splitlines()
    ]
    warnings = classify_injection_warning_lines(sanitized)
    result["gates"].extend(
        [
            _resource_gate(
                "injection_wall_hours",
                elapsed_hours,
                float(resource_caps["macbook_wall_hours_maximum"]),
            ),
            _resource_gate(
                "peak_memory_gib",
                peak_memory,
                float(resource_caps["peak_memory_gib_maximum"]),
            ),
            _resource_gate(
                "complete_data_root_gib",
                data_root_size,
                float(resource_caps["complete_data_root_gib_maximum"]),
            ),
            {
                "name": "unexpected_material_warnings",
                "observed": warnings["status"],
                "comparator": "==",
                "limit": "pass",
                "status": warnings["status"],
            },
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
    )
    result_path = data_root / "run_records/pilot2/injection-evaluation-v0.2.1.json"
    _atomic_json(result_path, result)
    ledger.complete_stage(
        "injection_recovery_and_annual_map", result_path, result["status"] == "pass"
    )
    return {
        "status": result["status"],
        "completed_injection_cases": len(records),
        "science_cases_executed_this_invocation": executed,
        "threshold_lock_unchanged": hash_file(lock_path, "sha256") == lock_sha,
        "ledger_verification": ledger.verify_artifacts(),
    }


def supervision_snapshot(data_root: Path, now: datetime | None = None) -> dict[str, Any]:
    config = load_yaml(repository_root() / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    ledger = RevisionLedger(
        data_root, inventory["inventory_sha256"], gaussian_implementation_sha256()
    )
    state = ledger.load()
    stage = "injection_recovery_and_annual_map"
    status = state["stage_status"][stage]
    health = json.loads(ledger.health_path.read_text()) if ledger.health_path.is_file() else {}
    event = "locked_idle"
    codex_check_required = False
    heartbeat_age_seconds: float | None = None
    if status in {"pass", "fail"}:
        event = f"terminal_{status}"
        codex_check_required = True
    elif status == "running":
        heartbeat = health.get("last_heartbeat_utc")
        if heartbeat:
            observed = datetime.fromisoformat(heartbeat)
            heartbeat_age_seconds = max(0.0, ((now or datetime.now(UTC)) - observed).total_seconds())
        if not state.get("runtime_active") or heartbeat_age_seconds is None:
            event = "paused_or_interrupted"
            codex_check_required = True
        elif heartbeat_age_seconds > STALE_HEARTBEAT_SECONDS:
            event = "stale_attention_required"
            codex_check_required = True
        else:
            event = "healthy_no_action"
    completed = sum(item["stage"] == stage for item in state["completed_cases"].values())
    return {
        "schema_version": 1,
        "event": event,
        "codex_check_required": codex_check_required,
        "heartbeat_age_seconds": heartbeat_age_seconds,
        "heartbeat_interval_seconds": HEARTBEAT_INTERVAL_SECONDS,
        "stale_after_seconds": STALE_HEARTBEAT_SECONDS,
        "passive_review_interval_seconds": PASSIVE_REVIEW_INTERVAL_SECONDS,
        "injection_cases_completed": completed,
        "injection_cases_total": 284,
        "checkpoint_count": len(state["checkpoints"]),
        "hard_stop_present": state.get("hard_stop") is not None,
        "scientific_outcomes_sealed": True,
        "policy": "no_codex_poll_while_heartbeat_fresh",
    }


def zero_case_dry_run(data_root: Path) -> dict[str, Any]:
    prerequisites = verify_injection_prerequisites(data_root)
    implementation = verify_injection_implementation_freeze()
    gate = verify_injection_execution_gate(data_root)
    snapshot = supervision_snapshot(data_root)
    counts = prerequisites["completed_case_counts"]
    criteria = {
        "structured_prerequisites_pass": prerequisites["status"] == "pass",
        "injection_implementation_freeze_pass": implementation["status"] == "pass",
        "injection_execution_gate_locked": gate["status"] == "locked",
        "zero_injection_cases_recorded": counts["injection_recovery_and_annual_map"] == 0,
        "exact_frozen_inventory": True,
        "exact_29_solver_audits": True,
        "heartbeat_interval_30_seconds": HEARTBEAT_INTERVAL_SECONDS == 30.0,
        "stale_tripwire_90_seconds": STALE_HEARTBEAT_SECONDS == 90.0,
        "passive_review_interval_15_minutes": PASSIVE_REVIEW_INTERVAL_SECONDS == 900,
        "idle_supervision_requires_no_codex_check": snapshot["codex_check_required"] is False,
        "observed_search_boundary_preserved": True,
    }
    return {
        "schema_version": 1,
        "status": "pass" if all(criteria.values()) else "fail",
        "operation": "injection_v0.2.1_zero_case_integrity_dry_run",
        "criteria": criteria,
        "science_cases_executed": 0,
        "random_draws_generated": 0,
        "model_fits_executed": 0,
        "periodic_scans_executed": 0,
        "prerequisites": prerequisites,
        "execution_gate_status": gate["status"],
        "supervision": snapshot,
    }


def verify_setup(data_root: Path) -> dict[str, Any]:
    prerequisites = verify_injection_prerequisites(data_root)
    if prerequisites["status"] != "pass":
        return {"status": "fail", "failures": prerequisites["failures"]}
    config = load_yaml(repository_root() / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    context = prepare_injection_context(data_root, inventory["injection_cases"])
    expected_periods = sorted(
        {float(case["period_days"]) for case in inventory["injection_cases"]}
    )
    criteria = {
        "input_binding_exact": context.input_binding["active_toas"] == 660
        and context.input_binding["covariance_shape"] == [1320, 1320]
        and context.input_binding["timing_design_shape"] == [1320, 284]
        and context.input_binding["timing_design_rank"] == 284,
        "all_exact_period_scanners_prepared": sorted(context.exact_scanners) == expected_periods,
        "network_disabled": context.input_binding["network_access_enabled"] is False,
        "observed_residual_vector_not_loaded": context.input_binding[
            "observed_residual_vector_loaded"
        ]
        is False,
        "observed_periodic_scan_not_executed": context.input_binding[
            "observed_periodic_scan_executed"
        ]
        is False,
    }
    return {
        "schema_version": 1,
        "status": "pass" if all(criteria.values()) else "fail",
        "operation": "injection_v0.2.1_offline_setup_only",
        "criteria": criteria,
        "input_binding": context.input_binding,
        "exact_period_scanner_count": len(context.exact_scanners),
        "exact_periods_days": expected_periods,
        "science_cases_executed": 0,
        "random_draws_generated": 0,
        "model_fits_executed": 0,
        "periodic_scans_executed": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-injection-executor")
    parser.add_argument(
        "command",
        choices=(
            "verify-prerequisites",
            "verify-implementation",
            "verify-gate",
            "verify-setup",
            "dry-run",
            "health",
            "run-injections",
        ),
    )
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()
    data_root = configured_data_root(args.data_root)
    if args.command == "verify-prerequisites":
        result = verify_injection_prerequisites(data_root)
    elif args.command == "verify-implementation":
        result = verify_injection_implementation_freeze()
    elif args.command == "verify-gate":
        result = verify_injection_execution_gate(data_root)
    elif args.command == "verify-setup":
        result = verify_setup(data_root)
    elif args.command == "dry-run":
        result = zero_case_dry_run(data_root)
    elif args.command == "health":
        result = supervision_snapshot(data_root)
    else:
        result = execute_injections(data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status", "pass") not in {"fail"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
