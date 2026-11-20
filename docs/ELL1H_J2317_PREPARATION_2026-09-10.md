# J2317+1439 H3-only preparation — 10 September 2026

**J2317+1439 passed preparation on the first attempt and is ready for
conditional calibration.** The existing narrow H3-only adapter required no
code change. All 708 arrival times and their paired wideband DM measurements
are retained. No calibration, sensitivity experiment, observed periodogram or
planet search ran.

## Inputs and timing model

The saved NG15 v2.1.0 wideband archive supplied the original PAR/TIM pair,
verified against the pinned inventory and checked against the master before
selection. The offline Intel PINT 1.1.5 runtime used DE440, TDB and the existing
local GPS/BIPM2019 clock resources. The model retains explicit ELL1H, fitted H3
and NHARMS=3, with no H4 or STIGMA. The original six fitted orbital terms are
PB, A1, TASC, EPS1, EPS2 and H3.

The weak H3 coefficient remains **0.061015 ± 0.044530 microseconds**. It is
neither deleted nor forced positive. Its three-sigma local neighborhood crosses
zero, which is allowed for this released linear harmonic coefficient. It is not
converted into a physical mass/inclination posterior. All orbital values,
uncertainties and fit flags survive saved-model serialization unchanged; the
full released free-parameter list is also preserved.

| Preparation measurement | Result |
| --- | ---: |
| Arrival times / paired DM measurements | 708 / 708 |
| Barycentric observing-day bins | 312 |
| Barycentric span | 5,714.438595 days (15.65 yr) |
| Inner binary period | 2.459331465 days |
| Prospective outer-period bounds | 30–2,000 days |
| Joint data / timing-design dimensions | 1,416 × 328 |
| Design rank | 328 / 328 |
| Normalized design condition number | 704.065 |
| Largest relative orbital-derivative discrepancy | 2.183e-7 |
| Largest three-sigma nonlinear remainder | 8.593e-7 TOA sigma |
| Largest local fitted orbital shift | 2.442e-5 published sigma (EPS1) |
| H3 local fitted shift | 1.101e-5 published sigma |
| Independent null chi-square relative discrepancy | 0 at saved precision |
| Null chi-square / degrees of freedom | 1,095.543348 / 1,088 |
| Reduced chi-square | 1.006933 |
| Conditional null upper tail | 0.430296 |

The earlier model-only inventory counted 313 days by flooring raw site MJDs;
the preparation counts 312 by flooring barycentric TDB MJDs. This is a time-bin
definition difference, not dropped observations. All 708 observations remain.
The orbital shifts are local GLS diagnostics at the released reference model,
not a replacement nonlinear timing solution. Real-TOA derivative and
three-sigma linearity checks passed for every free orbital term. The independent
full-design null fit agrees with the production projection.

## Noise compatibility and limits

The release supplies white-noise and DM-uncertainty scaling terms, with DMX and
instrumental timing terms retained in the design. It supplies **no red-noise
component**. Preparation records NO_RELEASED_RED_COMPONENT; it does not invent
an amplitude/slope or import J2145's red spectrum. There is consequently no
released red Fourier spectrum to extend.

Reduced chi-square near one shows no excess scatter in the aggregate check
under this covariance. It does not rule out weak correlated or chromatic noise,
and is not validation of a noise posterior. Any later calibration and search
remain explicitly conditional on the supplied noise model. A qualifying future
crossing would receive the standing bounded noise/robustness review.

## Evidence, register and next step

[Saved evidence](../results/research/ell1h-j2317-preparation-20260910/) includes
selection, receipt, profile metadata, verification, external-file bindings and
closeout. Full original inputs, numerical arrays and logs remain outside Git in
`RECHERCHE_DATA/ell1h-j2317-preparation-20260910`. No public artifact contains a
personal installation path.

The already completed 11 H3-only adapter regression checks are reused by hash;
the same adapter is unchanged, so they were not repeated. Direct verification
checks this new target's prepared inputs, profile and orbital serialization.
All 71 publication-source hashes are unchanged. There was no preparation
failure or retry.

Two Work log records are appended to the canonical master. All 359 Searches
rows, eight grades and historical notes are preserved. Totals remain 783
registered targets and 285 observed identities. No observed result or new
candidate has been created for J2317.

The completed selection uses `config/ell1h-j2317-preparation-selection.json`
with `tools/recherche binary-pilot select`; preparation uses:

```sh
tools/recherche binary-pilot prepare \
  --data "$RECHERCHE_DATA/ell1h-j2317-preparation-20260910" --target J2317+1439
```

Inspect the saved preparation rather than repeating it. **Next recommend
threshold, annual/projection-mask and sensitivity calibration on this preserved
profile**, including the existing bounded injection checks. The saved policy
specifies one target, 4,096 nulls and a conditional 1% allowance over 30–2,000
days; no calibration has run. A later observed launch must freeze the verified
calibration and inputs first. J1802's missing-Shapiro-model hold and the four
previous nonlinear Shapiro holds remain separate. No job is active and no push
or release was performed.
