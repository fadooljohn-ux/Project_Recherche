# EPTA J1012+5307: native timing compatibility and candidate comparison

Completed 10 September 2026 under the owner's bounded follow-up authorization.
**The EPTA observations do not corroborate the saved 138.911-day NG15 feature.**
Native T2/H3/H4 compatibility is established for this dataset. This is a
fixed-period candidate review, not a new EPTA period search or a general binary
adapter qualification.

## Observations and the repaired clock boundary

The acquired EPTA DR2full release supplies 5,325 arrival-time measurements, a TCB
T2 model with fitted H3/H4, DE440, TT(BIPM2021), and released group-specific white,
red and dispersion noise. The existing pinned TEMPO2 2025.02.1 / libstempo 2.5.1
runtime evaluates that model natively. No measured Shapiro term is removed or
translated into another binary convention. No explicit NHARMS parameter is set;
the native runtime's default is retained, not interpreted as zero harmonics.

Preparation attempt01 retained all measurements and passed binary derivative
checks, but was held because TEMPO2 approximated the missing clock correction
for one Effelsberg arrival at MJD 59295.066895585. The measured effix2gps file ends
at MJD 59294.5. The public [IPTA clock record](https://ipta.github.io/pulsar-clock-corrections/T2runtime/clock/effix2gps.clk.html)
also identifies that endpoint. No extrapolation was introduced.

Attempt02 comments out that one arrival in a derived TIM tree before any
periodic comparison. All original files and the first held attempt remain
preserved. The final dataset contains **5,324 arrivals on 1,974 observing days**,
spanning **8,646.871 days (23.67 years)**, TDB MJD 50647.198–59294.068. The exact
arrival identifier, file, reason and clock hashes are in the evidence package.

## Compatibility evidence

- All nine free binary columns, including H3/H4, passed finite-difference and
  three-published-sigma local-linearity checks. The maximum relative derivative
  discrepancy is 7.03e-5; the largest nonlinear remainder is 0.000382 raw TOA
  uncertainty, below the predeclared 0.1 limit.
- Independent native exports agree exactly in residuals and barycentric times.
  All 5,324 retained rows are included and no missing-clock warning remains.
- Imported EFAC/EQUAD variances and red/DM Fourier covariance products agree
  with native TEMPO2 to relative errors below 1e-15.
- A Woodbury GLS null calculation and a separate augmented least-squares solve
  both give chi-square **5224.767086**, with full rank **443/443**. Dividing by
  5,324 minus 55 timing columns gives 0.991605. This is a convention/numerical
  compatibility check, not proof of complete stochastic-model adequacy.
- Null-fit binary shifts are below the predeclared three-published-sigma limit;
  the largest is H3 at **1.644 sigma**. These are local linear checks, not a new
  posterior determination of the binary orbit.

## Frozen fixed-period comparison

The period is the saved NG15 candidate value, **138.9110415844769 TDB days**,
with common reference epoch MJD 56104.0. Sine and cosine coefficients are fitted
jointly with all 55 linear timing columns. Native TCB time arguments and residual
amplitudes are consistently scaled for the TDB comparison using the pinned PINT
conversion constants. The released binary model itself remains in native TCB.

Three noise alternatives were bound before the periodic fits: released
red149/DM45; red256/DM64; and red256 with twice its power plus DM64. Extending DM
from 45 to 64 modes in the latter two alternatives explicitly includes the
candidate frequency (the released DM cutoff is about 192 days). Red256/DM64
cutoffs are about 33.8/135.1 days. White noise and spectral slopes/amplitudes are
otherwise held at their declared values. There is no noise-model selection or
scan over EPTA periods in this comparison.

| EPTA noise model | Fixed-period delta chi-square | Conditional p, 2 d.o.f. | Fitted amplitude (microseconds) |
|---|---:|---:|---:|
| Released red149 / DM45 | 2.4563 | 0.2928 | 0.07454 |
| Covered red256 / DM64 | 2.2488 | 0.3249 | 0.07332 |
| Covered red256, doubled red power / DM64 | 1.3037 | 0.5211 | 0.07049 |

The corresponding NG15 joint-noise reference amplitude is **0.49463
microseconds** (the original search fit was 0.50381 microseconds). EPTA's
coefficient uncertainties are about 0.047–0.062 microseconds. For the exact saved
NG15 waveform, analytic noncentral-chi-square power at a **fixed-period 1% test**
is above 99.9999% in all three declared models. These are conditional analytic
calculations, not empirical injections, blind-search sensitivity, or a universal
planet-exclusion probability.

The coefficient contrast against NG15 gives conditional p=0.0128–0.0146 when
using the sum of the two fitted covariance matrices. That approximation treats
their errors as independent; different observatories can share propagation
noise. It also conditions on the previously selected NG15 noise model, period
and waveform. Period/model uncertainty, cross-source covariance, eccentric
signals and source-selection effects are not integrated. Therefore this number
is not a discovery sigma or a calibrated rejection probability for all planetary
interpretations. The much smaller EPTA amplitude nevertheless fails to support
the specified persistent circular waveform in an informative dataset.

## Disposition and bookkeeping

J1012 remains **INCONCLUSIVE_NOISE_SENSITIVE**. Its three measures are now:

1. Statistical significance: **NOT_ESTABLISHED**; global FAP and sigma unavailable.
2. Robustness: **NOISE_SENSITIVE**, retaining both earlier noise reviews.
3. Independent confirmation: **NOT_CORROBORATED**, replacing UNAVAILABLE for this
   specific fixed-period, source-separated comparison.

The original crossing and threshold, previous assessments, and original data are
unchanged. The new assessment is an immutable successor. The master records the
held first preparation, successful clock-bounded preparation, comparison and
grade revision in Work log; all **356 search/refinement rows and 282 observed
identities** remain unchanged. No new planetary discovery is claimed.

## Reproduction and scope

The new commands are available through the offline operator entry point:

```sh
tools/recherche epta-binary-followup prepare --data "$RECHERCHE_DATA" \
  --output "$NEW_NATIVE_PREPARATION"
tools/recherche epta-fixed-comparison --data "$RECHERCHE_DATA" \
  --prepared "$NEW_NATIVE_PREPARATION" --output "$NEW_COMPARISON"
```

These are target-specific commands requiring the pinned native IPTA runtime,
the acquired EPTA source tree and clocks, and saved NG15 development artifacts.
They are not download commands or authorization to repeat consumed science.
Use the existing preparations/results for inspection; the original external
directories are `epta-j1012-followup-20260910-attempt01`,
`epta-j1012-followup-20260910-attempt02`, and
`epta-j1012-comparison-20260910`, relative to RECHERCHE_DATA. Use the Intel science
Python for the extended-precision NPZ artifacts. Personal installation paths
and raw timing exports remain outside the public evidence package.

The [evidence package](../results/research/epta-j1012-followup-20260910/closeout.json)
binds input, code, runtime, clock, preparation and result hashes. All 71 preserved
publication-source hashes were checked unchanged. No broad qualification or new
simulation campaign was needed. No job remains active; no push or release was
performed.

A post-run operator fix rejects an existing preparation before its error handler
can write a failure receipt into that consumed directory. The rejection was
verified with all existing artifacts unchanged. The executed preparation code is
retained in the evidence package separately from this small operator correction;
the scientific computation was not repeated.

The next practical science step is a separately authorized preparation and
search of **J0509+0856**, next in the saved bounded binary queue, with explicit
noise-frequency coverage and target-specific calibration. Reopening J1012 would
need a concrete new question or better data/model evidence; repeating these
completed checks is unlikely to be productive.
