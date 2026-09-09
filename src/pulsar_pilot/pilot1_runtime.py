from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy.linalg import cholesky, qr, solve_triangular

from .c1r1 import _joint_full_covariance_fit, wrapped_phase_difference
from .circular_signal import ProjectCircularSignal
from .config import load_yaml
from .paths import repository_root
from .provenance import hash_file, logical_path

SEARCH_GRID_OVERSAMPLING = 5
INJECTION_BASE_SEED = 17441137
PREFLIGHT_PERIODS_DAYS = (100.0, 365.25)
PREFLIGHT_AMPLITUDE_TOLERANCE_US = 0.01
PREFLIGHT_PHASE_TOLERANCE_RADIANS = 0.001
PREFLIGHT_ANNUAL_PHASE_TOLERANCE_RADIANS = 0.01
PREFLIGHT_DELTA_CHI2_TOLERANCE = 0.1


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _seed_for_case(base_seed: int, case_id: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{case_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def build_search_frequency_grid(
    times_mjd_tdb: np.ndarray,
    minimum_period_days: float,
    maximum_period_days: float,
    oversampling: int = SEARCH_GRID_OVERSAMPLING,
) -> tuple[np.ndarray, dict[str, Any]]:
    times = np.asarray(times_mjd_tdb, dtype=float)
    if times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times)):
        raise ValueError("Search times must be a finite one-dimensional array")
    if minimum_period_days <= 0 or maximum_period_days <= minimum_period_days:
        raise ValueError("Search-period bounds are invalid")
    if oversampling < 1:
        raise ValueError("Frequency oversampling must be positive")
    span_days = float(np.ptp(times))
    if span_days <= 0:
        raise ValueError("Search times must span more than zero days")
    minimum_frequency = 1.0 / maximum_period_days
    maximum_frequency = 1.0 / minimum_period_days
    frequency_step = 1.0 / (span_days * oversampling)
    count = math.floor((maximum_frequency - minimum_frequency) / frequency_step) + 1
    frequencies = minimum_frequency + np.arange(count, dtype=float) * frequency_step
    if not np.isclose(frequencies[-1], maximum_frequency, rtol=0, atol=1e-15):
        frequencies = np.append(frequencies, maximum_frequency)
    return frequencies, {
        "algorithm": "linear_frequency_independent_bin_oversampling",
        "oversampling": oversampling,
        "span_days": span_days,
        "minimum_period_days": minimum_period_days,
        "maximum_period_days": maximum_period_days,
        "minimum_frequency_per_day": minimum_frequency,
        "maximum_frequency_per_day": maximum_frequency,
        "frequency_step_per_day": frequency_step,
        "frequency_count": len(frequencies),
    }


def circular_signal_templates(
    times_mjd_tdb: np.ndarray,
    frequencies_per_day: np.ndarray,
    reference_epoch_mjd_tdb: float,
    data_dimension: int,
) -> np.ndarray:
    times = np.asarray(times_mjd_tdb, dtype=float)
    frequencies = np.asarray(frequencies_per_day, dtype=float)
    if data_dimension < len(times):
        raise ValueError("Data dimension cannot be smaller than the TOA count")
    phase = 2.0 * np.pi * (times[:, None] - reference_epoch_mjd_tdb) * frequencies[None, :]
    templates = np.zeros((data_dimension, len(frequencies), 2), dtype=float)
    templates[: len(times), :, 0] = np.sin(phase)
    templates[: len(times), :, 1] = np.cos(phase)
    return templates


@dataclass(frozen=True)
class CovarianceGLSScanner:
    frequencies_per_day: np.ndarray
    covariance_cholesky: np.ndarray
    timing_projection_basis: np.ndarray
    projected_whitened_templates: np.ndarray
    template_gram_pseudoinverse: np.ndarray
    template_condition_numbers: np.ndarray
    timing_design_rank: int

    def whiten_and_project(self, residuals: np.ndarray) -> np.ndarray:
        values = np.asarray(residuals, dtype=float)
        if values.shape != (self.covariance_cholesky.shape[0],):
            raise ValueError("Residual vector has the wrong dimension")
        whitened = solve_triangular(
            self.covariance_cholesky, values, lower=True, check_finite=True
        )
        basis = self.timing_projection_basis
        return whitened - basis @ (basis.T @ whitened)

    def scan(self, residuals: np.ndarray) -> dict[str, Any]:
        projected = self.whiten_and_project(residuals)
        rhs = np.einsum("nfi,n->fi", self.projected_whitened_templates, projected)
        coefficients = np.einsum("fij,fj->fi", self.template_gram_pseudoinverse, rhs)
        delta_chi2 = np.maximum(0.0, np.einsum("fi,fi->f", rhs, coefficients))
        peak_index = int(np.argmax(delta_chi2))
        sine_s, cosine_s = coefficients[peak_index]
        return {
            "trigger_statistic": float(delta_chi2[peak_index]),
            "peak_index": peak_index,
            "peak_frequency_per_day": float(self.frequencies_per_day[peak_index]),
            "peak_period_days": float(1.0 / self.frequencies_per_day[peak_index]),
            "sine_coefficient_us": float(sine_s * 1e6),
            "cosine_coefficient_us": float(cosine_s * 1e6),
            "amplitude_us": float(np.hypot(sine_s, cosine_s) * 1e6),
            "phase_radians": float(np.arctan2(cosine_s, sine_s)),
            "projected_null_chi2": float(projected @ projected),
            "frequency_count": len(self.frequencies_per_day),
            "all_delta_chi2": delta_chi2,
            "all_coefficients_seconds": coefficients,
        }


def prepare_covariance_gls_scanner(
    covariance: np.ndarray,
    timing_design_matrix: np.ndarray,
    times_mjd_tdb: np.ndarray,
    frequencies_per_day: np.ndarray,
    reference_epoch_mjd_tdb: float,
) -> CovarianceGLSScanner:
    covariance = np.asarray(covariance, dtype=float)
    design = np.asarray(timing_design_matrix, dtype=float)
    if covariance.ndim != 2 or covariance.shape[0] != covariance.shape[1]:
        raise ValueError("Covariance must be square")
    if design.ndim != 2 or design.shape[0] != covariance.shape[0]:
        raise ValueError("Timing design and covariance dimensions do not agree")
    if not np.allclose(covariance, covariance.T, rtol=1e-10, atol=1e-18):
        raise ValueError("Covariance must be symmetric")
    covariance_cholesky = cholesky(covariance, lower=True, check_finite=True)
    whitened_design = solve_triangular(
        covariance_cholesky, design, lower=True, check_finite=True
    )
    column_norms = np.linalg.norm(whitened_design, axis=0)
    usable = np.isfinite(column_norms) & (column_norms > 0)
    if not np.any(usable):
        raise ValueError("Timing design matrix has no usable columns")
    normalized_design = whitened_design[:, usable] / column_norms[usable]
    q, r, _ = qr(normalized_design, mode="economic", pivoting=True, check_finite=True)
    diagonal = np.abs(np.diag(r))
    tolerance = (
        max(normalized_design.shape) * np.finfo(float).eps * diagonal.max()
        if len(diagonal)
        else 0.0
    )
    rank = int(np.sum(diagonal > tolerance))
    if rank == 0:
        raise ValueError("Timing design matrix has zero numerical rank")
    projection_basis = q[:, :rank]

    templates = circular_signal_templates(
        times_mjd_tdb,
        frequencies_per_day,
        reference_epoch_mjd_tdb,
        covariance.shape[0],
    )
    flat_templates = templates.reshape(covariance.shape[0], -1)
    whitened_templates = solve_triangular(
        covariance_cholesky, flat_templates, lower=True, check_finite=True
    )
    whitened_templates -= projection_basis @ (projection_basis.T @ whitened_templates)
    projected_templates = whitened_templates.reshape(covariance.shape[0], -1, 2)
    gram = np.einsum("nfi,nfj->fij", projected_templates, projected_templates)
    condition_numbers = np.asarray([np.linalg.cond(item) for item in gram], dtype=float)
    gram_pseudoinverse = np.asarray([np.linalg.pinv(item, rtol=1e-12) for item in gram])
    return CovarianceGLSScanner(
        frequencies_per_day=np.asarray(frequencies_per_day, dtype=float),
        covariance_cholesky=covariance_cholesky,
        timing_projection_basis=projection_basis,
        projected_whitened_templates=projected_templates,
        template_gram_pseudoinverse=gram_pseudoinverse,
        template_condition_numbers=condition_numbers,
        timing_design_rank=rank,
    )


def generate_covariance_null(
    covariance_cholesky: np.ndarray, generator: np.random.Generator
) -> np.ndarray:
    factor = np.asarray(covariance_cholesky, dtype=float)
    if factor.ndim != 2 or factor.shape[0] != factor.shape[1]:
        raise ValueError("Covariance Cholesky factor must be square")
    return factor @ generator.standard_normal(factor.shape[0])


def null_ensemble_diagnostics(
    samples: np.ndarray, covariance_cholesky: np.ndarray
) -> dict[str, Any]:
    values = np.asarray(samples, dtype=float)
    if values.ndim != 2 or values.shape[1] != covariance_cholesky.shape[0]:
        raise ValueError("Null ensemble has the wrong shape")
    whitened = solve_triangular(
        covariance_cholesky, values.T, lower=True, check_finite=True
    ).T
    maximum_lag = min(32, whitened.shape[1] - 1)
    lag_correlations: list[float] = []
    for lag in range(1, maximum_lag + 1):
        left = whitened[:, :-lag].reshape(-1)
        right = whitened[:, lag:].reshape(-1)
        lag_correlations.append(float(np.corrcoef(left, right)[0, 1]))
    return {
        "sample_count": values.shape[0],
        "dimension": values.shape[1],
        "whitened_variance": float(np.var(whitened, ddof=1)),
        "correlation_method": "maximum_absolute_pooled_whitened_lag_correlation",
        "maximum_lag": maximum_lag,
        "lag_correlations": lag_correlations,
        "maximum_absolute_ensemble_correlation": float(
            np.max(np.abs(lag_correlations)) if lag_correlations else 0.0
        ),
    }


def conservative_nearest_rank(values: np.ndarray, quantile: float) -> float:
    samples = np.sort(np.asarray(values, dtype=float))
    if samples.ndim != 1 or len(samples) == 0 or not np.all(np.isfinite(samples)):
        raise ValueError("Threshold samples must be a non-empty finite vector")
    if not 0 < quantile <= 1:
        raise ValueError("Threshold quantile must be in (0, 1]")
    rank = math.ceil(quantile * len(samples))
    return float(samples[rank - 1])


def build_pilot1_case_inventory(plan: dict[str, Any]) -> dict[str, Any]:
    null_cases: list[dict[str, Any]] = []
    for family, count_key, seed_key in (
        ("calibration", "calibration_count", "calibration_seed"),
        ("sealed_evaluation", "sealed_evaluation_count", "sealed_evaluation_seed"),
    ):
        for index in range(int(plan["nulls"][count_key])):
            case_id = f"null-{family}-{index:04d}"
            null_cases.append(
                {
                    "case_id": case_id,
                    "family": family,
                    "index": index,
                    "seed": _seed_for_case(int(plan["nulls"][seed_key]), case_id),
                }
            )

    injection_cases: list[dict[str, Any]] = []
    matrix_names = (
        ("main", "main_matrix"),
        ("annual", "annual_identifiability_matrix"),
        ("boundary", "search_boundary_matrix"),
    )
    for family, matrix_key in matrix_names:
        matrix = plan["injections"][matrix_key]
        for period_index, period in enumerate(matrix["periods_days"]):
            for amplitude_index, amplitude in enumerate(matrix["amplitudes_microseconds"]):
                for phase_index, phase in enumerate(matrix["phases_radians"]):
                    for noise_index in range(
                        int(matrix["covariance_noise_realizations_per_phase"])
                    ):
                        case_id = (
                            f"inj-{family}-p{period_index:02d}-a{amplitude_index:02d}"
                            f"-h{phase_index:02d}-n{noise_index:02d}"
                        )
                        injection_cases.append(
                            {
                                "case_id": case_id,
                                "family": family,
                                "period_days": float(period),
                                "amplitude_microseconds": float(amplitude),
                                "phase_radians": float(phase),
                                "noise_realization_index": noise_index,
                                "seed": _seed_for_case(INJECTION_BASE_SEED, case_id),
                            }
                        )
    audit_count = math.ceil(
        len(injection_cases)
        * float(plan["independent_audit"]["deterministic_fraction"])
    )
    ranked = sorted(
        injection_cases,
        key=lambda item: hashlib.sha256(item["case_id"].encode()).hexdigest(),
    )
    audit_case_ids = [item["case_id"] for item in ranked[:audit_count]]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "plan_id": plan["plan_id"],
        "execution_authorized": bool(plan["execution_authorized"]),
        "null_cases": null_cases,
        "injection_cases": injection_cases,
        "independent_audit_case_ids": audit_case_ids,
    }
    payload["inventory_sha256"] = hashlib.sha256(_canonical_json(payload)).hexdigest()
    return payload


def inventory_summary(inventory: dict[str, Any]) -> dict[str, Any]:
    nulls = inventory["null_cases"]
    injections = inventory["injection_cases"]
    return {
        "schema_version": inventory["schema_version"],
        "plan_id": inventory["plan_id"],
        "execution_authorized": inventory["execution_authorized"],
        "inventory_sha256": inventory["inventory_sha256"],
        "calibration_nulls": sum(item["family"] == "calibration" for item in nulls),
        "sealed_evaluation_nulls": sum(
            item["family"] == "sealed_evaluation" for item in nulls
        ),
        "injections": len(injections),
        "independent_audits": len(inventory["independent_audit_case_ids"]),
        "unique_case_ids": len({item["case_id"] for item in nulls + injections}),
        "unique_seeds": len({item["seed"] for item in nulls + injections}),
    }


class ResumableArtifactLedger:
    def __init__(self, path: Path, inventory_sha256: str, implementation_sha256: str):
        self.path = path
        self.inventory_sha256 = inventory_sha256
        self.implementation_sha256 = implementation_sha256

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "inventory_sha256": self.inventory_sha256,
            "implementation_sha256": self.implementation_sha256,
            "completed_cases": {},
        }

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        state = json.loads(self.path.read_text(encoding="utf-8"))
        for key, expected in (
            ("inventory_sha256", self.inventory_sha256),
            ("implementation_sha256", self.implementation_sha256),
        ):
            if state.get(key) != expected:
                raise RuntimeError(f"Resume ledger {key} does not match the frozen run")
        return state

    def record(self, case_id: str, artifact_path: Path, data_root: Path) -> dict[str, Any]:
        state = self.load()
        record = {
            "logical_path": logical_path(artifact_path, data_root),
            "bytes": artifact_path.stat().st_size,
            "sha256": hash_file(artifact_path, "sha256"),
        }
        prior = state["completed_cases"].get(case_id)
        if prior is not None and prior != record:
            raise RuntimeError(f"Case {case_id} already has a different artifact")
        state["completed_cases"][case_id] = record
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)
        return record

    def verify(self, data_root: Path) -> dict[str, Any]:
        state = self.load()
        failures: list[str] = []
        for case_id, artifact in state["completed_cases"].items():
            path = data_root / artifact["logical_path"]
            if not path.is_file() or hash_file(path, "sha256") != artifact["sha256"]:
                failures.append(case_id)
        return {
            "status": "pass" if not failures else "fail",
            "completed_cases": len(state["completed_cases"]),
            "failures": failures,
        }


def _load_release_context(data_root: Path) -> tuple[Any, Any]:
    controlled = data_root / "controlled" / "nanograv15yr-v2.1.0"
    clock_dir = controlled / "clock"
    par_path = controlled / "wideband" / "par" / "J1744-1134_PINT_20230131.wb.par"
    tim_path = controlled / "wideband" / "tim" / "J1744-1134_PINT_20230131.wb.tim"
    for required in (clock_dir, par_path, tim_path):
        if not required.exists():
            raise FileNotFoundError(f"Required controlled input is missing: {required}")
    os.environ["PINT_CLOCK_OVERRIDE"] = str(clock_dir)
    os.environ["XDG_CACHE_HOME"] = str(data_root / "derived" / "cache")
    import pint.logging
    from pint.models import get_model_and_toas

    pint.logging.setup(level="WARNING", usecolors=False, capturewarnings=True, removeprior=True)
    return get_model_and_toas(
        par_path,
        tim_path,
        ephem="DE440",
        include_bipm=True,
        bipm_version="BIPM2019",
        planets=True,
        usepickle=False,
        limits="warn",
    )


def _ordinary_full_covariance_fit(toas: Any, model: Any, max_iterations: int) -> dict[str, Any]:
    from pint.fitter import WidebandTOAFitter
    from pint.residuals import WidebandTOAResiduals

    fitter = WidebandTOAFitter(toas, copy.deepcopy(model))
    returned_chi2 = float(
        fitter.fit_toas(maxiter=max_iterations, threshold=1e-14, full_cov=True)
    )
    residuals = WidebandTOAResiduals(toas, fitter.model)
    return {
        "model": fitter.model,
        "chi2": float(residuals.chi2),
        "returned_chi2": returned_chi2,
        "completed": bool(np.isfinite(returned_chi2) and np.isfinite(residuals.chi2)),
    }


def _pint_signal_template_difference(
    toas: Any,
    model: Any,
    frequencies: np.ndarray,
    epoch_mjd_tdb: float,
) -> float:
    from pint.fitter import WidebandTOAFitter

    maximum = 0.0
    times = np.asarray(toas.table["tdbld"].data, dtype=float)
    for frequency in frequencies:
        signal_model = copy.deepcopy(model)
        component = ProjectCircularSignal()
        component.CSEPOCH.value = epoch_mjd_tdb
        component.CSEPOCH.frozen = True
        component.CSFREQ.value = float(frequency)
        component.CSFREQ.frozen = True
        component.CSSIN.value = 0.0
        component.CSCOS.value = 0.0
        component.CSSIN.frozen = False
        component.CSCOS.frozen = False
        signal_model.add_component(component, validate=True)
        matrix = WidebandTOAFitter(toas, signal_model).get_designmatrix()
        labels = matrix.axis_labels[1]
        pint_template = np.column_stack(
            (
                matrix.matrix[:, labels["CSSIN"][0]],
                matrix.matrix[:, labels["CSCOS"][0]],
            )
        )
        formula = circular_signal_templates(
            times, np.asarray([frequency]), epoch_mjd_tdb, len(pint_template)
        )[:, 0, :]
        maximum = max(maximum, float(np.max(np.abs(pint_template - formula))))
    return maximum


def run_pilot1_preflight(data_root: Path, max_iterations: int = 10) -> dict[str, Any]:
    plan = load_yaml(repository_root() / "config" / "pilot1.yaml")
    if plan["execution_authorized"] is not False:
        raise RuntimeError("Preflight requires the review-only Pilot 1 design")
    wall_start = time.perf_counter()
    release_model, toas = _load_release_context(data_root)
    baseline = _ordinary_full_covariance_fit(toas, release_model, max_iterations)
    if not baseline["completed"]:
        raise RuntimeError("Ordinary full-covariance preflight fit did not complete")

    from pint.fitter import WidebandTOAFitter
    from pint.residuals import WidebandTOAResiduals

    baseline_model = baseline["model"]
    fitter = WidebandTOAFitter(toas, baseline_model)
    design = fitter.get_designmatrix().matrix
    covariance = fitter.get_noise_covariancematrix().matrix
    residuals = WidebandTOAResiduals(toas, baseline_model).calc_wideband_resids()
    times = np.asarray(toas.table["tdbld"].data, dtype=float)
    frequencies = 1.0 / np.asarray(PREFLIGHT_PERIODS_DAYS)
    epoch = float(plan["injections"]["reference_epoch_mjd_tdb"])
    scanner = prepare_covariance_gls_scanner(
        covariance, design, times, frequencies, epoch
    )
    analytic = scanner.scan(residuals)
    template_difference = _pint_signal_template_difference(
        toas, baseline_model, frequencies, epoch
    )

    comparisons: list[dict[str, Any]] = []
    all_delta = analytic["all_delta_chi2"]
    all_coefficients = analytic["all_coefficients_seconds"]
    for index, (period, frequency) in enumerate(zip(PREFLIGHT_PERIODS_DAYS, frequencies)):
        direct = _joint_full_covariance_fit(
            toas, baseline_model, float(frequency), epoch, max_iterations
        )
        sine_us, cosine_us = all_coefficients[index] * 1e6
        analytic_amplitude_us = float(np.hypot(sine_us, cosine_us))
        analytic_phase = float(np.arctan2(cosine_us, sine_us))
        direct_delta = float(baseline["chi2"] - direct["chi2"])
        comparisons.append(
            {
                "period_days": period,
                "frequency_per_day": float(frequency),
                "analytic_delta_chi2": float(all_delta[index]),
                "direct_delta_chi2": direct_delta,
                "absolute_delta_chi2_difference": abs(float(all_delta[index]) - direct_delta),
                "analytic_amplitude_us": analytic_amplitude_us,
                "direct_amplitude_us": direct["amplitude_us"],
                "absolute_amplitude_difference_us": abs(
                    analytic_amplitude_us - direct["amplitude_us"]
                ),
                "analytic_phase_radians": analytic_phase,
                "direct_phase_radians": direct["phase_radians"],
                "absolute_phase_difference_radians": abs(
                    wrapped_phase_difference(analytic_phase, direct["phase_radians"])
                ),
                "direct_fit_completed": bool(direct["completed"]),
                "release_red_noise_preserved": bool(direct["release_red_noise_preserved"]),
                "wavex_absent": bool(direct["wavex_absent"]),
            }
        )
    criteria = {
        "review_only_design_preserved": plan["execution_authorized"] is False,
        "no_synthetic_realization_generated": True,
        "covariance_is_positive_definite": bool(
            np.all(np.diag(scanner.covariance_cholesky) > 0)
        ),
        "timing_design_has_nonzero_rank": scanner.timing_design_rank > 0,
        "project_signal_templates_exact": template_difference <= 1e-9,
        "fixed_frequency_direct_fits_completed": all(
            item["direct_fit_completed"] for item in comparisons
        ),
        "release_red_noise_preserved": all(
            item["release_red_noise_preserved"] for item in comparisons
        ),
        "wavex_absent": all(item["wavex_absent"] for item in comparisons),
        "amplitude_equivalence": all(
            item["absolute_amplitude_difference_us"]
            <= PREFLIGHT_AMPLITUDE_TOLERANCE_US
            for item in comparisons
        ),
        "phase_equivalence": all(
            item["absolute_phase_difference_radians"]
            <= (
                PREFLIGHT_ANNUAL_PHASE_TOLERANCE_RADIANS
                if item["period_days"] == 365.25
                else PREFLIGHT_PHASE_TOLERANCE_RADIANS
            )
            for item in comparisons
        ),
        "delta_chi2_equivalence": all(
            item["absolute_delta_chi2_difference"]
            <= PREFLIGHT_DELTA_CHI2_TOLERANCE
            for item in comparisons
        ),
    }
    status = "pass" if all(criteria.values()) else "fail"
    recorded = datetime.now(UTC)
    record = {
        "schema_version": 1,
        "preflight_id": recorded.strftime("pilot1-preflight-%Y%m%dT%H%M%SZ"),
        "recorded_utc": recorded.isoformat().replace("+00:00", "Z"),
        "status": status,
        "scope": "noninjected_fixed_frequency_numerical_preflight",
        "observed_residual_global_search_executed": False,
        "pilot1_synthetic_realizations_generated": 0,
        "template_maximum_absolute_difference": template_difference,
        "timing_design_shape": list(design.shape),
        "timing_design_rank": scanner.timing_design_rank,
        "covariance_shape": list(covariance.shape),
        "comparisons": comparisons,
        "tolerances": {
            "amplitude_microseconds": PREFLIGHT_AMPLITUDE_TOLERANCE_US,
            "phase_radians": PREFLIGHT_PHASE_TOLERANCE_RADIANS,
            "annual_stress_phase_radians": PREFLIGHT_ANNUAL_PHASE_TOLERANCE_RADIANS,
            "delta_chi2": PREFLIGHT_DELTA_CHI2_TOLERANCE,
        },
        "criteria": criteria,
        "wall_seconds": time.perf_counter() - wall_start,
    }
    output_dir = data_root / "run_records" / "pilot1"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{record['preflight_id']}.json"
    output_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        **record,
        "external_record": {
            "logical_path": logical_path(output_path, data_root),
            "bytes": output_path.stat().st_size,
            "sha256": hash_file(output_path, "sha256"),
        },
    }
