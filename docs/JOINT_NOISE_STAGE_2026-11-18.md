# Second-stage joint-noise test: stages 1 to 3 and the earlier candidates

**18 November 2026 (UTC). The tool is built and checked. Three already-exposed
targets ran once each under it (stage 2), J2043+1711 ran once after the
nonlinear-orbit combination (stage 3) and the six other September candidates
ran once each. All ten are below the joint-noise threshold. No fixed-noise
crossing recorded so far survives the second stage.**

Owner decisions, 17 November 2026: "1. Grid profile 2. Second stage 3. Stop
after stage 2". Background: all nine threshold crossings so far weakened once
the noise was allowed to vary (see
[the held-target record](HELD_NONLINEAR_SEARCHES_2026-11-17.md) and
[the September development](JOINT_NOISE_IMPROVEMENT_2026-09-10.md)).

## What the second stage is

A target that crosses its fixed-noise threshold is tested again with the noise
fitted together with the signal. A candidate must pass both. The expensive
calibration is therefore needed only for targets that cross.

- **Statistic.** The same timing-marginalised objective as September, with the
  covariance determinant, minimised over a finite noise grid separately under
  noise-only and noise-plus-signal. `tools/joint_noise.py` is unchanged.
- **Noise grid (105 members).** No red noise, or a red power law at five
  strengths (−1 to +1 dex around a reference) and four slopes (reference −1,
  0, +1, +2, clipped to 0–7); each with one scale on the TOA white-noise
  block (0.95, 1.0, 1.05, 1.1, 1.2). The reference is the released red noise;
  where none was released it is the strength at which red variance equals the
  median white variance, at slope 3. Nothing is chosen from a periodogram.
- **Threshold.** The largest 1% order threshold across five null generators
  that do not sit on the grid: released; stronger and steeper (+0.25 dex,
  +0.5, white ×1.03); strong and steep (+0.75, +1.5, ×1.07); weak and shallow
  with inflated white (−0.75, −0.5, ×1.15); white only (×1.08). Each has 1,024
  calibration and 1,024 separate validation nulls. Calibration holds if any
  validation set's false-alarm interval lies wholly above 1%.
- **Injections.** Three periods × three amplitudes (1, 2 and 4 times the
  fixed-noise median worst-phase amplitude) × 32, per generator. Recovery
  means crossing the threshold with the period located within 5%.
- **Operation.** `tools/recherche joint-noise-stage prepare | calibrate |
  freeze | run`. Calibration reads no observed residuals; `run` writes
  `run01` once and refuses if the scope, calibration, observed file or code
  changed.

## Stage 1 checks

- The new covariance term matches September's saved per-member observed
  objectives for J1012 and J1752 to 7e-10 (12 chromatic-free members each).
- Each run compares the compressed statistic with a direct full-dimensional
  fit at two generators, one with a white scale: agreement 8e-12 or better.
- Unit tests: `tests/test_joint_noise_stage.py` (family, grid edges, white
  scale and determinant against a direct fit).

## Stage 2 results

| Quantity | J1752−2806 | J1012+5307 | J1738+0333 |
|---|---:|---:|---:|
| Role | regression | regression | quiet control |
| Fixed-noise statistic / threshold | 57.67 / 26.50 | 32.11 / 24.27 | 11.13 / 23.54 |
| Joint statistic, highest cell | 10.75 at 81.8 d | 18.86 at 223.0 d | 11.31 at 31.1 d |
| Joint statistic at the fixed-noise period | 10.75 | 13.94 | 11.31 |
| Joint threshold | 23.06 | 40.56 | 22.10 |
| September joint statistic / threshold | 11.54 / 23.54 | 11.34 (14.83 peak) / 33.40 | — |
| Status | below | below | below |
| Validation false alarms per generator (of 1,024) | 0, 5, 10, 2, 2 | 0, 4, 4, 0, 0 | 1, 5, 10, 2, 5 |
| Fitted noise on a grid edge | yes (white 0.95; steepest slope) | yes (white 0.95) | no |
| Calibration time | 12 s | 2.5 min | 1 min |

All validation intervals include 1%; the worst rate is 0.98%. The two
September candidates stay below threshold with numbers close to September's.
The quiet control stays quiet and its statistic barely moves (11.13 to 11.31).

**Sensitivity cost** (recoveries of 32, range across the five generators):

| Injected amplitude | J1752 60 / 201 / 301 d | J1012 60 / 199 / 601 d | J1738 60 / 200 / 594 d |
|---|---|---|---|
| 1× fixed-noise amplitude | 0–31 / 0–28 / 0–15 | 0–22 / 0–24 / 0–20 | 32 / 29–32 / 11–31 |
| 2× | 1–32 / 0–32 / 0–32 | 2–32 / 0–32 / 0–32 | 32 / 32 / 31–32 |
| 4× | 15–32 / 0–32 / 0–32 | 31–32 / 0–32 / 0–32 | 32 / 32 / 32 |

Where the generator is white or weak, signals at the fixed-noise amplitude
are mostly recovered. Under the strong, steep generator J1752 and J1012 lose
almost everything beyond 60 days. J1738, whose released red noise is very
steep, loses little.

## Limits found

- **J1012's threshold is set by one harsh generator** (40.56 from strong and
  steep; the others give 20.8–36.4). The largest-over-generators rule is
  conservative by design and costs sensitivity.
- **White scale 0.95 is too close.** J1752 and J1012 both fit at that edge.
  A wider range below 1 should be declared before stage 3, not adjusted
  after seeing a result.
- **Grid edges in nulls.** Generators at ±0.75 dex put many null fits on the
  amplitude edge (up to 98% for J1738's strong, steep generator, whose slope
  is clipped at 7).
- One global white scale, not per-backend; no chromatic process; linear
  timing model only; finite grid, not a posterior; no survey-wide
  false-alarm probability.
- These three targets were already exposed. The runs are development and
  regression, not new searches or confirmation, and no grade changes.

## Evidence

- `results/research/joint-noise-stage-20261118/`: per-target scope,
  calibration, freeze and result; September equivalence script and output;
  `closeout.json`; for stage 3 `j2043/` (with both nonlinear checks),
  `j2043-assessments.json` and `stage3-closeout.json`.
- Scopes: `config/{j1012,j1752,j1738}-joint-noise-stage.json`.
- Working folder: `../Project Recherche Data/joint-noise-stage-20261118/`.

## Stage 3: nonlinear orbit and J2043+1711

Owner instruction, 18 November 2026: "Proceed with stage 3".

**How the orbit is handled.** Re-fitting the orbit nonlinearly for every noise
member and every simulated null would take weeks (about 1.7 s per vector per
member, 189 members, more than 14,000 vectors). The frozen decision statistic
therefore treats the orbit as its eight derivative columns at the published
values, and `tools/joint_noise_nonlinear_check.py` measures what that costs
with the full nonlinear fit:

- **Simulated, before the freeze:** 42 vectors, six from each generator, re-fitted
  nonlinearly at the noise members the linearised fit selected. Largest change
  in the statistic 0.11 (tolerance 0.5, declared in the tool). No observed
  residuals read. A one-vector trial of the same check is kept alongside.
- **Observed, after the run:** the whole family repeated with the nonlinear
  orbit fit, once.

**Declared before the run** ([config](../config/j2043-joint-noise-stage.json)):
the same family rule as stage 2 with the white scale widened to 0.8–1.3
(nine values; 189 members). J2043 has no released red noise, so the reference
is the white-equivalent strength at slope 3: log10 A = −14.10, giving −15.1 to
−13.1 and slopes 2 to 5. That range covers NANOGrav's released wideband noise
chain without adjustment. Seven null generators: released white only; white
×1.08; reference red; stronger and steeper; strong and steep; weak, shallow
with white ×1.15; and 256 draws of the red term from the released chain.

| Quantity | J2043+1711 |
|---|---:|
| Fixed-noise statistic / threshold | 26.871 / 23.998 at 37.48 d |
| Joint threshold | 23.001 (per generator 19.69–23.00) |
| Validation false alarms per generator (of 1,024) | 3, 2, 3, 10, 9, 0, 2 |
| Joint statistic, highest cell | 18.419 at 37.57 d (the adjacent cell) |
| Joint statistic at 37.48 d | 18.240, amplitude 0.081 µs |
| Status | `BELOW_JOINT_NOISE_THRESHOLD` |
| Nonlinear-orbit joint statistic (check) | 18.446 at 37.57 d; difference +0.027; `CONSISTENT` |
| Fitted noise, no signal | red log10 A −14.60, slope 4, white ×1.0 |
| Fitted noise, with signal | red −15.10, slope 5, white ×0.95 (amplitude and slope on the grid edge) |
| Validation nulls at or above 18.419, per generator | 17 to 53 of 1,024 (1.8%–5.3%) |
| Compressed versus direct fit | 1e-13 |

The result agrees with the review's estimate (about 18–19 once red noise is
admitted) but comes from a procedure fixed before the run. The feature is
still in the upper few percent of noise-only simulations; it is not a
crossing. J2043's grade is unchanged (`INCONCLUSIVE_NOISE_SENSITIVE`); the
workbook row now carries the largest per-generator tail, 53 of 1,024, and the
[successor assessment](../results/research/joint-noise-stage-20261118/j2043-assessments.json).

**Sensitivity** (recoveries of 32 per generator at 1× the fixed-noise
amplitude, 0.129 µs): 22–32 at 60 days, 5–31 at 199 days, 0–28 at 590 days.
At 2×: 32, 31–32 and 0–32. The injection periods were fixed in the common
configuration and do not include 37.5 days.

**Notes.**

- In two of the 42 simulated vectors the linearised fit moved the orbit
  outside the ±5σ box at a cell away from the peak, where the boxed fit gives
  up to 1.6 less. The linearised statistic has no box. The statistic itself
  changed by 0.11 at most.
- `tools/joint_noise_stage.py` changed for stage 3, so the stage 2
  preparations can no longer be loaded. They were already consumed.

## The six other September candidates

Owner instruction, 18 November 2026: "Run them through". Each was prepared,
calibrated on simulated data, frozen and run once. All `run01` destinations
are consumed; do not rerun.

**Declared before the runs** (`config/{j1453,j1939,j1327,j1359,j0908,j1048}-joint-noise-stage.json`):
the stage 3 family rule (white scale 0.8–1.3). The four UTMOST targets have
released red noise and use the five stage 2 generators. J1453 and J1939 have
none, so the reference is the white-equivalent strength at slope 3 and they
use the six J2043 generators without the chain (no released chain for J1453
is on disk).

**J1939+2134 departures, declared before its run.**

- Its consumed fixed-noise result records a noise-only reduced chi-square of
  0.215: the released errors are about twice too large. The white-scale grid
  was widened down to 0.35 (13 values, 273 members) and two generators at
  white scale 0.47 were added (eight in all). This used the recorded
  chi-square and the September review's choice of 0.5, not the periodogram.
- It has 18,191 TOAs, too many for the tool's dense algebra. Its covariance
  is diagonal, so the data are reduced exactly to the 1,099-row subspace
  holding every timing, red-noise and signal column; the 17,092 dimensions
  outside it see only the white scale and enter as one term. A unit test
  compares this with the unreduced calculation, and the family member equal
  to the released noise gives back the fixed-noise statistic (149.353).

| Quantity | J1453+1902 | J1939+2134 | J1327−6222 | J1359−6038 | J0908−4913 | J1048−5832 |
|---|---:|---:|---:|---:|---:|---:|
| Source | NG15 wideband | InPTA | UTMOST | UTMOST | UTMOST | UTMOST |
| Fixed-noise statistic / threshold | 34.91 / 26.83 | 149.35 / 26.71 | 50.29 / 26.25 | 41.74 / 26.20 | 27.85 / 26.16 | 36.72 / 26.14 |
| Fixed-noise period (days) | 118.4 | 567.4 | 63.3 | 96.0 | 93.2 | 105.0 |
| Noise members / generators | 189 / 6 | 273 / 8 | 189 / 5 | 189 / 5 | 189 / 5 | 144 / 5 |
| Joint threshold | 22.35 | 29.07 | 23.26 | 23.79 | 25.37 | 24.69 |
| Validation false alarms per generator (of 1,024) | 5, 3, 4, 5, 13, 4 | 0, 0, 0, 1, 6, 0, 0, 0 | 1, 6, 10, 8, 1 | 3, 8, 11, 3, 1 | 0, 3, 2, 0, 0 | 0, 6, 4, 2, 1 |
| Joint statistic, highest cell | 18.61 at 118.4 d | 10.45 at 46.1 d | 6.13 at 74.2 d | 13.63 at 35.1 d | 11.31 at 31.8 d | 7.72 at 48.1 d |
| Joint statistic at the fixed-noise period | 18.61 | 1.82 | 0.53 | 7.49 | 7.24 | 1.58 |
| Status | below | below | below | below | below | below |
| Validation nulls at or above the observed value (of 1,024) | 17–46 | 376–812 | 891–1,006 | 80–240 | 278–476 | 687–835 |
| Released-noise member at the fixed-noise period | 34.91 | 149.35 | 0.62 | 7.30 | 6.40 | 1.63 |
| Fitted white scale (no signal) | 1.0 | 0.45 | 0.8 (edge) | 0.9 | 0.8 (edge) | 0.85 |
| Fitted noise on a grid edge | yes (shallowest slope) | yes (shallowest slope) | yes (white 0.8) | no | yes (white 0.8) | no |
| Calibration time | 37 s | 2 h 57 min | 36 s | 54 s | 20 s | 19 s |

- **J1453+1902** behaves like J2043: the peak stays at the same period but
  falls to 18.61, in the upper 1.8%–4.6% of noise-only simulations. Not a
  crossing.
- **J1939+2134**: the 567-day feature disappears (1.82) once the white scale
  and a shallow red term are fitted. The September review gave 15.2 with a
  coarser family.
- **The four UTMOST targets** need no noise fitting to lose their peaks. Their
  released red noise has 10 Fourier modes and reaches only 122–129 days; all
  four peaks are at shorter periods. Extending the same power law to 64
  modes, with nothing else changed, gives 0.6–7.3 at the fixed-noise period
  ("released-noise member" row).

**Sensitivity** (recoveries of 32 at 2× the fixed-noise amplitude, range
across generators): near 60 days J1453 32, J1939 32, J1327 9–32, J1359 32,
J0908 32, J1048 7–32; near 200 days 31–32 for J1453 and 0–32 or 2–32 for
the others; at the longest injected period 1–30 for J1453, 0–19 for J1359
and 0–30 or 0–32 for J1939, J1327 and J0908. Under the strong generators the second stage has
little power beyond 100–200 days for these data.

**Notes.**

- J1327 and J0908 fit at white scale 0.8, the lowest declared for them. The
  grid was not changed after the runs.
- J1048's released slope is 6.23, so the slope grid is clipped at 7 and has
  three values (144 members), and only two distinct injection periods.
- The UTMOST and J1939 noise-only tails differ from the September deep-review
  tails because the families differ. Grades are unchanged. The workbook's
  Candidate grades rows were updated to the second-stage tails afterwards, on
  the owner's instruction (see Next step).
- `tools/joint_noise_stage.py` changed for the reduction, so the J2043
  preparation can no longer be loaded. It was already consumed.
- Evidence: `results/research/joint-noise-stage-20261118/{j1453,j1939,j1327,j1359,j0908,j1048}/`
  and `candidates-closeout.json`.

## Sensitivity curve

Owner instruction, 18 November 2026: "Let's tackle long period weakness",
then "Yes, build it". The earlier injections used one amplitude at every
period, which made the second stage look weak at long periods. A
decomposition on simulated data shows two different things.

- **Mostly the noise, not the test.** `tools/joint_noise_sensitivity.py`
  compares the second stage with an ideal test that is told the true noise
  (its own 1% threshold over the same cells). Both are reported as the
  amplitude detected half the time, at 12 periods evenly spaced in log
  period, for every declared generator, with injections scaled to each
  period. For the four UTMOST targets the second stage needs 1.0–1.6 times
  the ideal amplitude under the released noise and at most 2.0 times under
  any generator, at every period. The ideal amplitude itself rises 30 to 55
  times between 30 days and the longest period, because the red noise does.
- **A real cost on a quiet pulsar.** For J1453+1902 the second stage needs
  1.2–1.4 times the ideal amplitude up to about 230 days, 1.6 at 457 days,
  2.4 at 640 days, 2.7 at 914 days and 4.0 at 1,279 days when the true noise
  is white. The red-noise members of the grid can absorb a slow sinusoid.
  This cost is stated, not removed.

Retrospective curves (simulated data only; the consumed runs are untouched),
amplitude detected half the time under the first-listed generator, in µs:

| Target | 30 d ideal / joint | about 100 d | about 200 d | Longest period | Largest joint amplitude over all generators, longest period |
|---|---:|---:|---:|---:|---:|
| J1453+1902 | 0.91 / 1.18 | 0.93 / 1.19 | 0.98 / 1.36 | 1.13 / 4.52 (1,279 d) | 82 |
| J1327−6222 | 94 / 110 | 516 / 569 | 1,800 / 2,100 | 5,170 / 6,360 (321 d) | 45,400 |
| J1359−6038 | 13.6 / 16.2 | 38.7 / 53.7 | 148 / 193 | 582 / 903 (319 d) | 5,360 |
| J0908−4913 | 34.5 / 42.5 | 92.8 / 129 | 359 / 435 | 1,110 / 1,590 (302 d) | 9,650 |
| J1048−5832 | 84.1 / 95.1 | 341 / 464 | 2,450 / 3,090 | 2,450 / 3,090 (202 d) | 16,100 |

J1939+2134 was computed at reduced size (8 periods, 16 injections per step),
so it is coarser than the rows above. Its first-listed generator is white
noise only; ratios to the ideal amplitude are given for that and for the
reference red-noise generator:

| Period (d) | Ideal / joint, white-only truth (µs) | Ratio, white-only truth | Ratio, reference red truth | Largest joint amplitude over all generators (µs) |
|---:|---:|---:|---:|---:|
| 30 | 0.57 / 0.74 | 1.3 | 1.4 | 0.89 |
| 84 | 0.57 / 0.74 | 1.3 | 1.3 | 1.10 |
| 234 | 0.58 / 0.89 | 1.5 | 1.4 | 6.33 |
| 449 | 0.87 / 1.79 | 2.1 | 1.4 | 35.0 |
| 634 | 0.62 / 1.91 | 3.1 | 1.9 | 80.3 |
| 1,078 | 0.66 / 6.63 | 10.1 | 2.6 | 249 |

This is the second quiet-data case and it agrees with J1453: when the true
noise is white, the red-noise members of the grid absorb a slow sinusoid and
the cost grows steeply beyond about 450 days, here to ten times the ideal
amplitude at the longest period.

J1752, J1012, J1738 and J2043 had no curve when this was written; curves
were rebuilt on 19 November 2026 from fresh development roots (see "Rebuilt
curves and J2043 under the fixed model" below).

**From now on.** `tools/recherche joint-noise-sensitivity --data --root` runs
after `calibrate` and writes `sensitivity.json`. `freeze` refuses without it
and binds its hash; `run` copies the per-period summary into `result.json`.
It reads no observed residuals and changes no threshold or statistic.

**Limits.** Half-detection amplitudes from a 14-step ladder (steps of 26%)
and 32 injections per step; conditional on the declared generators; the ideal
amplitude uses the median of a noncentral chi-square approximation. Not an
upper limit on any companion.

## Chain-bounded noise grid: tested, no gain, not adopted

Owner instruction, 18 November 2026: "Proceed with narrowing the noise grid to
further boost recovery". Tested on simulated data for J1453+1902 only; no
observed residuals were read, nothing was frozen and nothing was run.

**What was built.** An optional `chain_bound` in the family declaration
(`tools/joint_noise_stage.py`): at each grid slope, red members stronger than
the 99th percentile of the released chain's amplitude (draws within 0.5 of
that slope, first quarter discarded) are dropped. A chain generator can be
limited to the draws with most power at one cycle per span
(`strongest_fraction`). The rule was fixed before any curve was computed
(`config/j1453-joint-noise-chain-grid.json`). The NANOGrav 15-year wideband
chain for J1453 came from the archive already on disk.

**Result.** The chain removes 8 of the 20 red members (189 members to 117):
bounds −12.52, −12.82, −13.01 and −13.41 at slopes 2, 3, 4 and 5.

| Period (d) | Wide grid, joint / ideal | Chain-bounded, as calibrated (threshold 33.87) | Chain-bounded, threshold 23.94 (diagnostic) | No red members at all, threshold 21.45 (diagnostic) |
|---:|---:|---:|---:|---:|
| 320 | 1.4 | 2.0 | 1.4 | 1.3 |
| 457 | 1.6 | 2.6 | 1.7 | 1.3 |
| 640 | 2.4 | 3.8 | 2.5 | 1.5 |
| 914 | 2.7 | 4.0 | 3.0 | 2.0 |
| 1,279 | 4.0 | 5.8 | 4.3 | 1.5 |

White-only true noise; the diagnostic columns reuse the calibrated root with
one generator and a threshold taken from the other generators (5 periods, 32
injections per step, steps of 26%).

- **No gain from the bound.** With a comparable threshold the chain-bounded
  grid needs 4.3 times the ideal amplitude at 1,279 days against 4.0 for the
  wide grid: the same within the step size. The chain's own upper limit still
  allows red noise strong enough to absorb a slow sinusoid, because that limit
  comes from the same data.
- **Only removing red noise entirely recovers long periods** (1.3–2.0 times
  ideal). That is the fixed-noise assumption again, which the chain does not
  support and which produced the earlier crossings. Not adopted.
- **As calibrated it is worse.** The full-chain generator sets the threshold
  at 33.87 (9 of 1,024 validation nulls above it; the other five generators
  give 20.3–23.9). The large statistics all come from chain draws with slope
  below 1 and amplitude above −12.85, peak at 30–115 days, null fit at the
  top white scale (1.3). The grid has no slope below 2 and its white scale
  stops at 1.3, so it cannot fit that corner of the chain.
- **Caveat on that generator.** It adds the chain's red draws to the released
  white noise. In the chain, shallow strong red noise goes with lower white
  noise; drawing them separately overstates the total. A fair chain generator
  needs joint white-and-red draws, which the single white scale cannot
  represent.
- **Consequence for the consumed J1453 run.** Its wide grid has the same
  slope floor and white ceiling and was not calibrated against chain draws,
  so its threshold (22.35) is not shown to hold under them. The outcome does
  not depend on this: the statistic (18.61) was below threshold and a higher
  threshold leaves it below.

**Standing.** The option stays in the code, off by default, and is not part
of the standing rule. The J1453 root in
`../Project Recherche Data/joint-noise-chain-grid-20261118/j1453/` is a
development root: do not freeze or run it. Evidence:
`results/research/joint-noise-chain-grid-20261118/`. J1939 has no released
chain on disk and was not tested.

## Joint white-and-red chain draws: the high threshold remains

Owner instruction, 19 November 2026: "Have the chain noise model draw white
and red noise together to see if the threshold remains". Simulated data for
J1453+1902 only; no observed residuals read, nothing frozen or run.

**What was built.** A generator with `joint_white` in its declaration
(`tools/joint_noise_stage.py`) takes each chain draw whole: per-backend EFAC,
EQUAD, DMEFAC and DMEQUAD rebuild the white variance of every TOA and DM row
from the tim file, and the same draw's red noise is added. Before any draw is
used the released par values must reproduce the prepared covariance (J1453:
largest relative difference 7 × 10⁻¹⁶). Supported for an uncompressed
wideband source without released red noise.

**Result.** 256 draws, 1,024 calibration and 1,024 validation nulls each.

| Quantity | Wide grid (as used for the consumed run) | Chain-bounded grid |
|---|---:|---:|
| Status | `JOINT_NOISE_CALIBRATED` | `JOINT_NOISE_HOLD` (validation false-alarm excess) |
| Threshold with the joint chain generator | 30.01 | 33.96 |
| Set by | joint chain draws (red-only chain draws: 29.20) | joint chain draws (red-only: 33.87) |
| Largest threshold of the other generators | 21.40 | 23.20 |
| Joint-chain validation nulls above that threshold | 14 / 1,024 | 19 / 1,024 |
| Joint-chain validation nulls above 22.35 (the consumed run's threshold) | 96 / 1,024 | 101 / 1,024 |
| Joint-chain null fits ending on the grid edge | 86% | 87% |

- **The threshold was not an artefact.** Drawing white and red noise together
  makes it no lower. On the wide grid the 1% threshold under the chain is
  30.0, not 22.35; under joint chain draws the consumed run's threshold would
  be crossed by noise alone 9.4% of the time.
- **Cause: white noise, not red.** Across the chain the typical TOA
  uncertainty is 1.22 times the released (maximum-posterior) value (1st–99th
  percentile 0.86–1.75), the two backends move separately, and EQUAD draws
  raise single TOAs by a factor of 4 or more. One global white scale with a
  ceiling of 1.3 cannot follow that, so the null fit ends on the grid edge
  and the statistic is inflated. The red-only draws fail for the related
  reason given in the previous section.
- **Consumed results stand.** J1453's statistic (18.61) is below every
  threshold here; under joint chain draws 233 of 1,024 validation nulls reach
  it, so it is ordinary for noise. J2043 (18.42 against 23.00) was calibrated
  with red-only chain draws, not joint ones; it is below threshold either
  way. Grades and workbook candidate rows are unchanged.
- **What it means for the second stage.** For NANOGrav wideband targets a
  threshold calibrated without joint chain draws can be too low. A future
  second-stage test on such a target should include the joint generator, at
  the price of a higher threshold (about 15% in amplitude here), or the
  family should gain per-backend white scales and a wider range. Neither is
  yet part of the standing rule; that is an owner decision.

Evidence: `results/research/joint-noise-chain-joint-20261119/`; working roots
in `../Project Recherche Data/joint-noise-chain-joint-20261119/` are
development roots and must not be frozen or run.

## Per-receiver white noise: the threshold holds under joint chain draws

Owner instruction, 19 November 2026: "Proceed with steps 1-2" (step 1: fix
the white-noise model; step 2: state detection limits). Simulated data for
J1453+1902 only; no observed residuals read, nothing frozen or run.

**What was built.** `family.receiver_white` in the config replaces the one
global white scale. Backends are grouped by receiver (J1453: 430 MHz and
L-wide). Each group gets its own scale and, optionally, its own noise floor
added in quadrature to every TOA uncertainty (variance = scale² × (released² +
floor²)). Null and signal fits profile over all combinations together with
the red-noise grid.

**Result.** Same seven generators in every column (the original six plus 256
joint chain draws), 1,024 calibration and 1,024 validation nulls each.

| Quantity | One global scale (previous section) | Per-receiver scales only | Per-receiver scales and floors |
|---|---:|---:|---:|
| Family members | 189 | 1,029 | 6,300 |
| Status | `JOINT_NOISE_CALIBRATED` | `JOINT_NOISE_CALIBRATED` | `JOINT_NOISE_CALIBRATED` |
| Threshold | 30.01 | 27.77 | 23.04 |
| Set by | joint chain draws | joint chain draws | `strong_steep` (declared stress case) |
| Joint-chain 1% threshold | 30.01 | 27.77 | 22.10 |
| Largest threshold of the other generators | 21.40 | 21.49 | 23.04 |
| Joint-chain validation nulls above the threshold | 14 / 1,024 | 10 / 1,024 | 4 / 1,024 |

- **Floors, not scales, were the missing piece.** Scales alone (0.7–2.0)
  lower the chain threshold only to 27.8; the 430 MHz scale runs to its
  ceiling. With floors (430 MHz: 0, 2, 4, 8 µs; L-wide: 0, 0.7, 1.5 µs;
  scales 0.7–1.5) the chain's 1% threshold is 22.1, below the threshold the
  ordinary stress generator already sets. Every validation false-alarm rate
  is at or below 0.5%.
- **Cost in sensitivity is small.** Against the curve of the consumed run
  (threshold 22.35) the half-detection amplitude under released noise rises
  by 4–17% (117 days: 1.37 → 1.48 µs; 1,279 days: 4.52 → 4.83 µs). Ratios to
  the ideal test are 1.4–1.5 below 320 days and 4.3 at 1,279 days.
- **Edge fits remain common** (79–99% of null fits touch some grid edge).
  With six profiled dimensions that is expected, and a zero floor is not
  counted as an edge; the calibration and validation rates above are the
  check that matters, and they pass.
- **Consumed results stand.** This is a development root. J1453's consumed
  statistic (18.61, old family) is below every threshold; it was not and may
  not be recomputed under the new family. J2043 was recalibrated later the
  same day (section below).

**Adopted for future second-stage tests** (part of step 1, owner instruction
above; recorded in the [second-stage rule](CANDIDATE_GRADING.md#second-stage-rule)):
where a released noise chain exists for the target, the config must declare a
joint white-and-red chain generator and a per-receiver white family with
floors that span the chain's EQUAD range. Config to copy:
`config/j1453-joint-noise-receiver-white.json`.

Evidence: `results/research/joint-noise-receiver-white-20261119/`. Working
roots in `../Project Recherche Data/joint-noise-receiver-white-20261119/` are
development roots and must not be frozen or run.

## Rebuilt curves and J2043 under the fixed model

Owner instruction "Proceed with the three steps you've outlined" (19 November
2026), step 1. Simulated data only; no observed residuals were read and
nothing was frozen or run.

**Rebuilt curves.** J1752, J1738, J1012 and J2043 were prepared again from
their committed configs in fresh development roots. Each prepared input has
the same hash as the consumed run's and each calibration reproduces its
threshold (23.06, 22.10, 40.56, 23.00), so the curves describe the runs that
were made. Limits are in
[DETECTION_LIMITS_2026-11-19.md](DETECTION_LIMITS_2026-11-19.md).

**J2043 under the fixed white-noise model**
(`config/j2043-joint-noise-receiver-white.json`): per-receiver white scales
and floors for 430 MHz and L-wide (ASP and PUPPI pooled within each), plus a
joint white-and-red chain generator of 256 draws; 3,150 family members, eight
generators, 1,024 calibration and 1,024 validation nulls each.

| Quantity | As run (one global white scale) | Per-receiver white |
|---|---:|---:|
| Status | `JOINT_NOISE_CALIBRATED` | `JOINT_NOISE_CALIBRATED` |
| Threshold | 23.00 | 21.33 |
| Generator that sets it | — | `between_grid_stronger_steeper` |
| Joint-chain 1% threshold | not declared | 20.00 |
| Joint-chain validation nulls above the threshold | — | 9 / 1,024 |
| Half-detection amplitude, 30–90 days | 0.082–0.094 µs | 0.083–0.091 µs |

Every validation interval includes 1% (2 to 9 crossings of 1,024). The
threshold is lower than the consumed run's, and the curve is almost the same.
J2043's consumed statistic (18.42, old family) is below both thresholds; it
was not and may not be recomputed under the new family. Its grade is
unchanged.

**What the J2043 curve says about the September crossing.** That crossing was
0.089 µs at 37.48 days. The second stage detects a signal of that size about
half the time (50% amplitude 0.087–0.089 µs at 30–43 days; 95% amplitude
0.12 µs). The second-stage non-detection therefore does not exclude a real
signal of that size. Only independent data can settle it.

Evidence: `results/research/retrospective-curves-20261119/`. Working roots in
`../Project Recherche Data/retrospective-curves-20261119/` are development
roots and must not be frozen or run.

## Population limit and remaining targets

Steps 3 and 2 of the same instruction:
[POPULATION_LIMITS_2026-11-19.md](POPULATION_LIMITS_2026-11-19.md) combines
the saved fixed-noise curves of 271 pulsars into a limit on how common
companions can be (`tools/recherche population-limits`), and
[REMAINING_TARGETS_2026-11-19.md](REMAINING_TARGETS_2026-11-19.md) lists what
is left unsearched and proposes a first batch of MeerKAT binaries. That batch
is a proposal: nothing may be prepared or searched until the owner approves a
target list.

## Detection limits

The sensitivity curves are now turned into stated limits:
[DETECTION_LIMITS_2026-11-19.md](DETECTION_LIMITS_2026-11-19.md)
(`tools/recherche detection-limits`).

## Next step

None owed. Every fixed-noise crossing recorded so far has now been through
the second stage and none survives. On the owner's instruction ("Proceed with
1 & 2", 18 November 2026) the second stage is the
[standing rule](CANDIDATE_GRADING.md#second-stage-rule) for any future
fixed-noise crossing, and the six candidates' rows in Candidate grades now
carry their second-stage tails
([assessment](../results/research/joint-noise-stage-20261118/candidates-assessments.json)).
No new target has been searched. Narrowing the noise grid with a released
chain was tested and gives no long-period gain (section above); the
long-period cost on quiet pulsars stands as stated in the sensitivity curve.
Joint white-and-red chain draws were then built and the high threshold
remains with one global white scale; with per-receiver scales and floors it
holds at 23.0 (sections above), and that configuration is now required where
a released chain exists. Non-detections are stated as
[detection limits](DETECTION_LIMITS_2026-11-19.md). An independent check of
J2043 or J1453 still needs TOAs from another telescope; the sources are
ranked in
[INDEPENDENT_DATA_SOURCES_2026-11-19.md](INDEPENDENT_DATA_SOURCES_2026-11-19.md).
Any request for those data is the owner's decision and has not been made.
