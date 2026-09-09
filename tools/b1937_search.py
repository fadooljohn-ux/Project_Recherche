"""Prepare and execute one B1937+21 search using the qualified numerical runtime."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from recherche_operator import REPO, doctor, read, sha, write

from pulsar_pilot.c1r1 import (
    _joint_downhill_fit,
    _joint_full_covariance_fit,
    wrapped_phase_difference,
)
from pulsar_pilot.c3 import extract_annual_correlation_diagnostic
from pulsar_pilot.injection_integrity import classify_injection_warning_lines
from pulsar_pilot.one_shot_search import build_annual_mask, select_strongest_unmasked
from pulsar_pilot.pilot2_durable_ledger import durable_atomic_json, sync_directory
from pulsar_pilot.pilot2_injection_executor import ASTROMETRIC_PARAMETERS, _solver_audit_pass
from pulsar_pilot.pilot2_ioc_harness import _publish_status, _status_value, _terminalize
from pulsar_pilot.pilot2_offline_resources import OfflineRuntimeBoundary
from pulsar_pilot.pilot2_preflight import MAX_FIT_ITERATIONS
from pulsar_pilot.pilot2_release_contract import load_science_controls
from pulsar_pilot.pilot2_runtime_core import (
    prepare_context,
    validate_annual_mask,
    verify_predecessors,
)
from pulsar_pilot.runtime_limits import RuntimeLimits

POLICY = {
    "schema": "b1937-observed-search-v1",
    "target": "B1937+21",
    "run_id": "pilot2-ioc-observed-b1937-20260908-01",
    "selection": "strongest_unmasked_grid_cell",
    "annual_mapping": "nearest_period_cell_ties_to_lowest_index",
    "trigger_comparison": "strictly_greater",
    "maximum_scans": 1,
    "maximum_primary_fits": 2,
    "maximum_solver_audits": 1,
    "frequency_refinement": False,
    "threshold_retuning": False,
    "automatic_retry": False,
    "discovery_claim": False,
    "wall_seconds": 21600,
    "rss_gib": 16.0,
    "disk_gib": 1.5,
}


def stamp():
    return datetime.now(UTC).isoformat()


def code_hashes():
    paths = sorted((REPO / "src").rglob("*.py"))
    paths += [
        REPO / p
        for p in (
            "tools/b1937_search.py",
            "tools/recherche",
            "tools/recherche_operator.py",
            "config/pilot2_calibration_v0.2.1.yaml",
            "config/pilot2_injection_remediation_v0.2.2.yaml",
        )
    ]
    return {p.relative_to(REPO).as_posix(): sha(p) for p in paths}


def frequencies_from_grid(grid):
    from pulsar_pilot.pilot1_runtime import build_search_frequency_grid

    frequencies, rebuilt = build_search_frequency_grid(
        np.array([0.0, grid["span_days"]]), 30.0, 2000.0, 5
    )
    if rebuilt != grid:
        raise RuntimeError("Qualification frequency grid cannot be reconstructed exactly")
    return frequencies


def bind_evidence(data, qualification):
    """Read saved qualification evidence and input hashes; never construct residuals."""
    doctor(data)
    base, _, runner = load_science_controls(REPO)
    predecessors = verify_predecessors(data, runner)
    if predecessors["status"] != "pass":
        raise RuntimeError(str(predecessors["failures"]))
    for name in ("sealed_gaussian_result", "structured_tail_result"):
        if predecessors["records"][name]["status"] != "pass":
            raise RuntimeError(f"Predecessor is not PASS: {name}")
    result_path = qualification / runner["paths"]["result"]
    accepted = read(REPO / "results/qualification/qualification02-terminal-verification.json")
    if sha(result_path) != accepted["result_sha256"]:
        raise RuntimeError("Qualification 02 result differs from its terminal receipt")
    result = read(result_path)
    if (
        result["status"] != "pass"
        or len(result["payload"]["gates"]) != 21
        or not all(gate["status"] == "pass" for gate in result["payload"]["gates"])
    ):
        raise RuntimeError("Qualification 02 is not a complete PASS")
    mask_path = qualification / runner["paths"]["annual_mask"]
    if sha(mask_path) != result["annual_mask_sha256"]:
        raise RuntimeError("Qualification annual mask hash differs")
    mask = read(mask_path)
    validate_annual_mask(
        mask,
        execution_binding=result["execution_binding_sha256"],
        allowed_periods=base["injections"]["annual_identifiability_map"]["periods_days"],
    )
    if mask["status"] != "complete":
        raise RuntimeError("Annual mask is incomplete")
    records = {
        read(p)["case"]["case_id"]: p
        for p in (qualification / runner["paths"]["case_root"]).rglob("*.json")
    }
    bound_files = {str(result_path): sha(result_path), str(mask_path): sha(mask_path)}
    for group in mask["periods"]:
        values = []
        for case, digest in zip(
            group["contributing_case_ids"], group["contributing_artifact_sha256"], strict=True
        ):
            path = records[case]
            if sha(path) != digest:
                raise RuntimeError(f"Annual source record differs: {case}")
            record = read(path)
            if record["period_days"] != group["period_days"] or record["family"] != "annual":
                raise RuntimeError("Annual source period differs")
            values.append(record)
            bound_files[str(path)] = digest
        correlation = max(v["signal_astrometry_correlation"] for v in values)
        absorption = max(v["ordinary_absorption_fraction"] for v in values)
        eligible = (
            correlation < base["candidate_eligibility"]["maximum_signal_astrometry_correlation"]
            and absorption
            < base["candidate_eligibility"]["maximum_ordinary_model_absorption_fraction"]
        )
        if (
            group["maximum_signal_astrometry_correlation"] != correlation
            or group["maximum_ordinary_model_absorption_fraction"] != absorption
            or group["candidate_eligible"] != eligible
        ):
            raise RuntimeError("Annual eligibility differs from contributing records")
    first = read(records[min(records)])
    grid = first["input_binding"]["frequency_grid"]
    mapping = build_annual_mask(
        frequencies_from_grid(grid),
        [group["period_days"] for group in mask["periods"] if not group["candidate_eligible"]],
    )
    lock = data / runner["predecessor_bindings"]["threshold_lock"]["logical_path"]
    if sha(lock) != result["threshold_lock_sha256"]:
        raise RuntimeError("Threshold differs from qualification 02")
    return {
        "threshold": predecessors["threshold_delta_chi2"],
        "threshold_sha256": sha(lock),
        "annual_mask_sha256": sha(mask_path),
        "annual_grid_mapping": mapping,
        "frequency_grid": grid,
        "reference_epoch_mjd_tdb": first["input_binding"]["reference_epoch_mjd_tdb"],
        "qualification_files": bound_files,
        "data_files": {
            str(p): sha(p)
            for p in [
                *(
                    data / i["path"]
                    for i in read(REPO / "config/rehabilitation_inputs.json")["inputs"]
                ),
                data / ".project-recherche-data-root.json",
                data / "metadata/resources.json",
                data / "metadata/development-environment.json",
                data / "metadata/provisioning-receipt.json",
            ]
        },
    }


def prepare(data, qualification, package_path):
    evidence = bind_evidence(data, qualification)
    root = data / "observed-runs" / POLICY["run_id"]
    if root.exists() or (data / "b1937-observed-search-intent.json").exists():
        raise RuntimeError("The first-search destination is already consumed")
    package = {
        "policy": POLICY,
        "created_at": stamp(),
        "data_root": str(data),
        "run_root": str(root),
        "qualification_root": str(qualification),
        "evidence": evidence,
        "code_sha256": code_hashes(),
        "observed_residual_vector_read": False,
        "observed_scan_executed": False,
    }
    package_path.parent.mkdir(parents=True, exist_ok=True)
    with package_path.open("x") as handle:
        json.dump(package, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return {
        "status": "PREPARED",
        "package": str(package_path),
        "sha256": sha(package_path),
        "execution_started": False,
        "threshold": evidence["threshold"],
        "annual_grid_mapping": evidence["annual_grid_mapping"],
    }


def check(package_path):
    package = read(package_path)
    if package["policy"] != POLICY or package["code_sha256"] != code_hashes():
        raise RuntimeError("Search policy or implementation changed after preparation")
    data = Path(package["data_root"])
    if not data.is_absolute() or data.resolve() != data:
        raise RuntimeError("Search data root is not canonical")
    if Path(package["run_root"]) != data / "observed-runs" / POLICY["run_id"]:
        raise RuntimeError("Search output path differs")
    actual = bind_evidence(data, Path(package["qualification_root"]))
    if actual != package["evidence"]:
        raise RuntimeError("Search evidence changed after preparation")
    return package


def analyze(context, residuals, toas, evidence, output, completed):
    """Identical analysis for the observed entry point and synthetic integration check."""
    from pint.fitter import WidebandDownhillFitter
    from pint.residuals import WidebandTOAResiduals

    base, _, _ = load_science_controls(REPO)
    vector = np.asarray(residuals, dtype=float)
    if not np.all(np.isfinite(vector)):
        raise RuntimeError("Residual vector contains nonfinite values")
    scan = context.scanner.scan(vector)
    completed("scans")
    selection = select_strongest_unmasked(
        scan["all_delta_chi2"],
        context.scanner.frequencies_per_day,
        evidence["annual_grid_mapping"]["masked_grid_indices"],
    )
    write(
        output / "periodogram.json",
        {
            "frequency_per_day": context.scanner.frequencies_per_day.tolist(),
            "delta_chi2": scan["all_delta_chi2"].tolist(),
        },
    )
    triggered = selection["statistic"] > evidence["threshold"]
    result = {
        "disposition": "NO_TRIGGER",
        "triggered": bool(triggered),
        "threshold": evidence["threshold"],
        "selected_peak": selection,
        "global_peak_statistic": scan["trigger_statistic"],
        "global_peak_period_days": scan["peak_period_days"],
        "annual_grid_mapping": evidence["annual_grid_mapping"],
        "residual_vector_sha256": hashlib.sha256(vector.astype("<f8").tobytes()).hexdigest(),
        "discovery_claim": False,
        "false_alarm_probability_estimated": False,
    }
    if not triggered:
        return result
    ordinary = WidebandDownhillFitter(toas, copy.deepcopy(context.model))
    converged = bool(ordinary.fit_toas(maxiter=MAX_FIT_ITERATIONS)) and bool(ordinary.converged)
    completed("primary_fits")
    ordinary_chi2 = float(WidebandTOAResiduals(toas, ordinary.model).chi2)
    primary = _joint_downhill_fit(
        toas,
        context.model,
        selection["frequency_per_day"],
        context.reference_epoch,
        MAX_FIT_ITERATIONS,
    )
    completed("primary_fits")
    audit = _joint_full_covariance_fit(
        toas,
        context.model,
        selection["frequency_per_day"],
        context.reference_epoch,
        MAX_FIT_ITERATIONS,
    )
    completed("solver_audits")
    comparison = {
        "amplitude_difference_microseconds": abs(primary["amplitude_us"] - audit["amplitude_us"]),
        "phase_difference_radians": abs(
            wrapped_phase_difference(primary["phase_radians"], audit["phase_radians"])
        ),
        "chi2_difference": abs(primary["chi2"] - audit["chi2"]),
    }
    agreement = converged and _solver_audit_pass(primary, audit, comparison, base)
    correlation = extract_annual_correlation_diagnostic(
        primary["fitter"], list(ASTROMETRIC_PARAMETERS)
    )
    eligible = (
        correlation["maximum_absolute_correlation"]
        < base["candidate_eligibility"]["maximum_signal_astrometry_correlation"]
    )
    measurement = lambda fit: {
        k: v for k, v in fit.items() if k not in {"fitter", "model", "residuals"}
    }
    result.update(
        disposition=(
            "NUMERICAL_HOLD"
            if not agreement
            else "IDENTIFIABILITY_HOLD"
            if not eligible
            else "PERIODIC_SIGNAL_CANDIDATE"
        ),
        ordinary_fit_converged=converged,
        ordinary_chi2=ordinary_chi2,
        joint_chi2_improvement=ordinary_chi2 - primary["chi2"],
        primary=measurement(primary),
        audit=measurement(audit),
        solver_comparison=comparison,
        solver_audit_pass=bool(agreement),
        signal_astrometry_correlation=correlation,
        candidate_eligible=bool(agreement and eligible),
    )
    return result


def claim(data, package_path):
    """Consume the attempt atomically before loading the observed vector."""
    intent = data / "b1937-observed-search-intent.json"
    with intent.open("x") as handle:
        json.dump(
            {
                "package_sha256": sha(package_path),
                "started_at": stamp(),
                "run_id": POLICY["run_id"],
                "resume_allowed": False,
            },
            handle,
        )
        handle.flush()
        os.fsync(handle.fileno())
    sync_directory(data)
    return intent


def run(package_path, authorized_sha):
    if not authorized_sha or authorized_sha != sha(package_path):
        raise RuntimeError(
            "Execution requires explicit --authorize-package with the prepared SHA-256"
        )
    package = check(package_path)
    data, output = Path(package["data_root"]), Path(package["run_root"])
    if output.exists():
        raise RuntimeError("Search output already exists; no automatic rerun")
    claim(data, package_path)
    output.mkdir(parents=True)
    manifest = {"run_id": POLICY["run_id"], "package_sha256": authorized_sha, "package": package}
    write(output / "manifest.json", manifest)
    counts = {"scans": 0, "primary_fits": 0, "solver_audits": 0}
    started = time.monotonic()
    limits = RuntimeLimits(
        output,
        wall_seconds=POLICY["wall_seconds"],
        rss_gib=POLICY["rss_gib"],
        disk_gib=POLICY["disk_gib"],
    )
    stop = threading.Event()

    def pulse(state="running", error=None):
        status = _status_value(
            POLICY["run_id"],
            state,
            "run" if state == "running" else "terminal",
            int(state == "complete"),
            1,
            int(state == "complete"),
            "Observed search lifecycle",
            elapsed_seconds=time.monotonic() - started,
            error_type=error,
            terminal=state != "running",
        )
        _publish_status(output, status)
        return status

    def heartbeat():
        while not stop.wait(30):
            pulse()

    def completed(name):
        counts[name] += 1
        durable_atomic_json(output / "accounting.json", counts)
        limits.check(disk=True)

    pulse()
    durable_atomic_json(
        output / "ledger.json", {"runtime_active": True, "active_attempt": POLICY["run_id"]}
    )
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    state, error = "complete", None
    try:
        resources = read(data / "metadata/resources.json")
        with OfflineRuntimeBoundary(data, resources) as boundary:
            context = prepare_context(
                data,
                [],
                resource_manifest=resources,
                resource_manifest_sha256=sha(data / "metadata/resources.json"),
                environment_manifest_sha256=sha(data / "metadata/development-environment.json"),
                setup_log_relative=str((output / "context.log").relative_to(data)),
                resource_boundary=boundary,
            )
            if context.input_binding["frequency_grid"] != package["evidence"]["frequency_grid"]:
                raise RuntimeError("Runtime grid differs from the prepared qualification grid")
            limits.check()
            # This is the only observed-vector access; prepare/check never call it.
            from pint.residuals import WidebandTOAResiduals

            observed = WidebandTOAResiduals(context.toas, context.model).calc_wideband_resids()
            result = analyze(
                context, observed, context.toas, package["evidence"], output, completed
            )
            trace = boundary.verify_trace()
            if trace["status"] != "pass":
                raise RuntimeError(f"Offline resources differ: {trace['failures']}")
        warnings = classify_injection_warning_lines(
            (output / "context.log").read_text().splitlines()
        )
        if warnings["status"] != "pass":
            result.update(disposition="WARNING_HOLD", candidate_eligible=False)
        write(output / "resource-trace.json", trace)
        write(output / "warnings.json", warnings)
        write(
            output / "input-binding.json",
            {
                **context.input_binding,
                "observed_residual_vector_loaded": True,
                "observed_periodic_scan_executed": True,
            },
        )
        result.update(accounting=counts, observed_search=True, package_sha256=authorized_sha)
        with (output / "result.json").open("x") as handle:
            json.dump(result, handle, indent=2, allow_nan=False)
            handle.write("\n")
    except (
        Exception,  # noqa: BLE001 - terminalize every consumed-attempt failure
        KeyboardInterrupt,
    ) as exc:  # Preserve a consumed attempt on every runtime failure.
        state = "controlled_stop" if isinstance(exc, KeyboardInterrupt) else "operational_failure"
        error = type(exc).__name__
        write(output / "failure.json", {"type": error, "message": str(exc), "accounting": counts})
    finally:
        stop.set()
        thread.join()
        durable_atomic_json(
            output / "ledger.json",
            {"runtime_active": False, "active_attempt": None, "terminal_state": state},
        )
        final = pulse(state, error)
        terminal = _terminalize(output, manifest, state, error, final)
    return terminal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--data-root", type=Path, required=True)
    prep.add_argument("--qualification-root", type=Path, required=True)
    prep.add_argument("--package", type=Path, required=True)
    verify = sub.add_parser("check")
    verify.add_argument("--package", type=Path, required=True)
    execute = sub.add_parser("run")
    execute.add_argument("--package", type=Path, required=True)
    execute.add_argument("--authorize-package", required=True)
    args = parser.parse_args()
    try:
        package = args.package.resolve()
        if args.command == "prepare":
            result = prepare(
                args.data_root.resolve(strict=True),
                args.qualification_root.resolve(strict=True),
                package,
            )
        elif args.command == "check":
            checked = check(package)
            result = {
                "status": "PASS",
                "package_sha256": sha(package),
                "run_id": checked["policy"]["run_id"],
                "observed_scans_this_command": 0,
                "execution_state": "consumed"
                if (Path(checked["data_root"]) / "b1937-observed-search-intent.json").exists()
                else "ready",
            }
        else:
            result = run(package, args.authorize_package)
        print(json.dumps(result, indent=2))
        return 0 if result.get("terminal_state", "complete") == "complete" else 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "FAIL", "message": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
