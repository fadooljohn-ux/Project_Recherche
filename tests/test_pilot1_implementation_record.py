import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pilot1_implementation_record_and_manifest() -> None:
    root = Path(__file__).resolve().parents[1]
    record_path = root / "protocol" / "PILOT1_IMPLEMENTATION_RECORD_v0.1.json"
    manifest_path = root / "protocol" / "implementation_records.sha256"
    expected, relative = manifest_path.read_text(encoding="utf-8").strip().split("  ", 1)
    assert relative == "protocol/PILOT1_IMPLEMENTATION_RECORD_v0.1.json"
    assert _sha256(record_path) == expected

    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["execution_authorized"] is False
    assert record["pilot1_synthetic_realizations_generated"] == 0
    assert record["observed_residual_global_search_executed"] is False
    for relative, expected in record["implementation_sha256"].items():
        assert _sha256(root / relative) == expected
    assert _sha256(root / "pixi.lock") == record["pixi_lock_sha256"]
