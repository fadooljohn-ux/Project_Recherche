# Retired source

Modules and tests that no live code path uses. They were moved out of `src/`
and `tests/` on 16 November 2026 as part of Qualification 03 (code audit
finding 4) and are kept for reference only; nothing imports or collects them.

- `retired-source/pulsar_pilot/pilot2_injection_runner_v022.py` … `v027.py` and
  `pilot2_injection_executor_v025.py` … `v027.py`: copy-forward runner and
  executor versions superseded by `pilot2_injection_runner_v028.py`, which
  wraps the unchanged v0.2.3 science executor.
- `retired-tests/`: their six test files.

Historical freezes and receipts that name these files by their old `src/` and
`tests/` paths are unedited. `tools/checks history` runs the recorded
historical tests against the original commits with `git archive`, so it does
not need these copies. Every earlier version remains in Git history; the last
commit with them in place is `1d38a99`.
