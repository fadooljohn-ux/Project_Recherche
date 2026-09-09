from __future__ import annotations

import json
import os
import platform
import resource
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import psutil


def machine_manifest() -> dict[str, object]:
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(Path.cwd())
    return {
        "schema_version": 1,
        "recorded_utc": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "process_machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version.split()[0],
        "logical_cpus": os.cpu_count(),
        "memory_bytes": int(memory.total),
        "workspace_free_bytes": int(disk.free),
        "peak_rss_bytes_at_recording": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }


def write_manifest(path: Path) -> dict[str, object]:
    payload = machine_manifest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
