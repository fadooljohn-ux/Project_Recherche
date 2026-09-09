import json
from pathlib import Path

import numpy as np
import pytest
from scipy.linalg import cholesky, solve_triangular

from pulsar_pilot.config import load_yaml
from pulsar_pilot.pilot1_runtime import (
    ResumableArtifactLedger,
    build_pilot1_case_inventory,
    build_search_frequency_grid,
    circular_signal_templates,
    conservative_nearest_rank,
    generate_covariance_null,
    inventory_summary,
    null_ensemble_diagnostics,
    prepare_covariance_gls_scanner,
)


def _plan() -> dict:
    root = Path(__file__).resolve().parents[1]
    return load_yaml(root / "config" / "pilot1.yaml")


def test_search_frequency_grid_is_deterministic_and_includes_boundaries() -> None:
    times = np.linspace(53000.0, 58000.0, 25)
    first, metadata = build_search_frequency_grid(times, 30.0, 2000.0)
    second, _ = build_search_frequency_grid(times, 30.0, 2000.0)
    assert np.array_equal(first, second)
    assert first[0] == pytest.approx(1.0 / 2000.0)
    assert first[-1] == pytest.approx(1.0 / 30.0)
    assert np.all(np.diff(first) > 0)
    assert metadata["oversampling"] == 5


def test_circular_templates_use_toa_rows_and_zero_other_data_rows() -> None:
    times = np.array([56078.0, 56079.0])
    templates = circular_signal_templates(times, np.array([0.25]), 56078.0, 4)
    assert templates.shape == (4, 1, 2)
    assert templates[0, 0, 0] == pytest.approx(0.0)
    assert templates[0, 0, 1] == pytest.approx(1.0)
    assert templates[1, 0, 0] == pytest.approx(1.0)
    assert np.count_nonzero(templates[2:]) == 0


def test_covariance_gls_scanner_matches_direct_augmented_gls() -> None:
    times = np.linspace(0.0, 100.0, 80)
    frequency = 1.0 / 23.0
    rng = np.random.default_rng(8)
    raw = rng.normal(size=(80, 80))
    covariance = raw @ raw.T + np.eye(80) * 5.0
    design = np.column_stack((np.ones(80) * 1e20, times, times**2 * 1e-20))
    template = circular_signal_templates(times, np.array([frequency]), 0.0, 80)[:, 0, :]
    coefficients = np.array([3.2e-6, -1.7e-6])
    residuals = design @ np.array([1e-26, -2e-8, 3e10]) + template @ coefficients

    scanner = prepare_covariance_gls_scanner(
        covariance, design, times, np.array([frequency]), 0.0
    )
    result = scanner.scan(residuals)
    assert scanner.timing_design_rank == 3

    factor = cholesky(covariance, lower=True)
    whitened_y = solve_triangular(factor, residuals, lower=True)
    whitened_design = solve_triangular(factor, design, lower=True)
    whitened_augmented = solve_triangular(
        factor, np.column_stack((design, template)), lower=True
    )
    nuisance_scale = np.linalg.norm(whitened_design, axis=0)
    augmented_scale = np.linalg.norm(whitened_augmented, axis=0)
    nuisance_normalized = whitened_design / nuisance_scale
    augmented_normalized = whitened_augmented / augmented_scale
    nuisance_fit = nuisance_normalized @ np.linalg.lstsq(
        nuisance_normalized, whitened_y, rcond=None
    )[0]
    augmented_fit = augmented_normalized @ np.linalg.lstsq(
        augmented_normalized, whitened_y, rcond=None
    )[0]
    direct_delta = np.sum((whitened_y - nuisance_fit) ** 2) - np.sum(
        (whitened_y - augmented_fit) ** 2
    )
    assert result["trigger_statistic"] == pytest.approx(direct_delta, rel=1e-9, abs=1e-12)
    assert result["all_coefficients_seconds"][0] == pytest.approx(coefficients, rel=1e-8)


def test_covariance_null_generator_and_whitening_diagnostics() -> None:
    covariance = np.array([[2.0, 0.3, 0.1], [0.3, 1.0, -0.2], [0.1, -0.2, 1.5]])
    factor = cholesky(covariance, lower=True)
    first_generator = np.random.default_rng(123)
    second_generator = np.random.default_rng(123)
    assert np.array_equal(
        generate_covariance_null(factor, first_generator),
        generate_covariance_null(factor, second_generator),
    )
    generator = np.random.default_rng(456)
    samples = np.asarray([generate_covariance_null(factor, generator) for _ in range(5000)])
    diagnostics = null_ensemble_diagnostics(samples, factor)
    assert diagnostics["whitened_variance"] == pytest.approx(1.0, abs=0.04)
    assert diagnostics["maximum_absolute_ensemble_correlation"] < 0.05
    assert diagnostics["correlation_method"] == (
        "maximum_absolute_pooled_whitened_lag_correlation"
    )
    assert diagnostics["maximum_lag"] == 2


def test_conservative_nearest_rank_uses_strict_empirical_order_statistic() -> None:
    values = np.arange(1.0, 101.0)
    assert conservative_nearest_rank(values, 0.99) == 99.0
    assert conservative_nearest_rank(values, 0.995) == 100.0


def test_case_inventory_is_complete_disjoint_and_deterministic() -> None:
    first = build_pilot1_case_inventory(_plan())
    second = build_pilot1_case_inventory(_plan())
    assert first == second
    summary = inventory_summary(first)
    assert summary["calibration_nulls"] == 1000
    assert summary["sealed_evaluation_nulls"] == 500
    assert summary["injections"] == 284
    assert summary["independent_audits"] == 29
    assert summary["unique_case_ids"] == 1784
    assert summary["unique_seeds"] == 1784
    calibration_seeds = {
        item["seed"] for item in first["null_cases"] if item["family"] == "calibration"
    }
    evaluation_seeds = {
        item["seed"]
        for item in first["null_cases"]
        if item["family"] == "sealed_evaluation"
    }
    assert calibration_seeds.isdisjoint(evaluation_seeds)


def test_resumable_artifact_ledger_hashes_and_rejects_drift(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    artifact = data_root / "derived" / "case-1.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(json.dumps({"value": 1}) + "\n")
    ledger_path = data_root / "run_records" / "pilot1" / "ledger.json"
    ledger = ResumableArtifactLedger(ledger_path, "inventory-a", "implementation-a")
    record = ledger.record("case-1", artifact, data_root)
    assert record["logical_path"] == "derived/case-1.json"
    assert ledger.verify(data_root)["status"] == "pass"

    incompatible = ResumableArtifactLedger(ledger_path, "inventory-b", "implementation-a")
    with pytest.raises(RuntimeError, match="does not match"):
        incompatible.load()

    artifact.write_text(json.dumps({"value": 2}) + "\n")
    assert ledger.verify(data_root)["status"] == "fail"
