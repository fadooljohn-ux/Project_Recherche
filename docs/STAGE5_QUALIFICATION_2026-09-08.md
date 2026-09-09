# Stage 5 formal qualification

Owner authorization, 2026-09-08: “Proceed with stage 5”.

Status: **stage 5 execution and terminal review complete; scientific qualification FAIL**.
Completed 2026-09-08 at 02:40:39 Asia/Taipei. Stage 6 remains pending.

## Release review

The repaired source is unchanged from rehabilitation commit `6608085`.
Current checks: 411 passed, six historical checks deselected, 48.58 seconds.
The already completed environment reproduction and real development runs remain
applicable; they are recorded in the rehabilitation status.

The formal inventory is unchanged: 240 main, 60 phase-reference, 28 annual and
16 boundary cases; 688 primary fits and 35 solver audits. Its digest is
`811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`.
All nine predecessor bindings pass. The locked detection threshold remains
22.485020743823544. No scientific thresholds, case IDs or seeds were changed.

Review covered convergence, solver agreement, signal application, main recovery,
phase-reference error, annual eligibility and resource/accounting gates. Annual
eligibility uses the preserved correlation and absorption limits; numerical
convergence alone is insufficient. The scientific failure is retained.

The supported Intel environment and all local resources match their manifests.
Formal output paths were fresh at launch. The successor execution freeze binds the repaired
source, controls, manifests, input marker and one outer attempt. Legacy execution
freezes and historical records retain their original meaning.

## Execution and evidence

- Attempt: `pilot2-ioc-qualification-20260908-01`.
- Input/inner result root: `../Project Recherche Data/rehabilitation-20260907/`.
- Outer attempt: `../Project Recherche Data/qualification-20260908/runs/pilot2-ioc-qualification-20260908-01/`.
- Release review: `results/rehabilitation/stage5-release-review.json`.
- Freeze: `protocol/PILOT2_IOC_SCIENCE_EXECUTION_FREEZE_v1.json`.

The run completed through `tools/recherche run --manifest` at frozen commit
`0d25e7b31e79a8d103c9ce9743ba07d5f4759ae2`. Total elapsed time was 9,087.749
seconds (2 h 31 min 28 s). Peak memory was 0.879 GiB; data-root size was 0.127 GiB.
All 344 cases, 688 measured primary fits and 35 solver audits completed.

## Scientific disposition

**20 of 21 gates passed.** All fits converged; one solver audit failed. Strong
main controls and triggered-main frequency recovery were 100%. Median triggered
main amplitude bias was 9.406%, within the 10% limit. All 60 phase-reference
controls triggered; their 90th-percentile phase error was 0.07014 radians, within
0.1. Signal-application, annual-eligibility, resource and warning gates passed.

The single failing case is `p2r3-inj-annual-p03-h02-n00`: 365.25 days, injected
amplitude 5 microseconds, phase pi. The augmented and explicit full-covariance
solvers converged but differed as follows:

| Quantity | Difference | Frozen maximum | Result |
|---|---:|---:|---|
| Amplitude, microseconds | 0.01125621 | 0.01000000 | FAIL |
| Phase, radians | 0.0000043154 | 0.001 | PASS |
| Chi-square | 0.00744980 | 0.1 | PASS |

Amplitude exceeded the absolute limit by 0.00125621 microseconds (1.25621 ns).
The case's signal/astrometry correlation is 0.9999702. Poor conditioning near the
year-long period is a plausible contributor, not an established root cause.
The annual mask correctly excludes 365.25 days and admits the sampled 300, 330,
350, 380, 400 and 450-day periods. That exclusion does not waive the separate
solver-audit criterion, so the formal result remains FAIL.

The base calibration file's historical audit count is 29; the current frozen
remediation inventory and runtime contract require 35, and exactly 35 executed.
No thresholds, seeds, case IDs or frozen implementation were changed. No formal
case was retried. No observed-residual search or promotion grade was performed.

## Terminal verification and preservation

- Exact outer file set: all nine artifacts matched sizes and SHA-256 hashes.
- All four science receipt artifacts matched, including ledger, result, mask and health.
- Ledger verification passed for 344 case artifacts and two stage results.
- Every case matched its formal definition, audit selection, execution binding
  and record contract. The saved numerical grading was reproduced without fits.
- All seven annual-mask groups matched their contributing case hashes and
  recomputed correlation/absorption eligibility.
- Execution freeze verification passed; no active attempt or running ledger remains.
- The terminal hard stop is `stage_gate_failure`, not a crash or incomplete run.

Compact receipts: `results/qualification/stage5-terminal-verification.json` and
`results/qualification/stage5-backup-receipt.json`. The original result remains at
`../Project Recherche Data/rehabilitation-20260907/run_records/pilot2/injection-evaluation-v0.2.8.json`.

Backup: `../Recherche Recovery/20260907T223404/stage5-terminal-evidence.tar`.
All 436 archived files were verified by exact file set and content hash, and
source-after hashes matched. Frozen release history is separately preserved in
`stage5-frozen-release.bundle` at the same recovery location.

The bounded next engineering step is to diagnose the two solvers' agreement on
separate annual development fixtures while preserving this result. Scientific
qualification has not passed, so this is not an operational-release approval.
A further formal attempt and stage 6 have not been started. The monitoring
heartbeat is paused after this closeout.
