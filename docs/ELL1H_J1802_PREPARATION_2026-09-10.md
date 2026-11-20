# J1802-2124 bounded preparation — 10 September 2026

**The adapter and timing interface passed; preparation ends on a model-adequacy
hold. J1802 is not ready for calibration.** The released wideband data retain
orbital-phase structure and prefer additional correlated noise in the bounded
comparison. No calibration, observed outer-period scan or planet search ran.

## Implemented support and preserved inputs

The explicit `ell1h_omitted_in_release` mode admits the source-documented ELL1H
model with NHARMS 7 and no supplied Shapiro terms. It retains the native PINT
orthometric derivative and verifies its zero omitted-delay convention. It does
not alter the binary label, invent H3, or insert literature masses. The existing
ELL1 measured/omitted and ELL1H H3-only routes remain separate. Nineteen focused
adapter checks pass, including preservation of signed H3 and rejection of a held
or stale adequacy report before calibration/freeze.

The original NG15 v2.1.0 wideband PAR/TIM pair is byte-identical to the preceding
[source review](J1802_MODEL_CLARIFICATION_2026-09-10.md). All 126 arrivals and 126
paired DM measurements are retained. The five free orbital terms PB, A1, TASC,
EPS1 and EPS2 retain their values, uncertainties and fit flags; the entire
released free-parameter list survives serialization unchanged. Original phase
cuts remain intact: none of the retained arrivals lies in phase 0.15–0.35 under
the prepared native model. No omitted/excised arrivals were restored.

| Timing-interface measurement | Result |
| --- | ---: |
| TOAs / paired DM / barycentric day bins | 126 / 126 / 70 |
| Barycentric span | 1,262.623948 days |
| Inner binary period | 0.6988892433 days |
| Prospective outer-period bounds | 30–631.311974 days |
| Joint data rows / timing columns / rank | 252 / 66 / 66 |
| Normalized timing-design condition | 2.038e8 |
| Largest orbital derivative relative error | 6.032e-8 |
| Largest three-sigma nonlinear remainder | 1.639e-6 TOA sigma |
| Largest local orbital shift | 0.03858 published sigma |
| Null chi-square / degrees of freedom | 227.696910 / 186 |
| Reduced chi-square / conditional upper tail | 1.224177 / 0.020055 |

The design is full rank but poorly conditioned, which remains a limitation;
independent likelihood verification agrees to 9.63e-12 relative error. These
are local GLS diagnostics at the supplied model, not a new nonlinear timing
solution. The released white/DM covariance contains no red component. Aggregate
scatter alone does not decide readiness.

## Bounded orbital and noise diagnostics

The diagnostic scope was saved before examining observed residuals. It includes
sine/cosine harmonics 3 through 7 of the known inner orbit and a 13-member noise
comparison: released covariance plus 12 red alternatives. The red grid uses
slopes 1.5, 3 and 4.33 and unprojected RMS values 0.25, 0.5, 1 and 2 microseconds.
Each has 64 Fourier pairs, reaching 19.73 days and covering the prospective
outer-period range. RMS normalization uses the mean covariance diagonal on this
wideband sampling. No narrowband amplitude was transplanted.

With every released timing/DM/orbital column projected, the ten orbital harmonic
coefficients have full rank and improve chi-square by **40.658723** under the
released covariance. The conditional chi-square(10) tail is **1.297e-5**, below
the declared 0.0027 adequacy criterion. This identifies residual phase structure;
it is not a planet-search significance or a physical Shapiro measurement.

The best red-grid member has **2 microseconds RMS, slope 1.5**. It improves the
timing-marginalized null objective by **16.991082**, exceeding the declared
10-unit diagnostic criterion. The objective includes the covariance determinant
and compares a common timing integration measure. Both amplitude and slope lie
at grid edges, so this is not an interior noise estimate or a settled model.
The saved amplitude-edge check explicitly records NOISE_GRID_BOUNDARY_HOLD.

Under that grid member, the orbital improvement falls to **25.769302**, with a
conditional tail of **0.004063**. This demonstrates noise sensitivity; it does
not establish that red noise fully explains the orbital structure. That tail
conditions on a model selected from these observations and is not adjusted for
noise-model selection. No red-grid model was promoted into the saved profile.

Independent full-design least-squares checks reproduce both orbital improvements
within 4.1e-8. A full-covariance timing-marginalized calculation reproduces the
noise-objective improvement within 1.1e-8. These checks substantiate the numerical
calculation, not the physical adequacy of the finite noise family.

Ten deterministic one-microsecond orbital harmonic perturbations were also
projected over the prospective outer-period grid. Their largest synthetic
statistic ranges from 1.58 to 7.58, showing that short-period structure can leak
into longer periods through sampling. Only synthetic perturbations entered this
grid; observed residuals were never scanned over planet periods. Unit harmonics
do not bound the real Shapiro waveform, and these values are not detection
thresholds, candidate evidence or calibrated sensitivity limits.

## Disposition and next step

The authoritative terminal disposition is **PREPARATION_ADEQUACY_HOLD**, with:

- OMITTED_ORBITAL_STRUCTURE_HOLD
- WIDEBAND_NOISE_MODEL_HOLD
- NOISE_GRID_BOUNDARY_HOLD

The lower-level receipt still accurately records a compatible timing interface.
It must be read together with `preparation-diagnostics.json`. The adapter now
requires a successful, input-bound adequacy report before this mode can calibrate
or freeze; the real held record was verified to reject progression without
running calibration. The original source-provenance question is resolved; these
are newly measured adequacy limitations, not missing downloads.

Recommend a separately bounded **joint orbital/Shapiro and noise comparison**
using this saved preparation. It should assess whether orbital structure remains
when the red model has an interior optimum and whether a physical companion-delay
model or explicit orbital nuisance terms can be supported without absorbing the
outer-companion signal. That work needs its own sensitivity checks before any
calibration. Do not widen the present grid until a fit passes, silently remove
FD/timing columns, or treat the best edge member as the final covariance.

## Evidence and operation

[Evidence directory](../results/research/ell1h-j1802-preparation-20260910/)
contains the original and adopted selections, timing receipt, profile metadata,
diagnostics, verification and workbook closeout. Numerical arrays, original
PAR/TIM files and logs remain in `RECHERCHE_DATA/ell1h-j1802-preparation-20260910`.
All 71 publication-source bindings remain unchanged.

Preparation succeeded once with no scientific retry. A later gate-only code
change uses the existing explicit preparation-adoption mechanism: the original
adapter, selection and receipt are retained; input arrays and diagnostics were
not rerun or regraded. One patch-script quoting error caused a missing-helper
regression failure; the patch was corrected and all 19 focused checks passed.

For a fresh authorized reproduction, selection uses
`config/ell1h-j1802-preparation-selection.json` with `tools/recherche binary-pilot
select`, then `prepare --target J1802-2124`. The bounded diagnostics run with the
pinned offline Intel runtime:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONPATH=src \
  /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  .pixi/envs/default/bin/python tools/j1802_preparation_diagnostics.py \
  --data "$RECHERCHE_DATA/ell1h-j1802-preparation-20260910" \
  --selection config/ell1h-j1802-preparation-selection.json \
  --output "$NEW_DIAGNOSTIC_JSON"
```

Inspect the preserved results for continuity rather than repeating the completed
assessment. Four Work log rows record the implementation, preparation, adequacy
hold and closeout. Counts remain **783 targets, 286 observed identities, 360
search/refinement records and eight candidate grades**. No observed result is
added and no candidate is declared. Previous searches and four nonlinear holds
are preserved. No job remains active; no push or release is included.
