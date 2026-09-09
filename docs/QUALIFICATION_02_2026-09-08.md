# Qualification 02

Owner authorization, 2026-09-08: “Proceed with steps 1-4. If readiness it determined
to meet criteria proceed with another qualification run.”

**Status: execution complete; scientific qualification PASS, 21/21 gates.**
Completed 2026-09-08 at 14:41:19 Asia/Taipei (06:41:19 UTC). This was a new
attempt on a separate data root. The original formal FAIL, its data and frozen
release remain preserved. Stage 6 and observed-data searches are not authorized.

- Attempt: `pilot2-ioc-qualification-20260908-02`.
- Data: `../Project Recherche Data/qualification-20260908-02/data/`.
- Outer run: `../Project Recherche Data/qualification-20260908-02/runs/pilot2-ioc-qualification-20260908-02/`.
- Inventory: the same fixed 344 cases and seeds; 688 primary fits and 35 solver audits.
- Inventory SHA-256: `811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`.
- Detection threshold: unchanged at 22.485020743823544; all other criteria unchanged.
- Repair/readiness: [spin-phase precision record](SOLVER_PRECISION_REPAIR_2026-09-08.md).

The new input root contains only the 21 admitted inputs and dedicated metadata.
Copy and source-after hashes match. The input archive was verified by its exact
file set and content hashes. No previous formal ledger or case outputs were copied.

The current execution freeze binds this repaired source, the pinned environment,
resource manifests, the new root marker and this one attempt. The first execution
freeze is retained in `protocol/archive/qualification01-execution-freeze.json`
and its original Git release.

## Terminal result

Frozen release: `f3c93efdfbc802ce8bf86a3b957ce493d8b7ef27`.
All 344 cases, 688 measured primary fits and 35 solver audits completed.
Elapsed time: 11,791.332 seconds (3 h 16 min 31 s). Peak memory: 0.786 GiB;
data-root size: 0.127 GiB. There was no hard stop, retry or threshold retuning.

All fits converged and all solver audits passed. Strong-control recovery and
triggered-main frequency recovery were 100%. Median triggered-main amplitude
bias was 9.408%, within the 10% limit. All 60 phase-reference controls triggered;
their 90th-percentile phase error was 0.070132 radians, within 0.1.

The previously failing case, `p2r3-inj-annual-p03-h02-n00`, now passes:

| Quantity | Difference | Unchanged maximum |
|---|---:|---:|
| Amplitude, microseconds | 0.000172853114 | 0.01 |
| Phase, radians | 0.0000000477604 | 0.001 |
| Chi-square | 0.000067862695 | 0.1 |

The annual mask still excludes 365.25 days because its signal/astrometry
correlation is 0.9999702. The sampled 300, 330, 350, 380, 400 and 450-day periods
remain eligible. Solver agreement does not establish identifiability at one year.

## Verification and preservation

All nine outer artifacts and four science receipt artifacts matched their sizes
and hashes. Ledger verification covered 344 cases and two stage results. Every
case matched its inventory definition, execution binding and record contract;
the saved numerical grading was reproduced without fits. All seven annual-mask
groups matched contributing case hashes and recomputed eligibility. Release
freeze verification passed. The ledger is inactive with no active attempt.

The first qualification's four science receipt artifacts were rechecked and
remain byte-for-byte unchanged. No observed-residual search or promotion grade
was executed.

- Terminal receipt: `results/qualification/qualification02-terminal-verification.json`.
- Result SHA-256: `dcc9498190c364f88d923e87574fa44d6333be376caafcadcb878569120ee3a8`.
- Archive: `../Recherche Recovery/20260907T223404/qualification02-terminal-evidence.tar`.
- Backup receipt: `results/qualification/qualification02-backup-receipt.json`.
- Frozen source/history: `../Recherche Recovery/20260907T223404/qualification02-frozen-release.bundle`.

The archive's exact file set, content hashes and source-after hashes were verified.
The 30-minute monitoring heartbeat is paused after terminal closeout. Stage 5 is
complete with a passing qualification. Stage 6 operational packaging and operator
handoff is next; stage 6 and observed-data searches have not been started.
