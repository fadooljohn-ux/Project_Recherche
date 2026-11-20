# H3-only adapter and J2145-0750 preparation — 10 September 2026

**The narrow adapter extension is implemented, and J2145-0750 is ready for
calibration.** Preparation passed on the first attempt with the released H3
coefficient retained. No threshold calibration, mask, sensitivity experiment,
observed periodogram or planet search was performed.

## Implementation

`tools/recherche binary-pilot` now accepts explicit `shapiro_mode: h3_only`
selections only for released `BINARY ELL1H`, fitted H3 and `NHARMS 3` models.
Other Shapiro terms (including a supplied zero H4) are rejected rather than
removed. The H3 coefficient remains signed and free. PINT's native orthometric
derivatives are retained; the existing ELL1 M2/SINI derivative repair remains
on its original branch. All free orbital, spin, astrometric, DM and instrument
columns participate in the joint timing projection.

This is the small extension identified by the
[prior assessment](ELL1H_COMPATIBILITY_2026-09-10.md), not general binary or
arbitrary ELL1H support. J2317+1439 remains a future preparation candidate.
J1802-2124's missing-Shapiro-model hold and the four earlier nonlinear Shapiro
holds are preserved. The 71 publication-source files are unchanged.

## Real-data preparation

The NG15 v2.1.0 wideband PAR/TIM files were re-extracted from the already pinned
archive, verified against the saved inventory and checked against the master.
The offline pinned Intel PINT 1.1.5 runtime used DE440 and the local GPS/BIPM2019
clock chain. All 400 arrival times and 400 paired DM measurements are retained.

| Quantity | Result |
| --- | ---: |
| Arrival times / observing-day epochs | 400 / 285 |
| Barycentric span | 5,675.371656 days (15.54 yr) |
| Inner binary period | 6.838902510 days |
| Prospective outer-period range | 68.389025–2,000 days |
| Joint design dimensions | 800 rows × 184 columns |
| Joint design rank | 184 / 184 |
| Normalized design condition number | 3.0083 million |
| Largest relative orbital-derivative discrepancy | 1.887e-7 |
| Largest three-sigma nonlinear remainder | 4.916e-8 TOA sigma |
| Largest fitted orbital shift / published uncertainty | 0.103754 (A1) |
| H3 fitted shift / published uncertainty | 0.086056 |
| Independent null chi-square relative discrepancy | 3.531e-13 |
| Null chi-square / degrees of freedom | 612.371301 / 616 |
| Reduced chi-square | 0.994109 |
| Conditional null upper tail | 0.533703 |

The seven retained free orbital terms are PB, A1, A1DOT, TASC, EPS1, EPS2 and
H3. H3 remains **0.176960 ± 0.051491 microseconds** at the released reference
model. The fitted shifts above are local GLS diagnostics; the adapter does not
replace the published solution with a new nonlinear timing fit. Saved model
serialization preserves all orbital values, uncertainties and fit flags.
The complete list of released free parameters is also preserved.

The real-TOA derivative checks use central finite differences and the existing
three-sigma local-linearity criteria. The design is numerically conditioned but
full rank; the independent likelihood agreement provides a direct check of this
particular projection. The original synthetic-phase assessment alone was not
used to declare real-data compatibility.

## Noise coverage and limits

The existing coverage rule increases the released red spectrum from **30 to
128 Fourier modes** before calibration. Its shortest represented period moves
from 189.179055 to **44.338841 days**, covering the prospective 68.389025-day
lower search boundary. The released spectral amplitude (5.00655e-14) and slope
(2.53021) are unchanged. No periodogram was used to choose this extension.

The null statistic shows no excess scatter under this covariance. It does not
establish a complete noise model: the released amplitude/slope are fixed and
extrapolated, and frequency coverage is not noise-posterior validation. Released
DMX, FD and instrumental terms remain in the projection. No new solar-wind
model was fitted. The prior assessment's chromatic/annual caveat remains;
calibration must still compute the target-specific annual/projection mask.

## Verification, evidence and register

Eleven focused tests passed: signed and zero H3 retain the native derivative;
missing H3, absent/different NHARMS and incompatible Shapiro/model declarations
are refused; the existing ELL1 derivative repair remains active on ELL1.
The prepared profile, residuals, source inputs and receipt hashes were verified
without rerunning preparation. No preparation failure or retry occurred.

[Saved evidence](../results/research/ell1h-j2145-preparation-20260910/) includes
selection, receipt, profile metadata, verification, external-file hash bindings
and closeout. Full original inputs, numerical arrays and runtime logs are in
`RECHERCHE_DATA/ell1h-j2145-preparation-20260910`. Public materials contain no
personal installation paths. The canonical workbook receives three Work log
records. All 358 Search rows, eight grades and historical notes are preserved;
there remain 783 registered targets and 284 observed identities.

## Operation and next step

The completed preparation used the supported entry point:

```sh
tools/recherche binary-pilot select \
  --data "$RECHERCHE_DATA/ell1h-j2145-preparation-20260910" \
  --archive "$NG15_ARCHIVE" --inventory "$NG15_INVENTORY" \
  --selection config/ell1h-j2145-preparation-selection.json
tools/recherche binary-pilot prepare \
  --data "$RECHERCHE_DATA/ell1h-j2145-preparation-20260910" --target J2145-0750
```

These commands document the completed attempt; inspect saved evidence rather
than rerunning it. No observed destination is consumed. The recommended next
scope is **threshold, annual/projection-mask and sensitivity calibration on this
preserved profile**, including the existing bounded injection check. Its policy
is one target, 4,096 null realizations and a conditional 1% allowance. The policy
is saved but calibration has not run. A later observed launch must freeze the
verified calibration and inputs first. No job is active; no repository push or
release was performed in this scope.
