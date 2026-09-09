import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_preunblinding_result_manifest_and_failure_are_preserved() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = root / "manifests/preunblinding_validation_result_v0.1.sha256"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        assert _sha256(root / relative) == expected

    result = json.loads(
        (
            root / "results/pilot1/preunblinding_validation_result_v0.1.json"
        ).read_text(encoding="utf-8")
    )
    assert result["status"] == "fail"
    assert result["score"] == {
        "overall": "FAIL",
        "passed": 14,
        "total": 15,
        "failed_criterion": "deletion_hard_veto_cost_gates",
    }
    assert (
        result["deletion_stability_cost"]["paired_wideband_toa_row"]
        ["hard_veto_adoption_gate"]
        == "FAIL"
    )
    assert (
        result["deletion_stability_cost"]["all_rows_on_one_floor_mjd_utc_day"]
        ["hard_veto_adoption_gate"]
        == "FAIL"
    )
    assert result["integrity"]["observed_residual_access_executed"] is False
    assert result["integrity"]["observed_periodic_search_executed"] is False
