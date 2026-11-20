# Code audit disposition, 2026-11-16

Audit: `results/audits/Project_Recherche_Code_Audit_2026-10-29.pdf` (HEAD 7ed0e52).
Owner instruction: proceed with the audit fixes; defer requalification and new
science. No scientific run was made for this change, and `src/` is untouched:
all 71 qualified source files still match the qualification 02 lock.

| # | Finding | Disposition |
|---|---|---|
| 1 | Integrity checks written as `assert` | **Fixed.** All 97 `assert` statements in `tools/` are now `require(...)` from `tools/recherche_common.py`, which raises `IntegrityError` and is not removed by `python -O`. `IntegrityError` subclasses `AssertionError`, so existing handlers behave as before. A test fails if any tool uses `assert` again. |
| 2 | Workbook updater borrows the Codex Node runtime | **Fixed.** The hash-pinned `openpyxl` backend is the default and single supported path. The Node updater runs only with `RECHERCHE_WORKBOOK_BACKEND=codex-node`, for its legacy preparation and candidate modes. The backends were not made cell-identical: they write different work-log record IDs by design. |
| 3 | Union bound sets every threshold | **Studied and not adopted** (owner decision, 17 November 2026). An empirical per-search threshold was implemented and measured on 40 saved profiles: median amplitude gain 1.3% (0.4–3.3%), not the audit's 9%, which compared against the quantile at alpha rather than alpha/K. It needed about 25 times more null draws, so the rule was reverted and the union bound stays. Record: `results/research/threshold-study-20261116/summary.json`. |
| 4 | Copy-forward runner versions | **Fixed and requalified.** Runner v0.2.2–v0.2.7 and executor v0.2.5–v0.2.7 moved to `archive/retired-source/`; Qualification 03 passed 21/21 on the remaining 62 files. |
| 5 | Stale `.venv`, duplicated dependency specs | **Partly done.** A test keeps the `pyproject.toml` and `pixi.toml` ranges equal. Both files are hash-bound by the frozen environment manifest, so the stale `pixi.toml` description and the duplication stay until requalification. The owner deleted the stale `.venv` on 16 November 2026. |
| 6 | No CI | **Added.** `.github/workflows/tests.yml` installs `pixi.lock` on an Intel macOS runner, runs `agent_setup.py --install` and the suite. It is manual-only (`workflow_dispatch`) on the owner's instruction and has not yet completed a run: the first attempt was refused for account billing. `doctor` is not run there because its host binding is specific to the owner's Mac. |
| 7 | Hard-coded sibling data paths | **Fixed, with one exception.** Tools read `RECHERCHE_DATA_ROOT` and `RECHERCHE_RECOVERY_ROOT` through `tools/recherche_common.py`, defaulting to the sibling folders, and reject a value that is not an existing absolute directory. `tools/target_calibration.py` keeps its own default cache path because its file hash is part of every calibration cache key; pass `--cache` to relocate it. The 13 unused imports and 4 unused locals were removed in a follow-up commit. |

## Consequences

- The edited tools have new file hashes. Execution freezes written before this
  change record the old `code_sha256`, so they cannot be re-verified or resumed
  against the current files. All of them were already consumed.
- `tools/target_calibration.py` is unchanged, so saved calibration caches keep
  their implementation identity.
- Verification: 457 tests passed, 8 deselected; `tools/recherche doctor` PASS
  with 21 inputs and 10 resources; the bounded workbook check
  (`tools/check_agent_handoff.py`) PASS with the master workbook hash unchanged.
