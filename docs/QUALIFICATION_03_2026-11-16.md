# Qualification 03

Owner authorization, 2026-11-16: "Proceed with requal".

**Status: PASS, 21/21 gates. Completed 2026-11-17T05:56:40Z at frozen commit `01e564f`.**

Qualification 03 repeats the formal 344-case synthetic qualification on the
relocated checkout and the macOS 27.2.1 host. Qualification 01 (FAIL) and
qualification 02 (PASS, 21/21) are preserved with their data roots and records.

## What is unchanged

- Inventory: the same 344 cases and seeds, 688 primary fits and 35 solver audits
  (SHA-256 `811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`).
- Detection threshold 22.485020743823544 from the frozen v0.2.1 threshold lock,
  all 21 gates and their limits, the nine predecessor records, the resource
  manifest, `pixi.lock`, `pixi.toml` and `pyproject.toml`.
- Every remaining source file: 62 of the 71 qualification 02 files, byte for byte.

## What changed

- **Host and checkout.** The environment manifest
  `protocol/PILOT2_RUNTIME_ENVIRONMENT_MANIFEST_QUALIFICATION03.json` was
  generated on this host. It differs from the qualification 02 manifest only in
  its ID, the Python executable hash and the macOS version; all 134 packages,
  critical modules, precision and thread settings are identical.
- **Retired source.** Runner versions v0.2.2 to v0.2.7 and executor versions
  v0.2.5 to v0.2.7 moved to `archive/retired-source/` with their six test files
  (code audit finding 4). No live module imported them. The science executor
  v0.2.3, its v0.2.8 wrapper and the v0.2.8 runner are untouched. The runner
  configuration no longer lists runner v0.2.2 among its implementation paths.
- **Source lock.** `results/qualification/qualification03-readiness.json` lists
  the 62 files; `doctor` and `agent_setup.py --check` now use it.
- **Execution freeze.** `protocol/PILOT2_IOC_SCIENCE_EXECUTION_FREEZE_v1.json`
  binds the new attempt, data-root marker, environment manifest and source. The
  qualification 02 freeze is retained in
  `protocol/archive/qualification02-execution-freeze.json`.

`pixi.toml` and `pyproject.toml` were deliberately not edited. Both are pinned
by the 11 August 2026 v0.2.8 design freeze, a historical record that live
verification still checks; correcting the stale `pixi.toml` description would
mean rewriting that record.

## Readiness

A three-case development solver check ran on this host with the unchanged
qualification 02 source before the retirement: 264 s (287 s on the original
host), all fits converged, all solver audits passed, and all three case records
are numerically identical to the September readiness run.

- Attempt: `pilot2-ioc-qualification-20261116-03`.
- Data: `../Project Recherche Data/qualification-03-20261116/data/` (the 21
  admitted inputs only; no earlier ledger or case output was copied).
- Procedure scripts and receipts: `../Project Recherche Data/qualification-03-20261116/`.

The operational calibration threshold used by observed searches
(`tools/target_calibration.py`) is separate code and is not what this
qualification tests. It keeps the union bound (owner decision, 17 November 2026).

## Result

The formal attempt ran once, from 03:43:33Z to 05:56:40Z on 17 November 2026 UTC
(7,987 s; qualification 02 took 11,791 s on the original host). It completed all
344 cases, 688 primary fits and 35 solver audits with no hard stop, no error and
no failed solver audit. Peak memory was 0.76 GiB.

All 21 gates passed with unchanged limits. The two gates with the least margin
are the same as in qualification 02:

| Gate | Limit | Qualification 02 | Qualification 03 |
| --- | --- | --- | --- |
| Median amplitude bias | <= 0.1 | 0.09407506 | 0.09407504 |
| Phase-reference error, 90th percentile (rad) | <= 0.1 | 0.07013191 | 0.07013190 |

The annual mask is the same: 365.25 d excluded, the other six periods eligible.
Its recorded correlations differ from qualification 02 by less than 5e-10, so
the file hash is new: `8b7ece37fd7c0bb1b01b4a96427d9c33ab7580d7d4414fef49ee8e7b62d6e402`.

## Independent inspection

The qualification 02 inspection scripts were rerun against this attempt
(`inspect_terminal.py`, `inspect_annual_terminal.py` in the working folder):

- 9 outer artifacts and 4 science receipt artifacts match their recorded hashes
  and sizes; the ledger verified all 344 case artifacts and 2 stage results.
- Every case record matched its inventory definition, execution binding and
  record contract; the saved grading was reproduced from the records without fits.
- All seven annual-mask groups matched their contributing case hashes and
  recomputed eligibility. Release-freeze verification passed.
- No observed residual vector was used, no observed periodic scan ran and the
  threshold was not retuned.

## Comparison with qualification 02

`results/qualification/qualification03-comparison-with-qualification02.json`
compares all 344 case records field by field. Every discrete field (triggers,
convergence flags, audit outcomes, counts) is identical. The records are not
bit-identical: floating-point values differ slightly in every case. The largest
differences in recovered quantities are about 1.4e-6 rad in phase and 6e-8
microseconds in amplitude components; the two solver-agreement differences that
show large relative changes are themselves near zero (below 1.3e-5 in chi-square).
These differences did not move any gate value before the eighth decimal place.

## Evidence

- Terminal receipt: `results/qualification/qualification03-terminal-verification.json`.
- Result SHA-256: `41e123da9f84164c44692859046bd8f3d5c96685f4999ec77769b9cf8f193cf8`.
- Archive (404 files): `../Recherche Recovery/20260907T223404/qualification03-terminal-evidence.tar`,
  SHA-256 `d73550609c08a328f901ec700180c2c2cbdc1fc33a53ff89389e88f167b4ac6b`.
- Backup receipt: `results/qualification/qualification03-backup-receipt.json`.
- Frozen source/history: `../Recherche Recovery/20260907T223404/qualification03-frozen-release.bundle`.

The archive's exact file set, content hashes and source-after hashes were
verified. The attempt is consumed; it cannot be resumed or rerun. Qualification
01 and 02 data roots were not written to.
