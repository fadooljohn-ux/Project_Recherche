from __future__ import annotations

import argparse
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import brentq
from scipy.stats import kurtosis, skew

from .config import load_yaml
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _load_release
from .pilot1_injections import projected_mass_moon_masses
from .pilot1_runtime import prepare_covariance_gls_scanner
from .provenance import hash_file, logical_path

DIAGNOSTIC_ID = "pilot1-reference-discrepancy-v0.1"
FREEZE_PATH = "protocol/PILOT1_DISCREPANCY_DIAGNOSTIC_FREEZE_v0.1.json"
DIAGNOSTIC_SEED = 17441138
DIAGNOSTIC_NULL_COUNT = 1000
CENTRAL_INTERVAL = 0.99
MAXIMUM_LAG = 16

G_SI = 6.67430e-11
C_SI = 299792458.0
SOLAR_MASS_KG = 1.98847e30
MOON_MASS_KG = 7.342e22


def verify_diagnostic_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze = json.loads((root / FREEZE_PATH).read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "frozen_before_observed_residual_diagnostics":
        failures.append("freeze status is invalid")
    if freeze.get("authorization") != "nonperiodic_residual_diagnostics_only":
        failures.append("authorization is invalid")
    if freeze.get("observed_residual_global_search_authorized") is not False:
        failures.append("global observed-residual search must remain unauthorized")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        if hash_file(root / relative, "sha256") != expected:
            failures.append(f"hash mismatch: {relative}")
    return {"status": "pass" if not failures else "fail", "failures": failures}


def approximate_projected_mass_kg(
    timing_amplitude_microseconds: float,
    period_days: float,
    central_mass_solar: float,
) -> float:
    central_mass = central_mass_solar * SOLAR_MASS_KG
    period_seconds = period_days * 86400.0
    relative_semimajor_axis = (
        G_SI * central_mass * period_seconds**2 / (4.0 * math.pi**2)
    ) ** (1.0 / 3.0)
    projected_reflex_semimajor_axis = timing_amplitude_microseconds * 1e-6 * C_SI
    return projected_reflex_semimajor_axis * central_mass / relative_semimajor_axis


def exact_projected_mass_kg(
    timing_amplitude_microseconds: float,
    period_days: float,
    central_mass_solar: float,
) -> float:
    central_mass = central_mass_solar * SOLAR_MASS_KG
    period_seconds = period_days * 86400.0
    projected_reflex_semimajor_axis = timing_amplitude_microseconds * 1e-6 * C_SI
    scale = (G_SI * period_seconds**2 / (4.0 * math.pi**2)) ** (1.0 / 3.0)

    def residual(companion_mass: float) -> float:
        return (
            scale * companion_mass / (central_mass + companion_mass) ** (2.0 / 3.0)
            - projected_reflex_semimajor_axis
        )

    approximation = approximate_projected_mass_kg(
        timing_amplitude_microseconds, period_days, central_mass_solar
    )
    return float(brentq(residual, approximation * 0.1, approximation * 10.0))


def timing_amplitude_for_projected_mass_microseconds(
    projected_mass_moon: float,
    period_days: float,
    central_mass_solar: float,
) -> float:
    central_mass = central_mass_solar * SOLAR_MASS_KG
    companion_mass = projected_mass_moon * MOON_MASS_KG
    period_seconds = period_days * 86400.0
    scale = (G_SI * period_seconds**2 / (4.0 * math.pi**2)) ** (1.0 / 3.0)
    projected_reflex_semimajor_axis = (
        scale * companion_mass / (central_mass + companion_mass) ** (2.0 / 3.0)
    )
    return projected_reflex_semimajor_axis / C_SI * 1e6


def mass_conversion_audit() -> dict[str, Any]:
    amplitude = 0.5
    period = 100.0
    central_mass = 1.4
    implementation = projected_mass_moon_masses(amplitude, period, central_mass)
    independent_approximation = (
        approximate_projected_mass_kg(amplitude, period, central_mass) / MOON_MASS_KG
    )
    exact = exact_projected_mass_kg(amplitude, period, central_mass) / MOON_MASS_KG
    reference_amplitude_1p4 = timing_amplitude_for_projected_mass_microseconds(
        0.56, period, 1.4
    )
    reference_amplitude_1p5 = timing_amplitude_for_projected_mass_microseconds(
        0.56, period, 1.5
    )
    return {
        "timing_amplitude_microseconds": amplitude,
        "period_days": period,
        "central_mass_solar": central_mass,
        "implementation_projected_mass_moon": implementation,
        "independent_approximation_projected_mass_moon": independent_approximation,
        "exact_two_body_projected_mass_moon": exact,
        "implementation_relative_difference_from_independent": abs(
            implementation - independent_approximation
        )
        / independent_approximation,
        "low_mass_approximation_relative_difference_from_exact": abs(
            independent_approximation - exact
        )
        / exact,
        "published_0p56_implied_timing_amplitude_microseconds": {
            "central_mass_1p4_solar": reference_amplitude_1p4,
            "central_mass_1p5_solar": reference_amplitude_1p5,
        },
        "central_mass_assumption_relative_effect": abs(
            reference_amplitude_1p5 - reference_amplitude_1p4
        )
        / reference_amplitude_1p4,
        "status": "pass"
        if abs(implementation - independent_approximation) / independent_approximation < 1e-12
        and abs(independent_approximation - exact) / exact < 1e-6
        else "fail",
    }


def _maximum_block_lag_correlation(values: np.ndarray, toa_count: int) -> float:
    maximum = 0.0
    for block in (values[:toa_count], values[toa_count:]):
        for lag in range(1, min(MAXIMUM_LAG, len(block) - 1) + 1):
            correlation = float(np.corrcoef(block[:-lag], block[lag:])[0, 1])
            if np.isfinite(correlation):
                maximum = max(maximum, abs(correlation))
    return maximum


def _metrics(values: np.ndarray, timing_rank: int, toa_count: int) -> dict[str, float]:
    vector = np.asarray(values, dtype=float)
    degrees_of_freedom = len(vector) - timing_rank
    return {
        "projected_energy_per_dof": float(vector @ vector / degrees_of_freedom),
        "maximum_absolute": float(np.max(np.abs(vector))),
        "maximum_absolute_block_lag_correlation": _maximum_block_lag_correlation(
            vector, toa_count
        ),
        "variance": float(np.var(vector, ddof=1)),
        "absolute_skewness": abs(float(skew(vector, bias=False))),
        "absolute_excess_kurtosis": abs(float(kurtosis(vector, fisher=True, bias=False))),
        "median_absolute_deviation": float(np.median(np.abs(vector - np.median(vector)))),
    }


def _central_interval(values: np.ndarray) -> dict[str, float]:
    tail = (1.0 - CENTRAL_INTERVAL) / 2.0
    return {
        "lower": float(np.quantile(values, tail, method="inverted_cdf")),
        "upper": float(np.quantile(values, 1.0 - tail, method="inverted_cdf")),
    }


def residual_covariance_diagnostic(data_root: Path) -> dict[str, Any]:
    plan = load_yaml(repository_root() / "config/pilot1.yaml")
    model, toas = _load_release(data_root)
    from pint.fitter import WidebandTOAFitter
    from pint.residuals import WidebandTOAResiduals

    fitter = WidebandTOAFitter(toas, model)
    covariance = fitter.get_noise_covariancematrix().matrix
    design = fitter.get_designmatrix().matrix
    times = np.asarray(toas.table["tdbld"].data, dtype=float)
    epoch = float(plan["injections"]["reference_epoch_mjd_tdb"])
    scanner = prepare_covariance_gls_scanner(
        covariance, design, times, np.asarray([1.0 / 100.0]), epoch
    )
    observed_residuals = WidebandTOAResiduals(toas, model).calc_wideband_resids()
    observed_projected = scanner.whiten_and_project(observed_residuals)

    generator = np.random.default_rng(DIAGNOSTIC_SEED)
    standard_whitened = generator.standard_normal(
        (DIAGNOSTIC_NULL_COUNT, covariance.shape[0])
    )
    basis = scanner.timing_projection_basis
    simulated_projected = standard_whitened - (standard_whitened @ basis) @ basis.T

    observed = _metrics(observed_projected, scanner.timing_design_rank, len(toas))
    simulated_metrics = [
        _metrics(row, scanner.timing_design_rank, len(toas)) for row in simulated_projected
    ]
    ensemble_metrics = {
        key: np.asarray([item[key] for item in simulated_metrics], dtype=float)
        for key in observed
    }
    intervals = {key: _central_interval(values) for key, values in ensemble_metrics.items()}
    outcomes = {
        key: intervals[key]["lower"] <= value <= intervals[key]["upper"]
        for key, value in observed.items()
    }
    hard_names = (
        "projected_energy_per_dof",
        "maximum_absolute",
        "maximum_absolute_block_lag_correlation",
    )
    advisory_names = (
        "variance",
        "absolute_skewness",
        "absolute_excess_kurtosis",
        "median_absolute_deviation",
    )
    hard_failures = [name for name in hard_names if not outcomes[name]]
    advisory_failures = [name for name in advisory_names if not outcomes[name]]
    status = "pass" if not hard_failures and len(advisory_failures) < 2 else "fail"
    return {
        "diagnostic_id": DIAGNOSTIC_ID,
        "status": status,
        "observed_residual_global_search_executed": False,
        "seed": DIAGNOSTIC_SEED,
        "null_count": DIAGNOSTIC_NULL_COUNT,
        "central_interval": CENTRAL_INTERVAL,
        "quantile_method": "inverted_cdf",
        "residual_dimension": covariance.shape[0],
        "toa_count": len(toas),
        "dm_residual_count": covariance.shape[0] - len(toas),
        "timing_design_rank": scanner.timing_design_rank,
        "projected_degrees_of_freedom": covariance.shape[0] - scanner.timing_design_rank,
        "observed_metrics": observed,
        "empirical_intervals": intervals,
        "metric_outcomes": {key: "pass" if value else "fail" for key, value in outcomes.items()},
        "hard_failures": hard_failures,
        "advisory_failures": advisory_failures,
    }


def run(data_root: Path) -> dict[str, Any]:
    freeze = verify_diagnostic_freeze()
    if freeze["status"] != "pass":
        raise RuntimeError(f"Discrepancy diagnostic freeze failed: {freeze}")
    result = {
        "schema_version": 1,
        "diagnostic_id": DIAGNOSTIC_ID,
        "freeze": freeze,
        "mass_conversion": mass_conversion_audit(),
        "residual_covariance": residual_covariance_diagnostic(data_root),
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    result["status"] = (
        "pass"
        if result["mass_conversion"]["status"] == "pass"
        and result["residual_covariance"]["status"] == "pass"
        else "fail"
    )
    output = data_root / "run_records/pilot1/reference-discrepancy-v0.1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["external_record"] = {
        "logical_path": logical_path(output, data_root),
        "bytes": output.stat().st_size,
        "sha256": hash_file(output, "sha256"),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot1-discrepancy")
    parser.add_argument("command", choices=("mass", "run"))
    parser.add_argument("--data-root")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.command == "mass":
        result = mass_conversion_audit()
    else:
        data_root = configured_data_root(args.data_root)
        require_initialized_data_root(data_root)
        result = run(data_root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result.get("status") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
