# Project Recherche operational rehabilitation roadmap

Accepted 2026-09-07. The owner authorized stages 1–4, including routine repairs,
offline setup, and real development-fixture execution. On 2026-09-08 the owner
also authorized stage 5 and subsequently stage 6: “Proceed with stage 6”.
Stages 1–6 are complete for the qualified local workflow. The subsequently
authorized first B1937+21 observed search is complete with NO_TRIGGER. Additional
searches require their own owner-directed scope.

This is the current prospective roadmap. It supersedes earlier engineering
sequencing and development-attempt restrictions within stages 1–4. Historical
documents, formal results, scientific thresholds, and formal case inventories
retain their original meaning. A development run is not formal qualification.

Operational status means the owner can verify the installation, launch an
approved workload, inspect meaningful progress, stop it, and retrieve a complete,
reproducible result with verified backup.

## Stages

1. **Recoverable baseline.** Preserve repository and Git history, identify code,
   configuration and data locations, and record the current state. Finish with
   a restored, hash-verified recovery copy and an unambiguous starting point.
2. **Rehabilitate the active application.** Establish one supported command path,
   repair demonstrated defects, separate historical verification from current
   tests, and reduce version coupling where it obstructs maintenance. Finish
   with coherent current tests and specific, reproducible remaining blockers.
3. **Self-contained runtime.** Provision Recherche's dedicated APFS location,
   verify required inputs and offline resources, and reproduce the pinned
   environment. Finish with real B1937+21 context construction offline and a
   verified input backup/restore. Read historical Recherche sources without
   changing shared-drive mounts or interfering with Project Trammel.
4. **Real development integration.** Use separate development case IDs and seeds
   for a small representative ordinary, annual, boundary and solver-audit
   workload through the actual conductor, adapter, scientific functions, ledger
   and output generation. Diagnose and repair ordinary failures, then rerun
   development fixtures as needed. Inspect actual numerical output and exercise
   interruption. Development results do not count toward formal qualification
   and do not justify tuning its thresholds.
5. **Formal qualification — qualification 02 PASS, 2026-09-08.** Review scientific controls,
   freeze the repaired release, and execute the approved 344-case run with
   terminal inspection and reporting. Evaluate complete scientific and
   operational evidence. Preserve a scientific failure rather than rerunning
   or retuning until it passes.
6. **Operational release — complete, 2026-09-08.** Package the environment and
   commands, provide a concise operator guide, validate on the intended host,
   and establish backup and maintenance procedures. The accepted installation
   must operate without reconstructing development history or repairing caches.

## Initial repair priorities

- Distinguish process liveness, progress and the last completed checkpoint.
- Check resource limits during execution and document their enforcement bounds.
- Derive case, fit and audit accounting from actual execution.
- Share grading/validation functions when current code depends on old runners;
  trace dependencies before removing any executable path.
- Give current tests and historical release checks separate named commands.

## Working rules

Each test must establish a scientific property, cover an observed defect, or
verify necessary operational behavior. Run affected checks after repairs and
the current release suite before freezing. Broaden/repeat only when changes or
unresolved evidence justify it. Avoid a replacement framework or cosmetic
rewrite. Preserve existing historical evidence; keep development records in a
new namespace. Stages 1–4 are one engineering scope. Changes to scientific
method, destructive actions, materially expanded scope, formal qualification,
and observed-data search require a new owner decision.

## Recovery anchor

- Original commit: `750a0b4239f22a2fc10bd7039f8b376236b1692a`.
- Working branch: `codex/recherche-rehabilitation-20260907`.
- Recovery directory: `../Recherche Recovery/20260907T223404/`.
- `repository.tar` preserves 1,848 files including Git history; its restored
  files matched every recorded SHA-256 and restored `git fsck --full` passed.
- Rebuildable `.pixi`, `.venv`, pytest/ruff and bytecode caches are excluded;
  dependency declarations and locks are included. Existing environments remain
  available. Scientific input backup is stage 3.

Progress and final evidence belong in `REHABILITATION_STATUS_2026-09-07.md`.

Owner clarification during implementation: avoid design, testing and safety
spirals; prioritize coding stability, rigidity and long-term maintenance.
Diagnose problems, repair them and continue within the authorized stages.

## Stage 5 closeout, 2026-09-08

The approved 344-case run and terminal review are complete. Execution was stable;
20 of 21 gates passed. One 365.25-day solver audit exceeded the frozen amplitude
agreement limit (0.01125621 versus 0.01000000 microseconds). The formal FAIL is
preserved with verified artifacts and backup. See
[the terminal report](STAGE5_QUALIFICATION_2026-09-08.md).

Next: bounded development diagnosis of annual solver agreement, using separate
fixtures. No threshold relaxation or automatic formal rerun. Stage 6 remains
pending; this result does not establish scientific qualification.

## Targeted diagnosis, 2026-09-08

[Annual solver diagnosis](ANNUAL_SOLVER_DIAGNOSIS_2026-09-08.md) identified and
repaired a signal/Jacobian mismatch. An audit-stopping change was tested and
rejected because it regressed the second annual fixture. Numerical consistency
in the annual weakly constrained direction remains the next engineering issue;
a simple stopping-rule change is not sufficient. Stage 6 remains pending.

## Precision repair and qualification 02, 2026-09-08

Spin-phase evaluation now preserves fractional turns before conversion to PINT.
Both annual development fixtures and the ordinary control pass with unchanged
solver settings and limits. The 418 current tests pass. Readiness passed for the
owner-authorized second qualification on a fresh data root; the first formal
FAIL remains preserved. See [the current attempt](QUALIFICATION_02_2026-09-08.md)
and [repair evidence](SOLVER_PRECISION_REPAIR_2026-09-08.md). Stage 6 remains pending.

## Qualification 02 closeout, 2026-09-08

Qualification 02 passed all 21 unchanged gates at frozen commit `f3c93ef`.
All 344 cases, 688 measured primary fits and 35 solver audits completed in
3 h 16 min 31 s, without a hard stop. The previously failing annual case now has
amplitude disagreement 0.000172853 microseconds against the same 0.01 limit.
The 365.25-day period remains excluded by the original annual eligibility rule.

Terminal inventories, ledger, case contracts, numerical grading and annual-mask
source hashes/eligibility were verified. Results and the original qualification
01 FAIL are preserved; the new terminal archive has verified content hashes.
See [qualification 02](QUALIFICATION_02_2026-09-08.md). The monitoring heartbeat
is paused after closeout. The next roadmap step is stage 6 operational packaging
and operator handoff; stage 6 and observed-data searches remain unstarted and
outside the current authorization.

## Stage 6 operational release, 2026-09-08

Stage 6 is complete under the owner's “Proceed with stage 6” authorization.
The package includes source/history, the Intel runtime, Pixi, admitted inputs,
operator instructions and verified receipts. Clean locked installation and an
actual runtime-archive restore passed on this Mac at the canonical checkout path.
The ordinary restored-input development case passed (two fits, one solver audit);
all 71 qualified source files and both formal terminal records remain unchanged.

The Python executable embeds its install prefix: this release supports the
canonical path and qualified host. A different location or OS requires a new
environment binding. The archive allows offline restore without a package cache.
See [the operational release](OPERATIONAL_RELEASE_2026-09-08.md) and
[operator guide](OPERATOR_GUIDE.md). No further qualification or observed search
was run. The next scientific workload requires its own scope; no run is active.

## First observed-search preparation, 2026-09-08

The owner authorized connecting the B1937+21 observed-search entry point to the
repaired runtime and preparing the first search with the existing threshold and
qualification 02 annual mask. See [the first-search scope](B1937_FIRST_OBSERVED_SEARCH_2026-09-08.md).
This is preparation; the observed residual vector remains unsearched. Automated
calibration for future pulsar ingestion is deferred until after this run is complete.

## First observed-search closeout, 2026-09-08

The owner authorized “Launch”. The prepared B1937+21 search completed once in
8.494 seconds with **NO_TRIGGER**. The strongest eligible periodogram peak was
138.38135 days, statistic 12.75670, below the fixed threshold 22.48502. No candidate
was generated. Accounting: one scan, zero primary fits and zero solver audits.
The conditional fits were not needed. Terminal hashes, package bindings, selected
peak, accounting and offline resources were verified, and evidence was backed up.
See [the observed report](B1937_FIRST_OBSERVED_SEARCH_2026-09-08.md). No run remains
active and the monitor is paused. Future-target calibration automation remains a
separate deferred expansion; it has not been automatically started.

## B1257+12 benchmark closeout, 2026-09-08

The owner authorized the bounded route through acquisition, target calibration,
two-large-planet recovery, inner-planet attempt, and published comparison.
Public I-LOFAR TOAs yielded periods 66.6218 +/- 0.1002 and 98.0558 +/- 0.1602 days.
The 25.262-day planet did not trigger and was recovered in 0/256 injections at
its published 3-us amplitude. Both larger planets were recovered in 31/32
separate synthetic cases using this sampling. The bounded route is complete
with two observed recoveries and an explicit sensitivity limitation. Evidence:
[B1257+12 benchmark](B1257_BENCHMARK_2026-09-08.md). Higher-precision timing data
are needed to demonstrate recovery of all three. General ingestion/calibration
automation remains deferred. B1937's qualification and result are unchanged.

The owner directed that the project remain private on 2026-09-08. Publication
or sharing requires explicit owner authorization. The completed operational
release and recovery benchmark do not establish publication readiness.

## Automatic calibration, authorized 2026-09-08

The owner authorized automatic calibration, superseding the earlier deferral.
The implementation provides prepared-data ingestion, reusable target profiles,
automatic thresholds, identifiability masks and sensitivity curves, with cached
results bound to data/model/noise/grid/code inputs. Both existing target formats
are supported. See [the calibration guide](AUTOMATIC_CALIBRATION_2026-09-08.md).
This scope uses existing data for engineering verification and does not depend
on finding more known planets or beginning a public-data survey.

## Five additional companions, 2026-09-08

The owner authorized the five systems in IMG_5521.jpg. Public-data recovery
completed for J1719-1438, J2322-2650 and J1544+4937, conditional on published
pulse connection and targeted period windows. M62H and B1620-26 require suitable
timing data; they have not been searched and are not passed tests. The owner's
five-target condition for going public is unmet, so Recherche remains private.
See [results and required inputs](FIVE_COMPANION_BENCHMARK_2026-09-08.md).

## First bounded original-search batch, 2026-09-08

The owner subsequently authorized the four-step MPTA batch: inventory prior
search coverage, choose ten targets, apply published-noise calibration and run
one 30–400-day search per target. All four steps are complete. Ten observed
searches returned NO_TRIGGER, with no candidates or execution failures.
Selection, numerical verification, conditional sensitivity and preservation:
[First MPTA batch](MPTA_BATCH01_2026-09-08.md). Recherche remains private.
