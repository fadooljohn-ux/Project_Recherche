# J1721−2457 IPTA calibration — 9 September 2026

**CALIBRATED_CONDITIONAL.** Threshold, annual identifiability mask and circular
signal sensitivity are saved. No observed planet search or execution freeze was
performed. This is calibration of the completed IPTA preparation, not a repeat
of the earlier MeerKAT observed search.

The owner authorized this calibration after the bounded adapter passed. The
range is the existing long-baseline PTA convention: **30–2,000 days**, below
half the 4,661.159-day prepared baseline. The false-alarm allowance is **1% for
this one fixed target search**, conditional on the released Gaussian noise model.
It is not a shared allowance for all 14 possible IPTA datasets or the entire
Recherche survey. There are 150 TOAs and 13 projected timing nuisance columns.

## Threshold

| Quantity | Value |
|---|---:|
| Adopted Δχ² threshold | **22.4953139747** |
| Empirical 99th percentile of noise-only maxima | 20.6834988318 |
| Conservative analytical bound | 22.4953139747 |
| Noise-only simulations | 4,096 |
| Simulations exceeding adopted threshold | 19 / 4,096 (0.464%) |
| Frequency cells / oversampling | 767 / 5 |
| Eligible / excluded cells | 760 / 7 |

The unchanged automatic calibration takes the larger of the empirical quantile
and `2 log(search_count × full_grid_count / alpha)`. The analytical bound counts
even the masked cells. The 19 null exceedances are simulation outcomes, not
observed candidate crossings and not an independently estimated discovery
significance. Seed: `202609091721`.

## Annual mask

The seven excluded grid periods, in days, are:

`349.659125, 354.985000, 360.475628, 366.138773, 371.982698, 378.016197, 384.248648`.

These are discrete grid centers, rather than independently established continuous
interval endpoints. The automatic mask rejects at least 80% additional signal
power loss after the full timing fit relative to the offset/dispersion/instrument
baseline, or ill-conditioned templates. At the grid cell nearest one year
(366.139 days), the worst retained power fraction is approximately 0.0000854.
The stored mask controls a future search; masked cells have no finite sensitivity
estimate. No other cells are excluded in this calibrated range.

## Sensitivity

Amplitudes are circular timing-signal semi-amplitudes in microseconds. Values
give **95% detection probability at the signal's grid cell**, conditional on the
fixed timing/noise model, with phase extrema shown separately.

| Grid period (days) | Best phase (µs) | Worst phase (µs) |
|---|---:|---:|
| 30.000 | 13.94 | 14.26 |
| 59.966 | 12.07 | 14.34 |
| 100.174 | 14.13 | 15.18 |
| 179.755 | 16.29 | 16.74 |
| 366.139 | Masked | Masked |
| 736.293 | 24.24 | 26.44 |
| 985.325 | 27.45 | 28.70 |
| 2,000.000 | 43.21 | 46.69 |

The median worst-phase amplitude is **14.9265 µs across the eligible frequency
grid**. A frequency-uniform grid places more cells at short periods, so that
median does not describe long-period sensitivity. The full 767-row curve and
mask are in `results/research/ipta-calibration01-20260909/sensitivity-and-mask.csv`.

Sensitivity was calculated analytically from the projected template information
and noncentral chi-square distribution, not measured with an additional Monte
Carlo injection campaign. One bounded noiseless integration check injected a
100-µs circular signal at 100.174 days plus baseline nuisance terms; it recovered
100.00000000000003 µs. It used synthetic data only and verifies array/template
integration, not the 95% recovery probability. No extra test campaign was needed.

These estimates do not include off-grid losses, eccentric or multi-planet
interference, nonlinear orbit fitting or uncertainty in the supplied noise
parameters. They are sensitivity predictions, not observed upper limits or a
planet result.

## Binding, evidence and next action

The source is the preserved
`../Project Recherche Data/ipta-adapter01-20260909/J1721-2457/attempt03/` package.
All its saved artifact and adapter-code hashes were checked before calibration.
Only times, covariance and the two nuisance-design arrays were copied into the
calibration profile. The observed residual vector was not loaded into a scanner.

The new profile and cache live outside Git at
`../Project Recherche Data/ipta-calibration01-20260909/`. Cache key:
`ea90776235fca7ce4ed6894a928e89d72c5651a3ae34d72cec8fbb3018bb1b32`.
The cache receipt binds the profile, policy, prepared arrays, implementation and
runtime; it hashes the threshold, mask/sensitivity arrays and null maxima.

Repository evidence is under `results/research/ipta-calibration01-20260909/`:
`closeout.json`, `calibration.json`, `profile.json`, the full CSV,
`integration-check.json`, `artifact-manifest.json`, workbook-update and
preservation receipts. The canonical master receives four Work log records and
no Search or Candidate grade additions. The qualified source, root environment
lock and prior result files remain unchanged.

Existing supported command used:

```sh
tools/recherche calibration run \
  --profile '../Project Recherche Data/ipta-calibration01-20260909/profile/profile.json' \
  --cache '../Project Recherche Data/ipta-calibration01-20260909/cache'
```

For later verification, use `calibration check` with the same arguments; it
verifies saved evidence without generating more simulations.

**Next: bind these results into a one-target execution freeze, then launch once
when directed by the owner.** Expanding the period range, noise model or number
of searches changes the calibration binding. J2010−1323 and the other IPTA
targets have not been prepared or calibrated by this work. Binary support and
the deferred J1752 NS follow-up remain unchanged.
