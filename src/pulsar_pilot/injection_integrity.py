import math

from .g2 import classify_warning_lines

TOA_ADJUSTMENT_KEY = "toa_adjustment_maximum_absolute_error_microseconds"
UNCENTERED_TARGET_KEY = (
    "uncentered_toa_residual_target_maximum_absolute_error_microseconds"
)
DM_ERROR_KEY = "dm_maximum_absolute_error"
EXPECTED_ARECIBO_OVERRIDE = "time_ao.dat overrides global clock file time_ao.dat"
EXPECTED_ARECIBO_DISPOSITION = "expected controlled release-clock override"


def classify_injection_warning_lines(lines: list[str]) -> dict[str, object]:
    """Apply the prospectively scoped Arecibo disposition to injection logs."""
    source = classify_warning_lines(lines)
    expected = list(source["expected_warnings"])
    unexpected: list[str] = []
    for line in source["unexpected_warnings"]:
        if EXPECTED_ARECIBO_OVERRIDE in line:
            expected.append(
                {"warning": line, "disposition": EXPECTED_ARECIBO_DISPOSITION}
            )
        else:
            unexpected.append(line)
    return {
        "status": "pass" if not unexpected else "fail",
        "expected_warning_count": len(expected),
        "expected_warnings": expected,
        "unexpected_warning_count": len(unexpected),
        "unexpected_warnings": unexpected,
    }


def separate_application_diagnostics(application: dict[str, object]) -> dict[str, float]:
    """Validate and retain injection-application diagnostics without conflation."""
    missing = [
        key
        for key in (TOA_ADJUSTMENT_KEY, UNCENTERED_TARGET_KEY, DM_ERROR_KEY)
        if key not in application
    ]
    if missing:
        raise ValueError(f"Missing injection-application diagnostics: {missing}")
    result = {
        TOA_ADJUSTMENT_KEY: float(application[TOA_ADJUSTMENT_KEY]),
        UNCENTERED_TARGET_KEY: float(application[UNCENTERED_TARGET_KEY]),
        DM_ERROR_KEY: float(application[DM_ERROR_KEY]),
    }
    invalid = [
        key for key, value in result.items() if not math.isfinite(value) or value < 0.0
    ]
    if invalid:
        raise ValueError(f"Invalid injection-application diagnostics: {invalid}")
    return result


def toa_adjustment_gate_value(record: dict[str, object]) -> float:
    """Return only the canonical TOA-adjustment metric and fail closed if absent."""
    if TOA_ADJUSTMENT_KEY not in record:
        raise ValueError(
            "Canonical TOA-adjustment metric is absent; a legacy conflated field "
            "cannot be graded"
        )
    value = float(record[TOA_ADJUSTMENT_KEY])
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("Canonical TOA-adjustment metric is invalid")
    return value


def phase_measurement_diagnostics(
    sine_microseconds: float,
    cosine_microseconds: float,
    sine_uncertainty_microseconds: float,
    cosine_uncertainty_microseconds: float,
    sine_cosine_correlation: float,
) -> dict[str, float]:
    """Calculate circular phase uncertainty from fitted Cartesian components."""
    values = (
        sine_microseconds,
        cosine_microseconds,
        sine_uncertainty_microseconds,
        cosine_uncertainty_microseconds,
        sine_cosine_correlation,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Nonfinite phase-measurement input")
    if sine_uncertainty_microseconds < 0.0 or cosine_uncertainty_microseconds < 0.0:
        raise ValueError("Negative phase-component uncertainty")
    if abs(sine_cosine_correlation) > 1.0:
        raise ValueError("Invalid sine-cosine correlation")
    amplitude_squared = sine_microseconds**2 + cosine_microseconds**2
    if amplitude_squared <= 0.0:
        raise ValueError("Phase is undefined at zero recovered amplitude")
    covariance = (
        sine_cosine_correlation
        * sine_uncertainty_microseconds
        * cosine_uncertainty_microseconds
    )
    gradient_sine = -cosine_microseconds / amplitude_squared
    gradient_cosine = sine_microseconds / amplitude_squared
    variance = (
        gradient_sine**2 * sine_uncertainty_microseconds**2
        + gradient_cosine**2 * cosine_uncertainty_microseconds**2
        + 2.0 * gradient_sine * gradient_cosine * covariance
    )
    if variance < -1e-15:
        raise ValueError("Calculated phase variance is negative")
    return {
        "recovered_sine_microseconds": sine_microseconds,
        "recovered_cosine_microseconds": cosine_microseconds,
        "sine_uncertainty_microseconds": sine_uncertainty_microseconds,
        "cosine_uncertainty_microseconds": cosine_uncertainty_microseconds,
        "sine_cosine_correlation": sine_cosine_correlation,
        "sine_cosine_covariance_microseconds_squared": covariance,
        "recovered_phase_radians": math.atan2(
            cosine_microseconds, sine_microseconds
        ),
        "phase_standard_error_radians": math.sqrt(max(0.0, variance)),
    }
