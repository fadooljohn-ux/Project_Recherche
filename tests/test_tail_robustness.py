import inspect
from pathlib import Path

import numpy as np

from pulsar_pilot.config import load_yaml
from pulsar_pilot.tail_robustness import (
    CONFIG_PATH,
    _recovery_surface,
    build_null_orders,
    build_recovery_order,
    generate_contaminated_null,
    observed_nonperiodic_localization,
    theoretical_mixture_excess_kurtosis,
    verify_freeze,
)


def _config() -> dict:
    root = Path(__file__).resolve().parents[1]
    return load_yaml(root / CONFIG_PATH)


def test_tail_inventory_is_exact_disjoint_and_deterministic() -> None:
    config = _config()
    nulls = build_null_orders(config)
    recovery = build_recovery_order(config)
    assert len(nulls["calibration"]) == 1000
    assert len(nulls["evaluation"]) == 500
    assert len(recovery) == 160
    assert len({case["seed"] for case in nulls["calibration"] + nulls["evaluation"]}) == 1500
    assert sum(case["complete_refit_audit"] for case in recovery) == 16
    assert sum(case["full_covariance_audit"] for case in recovery) == 4
    assert all(
        not case["full_covariance_audit"] or case["complete_refit_audit"]
        for case in recovery
    )


def test_scale_mixture_matches_frozen_kurtosis_and_is_reproducible() -> None:
    model = _config()["contamination_model"]
    probability = float(model["contaminated_coordinate_probability"])
    multiplier = float(model["contaminated_standard_deviation_multiplier"])
    expected = float(model["expected_excess_kurtosis"])
    assert abs(theoretical_mixture_excess_kurtosis(probability, multiplier) - expected) < 1e-12
    factor = np.eye(100)
    left, left_count = generate_contaminated_null(
        factor, np.random.default_rng(1234), probability, multiplier
    )
    right, right_count = generate_contaminated_null(
        factor, np.random.default_rng(1234), probability, multiplier
    )
    assert np.array_equal(left, right)
    assert left_count == right_count


def test_recovery_surface_requires_threshold_and_frequency_recovery() -> None:
    def record(amplitude: float, triggered: bool, recovered: bool) -> dict:
        return {
            "case": {"period_days": 100.0, "amplitude_microseconds": amplitude},
            "triggered": triggered,
            "frequency_recovered": recovered,
        }

    surface = _recovery_surface(
        [
            record(0.2, True, False),
            record(0.35, True, True),
            record(0.5, True, True),
        ]
    )
    cells = surface["periods"]["100.0"]["cells"]
    assert [cell["fraction"] for cell in cells] == [0.0, 1.0, 1.0]


def test_observed_localization_cannot_scan_a_frequency_grid() -> None:
    source = inspect.getsource(observed_nonperiodic_localization)
    assert ".scan(" not in source
    assert "whiten_and_project" in source


def test_tail_execution_freeze_verifies() -> None:
    result = verify_freeze()
    assert result["status"] == "pass"
    assert result["failures"] == []
