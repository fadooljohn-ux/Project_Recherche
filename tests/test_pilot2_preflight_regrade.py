import hashlib
import json
from pathlib import Path

from pulsar_pilot.pilot2_preflight_regrade import evaluate_records


def _record(case_id: str, family: str, audited: bool = False) -> dict:
    record: dict = {
        "case": {"case_id": case_id, "family": family},
        "observed_residual_vector_used": False,
    }
    if audited:
        record.update(
            {
                "application": {
                    "toa_adjustment_maximum_absolute_error_microseconds": 0.00001,
                    "uncentered_toa_residual_target_maximum_absolute_error_microseconds": 0.0015,
                },
                "primary_solver": {
                    "returned_converged": True,
                    "fitter_converged": True,
                    "release_red_noise_preserved": True,
                    "wavex_absent": True,
                },
                "full_covariance_solver": {
                    "completed": True,
                    "release_red_noise_preserved": True,
                    "wavex_absent": True,
                },
                "solver_comparison": {
                    "amplitude_difference_microseconds": 0.001,
                    "phase_difference_radians": 0.0001,
                    "chi2_difference": 0.01,
                },
            }
        )
    return record


def _summary() -> dict:
    warning = (
        "WARNING Clock file from RECHERCHE_DATA_ROOT/controlled/"
        "nanograv15yr-v2.1.0/clock/time_ao.dat overrides global clock file "
        "time_ao.dat because of PINT_CLOCK_OVERRIDE"
    )
    return {
        "warnings": {
            "expected_warning_count": 3,
            "unexpected_warnings": [warning],
        },
        "reproduction": {"status": "pass"},
        "synthetic_benchmark": {
            "runtime_projection": {"total_hours": 2.0},
            "observed_residual_vector_used": False,
        },
        "resources": {
            "wall_hours": 0.25,
            "peak_memory_gib": 1.0,
            "complete_data_root_gib": 0.2,
            "additional_download_bytes": 0,
        },
        "observed_residual_global_search_executed": False,
        "threshold_calibration_executed": False,
    }


def test_regrade_uses_toa_application_gate_not_descriptive_residual_error() -> None:
    records = [_record(f"null-{index}", "null") for index in range(20)]
    records.extend(
        _record(f"inj-{index}", "injection", audited=index < 10)
        for index in range(30)
    )
    result = evaluate_records(_summary(), records)
    assert result["status"] == "pass"
    assert result["maximum_toa_application_error_microseconds"] == 0.00001
    assert result["maximum_uncentered_residual_target_diagnostic_microseconds"] == (
        0.0015
    )
    assert all(item["status"] == "PASS" for item in result["audit_results"])


def test_regrade_does_not_hide_other_unexpected_warnings() -> None:
    records = [_record(f"null-{index}", "null") for index in range(20)]
    records.extend(
        _record(f"inj-{index}", "injection", audited=index < 10)
        for index in range(30)
    )
    summary = _summary()
    summary["warnings"]["unexpected_warnings"].append("WARNING unrelated")
    result = evaluate_records(summary, records)
    assert result["status"] == "fail"
    assert result["warning_regrade"]["remaining_unexpected_warning_count"] == 1


def test_regrade_module_has_no_science_execution_imports() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/pulsar_pilot/pilot2_preflight_regrade.py").read_text(
        encoding="utf-8"
    )
    assert "pint." not in source
    assert "numpy" not in source
    assert ".scan(" not in source
    assert "fit_toas" not in source
    assert "import random" not in source


def test_regrade_freeze_hashes_are_self_consistent_if_present() -> None:
    root = Path(__file__).resolve().parents[1]
    freeze_path = root / "protocol/PILOT2_PREFLIGHT_R1_REGRADE_FREEZE_v0.2.1.json"
    if not freeze_path.exists():
        return
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    for relative, expected in freeze["frozen_sha256"].items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
