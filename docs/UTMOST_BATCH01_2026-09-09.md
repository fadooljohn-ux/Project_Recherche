# UTMOST batch 01 observed closeout — 9 September 2026

The owner authorized “Launch” for the four prepared UTMOST datasets. All four
observed searches completed once: **four NO_TRIGGER, zero candidates, zero
execution failures and zero noise-adequacy flags**. These are public UTMOST DR1
observations, not the noise-only simulations used during preparation.

| Target | TOAs | Strongest eligible period (days) | Peak statistic | Frozen threshold | Result |
|---|---:|---:|---:|---:|---|
| J1807-0847 | 74 | 293.1195 | 10.8803 | 22.6192 | NO_TRIGGER |
| J0134-2937 | 198 | 34.7456 | 7.3892 | 22.4664 | NO_TRIGGER |
| J1453-6413 | 234 | 30.3922 | 16.5912 | 22.5493 | NO_TRIGGER |
| J1224-6407 | 367 | 80.2307 | 5.8113 | 22.5392 | NO_TRIGGER |

J1453-6413 was closest to its threshold, reaching 73.6% of the threshold
statistic. That ratio is not a detection confidence or a probability of a planet.
Its subthreshold peak does not meet the standing candidate deep-review trigger.
No target warrants a candidate claim from this batch.

## Scope and execution

The 873 TOAs were searched with the already prepared 30–400-day circular grids,
fixed released noise, per-target timing-projection masks, and shared conditional
1% four-target false-alarm allowance. The four calibration keys, thresholds,
arrays and observed residuals were verified and frozen without recalibration,
retuning or changing the timing adapter. No binary support was added. The
qualified scientific source and existing `mpta_batch.run` search implementation
were unchanged.

`tools/utmost_search.py` provides the source-specific binding and verified
prelaunch archive. A profile-directory alias makes the preserved preparations
compatible with the existing runner without copying or changing profile bytes.
The operator entry point is `tools/recherche utmost-search`. Every `run01`
destination is consumed; repeating a run is not a continuation.

The saved peaks passed the existing independent full-design likelihood checks.
Reduced null chi-squared values were 1.010, 0.996, 1.029 and 0.979, respectively.
No execution repair or scientific retry was needed for this launch.

## Interpretation and retained limits

NO_TRIGGER means no threshold-crossing signal in the eligible cells of this
bounded search. It does not exclude smaller signals, masked periods, orbital
periods outside 30–400 days, or configurations outside the circular model.
The preparation's 95% on-grid sensitivity remains conditional on fixed
published covariance and timing projection. Median worst-phase sensitivity is
22.9–50.2 microseconds across these four targets.

UTMOST's effective single band cannot independently distinguish achromatic
orbital delays from dispersion/scattering effects. The released clock's
out-of-order segment is replayed with Tempo2 semantics at the bound TOAs, as
documented in the [preparation report](UTMOST_PREPARATION01_2026-09-09.md).
This launch does not remove those limitations or establish planet absence.

## Evidence and bookkeeping

Frozen inputs, original profiles, cache entries and consumed run directories
remain under `../Project Recherche Data/utmost-preparation01-20260909/`.
The verified backup is `prelaunch-inputs.tar.gz` in that directory. Its SHA-256
is recorded in the execution freeze.

Portable evidence is in `results/observed/utmost-batch01-20260909/`: the freeze,
four terminal results and periodograms, individual workbook-update receipts,
summary table and final preservation checks. The master updated after each
search. All 252 historical search/refinement rows and operator notes were
preserved. It now records **225 observed targets and 256 search/refinement
records**, with no increase in candidate or discovery counts.

The source queue now has four completed UTMOST searches and 82 remaining
coverage candidates, all unprepared. Of those 82, 52 have no previous Recherche
observed search and 30 have other-source coverage. The 214 inventory exclusions
remain preserved. A further batch needs a new owner-directed scope; this launch
does not authorize the remaining pool. Recherche stays private. No background
job remains active.
