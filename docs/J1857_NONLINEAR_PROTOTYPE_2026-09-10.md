# J1857+0943 native nonlinear-Shapiro compatibility prototype

**10 September 2026 — CONDITIONAL_NONLINEAR_PROTOTYPE_COMPATIBLE.**

The bounded prototype passes on the saved NANOGrav 15-year wideband data for
J1857+0943 (B1855+09). Native evaluation resolves the specific Shapiro
linearization obstacle encountered in binary pilot02. The original failed
preparation remains unchanged. This successor is a compatibility result, not an
operational profile, threshold calibration, posterior or planet search.

## Implementation

`tools/j1857_nonlinear.py` evaluates all seven released orbital/Shapiro terms
(PB, A1, TASC, EPS1, EPS2, M2 and SINI) using PINT's native ELL1 delay. Inclination
is optimized through cos(i) to retain a physical domain. The 160 other timing,
dispersion and instrumental nuisance columns remain jointly fitted by linear
least squares at every native orbital evaluation. Orbital terms are removed
from that linear nuisance design, preventing double counting of their freedom.
The existing local PINT ELL1 derivative correction and precise spin-phase
binding are reused. The shared binary adapter and qualified scientific source
are unchanged; its old local-linearity gate is not bypassed.

The finite domain is the published central values plus/minus three reported
standard errors, transformed consistently for inclination. It is a numerical
prototype domain, not an independent measurement prior or a posterior result.
All tested optima lie in its interior. The full native timing calculation with
fitted nuisance parameters is checked against the local nuisance approximation.

The released red-noise amplitude and slope are retained in the reference
scenario. Its Fourier coverage extends from 30 to 64 modes before fitting:
the shortest represented period becomes 88.944 days, covering the prospective
123.272–2000-day search. A fixed set of four alternatives changes red amplitude
by factors 0.5 or 2, or spectral slope by minus/plus one. No white-noise terms
are discarded. Each scenario uses two declared optimizer starting points.

The comparison objective contains the profiled residual chi-square, covariance
log determinant and the linear nuisance integration measure. A smaller raw
chi-square alone does not select a noise model. This hybrid objective is a
bounded diagnostic; it does not integrate the nonlinear orbit into a Bayesian
evidence calculation. The scope and numerical criteria were saved before the
run in [config/j1857-nonlinear-prototype.json](../config/j1857-nonlinear-prototype.json).

## Results

All 364 arrival times and 364 paired dispersion measurements are retained.
The joint local design has rank 167/167, leaving 561 residual degrees of freedom.
All ten optimizer runs converge, with no boundary optimum or execution failure.

| Fixed noise scenario | Reduced chi-square | Objective above reference | Maximum orbital shift in published sigma |
|---|---:|---:|---:|
| Released amplitude/slope, 64 modes | 0.990714 | 0.000 | 0.020 |
| Half red amplitude | 1.020411 | 5.406 | 0.293 |
| Double red amplitude | 0.969624 | 5.420 | 0.292 |
| Slope reduced by one | 1.038564 | 14.245 | 0.210 |
| Slope increased by one | 0.973745 | 7.069 | 0.294 |

The released-noise scenario is the best of this declared set. Its chi-square
is 555.790512, with a conditional upper-tail diagnostic of 0.554. Remaining
orbital-harmonic structure has diagnostic delta chi-square 7.420 for rank 11,
with conditional tail 0.764. Neither triggers the declared 0.0027 adequacy
cutoff. These checks do not establish that the noise model is unique or fully
correct, and the conditional tails are not discovery significance.

Numerical verification across all five scenarios:

- Analytic native derivatives agree with finite differences to relative error
  below 2.4e-5. All seven terms are checked at each fitted solution.
- The largest projected, whitened difference between full native timing and
  the linear nuisance approximation is 6.65e-6, below the declared 0.1 limit.
- Independent full-residual and projected chi-squares agree within 1.14e-13.
- The two starting points agree in chi-square within 1.9e-6, below the 0.01
  criterion. This is a bounded convergence check, not proof of a global optimum.
- Normalized joint condition numbers range from approximately 191 to 194.

### Signal information

The five declared synthetic period templates use no observed periodogram.
Under the reference noise, local worst-phase information retained after the
full timing/orbital fit, relative to phase/DM/instrumental nuisance removal only,
is:

| Synthetic period, days | Worst-phase information retained |
|---:|---:|
| 150 | 84.28% |
| 300 | 83.10% |
| 600 | 85.17% |
| 1200 | 64.84% |
| 1800 | 83.87% |

These are local Fisher-information ratios under the same covariance, not
injection recoveries or detection probabilities. They include the cost of
spin, astrometric and orbital freedom; they are not the incremental cost of
nonlinear Shapiro alone. Across all noise scenarios the corresponding ratios
range from 48.35% to 87.75%. No annual mask or sensitivity curve was calibrated.

## Operation and retained evidence

Use the pinned runtime through the supported wrapper, with a new destination:

```sh
tools/recherche j1857-nonlinear \
  --data "$RECHERCHE_DATA" \
  --scope config/j1857-nonlinear-prototype.json \
  --output "$RECHERCHE_DATA/j1857-nonlinear-prototype-20260910/attempt01"
```

The completed `attempt01` is consumed. The script refuses an existing output
and records an execution failure if one occurs. Do not rerun it to update the
workbook. Saved private arrays include the input residuals, covariance,
nuisance design and fitted orbital solution for each noise scenario. Public
[receipt](../results/research/j1857-nonlinear-prototype-20260910/receipt.json),
[scope](../results/research/j1857-nonlinear-prototype-20260910/scope.json) and
[artifact manifest](../results/research/j1857-nonlinear-prototype-20260910/artifact-manifest.json)
provide installation-agnostic bindings. Original PAR/TIM files, earlier failure,
all historical search results and all 71 publication-source bindings remain
unchanged.

## Next step and limits

Recommend extracting a reusable, efficient nonlinear statistic and testing it
on a small declared set of synthetic nulls and injected signals before starting
full calibration. The same seven-parameter orbit treatment and chosen noise
policy must operate under both null and companion hypotheses. Nuisance terms
must remain fitted in each case. A fixed delay evaluated once at the best orbit
cannot substitute for that procedure.

The existing `ProjectedFit` accepts an input residual vector and can be reused,
but a full planet-grid statistic and calibrated execution path do not yet exist.
Benchmark native evaluation cost first; repeating full PINT model construction
and delay evaluation across every simulated period grid would be expensive.
Any caching or faster delay evaluation must be checked against this preserved
native reference. Finalize the parameter domain and noise policy before a
threshold run; do not tune them after observing a search peak.

Full threshold/annual-mask/sensitivity calibration and an observed search remain
subsequent scopes. This prototype is not general nonlinear-binary qualification.
The other three measured-Shapiro targets remain held; J1802 stays parked.

The canonical workbook receives four Work log entries for implementation,
noise adequacy, information checks and terminal closeout. Its 360 search rows,
eight candidate grades and all historical cells are preserved. Totals remain
783 registered targets and 286 observed identities. No job is active and
monitoring remains paused. This local development update is not pushed or released.
