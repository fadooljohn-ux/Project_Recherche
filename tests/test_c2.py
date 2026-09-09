import copy

from pulsar_pilot.c2 import (
    _scorecard,
    classify_boundary_recovery,
    validate_c2_configuration,
)


def _method() -> dict:
    return {
        "robust_recovery_fraction_minimum": 0.8,
        "robust_recovery_fraction_maximum": 1.2,
        "robust_phase_error_maximum_radians": 0.1,
        "partial_recovery_fraction_minimum": 0.25,
        "partial_recovery_fraction_maximum": 1.5,
        "partial_phase_error_maximum_radians": 0.5,
    }


def _frozen_configuration() -> dict:
    return {
        "stage_c": {
            "authorization": "c2_only",
            "c2": {
                "joint_component": "ProjectCircularSignal",
                "independent_crosscheck": "WidebandTOAFitter_explicit_full_covariance",
                "recovery_classification_role": "diagnostic_not_hard_gate",
                "exact_frequency_c0_comparison_role": "diagnostic_not_hard_gate",
            },
        },
        "trigger": {"false_alarm_probability": "prohibited"},
        "cases": [
            {
                "id": "C2",
                "period_days": 100.0,
                "amplitude_microseconds": 5.0,
                "hard_recovery_gate": False,
            }
        ],
    }


def test_c2_configuration_rejects_broad_authorization() -> None:
    frozen = _frozen_configuration()
    assert validate_c2_configuration(frozen)["status"] == "pass"
    broadened = copy.deepcopy(frozen)
    broadened["stage_c"]["authorization"] = "all_cases"
    assert validate_c2_configuration(broadened)["status"] == "fail"


def test_boundary_recovery_classification_is_frozen() -> None:
    method = _method()
    assert classify_boundary_recovery(1.0, 0.01, method) == "robust"
    assert classify_boundary_recovery(0.5, 0.2, method) == "partial"
    assert classify_boundary_recovery(0.1, 0.8, method) == "inconsistent"


def test_diagnostic_recovery_does_not_override_hard_gate() -> None:
    hard = {
        "configuration_frozen_and_c2_only": True,
        "release_red_noise_preserved_and_wavex_absent": True,
        "injection_application_within_tolerance": True,
        "toa_count_unchanged": True,
        "unmodeled_refit_converged": True,
        "c0_joint_fit_converged": True,
        "c2_joint_fit_converged": True,
        "full_covariance_fit_completed": True,
        "solver_amplitudes_agree": True,
        "solver_phases_agree": True,
        "solver_chi2_values_agree": True,
        "material_warnings_dispositioned": True,
        "periodogram_finite": True,
        "runtime_under_60_minutes": True,
        "peak_memory_under_16_gib": True,
        "c3_remains_blocked": True,
    }
    diagnostics = {
        "recovery_classification": "inconsistent",
        "exact_frequency_comparison": "at_or_below_c0",
        "global_peak_role": "diagnostic_not_acceptance_gate",
    }
    scorecard = _scorecard(hard, diagnostics)
    assert scorecard["overall"] == "PASS"
    assert scorecard["rows"]["boundary_recovery"]["outcome"] == "inconsistent"
    hard["material_warnings_dispositioned"] = False
    assert _scorecard(hard, diagnostics)["overall"] == "FAIL"
