# C0 matched-null report

## Decision

C0 **passes as a pipeline-integrity and matched-null case, pending review**.
C1-C3 remain blocked. This pass does not mean that the residual periodogram is
free of structure; it means that the zero-delay path, refit, frozen search, and
provenance controls executed as specified.

## Zero-injection integrity

The same TOA-adjustment method intended for nonzero signals was called with an
all-zero delay vector. All 433 authoritative high-precision Astropy `Time`
values were exactly unchanged, and the refit reproduced the G2 weighted RMS
and chi-squared.

The first C0 attempt exposed a representation issue worth retaining: PINT's
`adjust_TOAs` method refreshes an auxiliary float64 MJD cache. Ninety-nine
cached values changed by up to 0.629 microseconds even though their underlying
high-precision times did not move. The first integrity check compared this
cache and correctly stopped. The authoritative check now compares the
high-precision values and separately records the cache refresh.

## Frozen search result

The exploratory weighted periodogram evaluated 945 frequencies spanning 30
days to half the 5,724-day observation span, at five samples per independent
Fourier bin. It used scaled TOA uncertainties as diagonal weights.

The strongest null peak was:

| Quantity | C0 value |
|---|---:|
| Period | 30.4484 days |
| Power | 0.18097 |
| Fitted amplitude | 0.5819 microseconds |
| Diagonal-weighted delta chi-squared | 612.18 |

This peak lies near the 30-day short-period boundary. It is an uncalibrated
artifact diagnostic, not evidence for a companion. The trigger does not model
the release red-noise covariance and no false-alarm probability is permitted.

The exact null comparators at the frozen future-case periods are:

| Future cases | Period | Null amplitude | Null power | Null delta chi-squared |
|---|---:|---:|---:|---:|
| C1/C2 | 100 days | 0.1651 microseconds | 0.01457 | 49.29 |
| C3 | 365.25 days | 0.01329 microseconds | 0.0000970 | 0.33 |

These are empirical baselines for later transfer comparisons, not detection
thresholds.

## Resource and integrity checks

- Refit convergence: pass.
- TOA count: 433, unchanged.
- Weighted RMS: 0.940689 microseconds.
- Wideband chi-squared: 734.608063.
- Runtime: 3.71 seconds total.
- Peak memory: 244.9 MiB.
- Unexpected warnings: none.
- External data-root size: approximately 746 MiB.

The authoritative full record is
`run_records/c0_matched_null_20260809T020331Z.json` under
`RECHERCHE_DATA_ROOT`, SHA-256
`86e7b9d152d49383c912a951241c4c13b129186ccec32c5896124b46362b97ab`.
The record also fixes the exact Pixi lock SHA-256 used for the authoritative
run: `7412baa7d224dfdc419066b706f27257684931df9a0ad0f57949e1fe31cf68c8`.

## Review disposition and next gate

- C0 result: **pass**.
- Review status: **pending**.
- C1 authorization: **false**.
- C2/C3 authorization: **false**.

If this report is accepted and merged, the next action is to freeze and run C1
only: the 100-day, 20-microsecond strong positive control. C1 must be compared
against both the global C0 artifact and the exact 100-day C0 baseline before
C2 or C3 can be authorized.
