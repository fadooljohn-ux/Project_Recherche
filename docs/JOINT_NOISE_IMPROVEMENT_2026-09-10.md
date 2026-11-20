# Bounded joint signal-and-noise improvement

Owner authorization: 10 September 2026, proceed with the four-step improvement.
Development targets: J1012+5307 and J1752-2806, already exposed observations.

## Frozen numerical procedure

Use each target's original eligible frequency cells and timing design. Extend the
released red spectrum to cover the original minimum period, using the existing
power-of-two rule (maximum 256 modes). Keep published white/auxiliary noise fixed.
Compare log-amplitudes at released value -0.5, 0, +0.5 dex and spectral slopes at
released slope -1, 0, +1, +2, clipped to [0,7]. This is a finite grid, not a
continuous optimizer or Bayesian posterior. For J1012 compare absence/presence of
a 0.3 microsecond, 100-day exponential nu^-4 covariance at 1400 MHz. J1752 is
single-band; do not pretend that an additional chromatic process is identifiable.

Marginalize the same linear timing parameters under both hypotheses; profile
circular coefficients and the declared noise grid separately under noise-only and
noise-plus-signal hypotheses. Include covariance and timing determinant terms.
Exactly compress directions affected only by fixed noise; verify against direct
full-dimensional GLS for two different covariances before simulations.

Per target, three predeclared generators: published power law with extended
coverage; amplitude +0.25 dex and slope +0.5 (between fitted grid points); slope
+1 with the declared chromatic term where identifiable. Each generates 256
calibration and 256 independent validation nulls. Set the development threshold
to the largest finite-sample 1% order threshold among those three calibration
ensembles. Report validation binomial intervals without pooling generators.

For each generator inject signals at three saved-grid periods (near 60 days,
the candidate, and 300/200 days), two amplitudes (original fitted amplitude and
five times that), and 16 random phases/noise realizations per cell: 96 injections
per generator. Every simulation and injection repeats the full declared grid
selection under both hypotheses. Original survey thresholds are not reused.

Scope is bounded development calibration and recovery, not global discovery FAP,
formal qualification or an attempt to optimize candidate significance. Report
boundary fits and validation failures; do not repeatedly widen the family to
obtain a favorable outcome. Save all failed attempts and completed checkpoints.

## Follow-up data

Reassess the already acquired J1012 EPTA timing model and J1752 TPA sampling/power.
No outgoing data requests or unsupported timing-model substitutions. Saved
observations already used in review are not fresh independent confirmation.

## Results and interpretation

Both development analyses completed. No original search, threshold or candidate
grade was replaced. These are reanalyses of exposed observations, not new survey
records or independent confirmation.

| Development result | J1012+5307 | J1752-2806 |
|---|---:|---:|
| Arrival-time measurements | 624, plus paired DM measurements | 145 |
| Red Fourier modes | 256 | 64 |
| Declared noise-grid members | 24 | 12 |
| Original candidate period (days) | 138.911 | 81.785 |
| Joint candidate statistic | 11.336 | 11.537 |
| New development threshold | 33.395 | 23.536 |
| Validation false alarms, three separate 256-trial sets | 0, 1, 0 | 0, 0, 2 |
| Candidate diagnostic tail across those generators | 0.603–0.685 | 0.218–0.401 |
| Noise-grid boundary reached | No | Signal fit reaches upper slope |
| Candidate exceeds development threshold | No | No |

J1012's strongest development peak is at 223.012 days, statistic 14.834,
also below threshold. J1752's strongest peak remains its original candidate.
These conditional tails are not planet probabilities, global survey FAPs or
sigma values. The 256-trial validation sets are small: their exact 95% binomial
intervals extend above 1%, including approximately 0–1.43% for zero exceedances.
The evidence shows no clear excess false alarms in the declared generators; it
does not prove universal 1% control or resolve extreme discovery tails.

The reusable engine marginalizes linear timing parameters through fixed-noise
contrasts and removes directions affected only by fixed noise. J1012 contracts
from 1,248 measurements to 604 relevant dimensions; J1752 retains 139 timing-free
dimensions. Direct full-dimensional GLS checks at two covariances agree to within
3.1e-12 in signal statistics; relative likelihood determinant differences also
agree. The original covariance conventions were reproduced before analysis.
No qualified scientific source file changed.

### Signal recovery and the cost of noise flexibility

Across both targets: 1,536 calibration nulls, 1,536 separate validation nulls and
576 injected realizations. Every realization follows the same model-selection
procedure as observations. Injection recovery requires crossing the new threshold
and locating the period within 5%; a strong peak at an unrelated period does not
count as recovery. These are circular, on-grid injected signals, not real planets.

The table gives the range of recovered counts across the three declared generators;
each individual cell contains 16 realizations. It is not a pooled probability.

| Target / injected period | Original-size signal | Five-times-size signal |
|---|---:|---:|
| J1012 / 59.94 days | 0/16 in each generator | 16/16 in each generator |
| J1012 / 138.91 days | 0/16 in each generator | 16/16 in each generator |
| J1012 / 301.15 days | 0/16 in each generator | 3–16/16 |
| J1752 / 60.20 days | 0–4/16 | 16/16 in each generator |
| J1752 / 81.78 days | 0–4/16 | 15–16/16 |
| J1752 / 201.37 days | 0/16 in each generator | 0–12/16 |

The reference timing amplitudes are 0.50381 microseconds for J1012 and
137.196 microseconds for J1752 (the original frozen grid fits, not later local
refinements). Larger signals remain recoverable, but the candidate-size signals
are generally below this procedure's demonstrated sensitivity under the tested
noise. This is a quantified sensitivity limitation, not evidence that all real
planets are removed, nor proof that either candidate is physically absent.
The slope boundary for J1752 and sparse amplitude/slope grid remain limitations;
we did not repeatedly expand the family in pursuit of a favorable result.

### Follow-up assessment

J1012's already acquired EPTA DR2full PAR lists 5,325 TOAs and a T2 binary model
with fitted orthometric H3/H4 terms. The current adapter cannot faithfully compare
that model; the measurements and terms are preserved. No independent fit or
claim of non-corroboration was fabricated. A bounded orthometric adapter is the
concrete enabling work for that dataset.

J1752's available later TPA data contain 400 TOAs over 50 observing days, spanning
MJD 58787.78–60047.16, after UTMOST's MJD 56967.38–58427.21. The saved focused
review already evaluated them, including phase/period uncertainty. Its median
conditional detection powers are 31.4%, 22.2% and 25.0% across the three noise
basis fits. These data remain underpowered and already reviewed; rereading them
is not new confirmation. Neither development target crossed its new threshold,
so no further candidate-triggered search was launched. No data-owner message was
sent and no new observations were acquired.

## Implementation and operator use

`tools/joint_noise.py` is the reusable fixed-grid likelihood engine for TOA-only
variable stochastic processes, retaining fixed auxiliary covariance. It rejects
rank-deficient timing models and signal cells. `tools/noise_development.py` binds
the two authorized fixtures, noise families, original eligible grids, seeds and
source hashes. The supported entry point is:

```sh
tools/recherche joint-noise prepare --data "$RECHERCHE_DATA" \
  --output "$NEW_DEVELOPMENT_OUTPUT" --target J1012+5307
tools/recherche joint-noise run --data "$RECHERCHE_DATA" \
  --output "$NEW_DEVELOPMENT_OUTPUT" --target J1012+5307
```

The analogous target is J1752-2806. These commands describe completed development;
do not create another destination to repeat it without a new scientific scope.
Read `result.json` once complete. Partial model checkpoints resume only with
unchanged scope, code and source bindings. All 36 completed model-checkpoint
hashes are archived in the external manifests; large matrices remain external.
The current two-target CLI is deliberately narrower than the reusable engine.

Future UTMOST preparations now use the same pre-calibration frequency-coverage
rule as the binary adapter. Coverage details and helper hashes are bound in the
preparation and freeze; changed implementations reject stale preparations. No
historical UTMOST preparation or calibration was modified. Existing source
adapters and formal qualification are not silently converted to joint-noise
inference. This is a bounded development capability, not automatic survey-wide
noise-posterior estimation or a new qualification result.

Before running a future dataset, select its noise family independently of any
new candidate, calibrate that full procedure, and report period-specific recovery
alongside false alarms. For these already exposed cases, the highest-value further
evidence would be genuinely additional calibrated observations; EPTA binary-model
compatibility is the available engineering route for J1012. J1752 needs better
follow-up sensitivity. No further numerical expansion is queued.

## Preservation and closeout

The initial preparation used the wrong saved amplitude key for both targets.
Both failures were retained, the importer corrected to `peak_amplitude_us`, and
fresh preparations succeeded before numerical execution. There were no numerical
execution failures. All 71 qualified source hashes and all 356 prior Search rows,
old candidate grades and operator notes are preserved. The canonical workbook
records both failed preparations/repair, both completed development analyses and
the follow-up/implementation closeout. Unique observed identities remain 282.
No scientific job is active, no new binary was launched, and development remains
local without a GitHub push.

[Machine-readable closeout](../results/research/joint-noise-development-20260910/closeout.json)
contains bindings to results, simulations, verification and follow-up evidence.
The bounded approach is informed by joint timing/noise analyses such as
[Niţu et al. (2022)](https://arxiv.org/abs/2203.01136) and by the distinction between
chromatic and achromatic noise illustrated by
[Larsen et al. (2024)](https://arxiv.org/abs/2405.14941). This implementation is a
finite-grid frequentist development procedure, not a reproduction of their
Bayesian analyses.
