# Pilot 1 sensitivity extension result v0.1

## Outcome

**PASS — 14 of 14 extension rows pass.**

All 240 frozen lower-amplitude cases and 24 independent full-covariance audits
completed. Every ordinary and compatible joint fit converged; all audits passed;
frequency recovery among threshold triggers was 100%; the artifact ledger and
warning classifier passed; and no observed-residual periodic search was run.

The combined immutable parent and extension matrices bracket both the 50% and
90% recovery crossings at all five interior periods. Recovery requires both a
locked-threshold trigger and a global peak within one independent Fourier bin
of the injected frequency.

| Period (days) | 50% crossing (us) | 90% crossing (us) |
|---:|---:|---:|
| 50 | 0.2333 | 0.2867 |
| 100 | 0.1625 | 0.2600 |
| 200 | 0.2000 | 0.2800 |
| 500 | 0.2600 | 0.3400 |
| 1,000 | 0.3750 | 0.4760 |

At 100 days, the 90% crossing converts to 0.0418845 projected lunar masses
under the frozen 1.4-solar-mass convention. The ratio to the Behrens et al.
0.56-lunar-mass value is 0.07479 and remains contextual because the discrepancy
dossier established that the experiments are not method-matched.

## Resources and integrity

- Parent plus extension calibration time: 2.40865 hours (cap: 4 hours).
- Peak memory across the combined run: 0.60982 GiB (cap: 16 GiB).
- Complete external data root: 0.75935 GiB (cap: 5 GiB).
- Extension ledger: 240/240 verified.
- Independent audits: 24/24 completed, zero failures.
- Unexpected material warnings: zero.
- Observed-residual global search: not executed.

The external summary is
`run_records/pilot1/sensitivity-extension-v0.1-summary.json`, 331,606 bytes,
SHA-256 `fcc905f2648684418a4cbde150928d0e61a59ba2456134130ed6cccd65ca88b4`.
