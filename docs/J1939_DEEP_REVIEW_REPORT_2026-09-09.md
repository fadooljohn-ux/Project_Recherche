# A bounded deep review of the J1939+2134 periodic timing candidate

Project Recherche · 9 September 2026 · Private research report

## Abstract

We investigated the preserved InPTA J1939+2134 threshold crossing at 567.405 days using 18,191 arrival-time measurements over 157 observing days. A fixed 16-member white, achromatic and chromatic noise family reduces the original-period statistic from 149.353 to 15.223. Of 512 noise-only realizations, 40 produced a grid maximum at least this large (plus-one diagnostic estimate 0.0799). The signal survives every individual observing-day removal under the original noise model, but receiver-band and overlapping-source checks do not support a stable common timing delay. The final disposition is **INCONCLUSIVE / NOISE-SENSITIVE**; no planet is confirmed.

## 1. Data and fixed scope

The original source preparation, timing design, threshold (26.713) and consumed result remain unchanged. The InPTA data span approximately 2,156 days. Its released covariance is diagonal after the supplied EFAC scaling; the timing design includes projected DMX dispersion parameters. PPTA DR3 is retained with its own released correlated-noise covariance. All observations and original arrays remain outside Git.

The declared follow-up used the original eligible grid plus 400–800 days at 0.5-day spacing; 16 noise choices; 512 noise-only realizations and 256 injections with seed 2026092401; all observing-day deletions; two receiver bands divided at 1000 MHz; and a fixed-period cross-source comparison. Choices and source hashes were saved before the new calculations.

## 2. Likelihood and noise alternatives

We compared white-error scale 1 or 0.5, each with eight alternatives: white only; achromatic Fourier noise with gamma 2 and RMS 1 microsecond, or gamma 4 and RMS 1, 2 or 4 microseconds; dispersion-like or frequency^-4 noise with gamma 2 and RMS 1 microsecond at 400 MHz; and a joint model with gamma-4 achromatic RMS 2 microseconds plus both chromatic components. Each process uses 30 frequencies k/T with spectral weights normalized to its quoted RMS. These are explicitly chosen diagnostic covariances, not estimated physical noise parameters or an exhaustive model family.

The likelihood uses exact Woodbury covariance identities and projects/marginalizes the same linear timing parameters. Model comparison minimizes chi-square plus the covariance and timing-normal-matrix log determinants, with a common constant omitted. Noise selection is repeated separately under the null and sinusoid hypotheses. A small dense calculation verifies the low-rank likelihood, template Gram matrix and relative determinant; the original statistic is independently reproduced.

## 3. Original candidate and noise-only simulations

The released-noise local refinement peaks at 577.5 days, statistic 149.667, amplitude 1.797 microseconds. Under the preferred null model (white0.5_red_dm_chrom), the original 567.405-day statistic is 15.223 and its fitted amplitude is 0.768 microseconds. The half-scale white-error choice is a diagnostic response to the initially low reduced chi-square; it is not independently calibrated uncertainty correction.

To assess the original candidate without confusing it with a different noise-model peak, we compared its profiled statistic with the saved global maximum from every noise-only simulation. 40/512 exceeded it, giving (exceedances + 1)/(512 + 1) = 0.0799. This is a conservative search-adjusted diagnostic within the chosen plug-in family, not the original campaign false-alarm probability or a posterior probability that a planet exists. It does not establish an unusually small noise tail.

The same model family has a stronger residual maximum at 66.961 days, statistic 112.293; 0/512 simulated maxima exceed that different peak (plus-one resolution 1/513). This result concerns the roughly 67-day feature, not the original 567-day candidate. It indicates that the bounded noise family leaves unexplained structure. This review does not establish the origin of that structure, promote it to a new calibrated survey detection, or silently expand the follow-up into another search campaign.

Injections at 577.5 days and 1.797 microseconds recovered a period within 30 days in 228/256 realizations. Only 10/256 exceeded the much stronger observed *global* statistic, which belongs to the other period. The injections are sensitivity diagnostics under the selected null; they are not observed planet recoveries.

## 4. Observing-day, time and receiver-band checks

All 157 days were removed individually at the refined fixed period. The remaining statistic ranges from 131.793 to 159.629; two direct nuisance-refitted calculations verify the sufficient-statistic method. The original-noise candidate is not driven by a single observing day. These subset statistics do not inherit the original search threshold.

| Receiver subset | TOAs | Amplitude (microseconds) | Fixed-period statistic |
|---|---:|---:|---:|
| Below 1000 MHz | 17765 | 3.697 | 291.726 |
| At or above 1000 MHz | 426 | 2.437 | 0.838 |

The high-frequency amplitude is poorly constrained. A joint fit with separate band coefficients improves chi-square by 121.156 for two additional coefficients; its fixed-noise descriptive p-value is 4.91e-27. The analogous time-split value is 0.0071. These comparisons favor a more complex description than a common stationary sinusoid under the original covariance. They are post-selection, model-dependent diagnostics, not independent discovery probabilities or proof of a specific propagation process.

Annual and two-year sinusoidal fits were retained as descriptive alias checks. The annual fit is poorly constrained by astrometric projection. No categorical exclusion of sampling or timing-model aliases is claimed.

## 5. Overlapping PPTA comparison

At the refined 577.5-day period, full PPTA data give statistic 1.705 and amplitude 0.0396 microseconds. In the common TDB MJD interval 58241.995–59567.145, PPTA has 426 TOAs and InPTA 9067.

| Overlap source | Amplitude (microseconds) | Fixed-period statistic |
|---|---:|---:|
| PPTA | 0.338 | 2.229 |
| InPTA | 4.170 | 43.309 |

The conditional coefficient-contrast statistic is 41.281 for two degrees of freedom, assuming independent source errors. Shared propagation noise and imperfect noise models limit that calculation; nevertheless, the overlapping observations provide no corroboration of a common planetary timing delay. The later InPTA subset gives only statistic 5.798 with its own refitted nuisance terms.

## 6. Disposition and limitations

**Park the original candidate as INCONCLUSIVE / NOISE-SENSITIVE.** Preserve its historical threshold crossing. This review supplies concrete reasons to weaken the planetary interpretation: sensitivity to chromatic/correlated-noise choices, receiver-band inconsistency, and lack of overlapping-source corroboration. It does not establish that no planet exists.

The finite Fourier basis, coarse noise amplitudes, selected noise-only generator, approximate timing conversion and fixed source noise assumptions limit the conclusions. The unexplained roughly 67-day residual feature further limits the adequacy of this noise family. More simulations of the same family alone would not resolve that model issue. Any future investigation of that different feature requires a separately recorded, bounded scope and source/systematics checks.

![Saved deep-review diagnostics](../outputs/j1939-deep-review-20260909/diagnostics.png)

## Reproducibility and references

- [Declared review scope](J1939_DEEP_REVIEW_2026-09-09.md) and [recurring review policy](CANDIDATE_DEEP_REVIEW.md).
- [Original campaign report](PTA_CAMPAIGN_01_REPORT_2026-09-09.md), retained unchanged.
- [InPTA DR2](https://github.com/inpta/InPTA.DR2), pinned source commit recorded in the original campaign.
- [PPTA DR3](https://github.com/danielreardon/PPTA-DR3).
- [NANOGrav ENTERPRISE](https://github.com/nanograv/enterprise) and [Fourier noise-model implementation](https://github.com/nanograv/enterprise_extensions/blob/master/enterprise_extensions/models.py).
- Numerical receipts: `results/research/j1939-deep-review-20260909/`. Original inputs, saved simulation arrays and logs remain outside Git.
