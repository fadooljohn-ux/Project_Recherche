"""Verify the committed release snapshot without running scientific calculations."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HOST_PATH = re.compile(rb"/(?:Users|home)/[^/\s\"']+")


def main():
    manifest = json.loads((ROOT / 'publication-manifest.json').read_text())
    failures = []
    for name, record in manifest['files'].items():
        path = ROOT / name
        if not path.is_file():
            failures.append(name + ': missing')
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record['publication_sha256']:
            failures.append(name + ': differs from release snapshot')
        payloads = [data]
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                payloads.extend(archive.read(n) for n in archive.namelist())
        if any(HOST_PATH.search(value) for value in payloads):
            failures.append(name + ': local home path found')
    print(json.dumps({'status': 'FAIL' if failures else 'PASS',
                     'release': manifest['release'], 'files_checked': len(manifest['files']),
                     'failures': failures, 'scientific_runs_executed': 0}, indent=2))
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
