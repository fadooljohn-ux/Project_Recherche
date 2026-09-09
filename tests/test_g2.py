from pulsar_pilot.g2 import (
    classify_warning_lines,
    compare_parameter_values,
    validate_free_parameters,
)


def test_parameter_comparison_uses_three_sigma_limit() -> None:
    passing = compare_parameter_values(10.0, 10.29, 0.1, 3.0, 64)
    failing = compare_parameter_values(10.0, 10.31, 0.1, 3.0, 64)
    assert passing["pass"] is True
    assert failing["pass"] is False


def test_validate_free_parameters_requires_only_frozen_base_and_dmx() -> None:
    result = validate_free_parameters(["F0", "DMX_0001"], ["F0"])
    assert result["status"] == "pass"
    assert result["free_dmx_count"] == 1


def test_warning_classifier_dispositions_clock_overrides() -> None:
    expected = [
        (
            "WARNING: tai2tt_bipm2019.clk overrides global clock file "
            "tai2tt_bipm2019.clk because of PINT_CLOCK_OVERRIDE"
        )
    ]
    assert classify_warning_lines(expected)["status"] == "pass"
    assert classify_warning_lines(["WARNING: Unexpected parameter toa_noise_params"])[
        "status"
    ] == "pass"
    assert classify_warning_lines(["WARNING: unexpected"])["status"] == "fail"
