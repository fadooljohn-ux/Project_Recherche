# Publication provenance — v0.2.0

This is a publication snapshot of Project Recherche at 21 November 2026. The
original Git history, unredacted workbook, qualification records and scientific
evidence are preserved separately in a private archive and a verified local
backup. The public repository does not include that archive's Git objects.
v0.2.0 is one new commit on top of the v0.1.0 commit.

## Transformations

The edition is produced by [`tools/build_publication.py`](../tools/build_publication.py)
from one revision of the private archive (recorded as `original_revision` in
the manifest):

- **Files unchanged since v0.1.0** are taken byte-for-byte from the v0.1.0
  edition.
- **New or changed files** have personal home paths replaced: paths inside the
  repository become repository-relative; sibling folders become
  `../Project Recherche Data`, `../Recherche Recovery` and similar; other home
  paths become `${HOME}`; external volumes become `${EXTERNAL_VOLUME}`. These
  labels in archived JSON and logs are descriptive and are not expanded by the
  runtime. The workbook is rewritten member by member with the same
  replacements; its sheets, values, formulas and record IDs are otherwise
  unchanged.
- **`AGENTS.md`** is replaced by current operating instructions. The
  chronological owner-instruction log stays in the private archive.
- **Added for publication:** `CITATION.cff`, `CONTRIBUTING.md`,
  `RELEASE_NOTES.md`, this document, `tools/check_publication.py`,
  `config/publication-source.json`, `publication-manifest.json` and the
  release check record under `results/release/`.
- **Omitted:** the seven obsolete operator-preview screenshots omitted from
  v0.1.0, and the private archive's `publication/` overlay folder (its files
  are the added ones above).

No numerical algorithm is changed by these steps, and no search, calibration
or qualification was rerun to produce the edition. Personal commit email
metadata is absent from the public history. Scientific authorship and upstream
source attribution remain credited.

Dated reports in `docs/` are historical. Statements in them about private
status, pending approvals, or targets "not yet searched" describe their own
dates; `README.md`, `AGENTS.md` and the "Current state" section of
`AGENT_README.md` describe this edition.

## Hashes and reproduction

[`publication-manifest.json`](../publication-manifest.json) records, for every
included file, the distributed SHA-256 and, where the file exists in the
private archive, the original SHA-256 and whether it was changed. It excludes
itself; the Git tag and release checksums bind it. Verify distributed files
with:

```sh
python3 tools/check_publication.py
```

Hashes inside historical receipts and workbook rows deliberately remain those
of the private original bytes. For a redacted file they do not match the
distributed copy; use `publication_sha256` for that. Do not recompute
historical scientific hashes, and do not attempt to resume a redacted frozen
package. New work needs verified acquired inputs, new preparation and
calibration bindings and a distinct output ID.

[`config/publication-source.json`](../config/publication-source.json) lists the
SHA-256 of the scientific source files in this edition. Qualification 03
remains evidence for its recorded host, runtime and inputs; matching source
hashes does not transfer qualification to another host.

Three tests verify the SHA-256 of files that redaction changes (the
environment binding manifest and two pilot 2 execution-gate fixtures). They
pass on the private archive and cannot pass on redacted bytes, so the test
suite deselects exactly those three when `publication-manifest.json` is
present; they are listed with the reason in `tests/publication_state.json`.

Raw timing data sets, runtime resources, periodogram arrays and large
covariance products are external. The source reports and the
[agent guide](../AGENT_README.md) identify the upstream releases and the
acquisition and preparation conventions.
