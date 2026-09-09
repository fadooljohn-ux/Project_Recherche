# Automatic target calibration

The owner authorized this work on 2026-09-08. Recherche remains private.
The supported entry point is `tools/recherche calibration`. It accepts reusable
target profiles and automatically calculates a fixed-noise threshold, timing
identifiability mask and circular-signal sensitivity curve. It does not require
a known companion or execute an observed search. Existing formal qualification,
observed searches and benchmark records retain their original calibration.

## Usage

For the existing B1257 prepared observations:

```sh
tools/recherche calibration import-b1257 \
  --data '../Project Recherche Data/b1257-benchmark-20260908' \
  --output '/absolute/new/b1257-profile'
tools/recherche calibration run --profile '/absolute/new/b1257-profile/profile.json'
```

`import-b1937 --data '../Project Recherche Data/operational-20260908' --output
'/absolute/new/b1937-profile'` exports the existing offline wideband preparation.
It does not rerun the consumed B1937 search or replace its qualified threshold.

For a new pulsar, provide a prepared NPZ file with:

| Array | Contract |
| --- | --- |
| `times` | One-dimensional TOA arrival times in MJD TDB, length N |
| `covariance` | Finite positive-definite covariance, M by M, including supplied noise correlations |
| `design` | Full linear timing nuisance design, M rows |
| `baseline_design` | Offset, dispersion and instrument nuisance design; its column space must be contained in the full design |

M may exceed N for wideband TOA-plus-DM measurements. The first N rows are timing
residuals in seconds; auxiliary measurements follow. Covariance and design must
use consistent row units. Planetary timing templates are zero in auxiliary rows.
The baseline deliberately excludes spin/astrometric columns: the mask measures
additional timing loss after dispersion/instrument separation. Alternatively,
provide `--baseline-columns 0,8,9` to select the appropriate full-design columns.
Do not guess these columns from array position in a new dataset.

```sh
tools/recherche calibration ingest \
  --context '/absolute/prepared-context.npz' --target 'PSR-name' \
  --timing-model 'Source, version and preparation assumptions' \
  --noise-model 'Source and interpretation of the supplied covariance' \
  --minimum-period 10 --maximum-period 400 \
  --output '/absolute/new/target-profile'
tools/recherche calibration run --profile '/absolute/new/target-profile/profile.json'
tools/recherche calibration check --profile '/absolute/new/target-profile/profile.json'
```

Ingestion copies only the four calibration arrays. Any observed residual vector
in the source NPZ is omitted. The profile stores input hashes, preparation
provenance, reference epoch and numerical policy. Raw radio reduction and
arbitrary observatory/clock/model conversion are upstream preparation work;
this version does not infer those assumptions or estimate an unknown noise model.

## Calculation and reuse

Defaults are 10–400 days, frequency oversampling 5, 4,096 Gaussian nulls, a
1% false-alarm target and one fixed linear search. The B1257 import preserves its
10–400-day, three-search-count, seed-1257122026 benchmark policy for comparison.
The B1937 import uses 30–2,000 days with the new general calibration policy.

The threshold is the larger of the empirical 99th percentile of null maximum
statistics and `2 log(search_count * full_grid_count / alpha)`. The latter is
the two-coefficient Gaussian chi-square union bound for fixed linear searches.
It counts even excluded cells conservatively. It is conditional on the supplied
covariance/design; the multiplier alone does not calibrate adaptive orbit fits.

The mask excludes cells with at least 80% additional power loss or ill-conditioned
two-coefficient templates. This is a projection-based identifiability mask over
the entire period grid; it is not the historical qualification-02 annual map.

Sensitivity reports the best- and worst-phase circular timing amplitudes needed
for 95% detection probability at each eligible grid frequency. It uses the
noncentral chi-square distribution and projected template information. This
describes a signal exactly on a grid cell with a fixed linear model. Off-grid
loss, nonlinear parameter adjustment and interference among planets are outside
that estimate. Excluded cells have NaN amplitudes rather than invented limits.

Results go to `../Project Recherche Data/calibration-cache/<hash>/` by default:

- `calibration.json`: threshold, assumptions, grid and summary.
- `projection-and-sensitivity.npz`: frequencies, eligibility, retained power and amplitude curves.
- `null-maxima.npy`: the noise-only maximum statistics.
- `receipt.json`: full profile/code/runtime binding and artifact hashes.

Repeating `run` verifies and reuses the existing result. A changed profile,
dataset, covariance, timing design, search policy, implementation or recorded
runtime version selects a different cache entry. A changed array file without
a new ingestion receipt is reported as an error. Damaged cache artifacts are
reported instead of reused. Work is published to the cache only when complete.
`check` verifies an existing calibration without computing another one.

Keep each profile in a new external directory. When new observations arrive,
prepare their arrays, ingest a new profile and run calibration; unchanged
profiles reuse their verified cache. No daemon, survey or scheduled job is needed.

## Verification

Five focused checks cover cache reuse, grid/covariance invalidation, corruption,
residual omission, invalid covariance, nonnested baseline design, wideband row
handling, annual exclusion, and sensitivity against independent noisy-signal
trials. The sensitivity check uses an independently computed least-squares
projection, not the calibration's statistic implementation.

Both existing target profiles completed and verified cache reuse:

| Target | Grid cells | Excluded | Threshold |
| --- | ---: | ---: | ---: |
| B1257+12 | 360 | 16 | 23.179773012212713 |
| B1937+21 | 953 | 15 | 22.929570179284585 |

B1257's frequencies, mask, retained-power values, threshold and all 4,096 null
maxima reproduce its saved benchmark exactly. B1937's new calibration is separate
from its original consumed search; its new mask/threshold do not replace that
historical result. Both profiles are under
`../Project Recherche Data/automatic-calibration-20260908/`.

Five focused checks passed in 2.81 seconds; lint and runtime doctor passed.
All 71 qualified source files and both observed result hashes are unchanged.
Execution receipts are recorded in
`results/calibration/automatic-calibration-20260908.json`. This is engineering
verification of automatic calibration, not a new formal qualification or
observed planet-search result.
