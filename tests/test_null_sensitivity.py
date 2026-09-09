from pathlib import Path

from pulsar_pilot.null_sensitivity import (
    _smallest_supported_amplitude,
    projected_mass_moon_masses,
    wilson_interval_95,
)


def test_wilson_interval_preserves_finite_sample_limit() -> None:
    lower, upper = wilson_interval_95(12, 12)
    assert 0.75 < lower < 0.76
    assert upper == 1.0
    assert lower < 0.9


def test_conservative_grid_threshold_does_not_interpolate() -> None:
    cells = [
        {"amplitude_microseconds": 0.2, "recovered": 9, "cases": 12},
        {"amplitude_microseconds": 0.3, "recovered": 10, "cases": 12},
        {"amplitude_microseconds": 0.4, "recovered": 12, "cases": 12},
    ]
    assert _smallest_supported_amplitude(cells, 0.5) == 0.3
    assert _smallest_supported_amplitude(cells, 0.9) is None


def test_mass_conversion_reproduces_frozen_reference() -> None:
    observed = projected_mass_moon_masses(0.5, 100.0, 1.4)
    assert abs(observed - 0.08054709633545554) < 1e-15


def test_interpretation_module_has_no_observed_residual_or_search_path() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/pulsar_pilot/null_sensitivity.py").read_text(
        encoding="utf-8"
    )
    assert "WidebandTOAResiduals" not in source
    assert "prepare_covariance_gls_scanner" not in source
    assert "scan(" not in source
    assert "generate_covariance_null" not in source
