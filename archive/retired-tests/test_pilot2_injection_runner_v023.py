import json
from collections import OrderedDict
from pathlib import Path

import astropy.units as u
import numpy as np
import pytest
from pint.pint_matrix import CorrelationMatrix

from pulsar_pilot.config import load_yaml
from pulsar_pilot.paths import initialize_data_root
from pulsar_pilot.pilot2_injection_executor_v023 import (
    _correlation_parameter_block,
    phase_telemetry,
)
from pulsar_pilot.pilot2_injection_remediation import build_remediation_inventory
from pulsar_pilot.pilot2_injection_remediation_v023 import (
    V022_CONFIG_PATH,
    build_v023_inventory,
    load_design,
    validate_v023_design,
    verify_remediation_freeze,
)
from pulsar_pilot.pilot2_injection_runner_v023 import (
    EXECUTION_FREEZE_PATH,
    STAGE,
    V023Ledger,
    execute,
    implementation_sha256,
    terminalize_unexpected_exception,
    verify_execution_gate,
    verify_implementation_freeze,
    verify_readiness_freeze,
)


def _ledger(tmp_path: Path) -> V023Ledger:
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    inventory = build_v023_inventory()
    return V023Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())


def _pint_correlation() -> CorrelationMatrix:
    labels = OrderedDict(
        [
            ("CSSIN", (0, 1, u.dimensionless_unscaled)),
            ("CSCOS", (1, 2, u.dimensionless_unscaled)),
        ]
    )
    return CorrelationMatrix(
        np.asarray([[1.0, 0.25], [0.25, 1.0]]),
        [labels.copy(), labels.copy()],
    )


class _InstalledPintShapeFitter:
    def __init__(self) -> None:
        self.parameter_correlation_matrix = _pint_correlation()
        self.legacy_getter_calls = 0

    def get_parameter_correlation_matrix(self) -> str:
        self.legacy_getter_calls += 1
        return "formatted correlation matrix text"


def test_v023_inventory_is_disjoint_from_v021_and_all_v022_cases() -> None:
    validation = validate_v023_design()
    assert validation["status"] == "pass"
    assert validation["total_cases"] == 344
    assert validation["solver_audit_cases"] == 35
    assert validation["case_ids_disjoint_from_v0.2.1"] is True
    assert validation["seeds_disjoint_from_v0.2.1"] is True
    assert validation["case_ids_disjoint_from_v0.2.2"] is True
    assert validation["seeds_disjoint_from_v0.2.2"] is True
    assert validation["consumed_v0.2.2_case_excluded"] is True


def test_v023_inventory_excludes_the_entire_v022_namespace() -> None:
    root = Path(__file__).resolve().parents[1]
    base, _ = load_design()
    v022 = build_remediation_inventory(base, load_yaml(root / V022_CONFIG_PATH))
    v023 = build_v023_inventory()
    assert {item["case_id"] for item in v023["cases"]}.isdisjoint(
        {item["case_id"] for item in v022["cases"]}
    )
    assert {item["seed"] for item in v023["cases"]}.isdisjoint(
        {item["seed"] for item in v022["cases"]}
    )


def test_phase_telemetry_uses_real_pint_correlation_property_not_text_getter() -> None:
    fitter = _InstalledPintShapeFitter()
    primary = {
        "fitter": fitter,
        "sine_us": 1.0,
        "cosine_us": 0.0,
        "sine_uncertainty_us": 0.1,
        "cosine_uncertainty_us": 0.1,
    }
    result = phase_telemetry(primary, 0.0)
    assert np.isfinite(result["phase_standard_error_radians"])
    assert result["signed_wrapped_phase_error_radians"] == pytest.approx(0.0)
    assert fitter.legacy_getter_calls == 0


def test_phase_telemetry_fails_closed_on_missing_matrix_object() -> None:
    class InvalidFitter:
        parameter_correlation_matrix = "formatted text"

    with pytest.raises(RuntimeError, match="correlation-matrix object is unavailable"):
        _correlation_parameter_block(InvalidFitter())


def test_unexpected_exception_writes_terminal_result_and_hard_stop(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    ledger.begin_stage(STAGE)
    result_path = ledger.data_root / "run_records/pilot2/injection-evaluation-v0.2.3.json"
    result = terminalize_unexpected_exception(
        ledger,
        result_path,
        AttributeError("simulated compatibility failure"),
        "p2r3-test-case",
    )
    state = ledger.load()
    assert result["status"] == "fail"
    assert result["partial_scientific_metrics_recorded"] is False
    assert state["stage_status"][STAGE] == "fail"
    assert state["hard_stop"]["reason"] == "stage_gate_failure"
    assert state["active_stage"] is None
    assert state["stage_results"][STAGE]["sha256"]
    with pytest.raises(RuntimeError, match="hard stop"):
        ledger.begin_stage(STAGE)


def test_execution_stays_locked_before_context_or_predecessor_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[1]
    if (root / EXECUTION_FREEZE_PATH).is_file():
        pytest.skip("Preauthorization-only lock test")
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v023.verify_predecessor_bindings",
        lambda *_: pytest.fail("predecessors loaded before authorization"),
    )
    monkeypatch.setattr(
        "pulsar_pilot.pilot2_injection_runner_v023.prepare_context",
        lambda *_: pytest.fail("context loaded before authorization"),
    )
    assert verify_execution_gate()["status"] in {"locked", "fail"}
    with pytest.raises(RuntimeError, match="execution is locked"):
        execute(ledger.data_root)


def test_freezes_are_hash_bound_and_execution_remains_locked() -> None:
    if any(
        verifier()["status"] == "locked"
        for verifier in (
            verify_remediation_freeze,
            verify_implementation_freeze,
            verify_readiness_freeze,
        )
    ):
        return
    assert verify_remediation_freeze()["status"] == "pass"
    assert verify_implementation_freeze()["status"] == "pass"
    assert verify_readiness_freeze()["status"] == "pass"
    gate = verify_execution_gate()
    assert gate["status"] == "locked"
    assert gate["predecessors_loaded"] is False


def test_v023_source_preserves_science_boundaries() -> None:
    root = Path(__file__).resolve().parents[1]
    executor = (root / "src/pulsar_pilot/pilot2_injection_executor_v023.py").read_text()
    runner = (root / "src/pulsar_pilot/pilot2_injection_runner_v023.py").read_text()
    assert '"observed_residual_vector_used": False' in executor
    assert '"observed_periodic_scan_executed": False' in executor
    assert '"promotion_grade_executed": False' in runner
    assert "terminalize_unexpected_exception" in runner


def test_crash_audit_contains_no_scientific_outcome_fields() -> None:
    root = Path(__file__).resolve().parents[1]
    audit = json.loads(
        (root / "results/pilot2/injection_v022_crash_audit.json").read_text()
    )
    serialized = json.dumps(audit)
    assert audit["completed_case_records"] == 0
    assert audit["attempted_case"]["disposition"] == "consumed_never_reuse"
    for forbidden in ("trigger_statistic", "fit_result", "candidate_metric"):
        assert forbidden not in serialized
