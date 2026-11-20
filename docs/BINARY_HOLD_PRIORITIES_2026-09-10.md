# Remaining measured-Shapiro binary holds: priority assessment

**10 September 2026 — assessment complete; all four holds retained.**

Recommend **J1857+0943 (B1855+09)** for the first bounded nonlinear-Shapiro
compatibility prototype, then J0740+6620, J0613−0200 and J2043+1711. This order
balances available observations, prospective coverage and implementation effort.
It estimates neither the probability of planets nor calibrated search sensitivity.
J1802−2124 remains parked under its separate preparation-adequacy hold.

## Evidence and scope

The assessment verified all eight original PAR/TIM hashes against the saved
pilot selections and all four public failure records against the external copies.
It inspected the final timing-file text and primary literature. No timing fit,
new preparation, covariance calculation, calibration or observed search ran.
The four saved preparation failures remain evidence of the existing adapter's
local-linear limitation, not failed planet detections.

Reproduce the metadata inventory from the repository root with standard Python:

```sh
python3 tools/binary_hold_assessment.py \
  --data "$RECHERCHE_DATA" \
  --output /tmp/recherche-binary-hold-assessment.json
```

Use a new output destination. The source inputs must be the hash-bound original
files retained under `binary-pilot01-20260909` and `binary-pilot02-20260909` in
`RECHERCHE_DATA`. The script refuses to overwrite evidence. Numerical metadata
and input bindings are in
[assessment.json](../results/research/binary-hold-priorities-20260910/assessment.json).
Ranking is an explicit qualitative decision rather than an inferred score.

## Comparison

All four are NG15 v2.1.0 wideband ELL1 datasets with paired dispersion
measurements and fitted companion mass/inclination terms.

| Priority | Target | TOAs / site days | Raw span, years | Median raw TOA uncertainty, us | Prospective outer periods, days | Released red component |
|---|---|---:|---:|---:|---:|---|
| 1 | J1857+0943 / B1855+09 | 364 / 149 | 15.59 | 0.388 | 123.3–2000 | Present |
| 2 | J0740+6620 | 360 / 226 | 6.31 | 0.454 | 47.7–1152.5 | Absent |
| 3 | J0613−0200 | 423 / 327 | 15.04 | 0.188 | 30–2000 | Present |
| 4 | J2043+1711 | 459 / 225 | 9.05 | 0.210 | 30–1653.0 | Absent |

Site days count integer site-MJD bins, not independent measurements. Raw
uncertainties precede published noise scaling and timing projection; they do not
rank final sensitivity. Prospective bounds apply the existing rule
`max(30 d, 10 inner periods)` to `min(2000 d, half the span)` to site times;
future preparation must establish actual barycentric bounds. Absence of a
released red component is a model limitation, not proof of white residuals.

| Target | Published relative M2 uncertainty | Saved maximum Taylor remainder, TOA sigma | Interpretation |
|---|---:|---:|---|
| J1857+0943 | 3.68% | 0.401 | Smallest recorded curvature among the three comparable pilot02 checks |
| J0740+6620 | 2.17% | 0.924 | Tight mass constraint but nearly edge-on geometry |
| J0613−0200 | 27.64% | 6.794 | Broad mass uncertainty; earlier adapter and step convention |
| J2043+1711 | 3.92% | 1.814 | Larger pilot02 curvature and additional noise questions |

These remainders quantify a timing approximation error. They are **not detection
sigma, false-alarm evidence or companion significance**. J0613's earlier
record also contains a derivative mismatch predating the derivative repair; it
has not been rerun with the current adapter. Its numerical remainder should not
be treated as a precision-equivalent comparison with pilot02. Among the three
pilot02 cases the saved relative derivative errors are below 8e-6, while the
nonlinear remainders still exceeded the preparation criterion.

## Why this order

**J1857+0943 first.** It combines the longest retained span, a relatively narrow
mass constraint and the smallest comparable local nonlinear remainder. Its
released orbital fit has seven explicit orbital/Shapiro terms and no fitted
PBDOT; the other three include PBDOT. That makes it a useful first test of the
necessary nonlinear interface. The cost is real: only 149 site days, a 123-day
lower search bound and published red noise. Preparation must cover the searched
red-noise frequencies and demonstrate usable sensitivity after timing/noise
uncertainties; no improvement is guaranteed.

**J0740+6620 second.** It is a well-constrained, nearly edge-on system with
published high-cadence timing work that makes it a useful second benchmark.
Its saved baseline is the shortest and raw uncertainty the largest in this
set. Near-edge-on geometry still requires nonlinear inclination treatment.
The published GBT/CHIME work provides model context, not a new independent
planet test in this assessment. [Fonseca et al. (2021)](https://arxiv.org/abs/2104.00880)

**J0613−0200 third.** Its raw precision and long coverage offer substantial
potential return, including the full prospective 30–2000-day range. Broad
Shapiro uncertainty, released red noise and published variable interstellar
scattering make it a more involved first prototype. The scattering study used
different observations; it motivates scrutiny rather than proving inadequacy of
this saved wideband model. [Main et al. (2020)](https://arxiv.org/abs/2009.10707)

**J2043+1711 fourth.** It has good raw precision but a larger comparable
nonlinear remainder. A recent nonlinear timing study reports intrinsic red-noise
evidence in its NG12.5 data, although this saved NG15 wideband model omits a
red component. That finding must not be transplanted as an NG15 covariance.
The same study describes combining exact timing terms with linear nuisance
parameters, supporting a bounded hybrid implementation.
[Kaiser et al. (2026)](https://arxiv.org/abs/2608.18047)
Separate work discusses anomalous acceleration and a possible very wide stellar
companion or flyby. Those explanations lie outside the prospective short-period
search and do not establish a planet; they add interpretation work.
[Anomalous-acceleration study (2024 preprint)](https://arxiv.org/abs/2407.06482)

The third/fourth ordering is less decisive: J2043 has a narrower published mass
constraint, while J0613 offers the longer baseline and an explicit released red
model. Revisit that order after the first prototype gives an actual cost estimate.
None of these well-studied systems is claimed to be a low-traffic discovery field.

## Recommended next bounded implementation

1. Add a target-specific J1857 path that evaluates Shapiro delay nonlinearly
   across physical companion-mass/inclination uncertainty. Preserve the released
   inputs and old failed preparation. Do not bypass the existing linearity check
   or freeze uncertain Shapiro parameters to their point estimates.
2. Retain timing, dispersion and orbital uncertainty. Use the existing linear
   nuisance treatment where valid, evaluating coupled orbital terms nonlinearly
   if the target's diagnostics require it. Avoid introducing a general sampling
   framework before this one-target need is demonstrated.
3. Run one bounded compatibility preparation with explicit red-frequency
   coverage, noise adequacy, numerical checks and signal-information loss.
   Diagnose concrete implementation errors in that successor while retaining
   failed evidence. A finite diagnostic grid is not automatically a posterior
   marginalization or a qualified observed-search runtime.
4. Record its terminal result in the master. If compatible, define how the exact
   same nonlinear/noise procedure will operate in calibration and observed
   execution before requesting target-specific calibration. If still held, report
   the specific limitation; do not broaden the model search automatically.

This implementation has **not** run. No new threshold, annual mask, sensitivity
curve or launch-ready target is produced by the present assessment.

## Closeout

The master receives four target-priority entries and one assessment closeout in
its Work log. Counts remain **783 registered targets, 286 observed identities,
360 search/refinement records and eight candidate grades**. All historical cells,
original failures and the 71 publication-source bindings are preserved. No job
is active; the monitor remains paused. This is a local development update, not a
repository push or new release.

[Workbook receipt](../results/research/binary-hold-priorities-20260910/workbook-closeout.json)
and [closeout](../results/research/binary-hold-priorities-20260910/closeout.json)
bind the final artifacts.
