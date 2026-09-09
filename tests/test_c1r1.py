import copy

from pulsar_pilot.c1r1 import (
    _scorecard,
    validate_c1r1_configuration,
    wrapped_phase_difference,
)


def _frozen_configuration() -> dict:
    return {
        "stage_c": {
            "authorization": "c1_r1_only",
            "c1_r1": {
                "injection_waveform_unchanged": True,
                "joint_component": "ProjectCircularSignal",
                "independent_crosscheck": "WidebandTOAFitter_explicit_full_covariance",
                "blind_global_peak_role": "diagnostic_not_acceptance_gate",
            },
        },
        "trigger": {"false_alarm_probability": "prohibited"},
        "cases": [
            {"id": "C1", "period_days": 100.0, "amplitude_microseconds": 20.0}
        ],
    }


def test_c1r1_configuration_rejects_broad_authorization() -> None:
    frozen = _frozen_configuration()
    assert validate_c1r1_configuration(frozen)["status"] == "pass"
    broadened = copy.deepcopy(frozen)
    broadened["stage_c"]["authorization"] = "all_cases"
    assert validate_c1r1_configuration(broadened)["status"] == "fail"


def test_wrapped_phase_difference_handles_boundary() -> None:
    difference = wrapped_phase_difference(-3.13, 3.13)
    assert 0 < difference < 0.03


def test_scorecard_is_not_an_average() -> None:
    criteria = {
        "configuration_frozen_and_c1_r1_only": True,
        "release_red_noise_preserved_and_wavex_absent": True,
        "injection_application_within_tolerance": True,
        "toa_count_unchanged": True,
        "unmodeled_refit_converged": True,
        "exact_frequency_power_exceeds_c0": True,
        "exact_frequency_amplitude_exceeds_c0": True,
        "c0_joint_fit_converged": True,
        "c1_joint_fit_converged": True,
        "joint_recovery_fraction_within_bounds": True,
        "joint_phase_error_within_bound": True,
        "joint_chi2_improvement_exceeds_c0": True,
        "full_covariance_fit_completed": True,
        "solver_amplitudes_agree": True,
        "solver_phases_agree": True,
        "solver_chi2_values_agree": True,
        "material_warnings_dispositioned": False,
        "periodogram_finite": True,
        "runtime_under_60_minutes": True,
        "peak_memory_under_16_gib": True,
        "later_cases_remain_blocked": True,
    }
    scorecard = _scorecard(criteria)
    assert scorecard["overall"] == "FAIL"
    assert scorecard["rows"]["warning_hygiene"]["status"] == "FAIL"
    assert scorecard["rows"]["global_strongest_peak"]["status"] == "DIAGNOSTIC"
