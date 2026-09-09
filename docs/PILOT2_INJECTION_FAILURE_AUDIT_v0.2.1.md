# Pilot 2 B1937+21 injection failure audit v0.2.1

## Outcome

The v0.2.1 injection stage remains an authoritative **FAIL / HARD STOP**. All
10,284 cumulative case artifacts and all five stage-result artifacts verify
against the final ledger. The threshold lock remained unchanged, all 284
injection cases completed exactly once, and no observed periodic search or
promotion grade ran.

The terminal scorecard contained three failed gates. This audit finds one valid
scientific-performance failure and two grading implementation defects:

1. **Phase recovery is a valid hard-gate failure.** The p90 phase error was
   0.213672 radians against the frozen 0.1-radian maximum.
2. **The TOA-application grade is invalid and its correct result is
   indeterminate from retained JSON.** The executor again substituted the
   uncentered residual-target diagnostic for the frozen TOA-adjustment metric,
   despite the earlier v0.2.1 preflight correction. It retained only the
   conflated maximum.
3. **The warning grade is an implementation false failure.** Both flagged lines
   are the exact controlled Arecibo `time_ao.dat` override already frozen as an
   expected warning during preflight. No unexpected warning remains after that
   existing disposition is applied.

Correcting the warning classification does not promote the target. The valid
phase failure alone requires the hard stop, and the correct TOA-application
gate cannot be presumed to pass.

## Integrity and scope controls

| Control | Audit result | Evidence |
|---|---:|---|
| Cumulative case ledger | PASS | 10,284 of 10,284 artifacts verified; zero mismatch |
| Stage-result ledger | PASS | 5 of 5 artifacts verified; zero mismatch |
| Injection inventory | PASS | 240 main + 28 annual + 16 boundary = 284 |
| Checkpoints | PASS | 411 cumulative checkpoints |
| Threshold immutability | PASS | One value in all injection records; lock SHA-256 unchanged |
| Execution binding | PASS | One binding across all 284 records |
| Fit convergence | PASS | 284 of 284 ordinary fits and 284 of 284 joint fits |
| Solver cross-checks | PASS | 29 of 29; maximum solver phase difference 0.0001506 radians |
| Observed-search boundary | PASS | No observed residual vector used; no observed scan executed |
| Audit mutation boundary | PASS | No new case, rerun, retune, promotion, or observed-data access |

The authoritative terminal result is bound to SHA-256
`06cf10aa00231ecac05abccbe491b21c074371d749f8cc88dccff8cf034fba8c`.
The final cumulative ledger is bound to SHA-256
`cb13ffc749cd4bec1ab41dfcfe056850507d52546c9425e2b4fbfff49c1bc621`.

## Failed-gate diagnosis

### 1. Phase-error p90 — valid substantive failure

The grader uses the main injections that crossed the locked detection
threshold. Of 111 triggered main cases, 38 (34.23%) exceeded 0.1 radians. The
median was 0.070374 radians, p90 was 0.213672 radians, and the maximum was
0.397091 radians.

This is not explained by failed fits or disagreement between solvers:

- all 284 ordinary and joint fits converged;
- frequency recovery was 100%;
- all 29 full-covariance audits passed; and
- the maximum primary-versus-audit phase difference was only 0.0001506
  radians.

The issue also persists above the weakest detections. All 60 strongest-amplitude
controls triggered, but 11 exceeded 0.1 radians and their p90 phase error was
0.135697 radians. The frozen waveform uses `sin(omega*t + phase)`, the joint
model reports `atan2(cosine, sine)`, and the grader uses a wrapped phase
difference; those conventions are mutually consistent.

Disposition: **FAIL — scientific recovery performance.** The result does not
justify weakening the phase gate after seeing the data.

### 2. TOA-application error — invalid grade, correct value unavailable

The frozen configuration names
`maximum_toa_adjustment_error_microseconds` with a 0.001-microsecond maximum.
The v0.2.1 preflight regrade explicitly states that
`uncentered_toa_residual_target_maximum_absolute_error_microseconds` is a
descriptive diagnostic and must not be substituted for that gate.

The injection executor nevertheless calculated the maximum of those two values
and stored that maximum under `toa_adjustment_error_microseconds`. That is the
same grading defect corrected before the calibration design was approved. The
284 retained case records do not preserve the two components separately, so a
JSON-only audit cannot recover the correct maximum TOA-adjustment error.

For comparison, the preflight's actual TOA-adjustment maximum was
0.0000089418 microseconds, while its uncentered residual-target diagnostic was
0.0015975 microseconds. This illustrates why substituting the diagnostic can
reverse the gate, but it does not prove that all 284 injection cases pass.

Disposition: **INVALID GRADE / INDETERMINATE.** Fail closed; do not infer a
pass, rerun cases, or replace the terminal artifact.

### 3. Warning hygiene — invalid grade, corrected pass

The only two “unexpected” lines are duplicate occurrences of this exact
controlled-clock notice:

> Clock file from RECHERCHE_DATA_ROOT/controlled/nanograv15yr-v2.1.0/clock/time_ao.dat overrides global clock file time_ao.dat because of PINT_CLOCK_OVERRIDE

That exact string was already frozen as an expected controlled Arecibo clock
override in the v0.2.1 preflight regrade. The injection runner reused the older
generic warning classifier without carrying forward the frozen disposition.

Disposition: **PASS after applying the existing frozen disposition.** This is a
classifier defect, not evidence of a new material runtime warning.

## Scientific and operational scorecard

| Gate | Frozen requirement | Result | Audit status |
|---|---:|---:|---:|
| Main cases | 240 | 240 | PASS |
| Annual cases | 28 | 28 | PASS |
| Boundary cases | 16 | 16 | PASS |
| TOA application | <= 0.001 us | 0.001831 us, conflated metric | INVALID / INDETERMINATE |
| Fit convergence | All | All 284 | PASS |
| Solver audit count | 29 | 29 | PASS |
| Solver audit failures | 0 | 0 | PASS |
| Strong-control recovery | >= 90% | 100% | PASS |
| Frequency recovery | >= 95% | 100% | PASS |
| Median amplitude bias | <= 10% | 8.43% | PASS |
| Phase-error p90 | <= 0.1 rad | 0.213672 rad | **FAIL** |
| Monotonic periods | >= 3 | 5 | PASS |
| Bracketed periods | >= 3 | 5 | PASS |
| Annual eligibility violations | 0 | 0 | PASS |
| Runtime | <= 6 h | 1.816 h | PASS |
| Peak memory | <= 16 GiB | 0.827 GiB | PASS |
| Complete data root | <= 1.5 GiB | 0.171 GiB | PASS |
| Warning hygiene | No unexpected material warning | None after frozen disposition | PASS / GRADER DEFECT |
| Overall stage | Every hard gate passes | One valid fail; one indeterminate | **FAIL / HARD STOP** |

## Required next gate

The next permissible work is a separately versioned **v0.2.2 remediation
design only**. It must:

1. preserve every v0.2.1 artifact, hash, and terminal failure;
2. carry the already-frozen `time_ao.dat` warning disposition into the shared
   classifier;
3. retain and grade the TOA-adjustment metric separately from the uncentered
   residual-target diagnostic;
4. investigate the phase-recovery failure without relaxing the 0.1-radian gate
   merely to obtain a pass;
5. freeze any justified scientific or implementation change prospectively
   under the new version; and
6. require separate explicit authorization before any new synthetic execution.

No v0.2.2 execution, promotion, or observed-data search is authorized by this
audit.
