from __future__ import annotations

import contextlib
import json
import shutil
import tarfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from .config import PilotConfig
from .provenance import hash_file

ARCHIVE_PREFIX = "NANOGrav15yr_PulsarTiming_v2.1.0/"


def is_selected_member(name: str, target: str = "J1744-1134") -> bool:
    if not name.startswith(ARCHIVE_PREFIX):
        return False
    relative = name.removeprefix(ARCHIVE_PREFIX)
    if relative == "README" or relative.startswith("clock/"):
        return True
    exact = {
        "wideband/README.wideband",
        f"wideband/par/{target}_PINT_20230131.wb.par",
        f"wideband/tim/{target}_PINT_20230131.wb.tim",
        f"wideband/config/{target}.wb.yaml",
        f"wideband/dmx/{target}_dmxparse.wb.out",
        f"wideband/noise/{target}.wb.pars.txt",
        "correlations/wideband/README.wb_correlations",
        f"correlations/wideband/{target}_PINT_20230131.wb.correlation.txt",
    }
    return relative in exact


def download_archive(config: PilotConfig, data_root: Path) -> dict[str, object]:
    raw_dir = data_root / "raw" / "zenodo-16051178"
    raw_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_dir / config.archive_name
    partial = destination.with_suffix(destination.suffix + ".partial")
    if destination.exists():
        return verify_archive(config, destination)
    request = urllib.request.Request(config.archive_url, headers={"User-Agent": "Project-Recherche/0.1"})
    downloaded = 0
    with contextlib.closing(urllib.request.urlopen(request, timeout=60)) as response:
        length = response.headers.get("Content-Length")
        if length and int(length) > config.max_download_bytes:
            raise RuntimeError("Remote Content-Length exceeds the frozen 1 GB download cap")
        with partial.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                downloaded += len(chunk)
                if downloaded > config.max_download_bytes:
                    raise RuntimeError("Download exceeded the frozen 1 GB cap")
                handle.write(chunk)
    partial.replace(destination)
    destination.chmod(0o444)
    return verify_archive(config, destination)


def verify_archive(config: PilotConfig, path: Path) -> dict[str, object]:
    size = path.stat().st_size
    if size > config.max_download_bytes:
        raise RuntimeError("Archive exceeds the frozen 1 GB cap")
    md5 = hash_file(path, "md5")
    sha256 = hash_file(path, "sha256")
    if md5 != config.published_md5:
        raise RuntimeError(f"Published MD5 mismatch: expected {config.published_md5}, got {md5}")
    return {"path": path, "bytes": size, "md5": md5, "sha256": sha256}


def extract_target(config: PilotConfig, data_root: Path) -> dict[str, object]:
    archive = data_root / "raw" / "zenodo-16051178" / config.archive_name
    verify_archive(config, archive)
    destination = data_root / "controlled" / "nanograv15yr-v2.1.0"
    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[dict[str, object]] = []
    with tarfile.open(archive, mode="r:gz") as bundle:
        selected = [member for member in bundle.getmembers() if is_selected_member(member.name)]
        if not selected:
            raise RuntimeError("No controlled target members were found in the archive")
        for member in selected:
            if member.isdir():
                continue
            relative = Path(member.name.removeprefix(ARCHIVE_PREFIX))
            output = (destination / relative).resolve()
            if destination.resolve() not in output.parents:
                raise RuntimeError(f"Unsafe archive member path: {member.name}")
            source = bundle.extractfile(member)
            if source is None:
                raise RuntimeError(f"Could not read archive member: {member.name}")
            output.parent.mkdir(parents=True, exist_ok=True)
            with source, output.open("wb") as handle:
                shutil.copyfileobj(source, handle)
            output.chmod(0o444)
            extracted.append(
                {
                    "logical_path": output.relative_to(data_root).as_posix(),
                    "bytes": output.stat().st_size,
                    "sha256": hash_file(output, "sha256"),
                }
            )
    required_suffixes = (".wb.par", ".wb.tim")
    for suffix in required_suffixes:
        if not any(str(item["logical_path"]).endswith(suffix) for item in extracted):
            raise RuntimeError(f"Required target input missing after extraction: {suffix}")
    record = {
        "schema_version": 1,
        "recorded_utc": datetime.now(UTC).isoformat(),
        "dataset": "nanograv15yr-v2.1.0",
        "target": config.target_name,
        "files": extracted,
    }
    record_path = data_root / "run_records" / "pilot0_extraction.json"
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
