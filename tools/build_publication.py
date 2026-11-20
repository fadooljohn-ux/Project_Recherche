"""Build the public (redacted) edition of the repository from one private revision.

    python3 tools/build_publication.py --publication ../"Project Recherche Publication" --release v0.2.0 --date 2026-11-21

The private revision is HEAD of this checkout. The publication checkout must be
on a branch whose parent is the previous edition (ref `--base`, default `main`)
and have a clean working tree. This script replaces its working tree; it does
not commit, tag or push. It runs no scientific calculation.

Rules (see publication/docs/PUBLICATION_PROVENANCE.md):
  * a file whose private bytes equal the `original_sha256` recorded for it in
    the previous edition's manifest is copied from the previous edition;
  * any other file has personal home paths replaced (text files directly, zip
    containers such as the workbook member by member);
  * `AGENTS.md` and the files under `publication/` are overlay files;
  * a file that still contains a home path afterwards stops the build.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
USER = rb"/(?:Users|home)/[A-Za-z0-9._-]+"
WORKSPACE = USER + rb"/Documents/(?:ChatGPT|Project Recherche)"
SIBLINGS = (b"Project Recherche Data", b"Project Recherche Gate4 Evidence", b"Project Recherche Publication",
            b"Recherche Recovery", b"Recherche Releases")
RULES = (
    [(re.compile(WORKSPACE + rb"/" + re.escape(name)), b"../" + name) for name in SIBLINGS]
    + [(re.compile(WORKSPACE + rb"/Project Recherche/"), b""),
       (re.compile(WORKSPACE + rb"/Project Recherche(?![A-Za-z0-9 ])"), b"."),
       (re.compile(WORKSPACE), b".."),
       (re.compile(USER + rb"/\.pixi/bin/pixi"), b"pixi"),
       (re.compile(USER), b"${HOME}"),
       (re.compile(rb"/Volumes/[A-Za-z0-9._-]+"), b"${EXTERNAL_VOLUME}")])
HOST_PATH = re.compile(rb"/(?:Users|home)/[^/\s\"']+")
OVERLAY = "publication"
GENERATED = ("publication-manifest.json", "config/publication-source.json")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def redact(data):
    for pattern, replacement in RULES:
        data = pattern.sub(replacement, data)
    return data


def redact_file(name, data):
    """Redacted bytes of one file. Zip containers are rewritten member by member, order and compression kept."""
    if not HOST_PATH.search(data) and not zipfile.is_zipfile(io.BytesIO(data)):
        return data
    if zipfile.is_zipfile(io.BytesIO(data)):
        source = zipfile.ZipFile(io.BytesIO(data))
        if not any(HOST_PATH.search(source.read(n)) for n in source.namelist()):
            return data
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as target:
            for info in source.infolist():
                clone = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                clone.compress_type, clone.external_attr = info.compress_type, info.external_attr
                target.writestr(clone, redact(source.read(info.filename)))
        return out.getvalue()
    return redact(data)


def contains_host_path(data):
    payloads = [data]
    if zipfile.is_zipfile(io.BytesIO(data)):
        archive = zipfile.ZipFile(io.BytesIO(data))
        payloads += [archive.read(n) for n in archive.namelist()]
    return any(HOST_PATH.search(p) for p in payloads)


def git(root, *args, text=False):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=text).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--publication", type=Path, required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--base", default="main", help="ref of the previous edition in the publication checkout")
    args = parser.parse_args()
    pub = args.publication.resolve()
    if git(REPO, "status", "--porcelain", text=True).strip() or git(pub, "status", "--porcelain", text=True).strip():
        raise SystemExit("Both checkouts must be clean")
    revision = git(REPO, "rev-parse", "HEAD", text=True).strip()
    previous = json.loads(git(pub, "show", args.base + ":publication-manifest.json"))
    names = [n for n in git(REPO, "ls-files", "-z").decode().split("\0") if n]
    files, manifest, omitted, reused, changed = {}, {}, dict(previous.get("omitted", {})), 0, 0
    for name in names:
        if name.startswith(OVERLAY + "/") or name == "AGENTS.md":
            continue
        if name in omitted:
            continue
        original = (REPO / name).read_bytes()
        record = previous["files"].get(name, {})
        if record.get("original_sha256") == sha(original):
            data = git(pub, "show", f"{args.base}:{name}")
            reused += 1
        else:
            data = redact_file(name, original)
        if contains_host_path(data):
            raise SystemExit("Home path remains after redaction: " + name)
        files[name] = data
        manifest[name] = {"publication_sha256": sha(data), "original_sha256": sha(original),
                          "changed_for_publication": data != original}
        changed += data != original
    overlay = REPO / OVERLAY
    for path in sorted(p for p in overlay.rglob("*") if p.is_file()):
        name = path.relative_to(overlay).as_posix()
        data = path.read_bytes()
        if contains_host_path(data):
            raise SystemExit("Home path in overlay file: " + name)
        files[name] = data
        manifest[name] = {"publication_sha256": sha(data)}
        if (REPO / name).is_file() and name == "AGENTS.md":
            manifest[name].update(original_sha256=sha((REPO / name).read_bytes()), changed_for_publication=True)
    source = {n: sha(files[n]) for n in sorted(files) if n.startswith("src/pulsar_pilot/") and n.endswith(".py")}
    files["config/publication-source.json"] = (json.dumps(
        {"release": args.release, "qualification_transferred": False, "source_sha256": source}, indent=2) + "\n").encode()
    manifest["config/publication-source.json"] = {"publication_sha256": sha(files["config/publication-source.json"])}
    # Replace the working tree of the publication checkout.
    for name in [n for n in git(pub, "ls-files", "-z").decode().split("\0") if n]:
        (pub / name).unlink()
    for name, data in files.items():
        path = pub / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if (REPO / name).is_file():
            shutil.copymode(REPO / name, path)
        elif (overlay / name).is_file():
            shutil.copymode(overlay / name, path)
    (pub / "publication-manifest.json").write_text(json.dumps(
        {"release": args.release, "date": args.date, "original_revision": revision,
         "previous_release": previous["release"], "manifest_self_excluded": True,
         "files": dict(sorted(manifest.items())), "omitted": omitted}, indent=2) + "\n")
    print(json.dumps({"release": args.release, "original_revision": revision, "files": len(files),
                      "reused_from_previous_edition": reused, "changed_for_publication": int(changed),
                      "omitted": len(omitted)}, indent=1))


if __name__ == "__main__":
    main()
