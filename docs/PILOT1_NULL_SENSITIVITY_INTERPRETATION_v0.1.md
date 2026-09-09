# Pilot 1 null-result sensitivity interpretation v0.1

## Outcome

The completed v0.1 null search supports a bounded empirical sensitivity
description at five calibrated periods. It does not support a formal 95%
exclusion limit.

The frozen injection surface contains 12 cases per period–amplitude cell: four
fixed phases and three covariance-noise realizations per phase. The original
50% and 90% crossings remain valid as empirical interpolation point estimates.
They are not population guarantees or confidence limits.

## Period–amplitude interpretation

Projected masses use the frozen 1.4-solar-mass circular-orbit convention and
are expressed in lunar masses.

| Period (days) | Empirical 50% crossing (us) | Projected mass | Empirical 90% crossing (us) | Projected mass | Conservative sampled 50% (us) | Projected mass |
|---:|---:|---:|---:|---:|---:|---:|
| 50 | 0.2333 | 0.05967 | 0.2867 | 0.07331 | 0.3000 | 0.07672 |
| 100 | 0.1625 | 0.02618 | 0.2600 | 0.04188 | 0.3000 | 0.04833 |
| 200 | 0.2000 | 0.02030 | 0.2800 | 0.02842 | 0.3000 | 0.03044 |
| 500 | 0.2600 | 0.01432 | 0.3400 | 0.01873 | 0.3000 | 0.01653 |
| 1,000 | 0.3750 | 0.01302 | 0.4760 | 0.01652 | 0.5000 | 0.01735 |

“Conservative sampled 50%” is the smallest tested amplitude whose two-sided
95% Wilson lower bound is at least 50%. It is a grid summary, not an
interpolated limit or an exclusion statement.

All five periods satisfy that 50% diagnostic. No period satisfies the analogous
90% diagnostic at any tested amplitude. Even a 12/12 cell has a two-sided 95%
Wilson interval of approximately 75.75%–100%, so the finite matrix cannot
establish a true recovery probability of at least 90% with 95% confidence.

## Relation to the observed null

The one-shot observed search found no candidate. Its strongest eligible cell
was at 59.9641 days with delta chi-square 16.4991, below the strict 23.3343
threshold.

The sensitivity matrix was calibrated at 50 and 100 days, not at 59.9641 days.
Because cross-period interpolation was not frozen, no exact timing-amplitude or
projected-mass sensitivity may be assigned to that strongest observed cell.
The calibrated table instead describes the detector’s empirical behavior at
the five listed periods.

## Annual and model gaps

The 350, 365.25, and 380-day cells remain annual sensitivity gaps. Strong
eligibility controls at 300, 330, 400, and 450 days do not provide lower-
amplitude recovery crossings and therefore cannot be converted into sensitivity
limits.

The analysis does not cover periods outside 30–2,000 days, amplitudes below the
tested grid, eccentric or nonstationary signals, unrestricted phase/noise
populations, or signal families absorbed differently by the timing model.
Projected mass is inclination-dependent and is not a true companion mass.

## Scorecard

| Test area | Outcome |
|---|---:|
| Three frozen source records and hashes | PASS |
| Completed one-shot null preserved | PASS |
| Exactly one observed scan preserved | PASS |
| Five monotonic calibrated recovery surfaces | PASS |
| Forty cells at 12 cases each | PASS |
| Frozen empirical crossings reproduced | PASS |
| Wilson finite-sample uncertainty calculated | PASS |
| Conservative sampled 50% threshold at five periods | PASS |
| Conservative sampled 90% threshold | **Not supported at any period** |
| Annual sensitivity gaps preserved | PASS |
| No cross-period interpolation | PASS |
| No formal upper-limit claim | PASS |
| No new observed-data access or search | PASS |
| **Overall integrity** | **15/15 PASS** |

## Scientific disposition

The defensible result is an empirical recovery characterization accompanying a
null search, not a formal exclusion curve. The point-estimate crossings are
useful for planning and comparison within this exact pipeline. A publication-
grade 90%-recovery limit would require a separately frozen, substantially
larger injection ensemble designed for interval precision; it would not require
rerunning the completed v0.1 observed search.

## Next decision

Initial v0.1 has now yielded its complete bounded science product: a null
candidate result plus an empirical sensitivity characterization. The next
phase should scope a scientifically distinct v0.2. Candidate directions are a
new target selected under predeclared criteria, or a separately calibrated new
signal family. Neither may be treated as a retry or threshold revision of v0.1.
