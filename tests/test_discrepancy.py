import pytest

from pulsar_pilot.discrepancy import (
    approximate_projected_mass_kg,
    exact_projected_mass_kg,
    mass_conversion_audit,
    timing_amplitude_for_projected_mass_microseconds,
)


def test_mass_conversion_matches_independent_derivation_and_exact_solution() -> None:
    result = mass_conversion_audit()
    assert result["status"] == "pass"
    assert result["implementation_projected_mass_moon"] == pytest.approx(
        result["independent_approximation_projected_mass_moon"], rel=1e-14
    )
    assert result["low_mass_approximation_relative_difference_from_exact"] < 1e-6


def test_exact_mass_and_amplitude_are_inverse_relations() -> None:
    mass_kg = exact_projected_mass_kg(3.0, 100.0, 1.4)
    moon_mass = mass_kg / 7.342e22
    recovered_amplitude = timing_amplitude_for_projected_mass_microseconds(
        moon_mass, 100.0, 1.4
    )
    assert recovered_amplitude == pytest.approx(3.0, rel=1e-12)
    assert approximate_projected_mass_kg(3.0, 100.0, 1.4) == pytest.approx(
        mass_kg, rel=1e-6
    )
