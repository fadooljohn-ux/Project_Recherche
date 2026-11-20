# ELL1H compatibility assessment — 10 September 2026

Two saved exclusions have a plausible small adapter route: **J2145-0750** and
**J2317+1439**, both released as H3-only ELL1H models with explicit `NHARMS 3`.
**J1802-2124 remains MISSING_SHAPIRO_MODEL_HOLD.** These are model-only
compatibility findings, not timing/noise qualification or planet-search results.
No actual TOA fit, calibration, sensitivity experiment or observed search ran.

## Inputs and coverage

The three original PAR/TIM pairs were extracted from the already acquired
NANOGrav 15-year v2.1.0 release and checked against its saved inventory hashes.
All use TDB/DE440 and have paired wideband DM measurements on every active TOA.
Site-MJD observing-day counts below are text-inventory counts, not fitted epochs.

| Target | TOAs / observing days | Span | Released binary period | Prospective planet-period bounds | Disposition |
| --- | ---: | ---: | ---: | --- | --- |
| J2145-0750 | 400 / 285 | 15.54 yr | 6.83890 d | 68.39–2000 d | First H3-only adapter candidate |
| J2317+1439 | 708 / 313 | 15.65 yr | 2.45933 d | 30–2000 d | Second H3-only adapter candidate |
| J1802-2124 | 126 / 70 | 3.46 yr | 0.69889 d | 30–631.31 d | Missing Shapiro-model hold |

Bounds apply the existing `max(30 d, 10 PB)` to `min(2000 d, span/2)` rule only.
They are neither calibrated nor frozen. J2145/J1802 use GBT observations;
J2317 uses Arecibo. Median raw arrival-time uncertainties are respectively
0.245, 0.8635 and 0.206 microseconds; these are not fitted noise estimates.

## Model convention checks

The pinned PINT 1.1.5 models load without changing the released parameters.
For J2145 and J2317, H4 and STIGMA are absent and NHARMS is explicitly three.
Their Shapiro contribution is the linear third harmonic
`delay = -(4/3) H3 sin(3 orbital_phase)`. Across 256 synthetic orbital phases
per target, standalone delays and H3 derivatives agree with this expression
at relative errors below 6e-17. These checks exercise no observed residuals.
Full timing-design derivatives, rank and fit stability still need preparation.

- J2145: fitted H3 = **0.176960 ± 0.051491 microseconds**. Preserve H3 and all
  released orbital fit terms, including A1DOT.
- J2317: fitted H3 = **0.061015 ± 0.044530 microseconds**. This weak linear
  coefficient must not be clamped at zero or interpreted as a physical
  mass/inclination posterior. Its uncertainty range can include negative
  coefficients without implying a negative companion mass.
- J1802: H3, H4 and STIGMA are all absent; NHARMS is seven. The standalone
  runtime falls back to H3=0 and zero Shapiro delay. Successful model loading
  therefore does not establish suitable companion treatment.

The PINT ELL1H component removes the ELL1 M2/SINI parameters. The current
Recherche ELL1 adapter expects those parameters in its measured-Shapiro branch,
which explains the structural exclusion. The two H3-only cases do not require
conversion to M2/SINI or the native T2/H3/H4 route developed for EPTA J1012.
The latter's harmonic-convention issue is distinct from explicit NHARMS=3 here.
See [PINT's ELL1H documentation](https://nanograv-pint.readthedocs.io/en/latest/_autosummary/pint.models.binary_ell1.BinaryELL1H.html);
the evidence manifest binds the actual pinned source files used here.

## Noise and astrophysical context

J2145's released red spectrum has log10(A)=-13.3004617 and gamma=2.5302128.
Its 30-mode default reaches only 189.18 days. Covering the prospective 68.39-day
lower boundary needs at least 83 modes; the existing coverage rule selects
128, reaching 44.34 days. This is a computed preparation plan: no covariance
was built or calibrated. J2317 and J1802 have no released red component, which
must remain an explicit limitation rather than an assumption of no red noise.

J2145 has a white-dwarf companion; published VLBI work also identifies imperfect
solar-wind modelling as a possible source of timing-astrometry disagreement.
This motivates retaining chromatic/annual context during later preparation,
without claiming a diagnosis from this inventory.
[Deller et al. 2016](https://astrogeo.org/petrov/papers/psrpi_01.pdf).
J2317's white dwarf is independently identified optically.
[Dai et al. 2017](https://arxiv.org/abs/1705.02593).

J1802 has a published Shapiro-delay measurement and a white-dwarf mass of
0.78 ± 0.04 solar masses. Its supplied wideband model's missing terms therefore
need a source-consistent explanation or a separately bounded model comparison.
The reason for the omission is not established here; this is neither a claim
that the release is defective nor a nondetection of a companion.
[Ferdman et al. 2010](https://arxiv.org/abs/1002.0514).

## Smallest next step

Implement an explicit H3-only/NHARMS=3 branch and prepare **J2145-0750 first**.
Preserve its H3 nuisance term, check real-TOA derivatives, full-rank design and
orbital stability, and apply the existing red-frequency coverage rule before
assessing noise compatibility. Do not transplant the ELL1 M2/SINI derivative
patch unchanged. Reuse the existing wideband timing/DM and precision machinery.
J2317 follows after that first preparation succeeds. Keep J1802 and the four
previous nonlinear Shapiro holds separate. Calibration and observed launch are
later steps; this assessment grants no general ELL1H qualification.

## Evidence and closeout

[`results/research/ell1h-assessment-20260910`](../results/research/ell1h-assessment-20260910/)
contains the input manifest, corrected assessment, metadata correction and
closeout. The first output accidentally labelled linear red amplitude as log10;
the label was repaired, the model-only probe rerun, and initial output/code
retained. All other assessment fields are identical. No scientific result was
regraded. `tools/ell1h_assessment.py --data ASSESSMENT_DIR` is an assessment-only
script requiring the pinned science runtime, `PYTHONPATH=src`, single-thread
BLAS and offline execution; inputs remain outside Git. It refuses to overwrite
an existing assessment. It is not an observed operator command.

The canonical workbook receives four Work log records; all 358 Searches rows,
eight grades and historical notes remain preserved. Totals remain 783 registered
targets and 284 observed identities. All 71 publication-source hashes are unchanged.
No worker remains active. This closeout is saved locally; no release or push is
part of this assessment.
