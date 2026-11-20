# Operational release, 2026-11-16

Owner instruction: refresh the recovery baseline before requalification.

**Status: PASS as a restore point. It supersedes
`../Recherche Releases/operational-20260908/`, which restores the old checkout
path and is retained.**

The package is `../Recherche Releases/operational-20261116/` (425 MB):

| File | Content |
|---|---|
| `recherche.bundle` | All 61 refs of this repository at `3e39ede`. |
| `publication.bundle` | All refs of `../Project Recherche Publication`, including 24 commits on `codex/atlas-binary-pilot-20260909` that are on no remote. |
| `runtime.tar.gz` | `.pixi` and `.agent-venv` as rebuilt at this checkout. |
| `pixi` | The Pixi 0.62.2 executable. |
| `inputs.tar` | The admitted inputs of `operational-20260908`, written by `tools/recherche backup` with its receipt. |
| `environment-binding-20261116-data.tar` | The B1257 compatibility repeat and comparisons. |
| `RELEASE.json`, `SHA256SUMS` | Release record and checksums. |

It also carries the operator guide, the binding and audit reports, the
relocation link list, and the `doctor` and `agent_setup --check` outputs.

## Verification

- Both bundles pass `git bundle verify` and contain their checkout's HEAD.
- `runtime.tar.gz` and `inputs.tar` were extracted to a temporary directory and
  compared with the live copies: 23,055 runtime files, 1,383 links and 41 input
  files, with no differences.
- `doctor` PASS with the 16 November binding; 457 tests passed, 8 deselected.

## Limits

- The runtime embeds this checkout path, so it restores only at
  `.`. The
  restored copy was compared, not executed.
- The package sits on the same disk as the project. It protects against a bad
  source change, not against loss of the disk.
- `../Project Recherche Data` as a whole (16 GB) was not re-archived.
- CI has not completed a run: GitHub refused both attempts for account billing.
