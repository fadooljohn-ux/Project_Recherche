from __future__ import annotations

import copy
import math
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from contextlib import AbstractContextManager, ExitStack, nullcontext
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import numpy as np

from .injection_integrity import classify_injection_warning_lines
from .pilot1_benchmark import _directory_size_gib, _peak_rss_gib
from .pilot1_runtime import build_search_frequency_grid, prepare_covariance_gls_scanner
from .pilot2_case_contract import (
    BASE_RECORD_KEYS,
    DM_ERROR_KEY,
    RECORD_BOOLEAN_KEYS,
    RECORD_NUMERIC_KEYS,
    TOA_ADJUSTMENT_KEY,
    UNCENTERED_TARGET_KEY,
    _gate,
    _validate_solver_payload,
    grade_records,
)
from .pilot2_durable_ledger import (
    RUN_ID,
    STAGE,
    SingleWriterLock,
    V028Ledger,
    durable_atomic_json,
    durable_mkdirs,
    utc_now,
    validate_terminal_result,
)
from .pilot2_injection_executor import InjectionContext
from .pilot2_injection_executor_v028 import (
    RECORD_RUN_ID,
    RECORD_SCHEMA_VERSION,
    execute_injection_case,
)
from .pilot2_injection_remediation_v023 import build_v023_inventory
from .pilot2_offline_resources import OfflineRuntimeBoundary
from .pilot2_release_contract import (
    INVENTORY_SHA256,
    execution_binding_sha256,
    ioc_execution_binding_sha256,
    load_science_controls,
    verify_execution_gate,
    verify_ioc_science_execution_gate,
    verify_repository_execution_authorization,
)
from .pilot2_trusted_data import (
    TrustedDataError,
    canonical_sha256,
    exact_typed_equal,
    load_json,
    require_exact_keys,
    require_sha256,
    require_type,
)
from .provenance import hash_file
from .runtime_limits import RuntimeLimits

DATASET_ROOT = "controlled/nanograv15yr-v2.1.0"
TOTAL_CASES = 344
HEARTBEAT_INTERVAL_SECONDS = 30.0

INPUT_BINDING_KEYS = {
    "target",
    "active_toas",
    "covariance_shape",
    "timing_design_shape",
    "timing_design_rank",
    "frequency_grid",
    "reference_epoch_mjd_tdb",
    "resource_manifest_sha256",
    "environment_manifest_sha256",
    "resource_trace_sha256",
    "network_attempt_count",
    "observed_residual_vector_loaded",
    "observed_periodic_scan_executed",
    "network_access_enabled",
}
ANNUAL_MASK_KEYS = {
    "schema_version",
    "run_id",
    "status",
    "inventory_sha256",
    "execution_binding_sha256",
    "periods",
    "updated_utc",
}
ANNUAL_PERIOD_KEYS = {
    "period_days",
    "signal_astrometry_correlation_limit",
    "ordinary_model_absorption_fraction_limit",
    "contributing_case_ids",
    "contributing_artifact_sha256",
    "maximum_signal_astrometry_correlation",
    "maximum_ordinary_model_absorption_fraction",
    "candidate_eligible",
}


def _finite_number(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(value)


def validate_input_binding(binding: Any, trusted: Any | None = None) -> dict[str, Any]:
    item = require_exact_keys(binding, INPUT_BINDING_KEYS, "v0.2.8 input binding")
    expected = {
        "target": "B1937+21",
        "active_toas": 660,
        "covariance_shape": [1320, 1320],
        "timing_design_shape": [1320, 284],
        "timing_design_rank": 284,
        "network_attempt_count": 0,
        "observed_residual_vector_loaded": False,
        "observed_periodic_scan_executed": False,
        "network_access_enabled": False,
    }
    for key, value in expected.items():
        if not exact_typed_equal(item[key], value):
            raise TrustedDataError(f"v0.2.8 input binding differs: {key}")
    for key in (
        "resource_manifest_sha256",
        "environment_manifest_sha256",
        "resource_trace_sha256",
    ):
        require_sha256(item[key], f"v0.2.8 input binding.{key}")
    if type(item["reference_epoch_mjd_tdb"]) is not float or not math.isfinite(
        item["reference_epoch_mjd_tdb"]
    ):
        raise TrustedDataError("v0.2.8 reference epoch is invalid")
    grid = require_type(item["frequency_grid"], dict, "v0.2.8 frequency grid")
    required_grid = {
        "algorithm",
        "minimum_period_days",
        "maximum_period_days",
        "minimum_frequency_per_day",
        "maximum_frequency_per_day",
        "span_days",
        "oversampling",
        "frequency_step_per_day",
        "frequency_count",
    }
    require_exact_keys(grid, required_grid, "v0.2.8 frequency grid")
    if grid["algorithm"] != "linear_frequency_independent_bin_oversampling":
        raise TrustedDataError("v0.2.8 frequency-grid algorithm differs")
    if grid["oversampling"] != 5 or type(grid["oversampling"]) is not int:
        raise TrustedDataError("v0.2.8 frequency-grid oversampling differs")
    if grid["frequency_count"] < 2 or type(grid["frequency_count"]) is not int:
        raise TrustedDataError("v0.2.8 frequency-grid count is invalid")
    if grid["minimum_period_days"] != 30.0 or grid["maximum_period_days"] != 2000.0:
        raise TrustedDataError("v0.2.8 frequency-grid period boundary differs")
    for key in required_grid - {"algorithm", "oversampling", "frequency_count"}:
        if type(grid[key]) is not float or not math.isfinite(grid[key]):
            raise TrustedDataError(f"v0.2.8 frequency-grid value is invalid: {key}")
    if trusted is not None and not exact_typed_equal(item, trusted):
        raise TrustedDataError("case input binding differs from trusted context")
    return item


def validate_complete_case_record(
    record: Any,
    *,
    case: dict[str, Any],
    execution_binding: str,
    threshold_delta_chi2: float,
    audit_required: bool,
    trusted_input_binding: dict[str, Any],
) -> dict[str, Any]:
    expected_keys = set(BASE_RECORD_KEYS)
    if case["family"] != "annual":
        expected_keys.add("candidate_eligible")
    item = require_exact_keys(record, expected_keys, "v0.2.8 case record")
    failures: list[str] = []
    if item["schema_version"] != RECORD_SCHEMA_VERSION:
        failures.append("record schema version differs")
    if item["run_id"] != RECORD_RUN_ID:
        failures.append("record run ID differs")
    if item["execution_binding_sha256"] != execution_binding:
        failures.append("record execution binding differs")
    if not exact_typed_equal(item["case"], case) or item["family"] != case["family"]:
        failures.append("record case or family differs")
    for key in RECORD_NUMERIC_KEYS:
        if not _finite_number(item.get(key)):
            failures.append(f"record numeric value is invalid: {key}")
    for key in RECORD_BOOLEAN_KEYS:
        if type(item.get(key)) is not bool:
            failures.append(f"record boolean value is invalid: {key}")
    for key in ("period_days", "amplitude_microseconds", "phase_radians"):
        if item.get(key) != float(case[key]):
            failures.append(f"record case value differs: {key}")
    if item.get("locked_threshold_delta_chi2") != float(threshold_delta_chi2):
        failures.append("record locked threshold differs")
    if item.get("solver_audit_required") is not audit_required:
        failures.append("record solver-audit requirement differs")
    for key in (
        "frequency_recovery_tolerance_per_day",
        "amplitude_bias_fraction",
        "phase_error_radians",
        "sine_uncertainty_microseconds",
        "cosine_uncertainty_microseconds",
        "phase_standard_error_radians",
        "toa_adjustment_error_microseconds",
        TOA_ADJUSTMENT_KEY,
        UNCENTERED_TARGET_KEY,
        DM_ERROR_KEY,
    ):
        if _finite_number(item.get(key)) and item[key] < 0:
            failures.append(f"record value is negative: {key}")
    for key in ("ordinary_absorption_fraction", "signal_astrometry_correlation"):
        if _finite_number(item.get(key)) and not 0.0 <= item[key] <= 1.0:
            failures.append(f"record fraction is outside zero to one: {key}")
    if item.get("toa_adjustment_error_microseconds") != item.get(TOA_ADJUSTMENT_KEY):
        failures.append("record TOA-adjustment aliases differ")
    if item.get("observed_residual_vector_used") is not False:
        failures.append("record observed-residual boundary differs")
    if item.get("observed_periodic_scan_executed") is not False:
        failures.append("record observed-periodic boundary differs")
    if case["family"] != "annual" and item.get("candidate_eligible") is not True:
        failures.append("record candidate eligibility differs")
    try:
        validate_input_binding(item.get("input_binding"), trusted_input_binding)
    except TrustedDataError as error:
        failures.append(str(error))
    failures.extend(_validate_solver_payload(item, audit_required))
    if failures:
        raise RuntimeError(f"v0.2.8 case artifact validation failed: {failures}")
    return item


def verify_predecessors(data_root: Path, runner: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    records: dict[str, Any] = {}
    for name, binding in runner["predecessor_bindings"].items():
        path = data_root / binding["logical_path"]
        if not path.is_file() or hash_file(path, "sha256") != binding["sha256"]:
            failures.append(f"predecessor mismatch: {name}")
            continue
        try:
            records[name] = load_json(path, f"v0.2.8 predecessor {name}")
        except TrustedDataError as error:
            failures.append(str(error))
    lock = records.get("threshold_lock", {})
    if lock.get("status") != "locked_before_sealed_evaluation":
        failures.append("threshold-lock status is invalid")
    if "inventory_sha256" not in lock:
        failures.append("threshold-lock inventory identity is absent")
    if not _finite_number(lock.get("value_delta_chi2")):
        failures.append("threshold-lock value is invalid")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "records": records,
        "threshold_delta_chi2": float(lock["value_delta_chi2"]) if not failures else None,
    }


def _reset_pint_clock_state() -> None:
    from pint import observatory

    observatory._gps_clock = None
    observatory._bipm_clock_versions.clear()
    for name in observatory.Observatory.names():
        item = observatory.get_observatory(name)
        if hasattr(item, "_clock"):
            item._clock = None


def prepare_context(
    data_root: Path,
    cases: list[dict[str, Any]],
    *,
    resource_manifest: dict[str, Any],
    resource_manifest_sha256: str,
    environment_manifest_sha256: str,
    setup_log_relative: str,
    resource_boundary: OfflineRuntimeBoundary | None = None,
) -> InjectionContext:
    controlled = data_root / DATASET_ROOT
    par = controlled / "wideband/par/B1937+21_PINT_20230131.wb.par"
    tim = controlled / "wideband/tim/B1937+21_PINT_20230131.wb.tim"
    for required in (par, tim):
        if not required.is_file():
            raise RuntimeError(f"v0.2.8 controlled input is missing: {required}")
    log_path = data_root / setup_log_relative
    durable_mkdirs(log_path.parent)
    _reset_pint_clock_state()
    manager = (
        nullcontext(resource_boundary)
        if resource_boundary is not None
        else OfflineRuntimeBoundary(data_root, resource_manifest)
    )
    with manager as boundary:
        import pint.logging
        from pint.fitter import WidebandTOAFitter
        from pint.models import get_model_and_toas

        pint.logging.setup(
            level="INFO",
            sink=log_path,
            usecolors=False,
            capturewarnings=True,
            removeprior=True,
        )
        model, toas = get_model_and_toas(
            par,
            tim,
            ephem="DE440",
            include_bipm=True,
            bipm_version="BIPM2019",
            planets=True,
            usepickle=False,
            limits="warn",
        )
        from .spin_phase import bind_precise_spin_phase

        bind_precise_spin_phase(model)
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
                covariance,
                design,
                times,
                np.asarray([1.0 / period]),
                reference_epoch,
            )
            for period in sorted({float(case["period_days"]) for case in cases})
        }
        trace = boundary.verify_trace()
    if trace["status"] != "pass":
        raise RuntimeError(f"v0.2.8 offline resource trace failed: {trace['failures']}")
    binding = {
        "target": "B1937+21",
        "active_toas": len(toas),
        "covariance_shape": list(covariance.shape),
        "timing_design_shape": list(design.shape),
        "timing_design_rank": scanner.timing_design_rank,
        "frequency_grid": grid,
        "reference_epoch_mjd_tdb": reference_epoch,
        "resource_manifest_sha256": resource_manifest_sha256,
        "environment_manifest_sha256": environment_manifest_sha256,
        "resource_trace_sha256": canonical_sha256(trace),
        "network_attempt_count": trace["network_attempt_count"],
        "observed_residual_vector_loaded": False,
        "observed_periodic_scan_executed": False,
        "network_access_enabled": False,
    }
    validate_input_binding(binding)
    return InjectionContext(
        model=model,
        toas=toas,
        scanner=scanner,
        exact_scanners=exact_scanners,
        times=times,
        reference_epoch=reference_epoch,
        input_binding=binding,
    )


class HeartbeatServiceV028(AbstractContextManager["HeartbeatServiceV028"]):
    def __init__(self, ledger: V028Ledger, interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS):
        self.ledger = ledger
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> Self:
        self.ledger.heartbeat()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.ledger.heartbeat()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds + 1.0))


def record_path(data_root: Path, sequence: int, case: dict[str, Any]) -> Path:
    return (
        data_root
        / "derived/pilot2/calibration-v0.2.8/injections"
        / str(case["family"])
        / f"{sequence:04d}-{case['case_id']}.json"
    )


def prepare_case_directories(data_root: Path) -> None:
    root = data_root / "derived/pilot2/calibration-v0.2.8/injections"
    durable_mkdirs(root)
    for family in ("main", "phase_reference", "annual", "boundary"):
        durable_mkdirs(root / family)


def _empty_annual_mask(execution_binding: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "status": "building",
        "inventory_sha256": INVENTORY_SHA256,
        "execution_binding_sha256": execution_binding,
        "periods": [],
        "updated_utc": utc_now(),
    }


def validate_annual_mask(
    value: Any,
    *,
    execution_binding: str,
    allowed_periods: Iterable[float],
) -> dict[str, Any]:
    mask = require_exact_keys(value, ANNUAL_MASK_KEYS, "v0.2.8 annual mask")
    if mask["schema_version"] != 1 or type(mask["schema_version"]) is not int:
        raise TrustedDataError("v0.2.8 annual-mask schema is invalid")
    if mask["run_id"] != RUN_ID or mask["inventory_sha256"] != INVENTORY_SHA256:
        raise TrustedDataError("v0.2.8 annual-mask identity differs")
    if mask["execution_binding_sha256"] != execution_binding:
        raise TrustedDataError("v0.2.8 annual-mask execution binding differs")
    if mask["status"] not in {"building", "complete"}:
        raise TrustedDataError("v0.2.8 annual-mask status is invalid")
    periods = require_type(mask["periods"], list, "v0.2.8 annual-mask periods")
    allowed = set(allowed_periods)
    seen: set[float] = set()
    for index, raw in enumerate(periods):
        item = require_exact_keys(raw, ANNUAL_PERIOD_KEYS, f"annual period[{index}]")
        if type(item["period_days"]) is not float or item["period_days"] not in allowed:
            raise TrustedDataError("v0.2.8 annual-mask period is not authorized")
        if item["period_days"] in seen:
            raise TrustedDataError("v0.2.8 annual-mask period is duplicated")
        seen.add(item["period_days"])
        for key in (
            "signal_astrometry_correlation_limit",
            "ordinary_model_absorption_fraction_limit",
            "maximum_signal_astrometry_correlation",
            "maximum_ordinary_model_absorption_fraction",
        ):
            if type(item[key]) is not float or not math.isfinite(item[key]):
                raise TrustedDataError(f"v0.2.8 annual-mask value is invalid: {key}")
        case_ids = require_type(item["contributing_case_ids"], list, "annual case IDs")
        hashes = require_type(item["contributing_artifact_sha256"], list, "annual hashes")
        if not case_ids or len(case_ids) != len(hashes) or len(set(case_ids)) != len(case_ids):
            raise TrustedDataError("v0.2.8 annual-mask source binding is invalid")
        for digest in hashes:
            require_sha256(digest, "v0.2.8 annual artifact hash")
        require_type(item["candidate_eligible"], bool, "annual eligibility")
    if mask["status"] == "complete" and seen != allowed:
        raise TrustedDataError("v0.2.8 complete annual mask lacks an authorized period")
    return mask


def append_annual_period(
    *,
    mask_path: Path,
    ledger: V028Ledger,
    execution_binding: str,
    allowed_periods: list[float],
    period: float,
    records: list[dict[str, Any]],
    record_artifacts: list[dict[str, Any]],
    correlation_limit: float,
    absorption_limit: float,
) -> tuple[dict[str, Any], bool]:
    mask = (
        load_json(mask_path, "v0.2.8 annual mask")
        if mask_path.exists()
        else _empty_annual_mask(execution_binding)
    )
    validate_annual_mask(mask, execution_binding=execution_binding, allowed_periods=allowed_periods)
    existing = {item["period_days"]: item for item in mask["periods"]}
    correlation = max(float(item["signal_astrometry_correlation"]) for item in records)
    absorption = max(float(item["ordinary_absorption_fraction"]) for item in records)
    eligible = correlation < correlation_limit and absorption < absorption_limit
    expected = {
        "period_days": float(period),
        "signal_astrometry_correlation_limit": float(correlation_limit),
        "ordinary_model_absorption_fraction_limit": float(absorption_limit),
        "contributing_case_ids": [str(item["case"]["case_id"]) for item in records],
        "contributing_artifact_sha256": [str(item["sha256"]) for item in record_artifacts],
        "maximum_signal_astrometry_correlation": correlation,
        "maximum_ordinary_model_absorption_fraction": absorption,
        "candidate_eligible": eligible,
    }
    if period in existing:
        if not exact_typed_equal(existing[period], expected):
            raise RuntimeError("v0.2.8 resumed annual-mask decision differs")
    else:
        mask["periods"].append(expected)
        mask["periods"].sort(key=lambda item: item["period_days"])
    if {item["period_days"] for item in mask["periods"]} == set(allowed_periods):
        mask["status"] = "complete"
    mask["updated_utc"] = utc_now()
    validate_annual_mask(mask, execution_binding=execution_binding, allowed_periods=allowed_periods)
    durable_atomic_json(mask_path, mask)
    ledger.commit_stage_result("annual_mask", mask_path)
    return mask, eligible


def _load_or_recover_active_attempt(
    *,
    ledger: V028Ledger,
    cases: list[dict[str, Any]],
    execution_binding: str,
    input_binding_sha256: str,
    trusted_input_binding: dict[str, Any],
    threshold: float,
    audit_ids: set[str],
) -> dict[str, Any] | None:
    state = ledger.load()
    attempt = state["active_attempt"]
    if attempt is None:
        return None
    case_by_id = {str(case["case_id"]): case for case in cases}
    case = case_by_id.get(attempt["case_id"])
    try:
        if case is None or attempt["seed"] != case["seed"]:
            raise RuntimeError("interrupted attempt differs from frozen inventory")
        if attempt["execution_binding_sha256"] != execution_binding:
            raise RuntimeError("interrupted attempt execution binding differs")
        if attempt["input_binding_sha256"] != input_binding_sha256:
            raise RuntimeError("interrupted attempt input binding differs")
        path = ledger.data_root / attempt["artifact_logical_path"]
        record = validate_complete_case_record(
            load_json(path, "interrupted v0.2.8 case artifact"),
            case=case,
            execution_binding=execution_binding,
            threshold_delta_chi2=threshold,
            audit_required=attempt["case_id"] in audit_ids,
            trusted_input_binding=trusted_input_binding,
        )
        if attempt["case_id"] not in state["completed_cases"]:
            ledger.record_case(attempt["case_id"], attempt["sequence"], attempt["family"], path)
        ledger.clear_attempt("verified_artifact_adopted_without_recomputation")
        return record
    except Exception as error:
        ledger.fail(
            "interrupted_consumed_attempt_without_verified_artifact",
            str(error),
            attempt["case_id"],
        )
        raise RuntimeError("v0.2.8 consumed attempt lacks a verified artifact") from error


def verify_ioc_fresh_state(
    ledger_state: Mapping[str, Any],
    data_root: Path,
    runner_paths: Mapping[str, Any],
) -> dict[str, Any]:
    """Refuse every non-pristine inner state before successor science setup."""

    pristine = {
        "execution_binding_sha256": None,
        "active_stage": None,
        "active_stage_started_utc": None,
        "stage_status": {STAGE: "pending"},
        "completed_cases": {},
        "stage_results": {},
        "active_attempt": None,
        "attempt_history": [],
        "checkpoints": [],
        "hard_stop": None,
        "runtime_active": False,
        "runner_pid": None,
        "last_heartbeat_utc": None,
    }
    failures = [name for name, expected in pristine.items() if ledger_state.get(name) != expected]

    resolved_root = Path(data_root).resolve(strict=False)

    def bound_path(name: str) -> Path:
        value = runner_paths.get(name)
        if type(value) is not str or not value:
            raise RuntimeError(f"IOC science runner path is invalid: {name}")
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"IOC science runner path is not confined: {name}")
        path = resolved_root / relative
        resolved_path = path.resolve(strict=False)
        if not resolved_path.is_relative_to(resolved_root):
            raise RuntimeError(f"IOC science runner path escapes the data root: {name}")
        if resolved_path != path:
            raise RuntimeError(f"IOC science runner path traverses a symlink: {name}")
        return path

    for name in ("result", "annual_mask", "health"):
        path = bound_path(name)
        if path.exists() or path.is_symlink():
            failures.append(f"physical_artifact:{name}")

    case_root = bound_path("case_root")
    if case_root.is_symlink() or (case_root.exists() and not case_root.is_dir()):
        failures.append("physical_artifact:case_root")
    elif case_root.exists():
        try:
            if any(item.is_file() or item.is_symlink() for item in case_root.rglob("*")):
                failures.append("physical_artifact:case")
        except OSError as error:
            raise RuntimeError("IOC science case-root freshness cannot be verified") from error

    if failures:
        raise RuntimeError(f"IOC science inner state is not fresh: {sorted(failures)}")
    return {"status": "pass", "completed": 0, "total": TOTAL_CASES, "checkpoint": 0}


def _publish_ioc_progress(
    ledger: V028Ledger,
    publish_status: Callable[..., Any],
) -> None:
    state = ledger.load()
    checkpoints = state["checkpoints"]
    checkpoint = int(checkpoints[-1]["completed_cases"]) if checkpoints else 0
    publish_status(
        stage="run",
        completed=len(state["completed_cases"]),
        total=TOTAL_CASES,
        checkpoint=checkpoint,
    )


def _terminalize_ioc_failure(
    ledger: V028Ledger,
    error: BaseException,
    current_case_id: str | None,
) -> None:
    state = ledger.load()
    if state["stage_status"][STAGE] in {"pass", "fail"}:
        return
    reason = (
        "operator_controlled_stop"
        if isinstance(error, KeyboardInterrupt)
        else "operational_failure"
    )
    detail = str(error) or type(error).__name__
    ledger.fail(reason, detail, current_case_id)


def execute(
    data_root: Path,
    *,
    ioc_binding: Mapping[str, Any] | None = None,
    ioc_manifest_sha256: str | None = None,
    publish_status: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    successor = ioc_binding is not None
    if successor:
        if ioc_manifest_sha256 is None or publish_status is None:
            raise RuntimeError(
                "IOC science execution requires manifest binding and status callback"
            )
    elif ioc_manifest_sha256 is not None or publish_status is not None:
        raise RuntimeError("IOC science execution arguments require an IOC binding")
    else:
        repository_gate = verify_repository_execution_authorization()
        if repository_gate["status"] != "pass":
            raise RuntimeError(
                f"v0.2.8 repository execution is locked: {repository_gate['failures']}"
            )
    with SingleWriterLock(data_root), ExitStack() as resources:
        gate = (
            verify_ioc_science_execution_gate(data_root, ioc_binding)
            if successor
            else verify_execution_gate(data_root)
        )
        if gate["status"] != "pass":
            label = "IOC science execution" if successor else "v0.2.8 execution"
            raise RuntimeError(f"{label} is locked: {gate['failures']}")
        base, remediation, runner = load_science_controls()
        inventory = build_v023_inventory()
        if inventory["inventory_sha256"] != INVENTORY_SHA256:
            raise RuntimeError("v0.2.8 inventory identity differs")
        cases = inventory["cases"]
        audit_ids = set(inventory["solver_audit_case_ids"])
        freeze = gate["freeze"]
        ledger = V028Ledger(
            data_root,
            inventory_sha256=INVENTORY_SHA256,
            implementation_sha256=freeze["implementation_sha256"],
            science_control_sha256=freeze["science_control_sha256"],
            environment_manifest_sha256=freeze["environment_manifest_sha256"],
            resource_manifest_sha256=freeze["resource_manifest_sha256"],
        )
        expected_case_ids = [str(case["case_id"]) for case in cases]
        if successor:
            verify_ioc_fresh_state(ledger.load(), data_root, runner["paths"])
            if ledger.verify_artifacts()["status"] != "pass":
                raise RuntimeError("v0.2.8 artifact integrity failed before execution")
        else:
            if ledger.verify_artifacts()["status"] != "pass":
                raise RuntimeError("v0.2.8 artifact integrity failed before execution")
            if ledger.already_complete(expected_case_ids):
                return {
                    "status": "already_complete",
                    "science_cases_executed_this_invocation": 0,
                }
        current_case_id: str | None = None
        limits = RuntimeLimits(
            data_root,
            wall_seconds=float(runner["resource_caps"]["wall_hours_maximum"]) * 3600,
            rss_gib=float(runner["resource_caps"]["peak_memory_gib_maximum"]),
            disk_gib=float(runner["resource_caps"]["complete_data_root_gib_maximum"]),
        )
        operations = {"random_draws": 0, "scans": 0, "primary_fits": 0, "solver_audits": 0}

        def record_operation(name: str) -> None:
            operations[name] += 1
            limits.check()

        try:
            limits.check(disk=True)
            predecessors = verify_predecessors(data_root, runner)
            if predecessors["status"] != "pass":
                raise RuntimeError(f"v0.2.8 predecessor gate failed: {predecessors['failures']}")
            threshold = float(predecessors["threshold_delta_chi2"])
            lock_path = data_root / runner["predecessor_bindings"]["threshold_lock"]["logical_path"]
            threshold_sha = hash_file(lock_path, "sha256")
            context = prepare_context(
                data_root,
                cases,
                resource_manifest=gate["resource_manifest"],
                resource_manifest_sha256=freeze["resource_manifest_sha256"],
                environment_manifest_sha256=freeze["environment_manifest_sha256"],
                setup_log_relative=runner["paths"]["setup_log"],
                resource_boundary=resources.enter_context(
                    OfflineRuntimeBoundary(data_root, gate["resource_manifest"])
                ),
            )
            input_sha = canonical_sha256(validate_input_binding(context.input_binding))
            binding = (
                ioc_execution_binding_sha256(
                    implementation_hash=freeze["implementation_sha256"],
                    execution_freeze_sha256=gate["freeze_sha256"],
                    threshold_lock_sha256=threshold_sha,
                    inventory_sha256=INVENTORY_SHA256,
                    science_control_hash=freeze["science_control_sha256"],
                    environment_manifest_sha256=freeze["environment_manifest_sha256"],
                    resource_manifest_sha256=freeze["resource_manifest_sha256"],
                    input_binding_sha256=input_sha,
                    ioc_manifest_sha256=ioc_manifest_sha256,
                    ioc_run_id=gate["binding"]["ioc_run_id"],
                )
                if successor
                else execution_binding_sha256(
                    implementation_hash=freeze["implementation_sha256"],
                    execution_freeze_sha256=gate["freeze_sha256"],
                    threshold_lock_sha256=threshold_sha,
                    inventory_sha256=INVENTORY_SHA256,
                    science_control_hash=freeze["science_control_sha256"],
                    environment_manifest_sha256=freeze["environment_manifest_sha256"],
                    resource_manifest_sha256=freeze["resource_manifest_sha256"],
                    input_binding_sha256=input_sha,
                )
            )
            state = ledger.load()
            if state["stage_status"][STAGE] == "pending":
                ledger.begin_stage(binding)
            elif successor:
                raise RuntimeError("IOC science inner state ceased to be fresh")
            else:
                ledger.resume_runtime(binding)
            if successor:
                _publish_ioc_progress(ledger, publish_status)
        except BaseException as error:
            if successor:
                _terminalize_ioc_failure(ledger, error, current_case_id)
            raise
        result_path = data_root / runner["paths"]["result"]
        mask_path = data_root / runner["paths"]["annual_mask"]
        try:
            if not successor:
                _load_or_recover_active_attempt(
                    ledger=ledger,
                    cases=cases,
                    execution_binding=binding,
                    input_binding_sha256=input_sha,
                    trusted_input_binding=context.input_binding,
                    threshold=threshold,
                    audit_ids=audit_ids,
                )
            prepare_case_directories(data_root)
            started = time.perf_counter()
            executed = 0
            records_by_id: dict[str, dict[str, Any]] = {}

            def load_or_execute(sequence: int, case: dict[str, Any]) -> dict[str, Any]:
                nonlocal executed, current_case_id
                limits.check(disk=True)
                current_case_id = str(case["case_id"])
                path = record_path(data_root, sequence, case)
                state_now = ledger.load()
                if current_case_id in state_now["completed_cases"]:
                    return validate_complete_case_record(
                        load_json(path, "completed v0.2.8 case artifact"),
                        case=case,
                        execution_binding=binding,
                        threshold_delta_chi2=threshold,
                        audit_required=current_case_id in audit_ids,
                        trusted_input_binding=context.input_binding,
                    )
                ledger.begin_attempt(
                    case_id=current_case_id,
                    sequence=sequence,
                    seed=int(case["seed"]),
                    family=str(case["family"]),
                    artifact_path=path,
                    execution_binding_sha256=binding,
                    input_binding_sha256=input_sha,
                )
                record = execute_injection_case(
                    context,
                    case,
                    threshold,
                    current_case_id in audit_ids,
                    base,
                    binding,
                    on_operation=record_operation,
                )
                if case["family"] != "annual":
                    record["candidate_eligible"] = True
                validate_complete_case_record(
                    record,
                    case=case,
                    execution_binding=binding,
                    threshold_delta_chi2=threshold,
                    audit_required=current_case_id in audit_ids,
                    trusted_input_binding=context.input_binding,
                )
                durable_atomic_json(path, record)
                ledger.record_case(current_case_id, sequence, str(case["family"]), path)
                ledger.clear_attempt("committed_without_interruption")
                executed += 1
                if successor:
                    current_case_id = None
                    _publish_ioc_progress(ledger, publish_status)
                return record

            with HeartbeatServiceV028(ledger):
                for family in ("main", "phase_reference"):
                    for sequence, case in enumerate(cases, 1):
                        if case["family"] == family:
                            records_by_id[case["case_id"]] = load_or_execute(sequence, case)
                annual_periods = sorted(
                    {float(case["period_days"]) for case in cases if case["family"] == "annual"}
                )
                correlation_limit = float(
                    base["candidate_eligibility"]["maximum_signal_astrometry_correlation"]
                )
                absorption_limit = float(
                    base["candidate_eligibility"]["maximum_ordinary_model_absorption_fraction"]
                )
                annual_eligibility: dict[float, bool] = {}
                for period in annual_periods:
                    group: list[dict[str, Any]] = []
                    artifacts: list[dict[str, Any]] = []
                    for sequence, case in enumerate(cases, 1):
                        if case["family"] == "annual" and float(case["period_days"]) == period:
                            record = load_or_execute(sequence, case)
                            records_by_id[case["case_id"]] = record
                            group.append(record)
                            artifacts.append(ledger.load()["completed_cases"][case["case_id"]])
                    _, eligible = append_annual_period(
                        mask_path=mask_path,
                        ledger=ledger,
                        execution_binding=binding,
                        allowed_periods=annual_periods,
                        period=period,
                        records=group,
                        record_artifacts=artifacts,
                        correlation_limit=correlation_limit,
                        absorption_limit=absorption_limit,
                    )
                    annual_eligibility[period] = eligible
                for sequence, case in enumerate(cases, 1):
                    if case["family"] == "boundary":
                        records_by_id[case["case_id"]] = load_or_execute(sequence, case)
            graded_records: list[dict[str, Any]] = []
            for case in cases:
                record = copy.deepcopy(records_by_id[case["case_id"]])
                if case["family"] == "annual":
                    record["candidate_eligible"] = annual_eligibility[float(case["period_days"])]
                graded_records.append(record)
            if hash_file(lock_path, "sha256") != threshold_sha:
                raise RuntimeError("v0.2.8 threshold lock changed during execution")
            grade = grade_records(graded_records, base, remediation)
            elapsed_hours = (time.perf_counter() - started) / 3600.0
            warnings = classify_injection_warning_lines(
                [
                    line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
                    for line in (data_root / runner["paths"]["setup_log"])
                    .read_text(encoding="utf-8")
                    .splitlines()
                ]
            )
            grade["gates"].extend(
                [
                    _gate(
                        "injection_wall_hours",
                        elapsed_hours,
                        "<=",
                        float(runner["resource_caps"]["wall_hours_maximum"]),
                        elapsed_hours <= float(runner["resource_caps"]["wall_hours_maximum"]),
                    ),
                    _gate(
                        "peak_memory_gib",
                        _peak_rss_gib(),
                        "<=",
                        float(runner["resource_caps"]["peak_memory_gib_maximum"]),
                        _peak_rss_gib()
                        <= float(runner["resource_caps"]["peak_memory_gib_maximum"]),
                    ),
                    _gate(
                        "complete_data_root_gib",
                        _directory_size_gib(data_root),
                        "<=",
                        float(runner["resource_caps"]["complete_data_root_gib_maximum"]),
                        _directory_size_gib(data_root)
                        <= float(runner["resource_caps"]["complete_data_root_gib_maximum"]),
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
            grade["status"] = (
                "pass" if all(item["status"] == "pass" for item in grade["gates"]) else "fail"
            )
            mask_sha = hash_file(mask_path, "sha256")
            result = {
                "schema_version": 1,
                "run_id": RUN_ID,
                "status": grade["status"],
                "inventory_sha256": INVENTORY_SHA256,
                "execution_binding_sha256": binding,
                "completed_case_count": TOTAL_CASES,
                "authorized_primary_fits": operations["primary_fits"] if successor else 688,
                "solver_audits": operations["solver_audits"] if successor else 35,
                "annual_mask_sha256": mask_sha,
                "threshold_lock_sha256": threshold_sha,
                "threshold_retuned": False,
                "observed_residual_vector_used": False,
                "observed_periodic_scan_executed": False,
                "promotion_grade_executed": False,
                "science_cases_executed_this_invocation": executed,
                "payload": grade,
            }
            if result["status"] == "pass":
                validate_terminal_result(
                    result,
                    inventory_sha256=INVENTORY_SHA256,
                    execution_binding_sha256=binding,
                    annual_mask_sha256=mask_sha,
                )
            durable_atomic_json(result_path, result)
            ledger.commit_stage_result("terminal_result", result_path)
            if result["status"] != "pass":
                ledger.fail("stage_gate_failure", "one or more frozen v0.2.8 gates failed")
                failure = {"status": "fail", "completed_injection_cases": TOTAL_CASES}
                if successor:
                    failure["execution_binding_sha256"] = binding
                return failure
            verification = ledger.complete_pass(expected_case_ids)
            completion = {
                "status": verification["status"],
                "completed_injection_cases": TOTAL_CASES,
                "science_cases_executed_this_invocation": executed,
                "ledger_verification": verification,
                "promotion_grade_executed": False,
            }
            if successor:
                completion["execution_binding_sha256"] = binding
            return completion
        except BaseException as error:
            if successor:
                _terminalize_ioc_failure(ledger, error, current_case_id)
            elif isinstance(error, Exception):
                state = ledger.load()
                if state["stage_status"][STAGE] == "running":
                    ledger.fail("unexpected_execution_exception", str(error), current_case_id)
            raise
