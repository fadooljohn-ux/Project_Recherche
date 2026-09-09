# Publication provenance — v0.1.0

This is a clean-history publication snapshot of Project Recherche. The original
Git history, unredacted workbook, qualification records and scientific evidence
are preserved separately in a private archive and verified local backup.
The release does not include that archive's Git objects or historical pull requests.

## Transformations

Personal home paths were replaced by repository-relative paths, logical sibling
data/archive paths or `${HOME}`. Historical external-volume locations use
`${RECHERCHE_ARCHIVE_ROOT}` or `${EXTERNAL_VOLUME}`. These labels in archived
JSON/logs are descriptive and are not automatically expanded by the runtime.
Personal commit email metadata is absent from the new Git history. Scientific
authorship and upstream source attribution remain credited.

The workbook preserves its sheets, scientific values, formulas, formatting,
record IDs and historical hashes. Only path-bearing text and its current
publication-edition label changed. Seven obsolete operator-preview screenshots
were omitted; the scientific plots and all four PDF reports are unchanged.
Current operating instructions replace the original chronological agent log.
Historical private-status statements in dated reports describe that reporting
date; the README and agent instructions describe this edition.

Six of 71 scientific Python files had a hardcoded Pixi path in a displayed manual
refresh command. The edition uses `pixi` on PATH in those messages. The remaining
65 files are byte-identical to the original snapshot. Syntax-tree and line-diff
checks verified the six substitutions; no numerical algorithms were changed.
Operator-only edits support portable installation and bookkeeping checks on the
sanitized edition. No searches, calibration or formal qualification were rerun
to produce this release.

## Hashes and reproduction

[`publication-manifest.json`](../publication-manifest.json) records the original
and distributed SHA-256 for each included original file, hashes for new files,
and omitted files. It excludes itself to avoid a circular hash; the Git release
tag and release-asset checksums bind the manifest. Verify distributed files with:

```sh
python3 tools/check_publication.py
```

Original hashes inside historical receipts and workbook rows deliberately remain
unchanged. For a redacted file, those hashes refer to private original bytes,
not this derivative. Use `publication_sha256` to verify the distributed copy.
Do not recompute historical scientific hashes to conceal a mismatch or attempt
to resume a redacted frozen package. New work needs verified acquired inputs,
new preparation/calibration bindings and a distinct output ID.

[`config/publication-source.json`](../config/publication-source.json) is the
current source integrity map used by the fresh-checkout bootstrap. Qualification
02 remains historical evidence for its recorded runtime and inputs; matching
this edition's source map does not transfer qualification to another host.

Raw timing datasets, full runtime resources and large covariance products remain
external. The source reports and [agent guide](../AGENT_README.md) identify the
upstream releases and acquisition/preparation conventions. Publication does not
make the repository a complete restoration of those external inputs.
