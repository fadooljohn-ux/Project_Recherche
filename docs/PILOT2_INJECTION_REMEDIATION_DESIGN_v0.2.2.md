# Pilot 2 B1937+21 injection remediation design v0.2.2

## Status and boundary

This package is a zero-case remediation implementation. It does not authorize
new synthetic cases, reuse or rerun v0.2.1 cases, regrade the v0.2.1 failure,
load observed residual data, execute an observed periodic search, run a
promotion grade, or make a discovery claim.

The v0.2.1 terminal result remains **FAIL / HARD STOP**. Its 284 injection
records are development evidence only. Any future v0.2.2 acceptance decision
must use the prospectively frozen, seed-disjoint inventory in this package.

## Root-cause response

The record-only analysis verified all 284 injection artifacts and executed no
case. Absolute phase error was most strongly associated with detection
strength: the Spearman correlation was -0.4196. In the lowest trigger-strength
quartile, 63.0% of cases exceeded 0.1 radians; in the highest quartile, 14.3%
did. All fits converged, all solver audits passed, frequency recovery was 100%,
and ordinary-model absorption had almost no association with phase error.

The remediation therefore separates two different estimands:

1. **Detection recovery and sensitivity:** the existing 240-case main ladder
   continues to measure detection fraction and sensitivity crossings. Phase
   error for these cases remains reported but is not used as a hard detection
   gate.
2. **Phase accuracy:** a dedicated 60-case high-information control stratum
   tests phase measurement at twice the prior strongest amplitudes. The
   numerical p90 limit remains exactly 0.1 radians; it has not been relaxed.

The dedicated controls cover the same five main periods, four injected phases,
and three covariance-noise realizations per phase. Every control must trigger,
and the combined phase-error p90 must be at most 0.1 radians.

## Corrected application-integrity telemetry

The implementation now retains these fields separately:

- `toa_adjustment_maximum_absolute_error_microseconds` — the sole frozen
  0.001-microsecond application gate;
- `uncentered_toa_residual_target_maximum_absolute_error_microseconds` — a
  reported numerical diagnostic, never substituted for the gate; and
- `dm_maximum_absolute_error` — a separate DM-application diagnostic.

A legacy record containing only `toa_adjustment_error_microseconds` fails
closed. The v0.2.1 conflated field cannot be accepted by the v0.2.2 grader.

## Corrected phase telemetry

Future case records must retain:

- recovered sine and cosine coefficients;
- their individual uncertainties and correlation;
- their covariance in squared microseconds;
- recovered phase;
- signed wrapped phase error;
- absolute phase error; and
- the delta-method phase standard error.

This corrects the v0.2.1 telemetry limitation that retained only absolute phase
error. Uncertainty coverage will remain diagnostic until separately
prevalidated; it cannot become an improvised acceptance gate during execution.

## Corrected warning scope

The exact controlled `time_ao.dat` override is recognized as an expected
Arecibo release-clock warning in the v0.2.2 injection path. The correction is
scoped to this path so historical frozen manifests remain byte-for-byte valid.
Every other unexpected warning remains a hard failure.

## Prospective inventory

| Stratum | Cases | Role |
|---|---:|---|
| Main recovery | 240 | Detection fractions and bracketed sensitivity |
| Phase reference | 60 | Unchanged 0.1-radian phase-accuracy gate |
| Annual map | 28 | Astrometric and model-absorption eligibility |
| Search boundaries | 16 | 30- and 2,000-day behavior |
| **Total** | **344** | New seed-disjoint injection package |

The inventory uses the `p2r2` case prefix and four new deterministic seed bases.
All 344 case IDs and seeds are disjoint from v0.2.1. Thirty-five cases receive
the deterministic full-covariance solver audit. The projected runtime with 25%
contingency is 3.234 hours, below the six-hour MacBook cap.

## Acceptance sequence

1. Verify the remediation freeze, source hashes, v0.2.1 predecessor hashes,
   prospective inventory hash, and execution lock.
2. Require a separate explicit execution authorization before loading the
   timing-model execution context.
3. If authorized later, execute only the 344 new cases with checkpoints and the
   health-only heartbeat.
4. Fail closed on any missing canonical application metric, unexpected warning,
   nonconverged fit, solver-audit failure, phase-reference miss, integrity
   mismatch, or resource-cap breach.
5. Preserve any terminal failure. Do not reroll, retune, replace, or
   retroactively regrade it.

No execution is authorized by this design.
