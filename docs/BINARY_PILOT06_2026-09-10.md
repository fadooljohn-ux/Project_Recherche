# Binary pilot06: J0557+1551 and five-system queue closeout

Completed 10 September 2026 under the owner's authorization to prepare,
calibrate, freeze and run the final saved target. **J0557+1551 returned
NO_TRIGGER. The five-system queue is complete.** No additional candidate review
was triggered and no scientific code repair or repeated search was needed.

## Scope and preparation

NG15 v2.1.0 wideband inputs were extracted from the pinned archive, checked
against the saved intake hashes and reconciled with the master before selection.
The [discovery/timing study](https://arxiv.org/abs/1501.03746) describes J0557 as
a binary with a likely white-dwarf companion. This run searches for an additional
long-period circular signal; it does not recover or reclassify the known inner
companion.

The released ELL1 model has five fitted orbital parameters: PB, A1, TASC, EPS1
and EPS2. Their derivatives and local linearity passed, including the independent
null-likelihood and orbital-shift checks. The largest derivative discrepancy is
1.34e-8 and largest three-sigma nonlinear remainder is 1.44e-5 TOA sigma.
The joint TOA/DM design has full rank 59/59. The fixed released covariance and
all timing, dispersion and instrumental columns are retained.

As with the preceding conditional-branch cases, this release supplies no
red-noise component or fitted Shapiro terms. NO_RELEASED_RED_COMPONENT is
explicitly recorded before calibration. No missing stochastic component was
fitted to the observed peak. No general noise-posterior or arbitrary-binary
qualification is claimed.

## Frozen search results

| Measurement | Result |
|---|---:|
| TOAs, with paired wideband DM measurements | 47 |
| Observing-day epochs | 43 |
| Span | 1,667.379 days, approximately 4.57 years |
| Inner binary period | 4.846550 days |
| Additional-signal search range | 48.46550–833.68934 days |
| Calibration null realizations | 4,096 |
| Diagnostic injections recovered | 95 / 96 |
| Full / eligible frequency cells | 164 / 148 |
| Projection/annual excluded cells | 16 |
| Frozen threshold, delta chi-square | 19.410073 |
| Median worst-phase 95%-recovery amplitude | 7.45148 microseconds |
| Worst-phase sensitivity range | 6.35885–12.93238 microseconds |
| Strongest eligible period | 49.624365 days |
| Peak amplitude | 3.70938 microseconds |
| Peak delta chi-square | 8.437573 |
| Fraction of threshold | 43.470% |
| Final disposition | NO_TRIGGER |

The target-specific threshold uses the fixed one-grid conditional 1% Gaussian
allowance. Diagnostic injections cover three eligible periods and two phases,
with 16 realizations per cell. Their 95/96 recovery is a bounded check, not a
universal empirical recovery probability or population completeness measurement.
Sensitivity is for on-grid circular signals under the supplied covariance and
timing design, not a posterior mass limit.

The null chi-square is **30.901259 for 35 degrees of freedom**, reduced
chi-square **0.882893**, conditional upper tail **0.666347**. There is no excess
scatter in this check and no automated noise-adequacy flag. This does not prove
the absence of correlated noise or omitted timing effects. At the saved peak,
the independent full-design fit reproduces post-peak chi-square **22.463685**,
with rank 61. No execution failure occurred.

## Completed five-system queue

| Target | Original observed result | Current interpretation |
|---|---|---|
| J1012+5307 | Threshold crossing at 138.911 days | INCONCLUSIVE_NOISE_SENSITIVE; EPTA fixed-period follow-up NOT_CORROBORATED |
| J1738+0333 | NO_TRIGGER | Preserve conditional search and sensitivity |
| J1125+7819 | NO_TRIGGER | Preserve released-noise and omitted-Shapiro limitations |
| J0509+0856 | NO_TRIGGER; near threshold at 52.905 days | Excess residual scatter documented separately; threshold unchanged |
| J0557+1551 | NO_TRIGGER | Final queue member completed |

These searches have different sensitivities and historical conditional
allowances. They are not a pooled occurrence-rate experiment. The queue contains
four original nondetections, one preserved crossing and **zero confirmed new
planets**. The [reconciliation](../results/observed/binary-pilot06-20260910/five-system-queue.json)
binds each original result by hash. Earlier measured-Shapiro holds and other
binary-model exclusions remain separate from this completed queue.

## Register, evidence and next step

The master updated at observed closeout and again for calibration/context and
queue reconciliation. It now contains **783 targets, 284 observed identities
and 358 search/refinement records**. All 357 previous Search rows, eight candidate
grades and operator notes are preserved. All 71 publication-source hashes are
unchanged. No push or release was performed; the working science is local.

The [closeout](../results/observed/binary-pilot06-20260910/closeout.json) and
[archive bindings](../results/observed/binary-pilot06-20260910/archive-bindings.json)
preserve selection, preparation, calibration, freeze, null maxima, sensitivity,
periodogram and result. Archival JSON uses installation-agnostic paths with
original and archived hashes recorded separately. Full inputs remain in
RECHERCHE_DATA/binary-pilot06-20260910. Its run01 destination is consumed.

The recommended next scope is a **bounded compatibility assessment of the
three saved ELL1H exclusions: J1802-2124, J2145-0750 and J2317+1439**. Inspect
their released orthometric Shapiro parameters, runtime conventions and available
coverage, reusing the native orthometric work where applicable. Determine whether
one is a small, supportable adapter extension before calibration or search.
Keep all measured terms and the four existing nonlinear Shapiro holds intact.
This recommendation has not been launched and is not general binary support.
No job remains active.

The consumed workflow used `tools/recherche binary-pilot` actions `select`,
`prepare`, `calibrate`, `freeze` and `run`, with
`config/binary-pilot06-selection.json`. Use saved evidence for inspection; do not
rerun science to update documentation or the workbook.
