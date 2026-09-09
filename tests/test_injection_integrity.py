import pytest

from pulsar_pilot.injection_integrity import (
    DM_ERROR_KEY,
    TOA_ADJUSTMENT_KEY,
    UNCENTERED_TARGET_KEY,
    classify_injection_warning_lines,
    phase_measurement_diagnostics,
    separate_application_diagnostics,
    toa_adjustment_gate_value,
)


def test_scoped_warning_classifier_dispositions_arecibo_override() -> None:
    warning = (
        "WARNING: Clock file from RECHERCHE_DATA_ROOT/controlled/"
        "nanograv15yr-v2.1.0/clock/time_ao.dat overrides global clock file "
        "time_ao.dat because of PINT_CLOCK_OVERRIDE"
    )
    result = classify_injection_warning_lines([warning, warning])
    assert result["status"] == "pass"
    assert result["expected_warning_count"] == 2
    assert result["unexpected_warning_count"] == 0


def test_application_diagnostics_remain_separate() -> None:
    application = {
        TOA_ADJUSTMENT_KEY: 0.00001,
        UNCENTERED_TARGET_KEY: 0.0018,
        DM_ERROR_KEY: 0.0,
    }
    result = separate_application_diagnostics(application)
    assert result == application
    assert toa_adjustment_gate_value(result) == 0.00001


def test_toa_gate_rejects_legacy_conflated_field() -> None:
    with pytest.raises(ValueError, match="legacy conflated field"):
        toa_adjustment_gate_value({"toa_adjustment_error_microseconds": 0.0018})


@pytest.mark.parametrize(
    "application",
    [
        {TOA_ADJUSTMENT_KEY: 0.0, UNCENTERED_TARGET_KEY: 0.0},
        {
            TOA_ADJUSTMENT_KEY: float("nan"),
            UNCENTERED_TARGET_KEY: 0.0,
            DM_ERROR_KEY: 0.0,
        },
        {
            TOA_ADJUSTMENT_KEY: -0.1,
            UNCENTERED_TARGET_KEY: 0.0,
            DM_ERROR_KEY: 0.0,
        },
    ],
)
def test_application_diagnostics_fail_closed(application: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        separate_application_diagnostics(application)


def test_phase_measurement_diagnostics_use_cartesian_covariance() -> None:
    result = phase_measurement_diagnostics(3.0, 4.0, 0.3, 0.4, 0.25)
    assert result["recovered_phase_radians"] == pytest.approx(0.9272952180016122)
    assert result["sine_cosine_covariance_microseconds_squared"] == pytest.approx(
        0.03
    )
    assert result["phase_standard_error_radians"] == pytest.approx(
        0.05878775382679628
    )


def test_phase_measurement_diagnostics_reject_zero_amplitude() -> None:
    with pytest.raises(ValueError, match="zero recovered amplitude"):
        phase_measurement_diagnostics(0.0, 0.0, 0.1, 0.1, 0.0)
