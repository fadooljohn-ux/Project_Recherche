# Optional chromatic timing support

Current status: the owner subsequently authorized "freeze and launch". All four
observed searches are complete with NO_TRIGGER and no noise-adequacy flags.
See [observed closeout](MPTA_CHROMATIC_OBSERVED_2026-09-08.md). The development
record below describes the earlier preparation and injection checks.

Implemented on 2026-09-08 for the four remaining isolated MPTA targets. This is
development and conditional calibration, with no new observed planet search.
The 71 qualified scientific source files and completed observed results remain preserved.

## What changed

`tools/chromatic_timing.py` provides frequency scaling at 1400 MHz, scattering
covariance, a localized Gaussian event column, and annual sine/cosine columns.
`tools/mpta_batch.py` admits these only through an explicit target support profile.
Ordinary targets retain the previous covariance calculation exactly. The existing
detector, threshold calculation, projection mask and sensitivity calculation are reused.

Scattering uses the published Table 1 amplitude, temporal spectral index and
chromatic index, with the existing 120-harmonic covariance kernel. Each covariance
element receives the radio-frequency scaling of both observations. Gaussian
center, width and chromatic index are fixed at Table 2 MAP values; amplitude is
fitted as a linear nuisance coefficient. Annual sine and cosine coefficients
allow amplitude and phase to be fitted at a fixed published chromatic index.
These columns enter both the full timing design and the propagation/instrument
baseline. The absolute sensitivity calculation includes their loss even when
that loss is not part of the relative timing-projection mask.

The existing independent epoch-dispersion nuisance columns remain in place.
No published posterior residual waveform is subtracted. No additional free
scattering coefficient is fitted at every epoch.

## Evidence and measured cost

All four profiles prepared successfully: 9,326 TOAs, 307 epochs. Each calibration
used 4,096 Gaussian nulls and a 30–400-day circular grid, oversampling 5, with a
conditional 1% union-bound allowance across four grids. These are prospective
search settings; no execution freeze or observed scan has been created.

| Target | Added deterministic terms | Scattering | Median amplitude cost | Median 95% amplitude, µs | Injected-cell recoveries |
|---|---|---|---:|---:|---:|
| J1721−2457 | Gaussian, 1 coefficient | No | +0.006% | 3.155 | 93/96 |
| J1832−0836 | Gaussian, 1 coefficient | No | +0.060% | 0.918 | 95/96 |
| J1747−4036 | Gaussian, 1 coefficient | Yes | +1.175% | 1.569 | 92/96 |
| J1804−2858 | Annual, 2 coefficients | Yes | +19.095% | 4.878 | 93/96 |

Amplitude cost compares the full model against an optimistic reference that
omits chromatic effects, using identical thresholds and eligible cells. It is
the median of per-cell amplitude ratios, not the ratio of two medians. The
reference is not a scientifically adequate noise model for these targets.
The full range of costs over eligible cells is 0–0.128%, 0–0.854%, 0.607–14.273%,
and 14.653–26.349%, respectively. This extension therefore has a meaningful cost
for J1804−2858, rather than universally negligible effects.

The bounded check used 32 phases/noise draws at each of three requested periods:
60, 150 and 300 days, mapped to the nearest eligible grid cell. J1804−2858's last
cell is 288.395 days because the nearer cells are masked. Injections were set to
each cell's calculated worst-phase 95% amplitude, with the chromatic event also
present. Recovery means exceeding the threshold at the injected frequency; it
does not assert that the global peak identifies the correct period. There were
373/384 recoveries. Noiseless fitted orbital coefficients agree within 1e-5
relative tolerance in every target/period check (actual errors below 1e-12).
These small injection counts are engineering evidence, not a new qualification
or a measurement guaranteeing 95% completeness.

Eight focused tests passed in 3.24 seconds, including physical covariance units,
cross-frequency scaling, Gaussian localization, arbitrary annual phase,
unchanged legacy covariance, and existing MPTA selection/projection behavior.
Focused lint passed. No full qualification suite was repeated.

## Limits and source conventions

Calibration remains conditional on fixed published noise and event shapes.
It does not propagate their broad posterior uncertainty or establish the
adequacy of the model on observed residuals. A later observed search must inspect
noise adequacy as well as peak significance. Periods excluded by the new
target-specific mask have no claimed sensitivity. The present search family
remains circular and 30–400 days.

Source: [Miles et al., MPTA noise analysis](https://arxiv.org/html/2412.01148v1),
sections 3.5 and 3.7, Tables 1–2. The positive exponent printed in v1 equation 10
would grow away from the event, contradicting a localized Gaussian. This adapter
explicitly uses exp(−(t−center)²/(2 width²)). The annual model agrees with the
[enterprise_extensions annual implementation](https://github.com/nanograv/enterprise_extensions/blob/master/enterprise_extensions/chromatic/chromatic.py).
Fitting both annual quadratures makes its arbitrary phase origin immaterial.
Event epochs/widths use days; times use barycentric TDB MJD, an approximation to
the published epoch convention. Radio frequencies use MHz. No source table is
silently modified; its original text and SHA are retained in each support profile.

## Operation and records

Supported commands:

```sh
tools/recherche chromatic-support prepare --data NEW_EXTERNAL_DIRECTORY
tools/recherche chromatic-support diagnose --data THAT_DIRECTORY
tools/recherche master-workbook THAT_DIRECTORY --chromatic-development
```

The default prepared directory is
`../Project Recherche Data/chromatic-support-20260908`; its preparation and
diagnosis are complete. Do not run preparation over it. A completed diagnosis
refuses overwrite. If an interrupted diagnosis has completed target records,
it can continue from those records without repeating those targets.

The diagnosis reads calibration arrays and diagnostic metadata, never the
saved observed residuals. Preparation computes residuals for future use without
searching them. Profiles bind their arrays and chromatic module hash; a later
MPTA execution freeze also binds the chromatic module. The two import-order
versions of the preparation adapter are saved under the external `code/`
directory; their scientific behavior is identical.

Tracked results: `results/calibration/chromatic-support-20260908.json` and its
verification/workbook/backup receipts. The master records four development
closeouts and retains the existing observed-search counts. The next scientific
action is a separately authorized freeze and observed search of these four
prepared targets. Binary support remains outside this implementation.
