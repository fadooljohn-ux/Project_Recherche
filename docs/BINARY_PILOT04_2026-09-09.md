# Noise-frequency coverage improvement and binary pilot04

9 September 2026. The authorized improvement and next binary search are complete.
J1125+7819 returned **NO_TRIGGER** in one frozen observed search. J1012+5307's
earlier search and review remain unchanged; this work recomputed a covariance
matrix for verification, not its observed periodogram or calibration.

## What changed

The binary preparation now records explicit red-noise frequency coverage before
calibration. For a released linear Fourier red-noise basis with span T and
minimum searched period P, at least `ceil(T/P)` modes are needed to reach the
search band's highest frequency. A sufficient released count is retained.
Otherwise the adapter extends it to the next power of two, up to the bounded
256-mode limit, while keeping the released spectral amplitude and slope fixed.
It checks the resulting PINT frequency array rather than relying on the requested
count alone. Unsupported logarithmic layouts or larger required extensions are
held explicitly.

The choice uses sampling and the planned search bounds; it does not inspect an
observed peak. The covariance, coverage receipt and helper-code hash are bound
into preparation and freeze. Changed covariance receives its own calibration.
Previously consumed searches are preserved with their original implementation
hashes. The qualified scientific source was not changed.

A released model with no red-noise component receives
`NO_RELEASED_RED_COMPONENT`. Its released white-noise model is retained. This
status does not establish the absence of correlated noise, and adequate frequency
coverage alone does not validate a noise posterior or all possible processes.
Any extrapolation remains a stated conditional model assumption.

For the saved J1012 sampling, the old 30-mode basis stops at 189.09 days, whereas
the original search reaches 30 days. The new rule requires at least 190 modes and
selects 256, reaching 22.16 days. A covariance-only verification used a 50-day
scope, for which the rule selects 128 modes, and reproduced the retained
128-mode review covariance exactly (relative difference zero). It read no
observed residuals and launched no search or calibration. The previous
139-day candidate remains **INCONCLUSIVE_NOISE_SENSITIVE** based on its saved
review, where the statistic fell from 32.11 to 5.60 with broader red noise.
The 256-mode rule is not a newly executed J1012 search result.

## Next-target execution

J1125+7819 was the next ranked unsearched ELL1 system with a likely white-dwarf
companion. Its [discovery/timing study](https://par.nsf.gov/servlets/purl/10315467)
supports the likely helium-white-dwarf interpretation and discusses its variable
dispersion measure. This is a search for an additional long-period circular
signal, conditional on the released binary/dispersion model, not a recovery of
the already-known inner companion.

The NG15 wideband PAR supplies no red-noise component and omits fitted Shapiro
parameters. Both choices remain explicit. No optical mass/inclination measurement
or full nonlinear Shapiro inference is claimed. Free PB, A1, A1DOT, TASC, EPS1
and EPS2 are projected jointly with the other timing, DM and instrumental terms.

| Measurement | Result |
|---|---:|
| Arrival-time measurements | 206 |
| Observing-day epochs | 141 |
| Span | 2,299.53 days, approximately 6.30 years |
| Inner binary period | 15.35545 days |
| Frozen additional-companion range | 153.554–1,149.765 days |
| Joint design columns / rank | 96 / 96 |
| Calibrating noise realizations | 4,096 |
| Diagnostic injections recovered | 95 / 96 |
| Full / eligible frequency cells | 66 / 54 |
| Frozen threshold, Δχ² | 17.58965 |
| Typical worst-phase 95%-recovery amplitude | 1.40781 μs |
| Strongest observed eligible period | 1,045.24082 days |
| Peak amplitude | 0.70820 μs |
| Peak Δχ² | 9.61149 |
| Null reduced χ² | 1.12333 |
| Final observed disposition | NO_TRIGGER |

Preparation passed derivative, local-linearity, orbital-shift, rank and pulse
connection checks. The frozen peak's likelihood improvement agreed with an
independent full-design fit. The threshold uses a one-target 1% conditional
Gaussian allowance. Sensitivity is for on-grid circular signals under the fixed
supplied covariance/design, not a posterior upper limit or population completeness.
The projection/annual mask excludes twelve cells, which are preserved.
There were no preparation, calibration or observed-execution failures and no
automated noise-adequacy flags. No compelling crossing required a deep review.

## Closeout and next steps

The canonical master was updated immediately after the observed run and again
for the development closeout. It now holds **783 target rows, 282 observed pulsar
identities and 356 search/refinement records**, preserving all 355 earlier Search
rows, candidate grades and operator notes. The original J1012 crossing and its
review remain intact. No job is active. New code and evidence remain local.

J0509+0856 is next in the saved likely-white-dwarf queue, followed by J0557+1551.
Each needs its own preparation, explicit noise/model assessment, calibration and
new execution instruction. Repeating J1012 on the same observations would be a
declared follow-up reanalysis, not an independent confirmation or a fresh blind
search. The existing review already supplies the relevant evidence of noise
sensitivity; no repeat was needed to verify this improvement.

## Operator references

The implementation is `tools/binary_noise_coverage.py`, integrated into
`tools/recherche binary-pilot`. New selections carry `noise_coverage_rule` and
preparations preserve its result and implementation hash. Explicit per-target
Shapiro settings can be supplied as `target_models[target]` in a selection request;
fixed mode requires `fixed_shapiro` with `mass_solar` and `inclination_degrees`.
Do not edit an existing frozen selection.

```sh
tools/recherche binary-pilot select --data "$NEW_DATA" --archive "$NG15_ARCHIVE" \
  --inventory "$NG15_INVENTORY" --selection config/binary-pilot04-selection.json
tools/recherche binary-pilot prepare --data "$NEW_DATA" --target J1125+7819
tools/recherche binary-pilot calibrate --data "$NEW_DATA"
tools/recherche binary-pilot freeze --data "$NEW_DATA"
tools/recherche binary-pilot run --data "$NEW_DATA" --target J1125+7819
```

These commands document the consumed run; the selection guard prevents selecting
an already-registered target as new work. Read the saved
[closeout and evidence](../results/observed/binary-pilot04-20260909/closeout.json).
Raw inputs and executable bindings remain external. Path-redacted archival
preparation/freeze views retain the original file hashes.
