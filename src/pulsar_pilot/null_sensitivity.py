from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

WILSON_Z_95 = 1.959963984540054


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson_interval_95(recovered: int, cases: int) -> tuple[float, float]:
    if cases <= 0 or recovered < 0 or recovered > cases:
        raise ValueError("Binomial counts are invalid")
    fraction = recovered / cases
    z2 = WILSON_Z_95**2
    denominator = 1.0 + z2 / cases
    center = (fraction + z2 / (2.0 * cases)) / denominator
    half_width = (
        WILSON_Z_95
        * math.sqrt(
            fraction * (1.0 - fraction) / cases + z2 / (4.0 * cases**2)
        )
        / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)


def projected_mass_moon_masses(
    timing_amplitude_microseconds: float,
    period_days: float,
    pulsar_mass_solar: float,
) -> float:
    gravitational_constant = 6.67430e-11
    speed_of_light = 299792458.0
    solar_mass_kg = 1.98847e30
    moon_mass_kg = 7.342e22
    pulsar_mass = pulsar_mass_solar * solar_mass_kg
    period_seconds = period_days * 86400.0
    semi_major_axis = (
        gravitational_constant * pulsar_mass * period_seconds**2
        / (4.0 * math.pi**2)
    ) ** (1.0 / 3.0)
    projected_mass = (
        timing_amplitude_microseconds
        * 1e-6
        * speed_of_light
        * pulsar_mass
        / semi_major_axis
    )
    return projected_mass / moon_mass_kg


def verify_and_load_sources(
    data_root: Path, config: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for label, expected in config["sources"].items():
        path = data_root / expected["logical_path"]
        if not path.is_file() or path.stat().st_size != int(expected["bytes"]):
            raise RuntimeError(f"Missing or wrong-size source: {label}")
        if _sha256(path) != expected["sha256"]:
            raise RuntimeError(f"Source hash mismatch: {label}")
        records[label] = json.loads(path.read_text(encoding="utf-8"))
    return records


def _smallest_supported_amplitude(
    cells: list[dict[str, Any]], target: float
) -> float | None:
    for cell in sorted(cells, key=lambda value: float(value["amplitude_microseconds"])):
        lower, _ = wilson_interval_95(int(cell["recovered"]), int(cell["cases"]))
        if lower >= target:
            return float(cell["amplitude_microseconds"])
    return None


def build_interpretation(
    config: dict[str, Any], records: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    parent = records["parent_injection_summary"]
    sensitivity = records["sensitivity_extension_summary"]
    observed = records["observed_search_result"]
    if sensitivity.get("status") != "pass" or sensitivity["scorecard"]["overall"] != "PASS":
        raise RuntimeError("Frozen sensitivity extension did not pass")
    if observed["outcome"]["run_status"] != "complete":
        raise RuntimeError("Observed one-shot result is not complete")
    if observed["outcome"]["candidate_present"] is not False:
        raise RuntimeError("Null sensitivity interpretation requires a null result")
    if observed["integrity"]["observed_scan_count"] != 1:
        raise RuntimeError("Observed result does not contain exactly one scan")

    recovery_config = config["recovery_interpretation"]
    mass_config = config["mass_interpretation"]
    surface = sensitivity["combined_recovery_surface"]
    periods: dict[str, Any] = {}
    conservative_50_count = 0
    conservative_90_count = 0
    for period in recovery_config["periods_days"]:
        source = surface["periods"][str(float(period))]
        cells: list[dict[str, Any]] = []
        for source_cell in source["cells"]:
            recovered = int(source_cell["recovered"])
            cases = int(source_cell["cases"])
            lower, upper = wilson_interval_95(recovered, cases)
            cells.append(
                {
                    "amplitude_microseconds": float(
                        source_cell["amplitude_microseconds"]
                    ),
                    "recovered": recovered,
                    "cases": cases,
                    "empirical_fraction": float(source_cell["fraction"]),
                    "wilson_95": [lower, upper],
                }
            )
        conservative_50 = _smallest_supported_amplitude(cells, 0.5)
        conservative_90 = _smallest_supported_amplitude(cells, 0.9)
        conservative_50_count += int(conservative_50 is not None)
        conservative_90_count += int(conservative_90 is not None)
        crossing_50 = float(source["crossing_50_microseconds"])
        crossing_90 = float(source["crossing_90_microseconds"])
        pulsar_mass = float(mass_config["pulsar_mass_solar"])
        periods[str(float(period))] = {
            "cells": cells,
            "empirical_crossing_50_microseconds": crossing_50,
            "empirical_crossing_90_microseconds": crossing_90,
            "empirical_crossing_50_projected_lunar_masses": (
                projected_mass_moon_masses(crossing_50, float(period), pulsar_mass)
            ),
            "empirical_crossing_90_projected_lunar_masses": (
                projected_mass_moon_masses(crossing_90, float(period), pulsar_mass)
            ),
            "conservative_sampled_50_microseconds": conservative_50,
            "conservative_sampled_50_projected_lunar_masses": (
                projected_mass_moon_masses(
                    conservative_50, float(period), pulsar_mass
                )
                if conservative_50 is not None
                else None
            ),
            "conservative_sampled_90_microseconds": conservative_90,
            "supports_90_percent_recovery_at_95_percent_confidence": (
                conservative_90 is not None
            ),
        }

    annual = parent["annual_identifiability_map"]
    masked_periods = [
        float(period) for period, record in annual.items() if not record["eligible"]
    ]
    eligible_checks = [
        float(period) for period, record in annual.items() if record["eligible"]
    ]
    expected = config["expected_outcome"]
    score_checks = {
        "source_hashes_verified": True,
        "sensitivity_extension_passed": True,
        "observed_result_complete": True,
        "observed_result_is_null": True,
        "exactly_one_observed_scan_preserved": True,
        "five_calibrated_periods_present": len(periods)
        == int(expected["calibrated_period_count"]),
        "all_cells_have_frozen_case_count": all(
            cell["cases"] == int(recovery_config["cases_per_cell"])
            for record in periods.values()
            for cell in record["cells"]
        ),
        "all_recovery_surfaces_monotonic": all(
            surface["periods"][period]["monotonic"] for period in periods
        ),
        "all_empirical_crossings_bracketed": all(
            surface["periods"][period]["bracketed_50_percent"]
            and surface["periods"][period]["bracketed_90_percent"]
            for period in periods
        ),
        "conservative_50_supported_at_all_periods": conservative_50_count
        == int(expected["conservative_50_percent_supported_period_count"]),
        "conservative_90_not_supported": conservative_90_count
        == int(expected["conservative_90_percent_supported_period_count"]),
        "annual_mask_gaps_preserved": sorted(masked_periods)
        == [350.0, 365.25, 380.0],
        "no_period_interpolation": config["claim_rules"][
            "interpolate_sensitivity_across_period"
        ]
        is False,
        "no_formal_exclusion_claim": config["claim_rules"][
            "empirical_crossings_are_formal_upper_limits"
        ]
        is False,
        "no_new_observed_analysis": config["claim_rules"][
            "new_observed_periodic_search_authorized"
        ]
        is False,
    }
    return {
        "schema_version": 1,
        "interpretation_id": config["interpretation_id"],
        "status": "pass_bounded_sensitivity_interpretation",
        "target": config["target"],
        "source_records": config["sources"],
        "observed_null": {
            "candidate_present": False,
            "strongest_unmasked_period_days": observed["outcome"][
                "strongest_unmasked_period_days"
            ],
            "strongest_unmasked_statistic": observed["outcome"][
                "strongest_unmasked_statistic"
            ],
            "locked_threshold_delta_chi2": observed["detector"][
                "locked_threshold_delta_chi2"
            ],
        },
        "recovery_definition": surface["recovered_definition"],
        "periods": periods,
        "annual_identifiability": {
            "masked_sensitivity_gaps_days": sorted(masked_periods),
            "eligible_strong_control_checks_days": sorted(eligible_checks),
            "lower_amplitude_crossings_available_at_annual_checks": False,
        },
        "finite_sample_disposition": {
            "cases_per_cell": int(recovery_config["cases_per_cell"]),
            "interval": recovery_config["uncertainty_interval"],
            "fixed_phases": 4,
            "noise_realizations_per_phase": 3,
            "empirical_90_crossings_are_formal_95_percent_limits": False,
            "sampled_periods_supporting_90_percent_wilson_lower_bound": (
                conservative_90_count
            ),
        },
        "scorecard": {
            "overall": "PASS" if all(score_checks.values()) else "FAIL",
            "passed": sum(score_checks.values()),
            "total": len(score_checks),
            "criteria": score_checks,
        },
        "claim_boundary": config["claim_rules"],
    }
