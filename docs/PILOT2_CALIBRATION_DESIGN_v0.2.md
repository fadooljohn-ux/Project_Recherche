# Pilot 2 B1937+21 full-calibration design v0.2

## Outcome

The B1937+21 calibration design is complete and execution-locked. Its
deterministic inventory contains 4,784 unique cases, 4,784 unique seeds, and 29
preselected full-covariance audits. The projected MacBook runtime is 2.6754
hours with contingency, below the six-hour cap.

## Workload scorecard

| Workload | Cases | Role |
|---|---:|---|
| Gaussian threshold calibration | 1,000 | Lock global 99th-percentile threshold |
| Sealed Gaussian evaluation | 500 | Measure family-wise false-positive behavior |
| Timing-block structured tails | 1,000 | Red-noise/covariance robustness stress |
| DM-block structured tails | 1,000 | DM-noise robustness stress |
| Clustered observing-day tails | 1,000 | Correlated outlier stress |
| Main recovery injections | 240 | Recovery and bias surfaces |
| Annual identifiability map | 28 | Astrometric/annual sensitivity gaps |
| Search-boundary map | 16 | 30- and 2,000-day behavior |
| Full-covariance audits | 29 | Subset of the 284 injections |

The case total is 4,784; the 29 audits are repeat solver evaluations of selected
injection cases rather than additional synthetic draws.

## Target-specific amplitude design

| Period | Frozen amplitudes, microseconds |
|---:|---|
| 50 days | 0.025, 0.05, 0.1, 0.2 |
| 100 days | 0.025, 0.05, 0.1, 0.2 |
| 200 days | 0.025, 0.05, 0.1, 0.2 |
| 500 days | 0.1, 0.25, 0.5, 1.0 |
| 1,000 days | 0.25, 0.5, 1.0, 2.0 |

These ladders are planning choices informed by the synthetic preflight. They
are not sensitivity claims. If a ladder fails to bracket a recovery crossing,
the crossing remains unreported rather than extrapolated.

## Hard boundaries

- Calibration execution is not authorized.
- Observed residuals and observed periodic content remain inaccessible.
- No J1744 empirical threshold, mask, or recovery result transfers.
- The sealed evaluation cannot tune the detector or be rerolled.
- Structured-tail variants cannot be pooled or recalibrated.
- Passing calibration would authorize only preparation of a separate observed-
  search package.
- Fable is not required for design or routine calibration execution.

## Next gate

Implement the resumable calibration runner, operational dashboard, artifact
ledger, stage locks, and result grader. Bind the code, environment, case-order
hash, controlled inputs, and progress semantics in a separate execution freeze.
No synthetic calibration case may run before that package passes its tests.
