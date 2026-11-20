# Binary pilot05: J0509+0856

Completed 10 September 2026. The owner authorized preparation, calibration,
freeze and one observed search of the next saved binary target. **J0509+0856
returned NO_TRIGGER**, with a feature close to the frozen threshold and an
explicit residual-noise caveat. No additional candidate review was triggered.

## Scope and preparation

The previously unsearched NG15 v2.1.0 wideband observations were extracted from
the existing pinned archive and matched to the intake hashes and canonical
master. The saved [five-system assessment](ELL1_OMITTED_SHAPIRO_ASSESSMENT_2026-09-09.md)
identifies this as a likely white-dwarf system; its
[discovery study](https://arxiv.org/abs/1906.05071) supplies the physical context.
This is a search for an additional long-period circular signal, not a recovery
of the already-known 4.908-day inner companion.

The released ELL1 model omits fitted Shapiro terms and supplies no red-noise
component. Both assumptions remain explicit. The preparation records
NO_RELEASED_RED_COMPONENT and retains the released wideband TOA/DM covariance.
No observed peak was used to choose a different noise model, period range or
threshold. The recently developed finite noise-grid procedure was not silently
substituted for the existing calibrated search.

PB, A1, TASC, EPS1 and EPS2 are projected jointly with the timing, dispersion
and instrumental terms. All derivative and three-sigma local-linearity checks
passed; the largest derivative discrepancy is 1.34e-8 and largest nonlinear
remainder is 4.26e-5 TOA sigma. The joint design has rank 53/53, and the independent
null-likelihood check agrees. No preparation repair or retry was needed.

## Frozen execution

| Measurement | Result |
|---|---:|
| TOAs, with paired wideband DM measurements | 66 |
| Observing-day epochs | 38 |
| Span | 1,301.461 days, approximately 3.56 years |
| Inner binary period | 4.907977 days |
| Additional-signal period range | 49.07977–650.73070 days |
| Calibration null realizations | 4,096 |
| Diagnostic injections recovered | 91 / 96 |
| Full / eligible frequency cells | 124 / 107 |
| Projection/annual excluded cells | 17 |
| Frozen threshold, delta chi-square | 18.850904 |
| Median worst-phase 95%-recovery amplitude | 7.72952 microseconds |
| Worst-phase sensitivity range | 6.58771–13.17976 microseconds |
| Strongest eligible period | 52.904935 days |
| Peak fitted amplitude | 5.06766 microseconds |
| Peak delta chi-square | 18.048934 |
| Fraction of threshold | 95.746% |
| Observed disposition | NO_TRIGGER |

The threshold retains the one-target conditional 1% Gaussian allowance over the
fixed grid. The 96 injections cover three eligible periods and two phases, with
16 realizations each; they are a bounded diagnostic, not a universal empirical
95% recovery demonstration or population completeness. Sensitivities apply to
on-grid circular signals under the supplied fixed covariance and timing design.
They are not posterior companion-mass limits.

The saved peak agrees with an independent full-design fit: post-peak chi-square
114.983994, rank 55. Its statistic is 0.801969, or 4.254%, below the frozen
threshold. Proximity alone does not make it a candidate or authorize retrospective
threshold changes. Its fitted amplitude is a residual-sinusoid estimate, not a
planet measurement.

## Noise-model limitation

The null chi-square is **133.032928 for 79 degrees of freedom**, giving reduced
chi-square **1.683961** and conditional upper-tail probability **0.00013795**.
There is excess residual scatter under the fixed released model. The software's
coarse automated flag starts at reduced chi-square >=2, so its flag is false;
that must not be reported as proof of adequate noise modeling.

This mismatch weakens claims about the precision of the conditional sensitivity
and false-alarm accounting. It does not establish which stochastic or timing
process is responsible. No red process was invented or tuned after seeing the
52.9-day feature, and no alternate observed search was run. Preserve this
NO_TRIGGER result and the explicit limitation. A future targeted noise assessment
would be a new declared follow-up, not a replacement result.

## Closeout and next step

The canonical workbook updated immediately after the terminal search and again
with preparation and noise-context entries. It contains **783 targets, 283
observed identities and 357 search/refinement records**. All 356 prior search
rows, eight candidate-grade rows and operator notes remain intact. All 71
preserved publication-source hashes are unchanged. No scientific code repair,
new candidate, execution failure, additional search, push or release occurred.

The [machine-readable closeout](../results/observed/binary-pilot05-20260910/closeout.json)
and [archive bindings](../results/observed/binary-pilot05-20260910/archive-bindings.json)
preserve the selection, preparation, freeze, calibration nulls, sensitivity
arrays, periodogram and original result. Archival JSON uses installation-agnostic
paths and records original and archived hashes separately. Full inputs remain in
RECHERCHE_DATA/binary-pilot05-20260910. Its run01 destination is consumed.

The next target is **J0557+1551**, the final unsearched member of the saved
five-system omitted-Shapiro queue. It requires its own preparation, explicit
noise/model assessment, calibration and launch scope. No run remains active.

## Operator commands

These document the consumed workflow; do not rerun it to refresh documentation.

```sh
tools/recherche binary-pilot select --data "$NEW_DATA" --archive "$NG15_ARCHIVE" \
  --inventory "$NG15_INVENTORY" --selection config/binary-pilot05-selection.json
tools/recherche binary-pilot prepare --data "$NEW_DATA" --target J0509+0856
tools/recherche binary-pilot calibrate --data "$NEW_DATA"
tools/recherche binary-pilot freeze --data "$NEW_DATA"
tools/recherche binary-pilot run --data "$NEW_DATA" --target J0509+0856
```
