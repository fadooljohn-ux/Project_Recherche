# J2317+1439 calibration — 10 September 2026

**J2317+1439 is calibrated and ready for a frozen observed launch.** The
preserved H3-only preparation was used unchanged. Calibration and the bounded
injection checks completed once without execution failures or code changes.
No observed periodogram or planet search ran. Execution is not yet frozen.

## Threshold and search scope

| Measurement | Result |
| --- | ---: |
| Prospective period range | 30–2,000 days |
| Full grid / eligible cells | 940 / 929 |
| Excluded cells | 11 |
| Fixed-noise null realizations | 4,096 |
| Empirical 99th-percentile null maximum | 21.460319 |
| Full-grid analytical bound | 22.902100 |
| Selected delta-chi-square threshold | **22.902100** |
| Null maxima exceeding selected threshold | 20 / 4,096 |
| Conditional allowance | 1% for one fixed grid |
| Diagnostic injections recovered | **95 / 96** |
| Maximum noiseless relative amplitude-recovery error | 1.650e-15 |

The selected threshold is the larger of the empirical quantile and the
analytical bound. The bound includes all 940 grid cells, retaining masked cells
in its trials accounting. The 20/4,096 exceedances are calibration diagnostics,
not an observed-candidate significance or probability that a planet exists.
The allowance is conditional on fixed supplied Gaussian covariance and the
linear timing model, not adaptive noise/orbit selection.

## Annual and projection mask

The existing rule requires worst-direction retained power greater than 0.2
relative to the dispersion/instrument baseline, with a finite template
condition number below 1e10. The resulting excluded grid cells are:

| Feature | Cells | Period range of excluded cells |
| --- | ---: | --- |
| Annual region | 7 | 351.501600–379.514868 days |
| Half-year region | 4 | 180.509809–183.997110 days |

These describe sampled cells, not interpolated continuous boundaries. At the
nearest annual cell, 364.971486 days, the least favorable direction retains
only 4.991e-6 of baseline power. No finite sensitivity is assigned to excluded
cells. The mask is computed from timing projection, not adjusted around any
observed peak.

## Conditional sensitivity and injections

The worst-phase amplitude required for calculated 95% on-grid circular-signal
recovery ranges from **0.387048 to 0.745769 microseconds** across eligible cells,
with median **0.402931 microseconds**. It depends on period and phase and is
conditional on the prepared covariance; it is not a posterior mass limit or
population completeness measurement.

| Diagnostic period | Best-phase 95% amplitude | Worst-phase 95% amplitude |
| --- | ---: | ---: |
| 2,000 days | 0.405717 us | 0.449760 us |
| 58.395677 days | 0.375274 us | 0.405275 us |
| 30 days | 0.391320 us | 0.395385 us |

The bounded injection check used these three eligible periods, two phases and
16 fixed-noise realizations per cell, recovering **95/96**. That finite count
does not establish a universal empirical recovery rate. The noiseless
amplitude check agreed to 1.650e-15 relative error. No calibration or injection
check was repeated for a more favorable result.

## Preserved model and limitations

The [preparation](ELL1H_J2317_PREPARATION_2026-09-10.md) retains all 708 TOAs,
paired DM measurements, 328 timing columns and six free orbital terms including
the weak signed H3 coefficient. Its profile and preparation receipt are
unchanged. The released model has **no red-noise component**; none was added or
inferred during this calibration. Reduced chi-square near one at preparation
does not rule out correlated/chromatic noise. A future qualifying crossing
would require the standing bounded robustness and noise-model review.

## Records, evidence and next step

[Saved calibration evidence](../results/research/ell1h-j2317-calibration-20260910/)
contains null maxima, projection/sensitivity arrays, calibration settings,
receipts and closeout. Original and archived hashes are recorded separately
where the preparation JSON's local cache path is normalized. Other calibration
artifacts are byte-identical to their originals. Full inputs remain in
`RECHERCHE_DATA/ell1h-j2317-preparation-20260910` outside Git.

The master receives three Work log records. All 359 Searches rows, eight
grades and historical notes are preserved. Totals remain 783 registered
targets and 285 observed identities. The adapter and all 71 publication-source
files remain unchanged. No job is active and no repository push was performed.

The completed command was:

```sh
tools/recherche binary-pilot calibrate \
  --data "$RECHERCHE_DATA/ell1h-j2317-preparation-20260910"
```

**Next recommend freezing the verified inputs, calibration and mask, then
launching J2317's single observed search.** Use the existing `binary-pilot
freeze` and `run --target J2317+1439` actions on this data directory, update
the master at terminal closeout and apply bounded review to a valid crossing.
That launch has not run. J1802 and the four earlier nonlinear holds remain
separate; no other target was prepared in this scope.
