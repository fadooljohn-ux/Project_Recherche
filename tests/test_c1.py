import numpy as np

from pulsar_pilot.c1 import (
    complex_amplitude_difference,
    generate_circular_delay_us,
    validate_c1_configuration,
)


def test_circular_delay_uses_frozen_epoch_and_phase() -> None:
    phase = np.pi / 3
    values = generate_circular_delay_us(
        np.array([56078.0, 56178.0], dtype=np.longdouble),
        100.0,
        20.0,
        phase,
        56078.0,
    )
    assert np.allclose(values, 20 * np.sin(phase))


def test_complex_amplitude_difference_is_phase_aware() -> None:
    result = complex_amplitude_difference(3.0, 4.0, 0.0, 0.0)
    assert result["amplitude"] == 5.0
    assert np.isclose(result["phase_radians"], np.arctan2(4.0, 3.0))


def test_c1_configuration_rejects_broad_authorization() -> None:
    frozen = {
        "phase_radians": np.pi / 3,
        "stage_c": {
            "authorization": "c1_only",
            "c1": {"reference_epoch_mjd_tdb": 56078.0, "joint_component": "PINT_WaveX"},
        },
        "trigger": {"false_alarm_probability": "prohibited"},
        "cases": [
            {
                "id": "C1",
                "period_days": 100.0,
                "amplitude_microseconds": 20.0,
                "hard_recovery_gate": True,
            }
        ],
    }
    assert validate_c1_configuration(frozen)["status"] == "pass"
    frozen["stage_c"]["authorization"] = "all_cases"
    assert validate_c1_configuration(frozen)["status"] == "fail"
