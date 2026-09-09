# C1-R1 corrective strong positive-control report

## Decision

C1-R1 **passes all frozen hard gates, pending review**. This validates the
corrected recovery machinery for the strong 100-day control; it is not a
detection or false-alarm calibration. C2 and C3 remain blocked until this
record is reviewed and merged.

## Scorecard

| Area | Test | Outcome |
|---|---|---|
| Protocol control | v0.5 config/code/environment freeze; C1-R1 only | **PASS** |
| Injection integrity | 433 TOAs; maximum error <= 0.001 us | **PASS** (0.0000084 us) |
| Ordinary refit | Release-model fit completed | **PASS** |
| Frequency recovery | Exact 100-day amplitude and power exceed C0 | **PASS** |
| Joint recovery | 95-105% amplitude and <= 0.01 rad phase error | **PASS** |
| Independent cross-check | Explicit full covariance agrees with low-rank solver | **PASS** |
| Warning hygiene | No unexpected material warning | **PASS** |
| Reproducibility | Frozen and output hashes verified | **PASS** |
| Resource envelope | <= 60 minutes and <= 16 GiB | **PASS** |
| Scientific authorization | C2-C3 remain blocked pending review | **PASS** |
| Global strongest peak | Uncalibrated diagnostic only | **DIAGNOSTIC** |

Overall C1-R1 outcome: **PASS**. The score is not averaged; every hard-gate row
passed.

## Corrected compatible recovery

The project-owned `ProjectCircularSignal` component represents a deterministic
physical circular delay with two fitted coefficients. It is not a Fourier
red-noise model. The release `PLRedNoise` covariance component remained present
through every joint fit, and `WaveX` was absent.

After phase-aware subtraction of the same-run C0 fit, the low-rank joint solver
recovered:

| Quantity | Frozen target | C1-R1 result |
|---|---:|---:|
| Amplitude | 20.0 us | 20.000164 us |
| Recovery fraction | 0.95-1.05 | 1.0000082 |
| Absolute phase error | <= 0.01 rad | 0.0000190 rad |
| Joint chi-squared improvement | Greater than C0 | 219,331.19 vs 6.92 |

The numerical agreement previously seen with WaveX was reproduced without the
WaveX/PLRedNoise compatibility warning, resolving the C1 joint-grader failure.

## Independent covariance cross-check

The primary `WidebandDownhillFitter` uses PINT's low-rank covariance
representation. The independent check used `WidebandTOAFitter` with the
explicit full covariance matrix. Their injected-data joint results differed
by only:

- 0.000000260 microseconds in amplitude;
- 0.0000000414 radians in phase; and
- 0.000224 in chi-squared.

All are far inside the frozen 0.01-microsecond, 0.001-radian, and 0.1
cross-check tolerances.

## Residual-frequency diagnostic

The ordinary timing-model refit still absorbed or redistributed approximately
71.07% of the injected waveform. The exact 100-day residual amplitude was
5.7655 microseconds with power 0.14937, exceeding the C0 comparators of 0.1651
microseconds and 0.01457 power.

The global strongest residual peak remained the 30.096-day boundary feature.
Under Amendment A004 this is explicitly diagnostic rather than a recovery
gate: the diagonal periodogram does not include correlated noise and has no
calibrated false-alarm probability. It cannot support a companion claim.

## Resource and provenance checks

- Total runtime: 35.24 seconds.
- Peak memory: 308.9 MiB.
- Unexpected warnings: zero.
- Freeze record: `pilot0-v0.5-stage-c-c1-r1`.
- Pixi lock SHA-256:
  `7412baa7d224dfdc419066b706f27257684931df9a0ad0f57949e1fe31cf68c8`.

The authoritative full record is
`run_records/c1_r1_corrective_control_20260809T023108Z.json` under
`RECHERCHE_DATA_ROOT`, SHA-256
`3807008e56439befb913bd46da741ebb49fedf2695100683758011f542fd6bab`.

## Review disposition and next gate

- C1-R1 result: **pass**.
- Review status: **pending**.
- C2/C3 authorization: **false**.

After review and merge, the next action is to freeze and run C2 only: the
100-day, 5-microsecond boundary diagnostic. Its recovery bounds and scientific
role must be fixed before execution; C3 must remain blocked until C2 is
reviewed.
