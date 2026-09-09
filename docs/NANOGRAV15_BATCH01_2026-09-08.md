# NANOGrav 15-year batch 01

The owner authorized all 16 cases on 2026-09-08. This includes input preparation,
calibration, a fixed search definition and one observed search per target, with
master-workbook updates after each terminal run. All 16 observed searches are complete: 15 NO_TRIGGER and one periodic-signal candidate, J1453+1902.

Inputs are the public [NANOGrav v2.1.0 wideband release](https://zenodo.org/records/16051178).
Six targets are new to Recherche and ten have prior searches using other data.
B1937+21 is excluded because this same release was already searched. J1024−0719
is excluded as a known wide binary. Narrowband is an alternate reduction of the
same observations and is not a second confirmation dataset.

## Search definition

Each target retains its released PINT timing model and fixed published noise
covariance. The likelihood includes TOA residuals in seconds and wideband DM
measurements in pc/cm³. Free spin, astrometric, dispersion and instrumental timing
columns are projected. An achromatic planet delay enters only the TOA rows.
No fitted noise waveform is subtracted and no noise parameters are tuned to peaks.

Search circular periods from 30 days to min(2,000 days, prepared TDB span / 2),
with oversampling 5. The maximum is determined from timestamps before any observed
grid scan. Per-target calibration uses 4,096 Gaussian nulls and the existing
projection mask (retained power at least 0.2 and condition number at most 1e10).
The threshold retains the existing conservative grid/target union bound for a
1% conditional false-alarm allowance across these 16 searches. This allowance
applies to this batch under the fixed Gaussian noise/design assumptions, not
cumulatively to all Recherche campaigns. Report 95% on-grid circular-signal
sensitivity separately from measured peaks and candidate status.

The generic detector already supports auxiliary measurement rows. A localized
repair pads its final likelihood-audit template with zeros for those rows, so
its independent fit agrees with the scanner. A correlated TOA/DM regression
recovers a 50 μs injected orbit and verifies the saved likelihood result.
The six focused adapter checks passed. Qualified source code is unchanged.

## Execution and records

Supported commands are `tools/recherche ng15-batch inventory|prepare|calibrate|freeze|run
--data DATA_ROOT`, with `--target TARGET` for prepare/run. `run` updates the
existing master workbook automatically. Repairs to bookkeeping use
`tools/recherche master-workbook DATA_ROOT --ng15-observed`; they never rerun science.

Data root: `../Project Recherche Data/ng15-batch01-20260908/`.
The baseline preserves 215 historical scientific record hashes and the prior
master workbook. Existing searches and operator notes remain intact; ten new
NG15 records link to existing pulsars. Inputs, profiles, calibrations and code
are bound before execution. Peak likelihoods are checked with an independent
full-design fit. Terminal closeout will report all 16 outcomes, threshold
crossings and noise-adequacy flags without treating a periodic signal as a
confirmed planet.

## Verified intake

The release archive SHA-256 is
`91476bf20d4c8baa9f5ad39c6e114b581478a5a7e269876489cafc8f62c5708f`;
it matches the publisher's MD5. The 76 primary-directory PINT files resolve to
68 complete pulsar models plus eight telescope-specific variants. The complete
models contain 51 known binaries (including the explicit J1024−0719 exception),
17 singles, and 16 selected singles after preserving B1937's prior search.
B1937's original PAR/TIM files are byte-identical to this release.

The selected files contain 3,671 usable TOAs and paired wideband DM measurements.
All use Arecibo or GBT. Released observatory and BIPM2019 clocks match the
existing bound resources exactly. The actual wideband timestamps set coverage:
J1944+0907 has 3,296 days, and J0030+0451 has 724 usable TOAs. Paper table summary
figures (12.5 years and 727 TOAs respectively) do not override these input files.

## Completed observed searches

All 16 runs completed without execution failures or the predefined noise-adequacy
flag. Each reused its frozen calibration. Saved peak decisions and independent
full-design likelihood checks agree. The master was updated after every run and
now contains 691 targets, 220 targets with observed searches, 231 search/refinement
records, one periodic-signal candidate and zero confirmed new discoveries.
All 215 historical scientific records and existing operator notes are preserved.

**J1453+1902 crossed its frozen threshold:** Δχ² = 34.9142 against 26.8265,
at 118.4273 days with a fitted sinusoidal timing amplitude of 1.5262 μs.
The independent full-design χ² is 168.7615263647758, agreeing with the scanner's
168.7615263647760. Null reduced χ² is 1.2573; after the peak fit it is 1.0548.
The existing noise-flag rule (reduced χ² ≥ 2) did not fire. The null χ² upper-tail
probability is 0.0147, so passing that broad flag does not establish a complete
noise model. This is a candidate under the frozen fixed-noise model, not a
confirmed planet or a claim of discovery. No follow-up grid, noise retuning or
independent confirmation was performed in this batch.

J0645+5158 is the closest non-trigger: Δχ² = 26.2212 versus 27.3050, at
43.7286 days. It remains NO_TRIGGER; its threshold was not lowered.

A useful next bounded step is to examine J1453+1902's observing-window aliases,
consistency across epochs and instrumental setups, and sensitivity to plausible
noise models. Freeze that follow-up definition separately and preserve this
initial candidate record. Prioritize this candidate review before another
source batch. PPTA DR3 remains the next source in the saved queue.

| Pulsar | Result | Peak period (days) | Peak Δχ² | Threshold | Search maximum (days) |
|---|---|---:|---:|---:|---:|
| J1911+1347 | NO_TRIGGER | 57.761 | 9.728 | 26.822 | 1276.519 |
| J0645+5158 | NO_TRIGGER | 43.729 | 26.221 | 27.305 | 1617.957 |
| J1923+2515 | NO_TRIGGER | 244.329 | 18.149 | 27.328 | 1637.006 |
| J1944+0907 | NO_TRIGGER | 823.999 | 16.493 | 27.342 | 1647.998 |
| J0340+4130 | NO_TRIGGER | 35.706 | 9.891 | 27.132 | 1485.356 |
| J1453+1902 | CANDIDATE | 118.427 | 34.914 | 26.826 | 1279.014 |
| J0030+0451 | NO_TRIGGER | 34.123 | 14.787 | 28.432 | 2000.000 |
| J0931-1902 | NO_TRIGGER | 47.126 | 9.615 | 26.850 | 1295.957 |
| J1730-2304 | NO_TRIGGER | 32.920 | 11.332 | 25.362 | 628.767 |
| J1744-1134 | NO_TRIGGER | 59.964 | 16.499 | 28.449 | 2000.000 |
| J1747-4036 | NO_TRIGGER | 31.687 | 15.964 | 27.128 | 1482.972 |
| J1832-0836 | NO_TRIGGER | 117.777 | 11.883 | 26.850 | 1295.551 |
| J1843-1113 | NO_TRIGGER | 210.436 | 13.012 | 25.372 | 631.308 |
| J2010-1323 | NO_TRIGGER | 44.023 | 10.303 | 27.656 | 1923.822 |
| J2124-3358 | NO_TRIGGER | 49.398 | 14.177 | 25.372 | 632.298 |
| J2322+2057 | NO_TRIGGER | 126.260 | 9.868 | 26.292 | 984.831 |

The full eligible single-pulsar pool is now covered: 16 new dataset searches
plus B1937's prior search, with 51 known binaries excluded. Six of the 16 targets
are new to Recherche; ten add another dataset to existing target records.

Execution freeze: `d26357be7f077b5083d433777260d8fa011db0ef75f22e579a4211ca590aee25`.
Runtime adapter commit: `f0881af`.

- [Terminal receipt](../results/observed/ng15-batch01-20260908-observed-closeout.json)
- [Compact result table](../results/observed/ng15-batch01-20260908-observed-summary.csv)
- [Preparation checks](../results/calibration/ng15-batch01-20260908-verification.json)
- [Verified observed backup](../results/observed/ng15-batch01-20260908-backup.json)

Preparation and observed archives have 248 and 316 verified file members,
respectively. Raw inputs and arrays remain outside Git. This closeout updates
the local repository and master only; the project remains private.
