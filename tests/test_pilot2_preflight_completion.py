import hashlib
import json
from pathlib import Path


def test_pilot2_preflight_completion_record_is_self_consistent() -> None:
    root = Path(__file__).resolve().parents[1]
    record = json.loads(
        (root / "protocol/PILOT2_PREFLIGHT_COMPLETION_RECORD_v0.2.1.json")
        .read_text(encoding="utf-8")
    )
    assert record["status"] == "preflight_passed_after_frozen_json_only_regrade"
    assert record["score"] == "16_of_16"
    assert record["full_calibration_authorized"] is False
    assert record["observed_periodic_search_authorized"] is False
    assert record["execution_counts"] == {
        "released_fit_reproductions": 1,
        "synthetic_null_cases": 20,
        "synthetic_injection_cases": 30,
        "full_covariance_solver_audits": 10,
        "observed_periodic_searches": 0,
        "threshold_calibrations": 0,
    }
    for relative, expected in record["repository_sha256"].items():
        actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        assert actual == expected, relative
