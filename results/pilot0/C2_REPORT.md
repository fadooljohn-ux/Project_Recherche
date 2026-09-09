# C2 lower-amplitude boundary-diagnostic report

## Decision

C2 **passes every frozen hard execution gate and produces a robust recovery
classification, pending review**. The robust classification is a diagnostic
outcome, not a detection-efficiency or false-alarm calibration. C3 remains
blocked until this record is reviewed and merged.

## Scorecard

| Area | Test | Outcome |
|---|---|---|
| Protocol control | v0.6 config/code/environment freeze; C2 only | **PASS** |
| Injection integrity | 433 TOAs; maximum error <= 0.001 us | **PASS** (0.0000083 us) |
| Ordinary refit | Release-model fit completed | **PASS** |
| Joint execution | Compatible C0 and C2 fits converged | **PASS** |
| Independent cross-check | Explicit full covariance agrees with low-rank solver | **PASS** |
| Warning hygiene | No unexpected material warning | **PASS** |
| Reproducibility | Frozen and output hashes verified | **PASS** |
| Resource envelope | <= 60 minutes and <= 16 GiB | **PASS** |
| Scientific authorization | C3 remains blocked pending review | **PASS** |
| Boundary recovery | Frozen robust/partial/inconsistent classification | **DIAGNOSTIC: ROBUST** |
| Exact-frequency comparison | Compare 100-day residual with C0 | **DIAGNOSTIC: EXCEEDS C0** |
| Global strongest peak | Uncalibrated context only | **DIAGNOSTIC** |

Overall hard-gate outcome: **PASS**. The score is not averaged; every hard-gate
row passed. The diagnostic recovery class is reported separately as frozen.

## Boundary recovery

C2 injected a 100-day circular timing delay with a 5-microsecond amplitude.
After phase-aware subtraction of the same-run C0 coefficients, the compatible
joint model recovered:

| Quantity | Frozen diagnostic band | C2 result |
|---|---:|---:|
| Amplitude | 5.0 us requested | 5.000044 us |
| Recovery fraction | Robust: 0.8-1.2 | 1.0000088 |
| Absolute phase error | Robust: <= 0.1 rad | 0.0000215 rad |
| Joint chi-squared improvement | Diagnostic comparison | 13,960.97 vs C0 6.92 |

This meets the preregistered `robust` classification. `PLRedNoise` remained in
the release covariance model and `WaveX` was absent throughout.

## Independent covariance cross-check

The explicit full-covariance and primary low-rank solvers differed by:

- 0.00000106 microseconds in amplitude;
- 0.0000000277 radians in phase; and
- 0.000286 in chi-squared.

These differences are well inside the frozen 0.01-microsecond, 0.001-radian,
and 0.1 tolerances.

## Residual-frequency diagnostic

The ordinary timing-model refit absorbed or redistributed approximately 71.07%
of the injected waveform. The exact 100-day residual amplitude was 1.4330
microseconds with power 0.12407. Both exceeded the C0 values of 0.1651
microseconds and 0.01457 power.

The global strongest residual peak was again the 30.448-day boundary feature,
with 2.1000-microsecond amplitude and 0.24635 power. It is not evidence for
another signal: this diagonal periodogram does not model correlated noise and
has no calibrated false-alarm probability.

## Resource and provenance checks

- Ordinary injected-data weighted RMS: 2.9517 microseconds.
- Ordinary injected-data reduced chi-squared: 21.412.
- Total runtime: 32.71 seconds.
- Peak memory: 310.4 MiB.
- Unexpected warnings: zero.
- Freeze record: `pilot0-v0.6-stage-c-c2`.

The authoritative full record is
`run_records/c2_boundary_control_20260809T024248Z.json` under
`RECHERCHE_DATA_ROOT`, SHA-256
`2984669210dfe947a690594d47be82be0538554b38ececead0aa2579c71489c1`.

## Review disposition and next gate

- C2 hard-gate result: **pass**.
- C2 recovery classification: **robust**.
- Review status: **pending**.
- C3 authorization: **false**.

After review and merge, the next action is to freeze C3 only: the 365.25-day,
20-microsecond annual-absorption stress test. Its annual-systematics and
astrometric-covariance diagnostics must be specified before execution.
