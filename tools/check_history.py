"""Run historical-state assertions against their recorded Git versions."""

import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from collections import defaultdict
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    cases = json.loads((repo / "tests/historical_state.json").read_text())
    groups = defaultdict(list)
    for node, commit in cases.items():
        groups[commit].append(node)
    failed = 0
    for commit, nodes in groups.items():
        archive = subprocess.check_output(["git", "archive", commit], cwd=repo)
        with tempfile.TemporaryDirectory(prefix="recherche-history-") as temp:
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                tar.extractall(temp, filter="data")
            env = {**os.environ, "PYTHONPATH": str(Path(temp) / "src")}
            print(f"{commit}: {len(nodes)} historical checks", flush=True)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "--tb=short",
                    "-p",
                    "no:cacheprovider",
                    *nodes,
                ],
                cwd=temp,
                env=env,
                check=False,
            )
            failed += result.returncode != 0
    print(
        f"{len(cases)} historical tests accounted for in {len(groups)} Git versions; failed groups: {failed}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
