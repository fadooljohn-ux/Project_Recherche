import copy

from pulsar_pilot.c3 import (
    _scorecard,
    classify_absorption,
    classify_annual_coupling,
    classify_astrometric_shift,
    classify_solver_stability,
    validate_c3_configuration,
)


def _method() -> dict:
    return {
        "strong_correlation_minimum": 0.8,
        "moderate_correlation_minimum": 0.5,
        "severe_astrometric_shift_sigma": 10.0,
        "material_astrometric_shift_sigma": 3.0,
        "strong_absorption_fraction": 0.8,
        "material_absorption_fraction": 0.5,
        "solver_stability_amplitude_difference_microseconds": 0.01,
        "solver_stability_phase_difference_radians": 0.001,
        "solver_stability_chi2_improvement_difference": 0.1,
    }


def _frozen_configuration() -> dict:
    return {
        "stage_c": {
            "authorization": "c3_only",
            "c3": {
                "joint_component": "ProjectCircularSignal",
                "same_run_c0_ordinary_comparator": True,
                "independent_crosscheck": "WidebandTOAFitter_explicit_full_covariance",
                "annual_identifiability_role": "diagnostic_not_hard_gate",
                "final_pilot0_injection_case": True,
            },
        },
        "trigger": {"false_alarm_probability": "prohibited"},
        "cases": [
            {
                "id": "C3",
                "period_days": 365.25,
                "amplitude_microseconds": 20.0,
                "hard_recovery_gate": False,
            }
        ],
    }


def test_c3_configuration_rejects_broad_authorization() -> None:
    frozen = _frozen_configuration()
    assert validate_c3_configuration(frozen)["status"] == "pass"
    broadened = copy.deepcopy(frozen)
    broadened["stage_c"]["authorization"] = "all_cases"
    assert validate_c3_configuration(broadened)["status"] == "fail"


def test_annual_diagnostic_classifications() -> None:
    method = _method()
    assert classify_annual_coupling(0.9, method) == "strong"
    assert classify_annual_coupling(0.6, method) == "moderate"
    assert classify_annual_coupling(0.2, method) == "low"
    assert classify_astrometric_shift(12.0, method) == "severe"
    assert classify_astrometric_shift(4.0, method) == "material"
    assert classify_astrometric_shift(1.0, method) == "small"
    assert classify_absorption(0.9, method) == "strong"
    assert classify_absorption(0.6, method) == "material"
    assert classify_absorption(0.2, method) == "limited"


def test_solver_stability_classification() -> None:
    method = _method()
    assert classify_solver_stability(0.001, 0.0001, 0.01, method) == "stable"
    assert classify_solver_stability(0.1, 0.0001, 0.01, method) == "sensitive"


def test_diagnostic_annual_degeneracy_does_not_override_hard_gate() -> None:
    hard = {
        "configuration_frozen_and_c3_only": True,
        "release_red_noise_preserved_and_wavex_absent": True,
        "injection_application_within_tolerance": True,
        "toa_count_unchanged": True,
        "c0_ordinary_fit_converged": True,
        "c3_ordinary_fit_converged": True,
        "c0_joint_fit_converged": True,
        "c3_joint_fit_converged": True,
        "joint_outputs_finite": True,
        "c0_full_covariance_fit_completed": True,
        "c3_full_covariance_fit_completed": True,
        "full_covariance_outputs_finite": True,
        "material_warnings_dispositioned": True,
        "periodogram_finite": True,
        "runtime_under_60_minutes": True,
        "peak_memory_under_16_gib": True,
        "pilot0_injections_complete_and_no_next_case_authorized": True,
    }
    diagnostics = {
        "absorption_classification": "strong",
        "recovery_classification": "inconsistent",
        "annual_coupling_classification": "strong",
        "astrometric_shift_classification": "severe",
        "solver_stability_classification": "sensitive",
        "exact_frequency_comparison": "at_or_below_c0",
        "global_peak_role": "diagnostic_not_acceptance_gate",
    }
    scorecard = _scorecard(hard, diagnostics)
    assert scorecard["overall"] == "PASS"
    assert scorecard["rows"]["annual_identifiability"]["outcome"] == "strong"
    hard["joint_outputs_finite"] = False
    assert _scorecard(hard, diagnostics)["overall"] == "FAIL"
