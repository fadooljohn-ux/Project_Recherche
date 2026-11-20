# J2145-0750 calibration — 10 September 2026

**J2145-0750 is calibrated and ready for a frozen observed launch.** The
preserved H3-only preparation was used unchanged. Calibration and the bounded
injection checks completed once without an execution failure or code change.
No observed periodogram or planet search ran, and execution is not yet frozen.

## Threshold and scope

| Quantity | Result |
| --- | ---: |
| Prospective period range | 68.389025–2,000 days |
| Full grid / eligible cells | 402 / 390 |
| Excluded cells | 12 |
| Gaussian null realizations | 4,096 |
| Empirical 99th-percentile null maximum | 19.432551 |
| Full-grid analytical bound | 21.203245 |
| Selected delta-chi-square threshold | **21.203245** |
| Null maxima exceeding selected threshold | 13 / 4,096 |
| Conditional search allowance | 1% for one target/grid |
| Bounded injections recovered | **90 / 96** |
| Maximum noiseless relative amplitude-recovery error | 1.232e-15 |

The threshold is the larger of the empirical quantile and the analytical
full-grid bound. The latter retains all 402 cells in its trials accounting,
including excluded cells. The 13/4,096 empirical exceedances are a diagnostic
from the calibration simulations, not an observed-candidate false-alarm
probability or a significance claim. The guarantee is conditional on the fixed
supplied Gaussian covariance and linear timing model.

## Annual and projection mask

Eligibility requires worst-direction retained power greater than 0.2 and a
finite template condition number below 1e10. This computes timing-projection
losses relative to the retained dispersion/instrument baseline. It is not a
manually chosen calendar exclusion.

| Excluded grid feature | Cells | Periods of excluded cells |
| --- | ---: | --- |
| Annual region | 8 | 349.518504–382.497090 days |
| Half-year region | 4 | 180.527654–184.040128 days |

These ranges describe sampled excluded cells, not interpolated continuous
boundaries. The nearest annual grid cell is 362.929126 days and retains only
8.033e-5 of the baseline signal power in its least favorable direction. Its
exclusion follows directly from the existing projection rule. No finite
sensitivity is assigned to masked cells.

## Conditional sensitivity and recovery

Across eligible cells, the calculated worst-phase circular timing amplitude
needed for 95% recovery ranges from **0.633153 to 2.501439 microseconds**, with
median **0.685459 microseconds**. The amplitude depends on period and phase.
These values are on-grid calculations under the prepared covariance; they are
not measured companion masses, a noise posterior or population completeness.

| Diagnostic period | Best-phase 95% amplitude | Worst-phase 95% amplitude |
| --- | ---: | ---: |
| 2,000 days | 2.280651 us | 2.501439 us |
| 128.875338 days | 0.628588 us | 0.687780 us |
| 68.389025 days | 0.631622 us | 0.661238 us |

The existing bounded check used these three eligible periods, two phases and
16 fixed-noise realizations per cell: **90/96 recoveries (93.75%)**. It was not
repeated to obtain a more favorable count. This small diagnostic does not
establish 95% empirical recovery at every period. Noiseless amplitude recovery
agreed to 1.232e-15 relative error, checking the binary/timing projection path.

## Preserved preparation and remaining limits

The profile retains all 400 TOAs, their paired DM measurements and the full-rank
184-column joint model from the
[preparation](ELL1H_J2145_PREPARATION_2026-09-10.md). H3 and all six other free
orbital terms remain present. Red-frequency coverage remains 128 modes with
released amplitude and slope fixed. Calibration therefore accounts for this
broader covariance but does not validate all possible red/chromatic noise
models or adaptive nonlinear orbit fitting.

Profile, preparation receipt and calibration artifact hashes are verified.
The adapter and all 71 publication-source files remain unchanged. The master
receives three Work log records; all 358 Searches rows, eight grades and prior
notes are preserved. There remain 783 registered targets and 284 observed
identities. J2317 preparation, J1802's model hold and the four earlier nonlinear
Shapiro holds are outside this completed calibration.

## Evidence and next step

[Calibration evidence](../results/research/ell1h-j2145-calibration-20260910/)
contains the calibration settings, original null maxima, projection/sensitivity
arrays, receipts, verification summary and archive bindings. The archived
preparation JSON normalizes its local cache path; original and archived hashes
are recorded separately. Other archived calibration files are byte-identical
to their originals. Full preparation inputs remain outside Git in
`RECHERCHE_DATA/ell1h-j2145-preparation-20260910`.

The completed command was:

```sh
tools/recherche binary-pilot calibrate \
  --data "$RECHERCHE_DATA/ell1h-j2145-preparation-20260910"
```

The next recommended action is **freeze these verified inputs, threshold and
mask, then execute J2145's one observed search**, with workbook closeout and
bounded deep review if a valid threshold crossing occurs. Use the existing
`binary-pilot freeze` and `run --target J2145-0750` actions on this same data
directory. That launch has not been executed or implicitly included here.
No job is active. This closeout is saved locally without a repository push.
