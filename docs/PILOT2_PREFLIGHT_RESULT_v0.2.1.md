# Pilot 2 B1937+21 preflight result v0.2.1

## Outcome

The bounded B1937+21 preflight **passes 16 of 16 final gates** after a
hash-bound, JSON-only correction of two grading defects. The underlying R1 run
completed all 50 frozen synthetic cases and all 10 full-covariance audits. The
regrade generated no new random draw, model fit, scan, or scientific result.

This pass supports preparation of a target-specific full-calibration design.
It does not authorize calibration or an observed periodic search.

## Execution history

The first attempt stopped before any synthetic case because PINT fetched a
missing Arecibo clock-cache entry and the runner called an incompatible residual
accessor. That failure is preserved in
`results/pilot2/preflight_failed_attempt_v0.2.json`.

The corrective R1 run used a clean data root, pre-seeded the Arecibo cache from
the byte-identical controlled clock file, and blocked process-level network
connections. It completed 20 nulls, 30 injections, and 10 deterministic solver
audits. Its original overall grade was false because the implementation used a
descriptive recomputed-residual error instead of the frozen TOA-application
metric and omitted the expected Arecibo controlled-clock warning category.

The regrade verified the R1 summary SHA-256 and every case-artifact hash. It
restored the established 0.001-microsecond TOA-adjustment gate and classified
only the exact controlled `time_ao.dat` override warning as expected. No
threshold or tolerance changed.

## Scorecard

| Gate | Outcome | Evidence |
|---|---|---|
| Source summary integrity | PASS | Frozen SHA-256 verified |
| Case artifact integrity | PASS | 50 of 50 hashes verified |
| Null case count | PASS | 20 of 20 |
| Injection case count | PASS | 30 of 30 |
| Explicit solver audits | PASS | 10 of 10 |
| Solver agreement | PASS | All 10 within amplitude, phase, and chi-square limits |
| Released-fit reproduction | PASS | 660 TOAs; fit converged; finite timing and DM residuals |
| Red-noise preservation | PASS | Preserved in every audited solver fit |
| Synthetic/observed separation | PASS | Synthetic scanner never received observed residuals |
| Warning hygiene | PASS | No remaining unexpected warning |
| Projected calibration runtime | PASS | 2.1385 hours versus 6-hour cap |
| Preflight wall time | PASS | 802.24 seconds versus 3,600-second cap |
| Peak memory | PASS | 0.551 GiB versus 16-GiB cap |
| Complete data root | PASS | 0.1153 GiB versus 1.5-GiB cap |
| Additional downloads | PASS | 0 bytes in corrective run |
| Search/calibration boundary | PASS | No observed periodic search or threshold calibration |

## Numerical checks

- Covariance shape: 1,320 x 1,320.
- Timing-design shape and rank: 1,320 x 284, rank 284.
- Maximum frozen TOA-application error: 0.0000089418 microseconds against a
  0.001-microsecond limit.
- Maximum solver amplitude difference: 0.0009722 microseconds against a
  0.01-microsecond limit.
- Maximum solver phase difference: 0.00001482 radians against a
  0.001-radian limit.
- Maximum solver chi-square difference: 0.006743 against a 0.1 limit.

The 50-case trigger and recovery values remain diagnostic only. They do not
calibrate a threshold, define sensitivity, or support a companion claim.

## Next gate

Prepare a separately frozen B1937+21 calibration design with target-specific
null calibration, sealed false-positive evaluation, structured-noise stress,
injection recovery, annual identifiability mapping, checkpointing, and the
existing six-hour MacBook ceiling. No v0.1 J1744 empirical threshold, mask, or
recovery surface transfers.
