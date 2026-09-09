import numpy as np

from pulsar_pilot.c0 import (
    build_frequency_grid,
    fit_weighted_sinusoid,
    validate_c0_configuration,
)


def test_frequency_grid_uses_frozen_fourier_spacing() -> None:
    frequencies, metadata = build_frequency_grid(1000.0, 30.0, 0.5, 5)
    assert frequencies[0] == 1 / 500
    assert np.isclose(np.diff(frequencies).mean(), 1 / 5000)
    assert metadata["independent_fourier_bin_per_day"] == 1 / 1000
    assert frequencies[-1] <= 1 / 30 + metadata["frequency_step_per_day"] / 2


def test_weighted_sinusoid_recovers_known_amplitude() -> None:
    times = np.linspace(0, 200, 500)
    frequency = 1 / 50
    residuals = 2.0 + 3.0 * np.sin(2 * np.pi * frequency * times)
    residuals += 4.0 * np.cos(2 * np.pi * frequency * times)
    result = fit_weighted_sinusoid(times, residuals, np.ones_like(times), frequency)
    assert np.isclose(result["amplitude"], 5.0)
    assert result["delta_chi2"] > 0


def test_c0_configuration_rejects_broad_authorization() -> None:
    frozen = {
        "stage_c": {"authorization": "c0_only"},
        "trigger": {"false_alarm_probability": "prohibited"},
        "cases": [{"id": "C0", "period_days": None, "amplitude_microseconds": 0.0}],
    }
    assert validate_c0_configuration(frozen)["status"] == "pass"
    frozen["stage_c"]["authorization"] = "all_cases"
    assert validate_c0_configuration(frozen)["status"] == "fail"
