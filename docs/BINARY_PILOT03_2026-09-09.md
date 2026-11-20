# Binary pilot 03: observed searches and J1012 review

9 September 2026. The authorized four steps are complete: fixed-Shapiro model
comparison, final model selection before observed periodograms, calibration and
freeze, and one observed search each for J1012+5307 and J1738+0333. J1012 crossed
its original threshold, then failed robustness under broader red-noise coverage.
J1738 returned NO_TRIGGER. No planet is confirmed. New work remains local.

## Model preparation and calibration

J1012's fixed optical reference uses a white-dwarf mass of 0.165 solar masses and
inclination 50 degrees from the [optical study](https://arxiv.org/abs/2004.02901).
The first two Shapiro harmonics are removed from the apparent released orbit
before adding the physical delay, following the degeneracy described in
[Lange et al., Appendix A2](https://adsabs.harvard.edu/pdf/2001MNRAS.326..274L).
With `z = sin(i)/(1+cos(i))` and `r = GM_WD/c³`, the reference transformation is
`x_new = x_old − 4rz`, `x_new EPS1_new = x_old EPS1_old − 4rz²`, and
`x_new EPS2_new = x_old EPS2_old`. M2 and SINI remain fixed; all originally free
orbital parameters and their uncertainties remain in the joint timing projection.
No mass/inclination posterior is inferred.

The physical-reference preparation passed derivative, local-linearity, rank,
pulse-connection and independent likelihood checks. Its largest fitted orbital
shift about that reference was 0.357 published standard deviations. No retry was
needed. Over the same nine optical stress scenarios, the maximum remaining
long-period contamination fell from Δχ² 1.2434 to 0.2852, a 77% reduction. These
Cartesian scenarios are not a joint confidence region or a continuous bound.
The fixed reference was selected before observing the planet-search periodogram;
the choice was not an optimization of the observed residual likelihood.

J1738's previous preparation was copied byte-for-byte and explicitly adopted by
profile, receipt, adapter and predecessor-selection hashes. Its small tested
omitted-delay contamination remained Δχ² 0.04240. It was not prepared again.
The two-target policy and previously unused seeds were retained.

| Calibration | J1012+5307 | J1738+0333 |
|---|---:|---:|
| Real wideband TOAs | 624 | 336 |
| Observing-day epochs | 318 | 104 |
| Outer-period range, days | 30–2,000 | 30–1,960.127 |
| Full / eligible cells | 933 / 923 | 645 / 633 |
| Fixed-noise null realizations | 4,096 | 4,096 |
| Frozen threshold, Δχ² | 24.27345 | 23.53514 |
| Diagnostic injections recovered | 95 / 96 | 92 / 96 |
| Median worst-phase 95%-recovery amplitude, μs | 0.61375 | 0.82501 |

Each calibration supplied the target's projection/annual mask and sensitivity
curve. The ten and twelve excluded cells remain preserved. The thresholds use
the existing 1% two-target conditional Gaussian union-bound allowance. Sensitivity
is for on-grid circular signals at fixed covariance/design, not a posterior limit
or population completeness. Calibration and diagnostic injections are distinct.

## Observed outcome

| Frozen search | Peak period, days | Amplitude, μs | Peak Δχ² | Threshold | Original disposition |
|---|---:|---:|---:|---:|---|
| J1012+5307 | 138.9110 | 0.50381 | 32.11282 | 24.27345 | CANDIDATE |
| J1738+0333 | 31.1131 | 0.36133 | 11.12956 | 23.53514 | NO_TRIGGER |

Independent full-design likelihood fits verified both peaks. Null reduced χ²
was 1.0655 and 1.0094, respectively, with no automated noise-adequacy flags.
Each run01 destination is consumed. The master updated after each run, including
the original J1012 candidate row. A satisfactory scalar reduced χ² did not establish
that the covariance described the relevant short-period structure.

## Bounded J1012 candidate review

![Original periodogram and noise sensitivity](../results/research/j1012-review-20260909/search-and-noise-review.png)

The released RNAMP/RNIDX convention imports into PINT with 30 red Fourier modes
when a count is not specified. Here the shortest represented red-noise period is
189.09 days, longer than the 138.91-day candidate. The review reproduced the
original covariance, then extended the same released red amplitude and slope
to 64 and 128 modes (88.63 and 44.32 days). Further declared alternatives doubled
red power at 128 modes or added a ν^-4 timing-noise term with 0.3 μs RMS at
1400 MHz and a 100-day exponential correlation time.

Each model was analyzed separately with 512 noise-only realizations and 64
injections. Every realization scanned the original eligible grid. The diagnostic
tail compares the statistic at the original candidate period with simulated grid
maxima. No noise model was selected to minimize a p-value. The original threshold
and search result remain unchanged.

| Review covariance | Candidate Δχ² | Null maxima ≥ candidate | Plus-one diagnostic tail | Injected signal recovered |
|---|---:|---:|---:|---:|
| Released, 30 modes | 32.1128 | 0 / 512 | 0.001949 | 52 / 64 |
| 64 modes | 8.4771 | 496 / 512 | 0.96881 | 1 / 64 |
| 128 modes | 5.5966 | 512 / 512 | 1.00000 | 0 / 64 |
| 128 modes, twice red power | 2.9237 | 512 / 512 | 1.00000 | 1 / 64 |
| 128 modes plus chromatic term | 5.4247 | 512 / 512 | 1.00000 | 1 / 64 |

Injection recovery here requires exceeding the original threshold and locating
the injected 0.504 μs signal within 5% of its period. These finite, per-generator
diagnostics are not pooled global false-alarm probabilities. A tail of one means
all simulated maxima exceeded this model's weak candidate statistic; it is not
the probability that the signal is noise. The alternatives are limited stress
models, not fitted noise posteriors or replacement survey calibrations.

Additional checks completed within the declared review:

- Nine fixed-period Shapiro perturbations retained Δχ² 30.61–34.70 under released
  noise. The original crossing therefore is not explained away by this bounded
  optical Shapiro uncertainty check.
- All 318 observing days were removed in turn, keeping each TOA paired with its
  DM measurement and refitting nuisance terms. Fixed-period statistics ranged
  24.12–35.80 under released noise and 4.13–6.61 with 128 modes. The efficient GLS
  deletion identity was checked against direct reduced-data fits for both models.
  These are influence diagnostics; subset-specific thresholds were not calibrated.
- Temporal halves, two radio-frequency bands and GASP/GUPPI subsets were fitted
  at the same candidate period and phase origin. The temporal halves gave Δχ²
  16.90 and 13.95 under released noise, falling to 4.48 and 1.74 with 128 modes.
  The lower-frequency band was weak, while the higher-frequency band contributed
  more support. Unequal sensitivity and correlated noise prevent treating these
  subset differences as independent rejection or confirmation.
- Independent EPTA DR2full raw data are present: its PAR lists 5,325 TOAs, but uses
  T2 with fitted orthometric H3/H4 Shapiro parameters. The current adapter cannot
  claim a compatible independent comparison. Those measured terms were preserved;
  no independent fit or non-corroboration was asserted.

The broader context also argues for caution: the
[EPTA periodicity study](https://arxiv.org/abs/2408.09795) reported noise-model
limitations for J1012 and a different, approximately two-year periodicity.
The [NANOGrav chromatic-noise study](https://doi.org/10.3847/1538-4357/ad5291)
also discusses this pulsar's noise difficulties. Neither is independent
confirmation of our 139-day feature or a substitute for our numerical review.

## Assessment and next work

The three measures are **statistical significance NOT_ESTABLISHED**, **robustness
NOISE_SENSITIVE**, and **independent confirmation UNAVAILABLE with the current
compatible inputs/model**. The retained disposition is
**INCONCLUSIVE_NOISE_SENSITIVE**. The candidate does not currently support a
planetary claim. It remains a valid historical crossing of its stated fixed-model
threshold, not an erased result or an execution failure.

Before another binary batch, add a targeted preparation check that makes the
red-noise frequency coverage explicit and assesses a warranted extension before
the observed search. Start from this concrete failure mode; do not redesign the
solver or rerun completed survey results. The next bounded white-dwarf pool is
J1125+7819, J0509+0856 and J0557+1551, subject to their own model/noise checks.
Orthometric EPTA support is a separate useful follow-up if independent J1012
comparison is prioritized; it is not required to call this feature confirmed.

The master now contains 783 targets, 281 observed identities and 355 Search rows.
Eight candidate identities have bounded reviews; none is a confirmed planet.
All 353 earlier Search rows and operator notes are preserved. There were no
preparation, calibration, observed-run or review execution failures. No job is
active, no new publication occurred, and all 71 preserved scientific source
hashes remain unchanged.

[Batch evidence](../results/observed/binary-pilot03-20260909/closeout.json) and
[review assessment](../results/research/j1012-review-20260909/assessments.json)
bind the raw results, calibrations, model choice, diagnostics and workbook
closeout. Redacted archive views of preparation/freeze records retain their
original hashes; executable bindings and raw inputs remain external.

Operator details: a fixed-reference preparation uses the selected target row's
`shapiro_mode: fixed_from_literature` and `fixed_shapiro` object with `mass_solar`
and `inclination_degrees`. Record this in a new selection before preparation;
do not edit a frozen selection. Exact reused preparations are listed by target
under `reused_preparations` with profile, receipt, source adapter and predecessor
selection hashes. The binary calibration and freeze commands verify these
bindings. `tools/recherche j1012-review --data "$BINARY_DATA" --output "$REVIEW_DATA"`
reads the consumed result and writes checkpointed follow-up evidence.

The operator may set `RECHERCHE_WORKBOOK_HOOK` to an executable that receives the
usual workbook arguments and updates the canonical register from saved evidence.
This run used the artifact-tool workbook backend through that hook. A failing
hook propagates an error; repair bookkeeping alone and preserve the science.
Without the hook, the existing portable workbook updater remains the default
for binary observed closeout.
