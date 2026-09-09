import hashlib
import io
import json
import socket
import tarfile
from pathlib import Path

import pytest

from pulsar_pilot.config import load_yaml
from pulsar_pilot.pilot2_preflight import (
    _network_disabled,
    build_case_order,
    extract_selected_products,
    seed_required_clock_cache_entries,
)


def test_case_order_is_exact_and_deterministic() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / "config/pilot2_preflight_v0.2.yaml")
    first = build_case_order(config)
    second = build_case_order(config)
    assert first == second
    assert first["case_count"] == 50
    assert first["null_cases"] == 20
    assert first["injection_cases"] == 30
    assert first["full_covariance_audits"] == 10
    assert first["order_sha256"] == (
        "a12b25b37c09e2b404f439e799bf9611a7f1c82b589395d856d5304210c3afcc"
    )


def _test_archive(tmp_path: Path, symlink_label: str | None = None) -> tuple[Path, dict]:
    members = {
        "par": "wideband/par/B1937+21_PINT_20230131.wb.par",
        "tim": "wideband/tim/B1937+21_PINT_20230131.wb.tim",
        "noise": "wideband/noise/B1937+21.wb.pars.txt",
        "config": "wideband/config/B1937+21.wb.yaml",
        "dmx": "wideband/dmx/B1937+21_dmxparse.wb.out",
        "correlation": (
            "correlations/wideband/B1937+21_PINT_20230131.wb.correlation.txt"
        ),
    }
    archive = tmp_path / "test.tar.gz"
    selected: dict[str, dict[str, object]] = {}
    with tarfile.open(archive, "w:gz") as bundle:
        for label, relative in members.items():
            name = f"NANOGrav15yr_PulsarTiming_v2.1.0/{relative}"
            payload = f"{label}-payload\n".encode()
            info = tarfile.TarInfo(name)
            if label == symlink_label:
                info.type = tarfile.SYMTYPE
                info.linkname = "../../escape"
                info.size = 0
                bundle.addfile(info)
            else:
                info.size = len(payload)
                bundle.addfile(info, io.BytesIO(payload))
            selected[label] = {
                "archive_member": name,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
    selection = {
        "archive": {
            "bytes": archive.stat().st_size,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        },
        "selected_archive_members": selected,
    }
    return archive, selection


def test_extract_selected_products_writes_only_six_bound_files(tmp_path: Path) -> None:
    archive, selection = _test_archive(tmp_path)
    data_root = tmp_path / "data"
    data_root.mkdir()
    result = extract_selected_products(archive, data_root, selection)
    assert result["status"] == "pass"
    assert result["file_count"] == 6
    assert len(
        [item for item in (data_root / "controlled").rglob("*") if item.is_file()]
    ) == 6
    for item in result["files"]:
        output = data_root / str(item["logical_path"])
        assert hashlib.sha256(output.read_bytes()).hexdigest() == item["sha256"]


def test_extract_selected_products_rejects_selected_symlink(tmp_path: Path) -> None:
    archive, selection = _test_archive(tmp_path, symlink_label="par")
    data_root = tmp_path / "data"
    data_root.mkdir()
    with pytest.raises(RuntimeError, match="not a regular file"):
        extract_selected_products(archive, data_root, selection)


def test_preflight_source_keeps_observed_vector_out_of_scanner() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/pulsar_pilot/pilot2_preflight.py").read_text(
        encoding="utf-8"
    )
    assert "scanner.scan(requested)" in source
    assert "scanner.scan(residual" not in source
    assert '"observed_residual_global_search_executed": False' in source
    assert '"threshold_calibration_executed": False' in source


def test_required_arecibo_clock_cache_entry_is_seeded_without_network(
    tmp_path: Path,
) -> None:
    source = (
        tmp_path
        / "controlled/nanograv15yr-v2.1.0/clock/time_ao.dat"
    )
    source.parent.mkdir(parents=True)
    source.write_bytes(b"controlled-clock\n")
    records = seed_required_clock_cache_entries(tmp_path)
    assert len(records) == 1
    assert records[0]["network_download_bytes"] == 0
    contents = (
        tmp_path
        / "derived/cache/astropy/download/url"
        / records[0]["cache_key"]
        / "contents"
    )
    assert contents.read_bytes() == source.read_bytes()


def test_network_guard_rejects_socket_connections() -> None:
    with _network_disabled(), pytest.raises(RuntimeError, match="Network access"):
        socket.create_connection(("127.0.0.1", 9), timeout=0.01)


def test_corrective_execution_freeze_hashes_are_self_consistent_if_present() -> None:
    root = Path(__file__).resolve().parents[1]
    freeze_path = root / "protocol/PILOT2_PREFLIGHT_EXECUTION_R1_FREEZE_v0.2.1.json"
    if not freeze_path.exists():
        pytest.skip("Corrective execution freeze is created after implementation review")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    assert freeze["observed_periodic_search_authorized"] is False
    for relative, expected in freeze["frozen_sha256"].items():
        actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        assert actual == expected, relative


def test_failed_original_attempt_is_preserved() -> None:
    root = Path(__file__).resolve().parents[1]
    failure = json.loads(
        (root / "results/pilot2/preflight_failed_attempt_v0.2.json").read_text(
            encoding="utf-8"
        )
    )
    assert failure["status"] == "failed_pre_case_implementation_abort"
    assert failure["completed_synthetic_cases"] == 0
    assert failure["observed_periodic_search_executed"] is False
