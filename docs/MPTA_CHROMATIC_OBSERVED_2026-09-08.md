# Four chromatic MPTA observed searches

The owner authorized "freeze and launch" on 2026-09-08. All four prepared
targets were searched once using their actual observed timing residuals.
**Four NO_TRIGGER results, zero candidates, zero execution failures and zero
noise-adequacy flags.** No background search remains active.

This campaign consumed the four `run01` destinations under
`../Project Recherche Data/chromatic-support-20260908`. The earlier 384 injected
signals remain separate development evidence; they are not these observed runs.

## Frozen scope

The freeze bound the existing four profiles, observed input hashes, calibrated
thresholds, masks, scientific implementation and chromatic support module.
All four calibrations were verified cache hits; no new null simulation or
threshold tuning was needed. Source commit: `3740cc3`.

Freeze SHA-256:
`590ae1615ec52411f2388ae9322d162362effcf0771a6e0a5ffe7f1632e3b251`.

The scope was one circular 30–400-day frequency grid per target, oversampling
five, with published fixed noise, epoch dispersion nuisance terms and the
prepared Gaussian/annual chromatic support. Each target retained its existing
annual/projection mask. The four-grid false-alarm allowance is conditionally 1%
under these fixed Gaussian models. This is not a cumulative 1% guarantee over
all campaigns; the three original MPTA batch allowances sum to at most 3% under
their stated models.

## Observed results

| Pulsar | Strongest eligible period, days | Statistic | Frozen threshold | Null reduced χ² | Result |
|---|---:|---:|---:|---:|---|
| J1721−2457 | 52.886887 | 17.443304 | 22.455813 | 0.977755 | NO_TRIGGER |
| J1832−0836 | 131.371120 | 6.436816 | 22.969052 | 0.997616 | NO_TRIGGER |
| J1747−4036 | 124.901569 | 18.867304 | 22.867765 | 0.974027 | NO_TRIGGER |
| J1804−2858 | 160.471110 | 19.938811 | 22.815130 | 0.988622 | NO_TRIGGER |

These peaks are reported for audit and are not detected planetary periods.
The search covered 9,326 arrival times in 307 observing epochs. Every peak
remained below its frozen threshold. The reduced-χ² diagnostic did not raise
the existing flag (threshold 2); this alone does not establish complete noise
model adequacy or propagate uncertainty in published chromatic parameters.

Median worst-phase amplitudes for conditional 95% on-grid detection remain
3.155, 0.918, 1.569 and 4.878 microseconds respectively. No sensitivity claim is
made for masked cells, periods outside 30–400 days, arbitrary eccentric orbits,
or signals below the demonstrated sensitivity. These results do not establish
that the pulsars have no planets.

## Closeout

Each supported run independently checked its peak likelihood with a full
timing-plus-orbit design fit and updated the master workbook before the next
run launched. Closeout checked the saved grids against the frozen frequencies
and masks, reproduced the recorded peak/threshold decisions from those saved
arrays, and verified the retained likelihood checks. Closeout performed no new
period scans or fits.

All 20 historical observed result hashes and the prior chromatic development
diagnosis are unchanged. The qualified scientific source is unchanged.
The master now records 23 observed targets and 24 search/refinement records,
including 18 original MPTA targets with zero qualifying candidates across the
three batches (45,349 TOAs, 1,562 epochs).

Tracked evidence:

- `results/observed/mpta-chromatic-20260908-selection.json`
- `results/observed/mpta-chromatic-20260908-execution-freeze.json`
- `results/observed/mpta-chromatic-20260908-closeout.json`
- `results/observed/mpta-chromatic-20260908-summary.csv`
- `results/observed/mpta-chromatic-20260908-master-workbook-update.json`
- `results/observed/mpta-chromatic-20260908-backup.json`

The project remains private. Preserve these consumed results; any new data,
changed model or expanded period range belongs in a separately defined run.
