import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fable_disposition_is_hash_bound_and_preparation_only() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = root / "manifests/fable_preexecution_disposition_v0.1.sha256"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        assert _sha256(root / relative) == expected

    record = json.loads(
        (
            root / "results/pilot1/fable_preexecution_disposition_v0.1.json"
        ).read_text(encoding="utf-8")
    )
    assert record["selected_disposition"] == (
        "ONE_SHOT_FREEZE_PREPARATION_MAY_RESUME_WITH_DELETION_CHECKS_ADVISORY"
    )
    assert set(record["mandatory_conditions"]) == {
        "C1_advisory_demotion",
        "C2_frozen_deletion_reporting",
        "C3_no_rerolls_or_new_randomness",
        "C4_borderline_result_mandatory_reporting",
        "C5_robust_refit_containment",
        "C6_unchanged_locked_detector",
        "C7_authority_boundary",
    }
    assert record["deletion_checks_as_hard_vetoes"] is False
    assert record["robust_candidate_refit_included"] is False
    assert record["observed_residual_access_authorized"] is False
    assert record["observed_periodic_search_authorized"] is False
    assert record["final_fable_signoff_required"] is True
    assert record["explicit_user_execution_authorization_required"] is True
