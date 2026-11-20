# Reusable nonlinear statistic: synthetic verification and cost benchmark

**17 November 2026 — NONLINEAR_STATISTIC_VERIFIED on J1857+0943, no holds.**

Owner instruction: "Proceed with nonlinear work". This is the step recommended
at the close of the [J1857 prototype](J1857_NONLINEAR_PROTOTYPE_2026-09-10.md):
a reusable, efficient statistic that re-fits the nonlinear orbit under both the
null and the companion hypothesis, checked on simulated data before any
calibration. No observed residual vector was scanned, no threshold, mask or
sensitivity was calibrated, and no operational profile was written.

## What was built

`tools/nonlinear_statistic.py` (numerical library, no data access):

    delta_chi2(f) = min_x chi2(y - d(x) | N) - min_x chi2(y - d(x) | N, T_f)

- `d(x)` is the orbital delay in the seven released orbital/Shapiro terms, `N`
  the 160 linear nuisance columns and `T_f` the sine/cosine pair at one trial
  period. Linear terms are profiled exactly in both fits; the orbit is
  re-optimised at every period inside the declared domain.
- The native PINT delay is replaced by a polynomial fitted to native delays
  sampled across the domain, and checked on points it was not fitted to.
- After projection the problem reduces to a few hundred small bounded
  least-squares fits per data vector, solved together with a damped
  Gauss-Newton method that holds parameters on a bound when the fit pushes
  outward.

`tools/nonlinear_verification.py` runs the declared checks through
`tools/recherche nonlinear-verification`. Six tests in
`tests/test_nonlinear_statistic.py` cover a toy orbit: an exact polynomial fit,
equality with generalised least squares when the orbit is linear, and agreement
with a brute-force fit when it is not. The qualified source under `src/` is
unchanged.

## Declared run

Scope: [config/nonlinear-statistic-verification.json](../config/nonlinear-statistic-verification.json).
Two short development attempts chose the polynomial degree and exposed a bound
handling defect, which was fixed; criteria and seeds were then fixed before
`attempt01`. Development attempts are retained beside it.

Setup is the prototype's: 364 TOAs with paired DMs (728 rows), released red
noise extended to 64 modes, orbit domain of three published standard errors,
218 trial periods from 123.27 to 2000 days.

| Check | Result | Criterion |
|---|---:|---:|
| Surrogate error on 100 unseen points (whitened, projected norm) | 0.0136 max, 0.0020 median | <= 0.02 |
| Statistic against native reference, 40 comparisons | 0.0011 max difference | <= 0.02 |
| Null chi-square against native reference | 0.0029 max difference | <= 0.02 |
| Unconverged cells in 512 nulls (111,616 fits) | 0 | 0 |
| Mean statistic per cell, 512 nulls | 1.981 | 1.8 to 2.2 |
| Cells with the orbit on a domain bound | 1.76% | <= 10% |
| Strong injections located within two grid cells | 20 of 20 | >= 90% |
| Median amplitude bias of located injections | -2.6% | within 20% |

The polynomial is cubic: 119 terms fitted to 400 native delays.

## What the simulations show

- **The nonlinear and linearised statistics are nearly the same here.** Over
  512 simulated nulls the two maxima have the same quantiles to two decimals
  (median 8.79 against 8.80, 99th percentile 15.91 against 15.90). The largest
  single-cell difference in any null was 1.05 and the median of those maxima
  0.03. This is a simulation diagnostic, not a threshold.
- **The domain is reached in simulation.** 1.6% of null fits (8 of 512) ended
  on a domain bound: SINI 3, PB 2, A1, EPS2 and TASC 1 each. The domain must be
  settled before calibration, as the prototype record already requires.
- **Weak injections can be missed.** At an expected noncentrality of 25, two of
  20 cases peaked more than two cells from the injected period. This check is
  not a detection probability.
- **Long periods cost amplitude.** A fixed 0.3 microsecond signal gave an
  expected noncentrality of about 33 at 150 days, 18 at 600 days and 1.9 at
  1800 days in a development attempt, because spin and red-noise terms absorb
  slow signals.

## Cost

| Item | Time |
|---|---:|
| One native delay evaluation | 0.065 s |
| One simulated vector over the whole grid | 0.41 s |
| Projected 4096-null calibration | about 28 minutes |
| Projected 96-injection set | about 40 seconds |
| The same 4096 nulls with native fits (estimate) | about 36 days |

The whole declared run took 17 minutes, most of it the native reference fits.

## Limits

- One target, simulated Gaussian data under the fixed released covariance,
  generated at the published orbit. Not general nonlinear-binary qualification.
- The reference comparison covers 8 vectors at 5 periods, not every cell.
- Noise parameters stay fixed; this does nothing for the noise-sensitivity
  question raised by the candidate reviews.
- No annual mask, threshold or sensitivity exists for J1857. Its pilot02
  preparation failure is preserved and it remains held.

## Evidence

- Receipt and scope: `results/research/nonlinear-statistic-20261117/`.
- Arrays, log and development attempts:
  `../Project Recherche Data/nonlinear-statistic-20261117/`.

## Later change

The [J1857 calibration](J1857_NONLINEAR_CALIBRATION_2026-11-17.md) added
optional higher-order terms for a parameter pair to the surrogate and two
return values to the verification loader. The library and verification tool
therefore no longer match the code hashes in the `attempt01` receipt; the
declared run's behaviour with its own scope is unchanged.

## Next step

Decide the orbit domain, then prepare, calibrate and freeze J1857 with this
statistic in nulls, injections and the observed run alike. Each of those is a
separate scope needing the owner's instruction. J0740, J0613 and J2043 include
PBDOT and need their own surrogate check with the same tool.

Update, 18 November 2026: all four targets are done; see
[J1857](J1857_NONLINEAR_CALIBRATION_2026-11-17.md) and
[the other three](HELD_NONLINEAR_SEARCHES_2026-11-17.md). The default fit
iteration limit was raised from 60 to 200 and an optional physical cut of the
orbit box (`physical_floors`) was added for J0613.
