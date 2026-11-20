# Detection limits from the second-stage sensitivity curves

**19 November 2026. Owner instruction "Proceed with steps 1-2" (step 2: turn
non-detections into stated limits). Computed from saved sensitivity curves
(simulated injections); no observed residuals read, no search run.**

## What a limit here means

For each target and trial period, the amplitude of a circular-orbit
sinusoid that the second-stage test would have flagged (statistic above its
threshold, peak within 5% of the true period) in 50% and in 95% of simulated
injections. No second-stage run crossed its threshold, so a companion above
the 95% amplitude at that period is disfavoured at that level.

- "Amplitude" is the projected light-travel-time semi-amplitude of the pulsar.
- "Minimum mass" is m sin i for a 1.4 M☉ pulsar (change with
  `--pulsar-mass`). 1 M⊕ = 81 Moon masses; the Moon is 0.0123 M⊕.
- Main columns assume the released noise model. "Worst generator" is the
  largest value over every declared null generator, including strong
  red-noise stress cases; it is the conservative figure.
- Limits are conditional on the declared generators, come from 32 injections
  per amplitude step on a ladder of 2^(1/3) steps, and cover only the listed
  periods. "Not reached" means the ladder ended below 95%.
- Eccentric orbits, periods outside the searched band and signals absorbed by
  the timing-model fit are not covered.

## Summary

| Target | Periods covered (days) | 95% minimum mass, short-period end | 95% minimum mass, long-period end |
|---|---|---:|---:|
| J1939+2134 | 30–1,078 | 0.005 M⊕ (30 d) | 0.002 M⊕ (634 d); not reached at 1,078 d |
| J1453+1902 | 30–1,279 | 0.008 M⊕ (30 d) | 0.003 M⊕ (1,279 d) |
| J1359−6038 | 30–319 | 0.09 M⊕ (30 d) | 1.2 M⊕ (319 d) |
| J0908−4913 | 30–302 | 0.25 M⊕ (30 d) | 2.5 M⊕ (302 d) |
| J1048−5832 | 30–202 | 0.6 M⊕ (30 d) | 5.9 M⊕ (202 d) |
| J1327−6222 | 30–321 | 0.7 M⊕ (30 d) | 14 M⊕ (321 d) |
| J2043+1711 | 30–1,653 | 0.0006 M⊕ (30 d) | 0.0002 M⊕ (1,653 d) |
| J1738+0333 | 30–1,960 | 0.004 M⊕ (30 d) | 0.002 M⊕ (1,960 d) |
| J1012+5307 | 30–2,000 | 0.009 M⊕ (30 d) | 0.001 M⊕ (2,000 d) |
| J1752−2806 | 30–301 | 1.2 M⊕ (30 d) | 2.6 M⊕ (301 d) |

The last four rows were added later on 19 November 2026 from curves rebuilt
in fresh development roots (see "Rebuilt curves" below). J2043+1711,
J1012+5307 and J1738+0333 are binaries: their masses assume a total inner
mass of 1.6 M☉ and scale as that mass to the power 2/3.

## J1939+2134 (threshold 29.07; retrospective curve)

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 1078 | 6.63 | not reached | not reached | not reached | not reached |
| 634 | 1.91 | 4.1 | 0.00237 | 106 | 0.0612 |
| 449 | 1.79 | 2.29 | 0.00167 | 42.1 | 0.0306 |
| 234 | 0.892 | 1.38 | 0.00155 | 10.1 | 0.0114 |
| 140 | 0.691 | 1.09 | 0.00173 | 3.66 | 0.00578 |
| 84 | 0.738 | 1.03 | 0.00231 | 1.6 | 0.00357 |
| 50 | 0.688 | 0.944 | 0.00296 | 1.27 | 0.004 |
| 30 | 0.738 | 1.03 | 0.00456 | 1.31 | 0.00577 |

## J1453+1902

Two curves exist. The first belongs to the run that was actually made and is
the limit of record. The second is what a test with the per-receiver white
model would reach; it was never run on observed data.

**Consumed run (threshold 22.35, one global white scale).** Under the
released chain that threshold has a false-alarm rate near 9%, not 1%; that
does not weaken a non-detection.

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 1279 | 4.52 | 7.87 | 0.00285 | 121 | 0.0439 |
| 914 | 2.79 | 4.77 | 0.00216 | 58.1 | 0.0263 |
| 640 | 2.32 | 3.2 | 0.00184 | 34.7 | 0.0199 |
| 457 | 1.64 | 2.73 | 0.00196 | 14.2 | 0.0102 |
| 320 | 2.08 | 2.81 | 0.00257 | 8.68 | 0.00792 |
| 233 | 1.36 | 1.93 | 0.00217 | 4.2 | 0.00474 |
| 166 | 1.33 | 1.89 | 0.00267 | 3 | 0.00424 |
| 117 | 1.37 | 2.14 | 0.0038 | 2.5 | 0.00445 |
| 84 | 1.19 | 1.79 | 0.00399 | 2.27 | 0.00507 |
| 59 | 1.09 | 1.69 | 0.00474 | 2.46 | 0.00688 |
| 42 | 1.37 | 1.89 | 0.00666 | 2.73 | 0.0096 |
| 30 | 1.18 | 1.75 | 0.00772 | 2.56 | 0.0113 |

**Per-receiver white model (threshold 23.04; development root, not run).**
Its worst-generator column includes joint chain draws.

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 1279 | 4.83 | 9.92 | 0.00359 | 121 | 0.0439 |
| 914 | 2.9 | 4.89 | 0.00221 | 59.2 | 0.0268 |
| 640 | 2.43 | 3.2 | 0.00184 | 34.7 | 0.0199 |
| 457 | 1.71 | 2.53 | 0.00182 | 14.2 | 0.0102 |
| 320 | 2.19 | 2.88 | 0.00263 | 8.22 | 0.0075 |
| 233 | 1.44 | 2.24 | 0.00253 | 4.2 | 0.00474 |
| 166 | 1.47 | 2.2 | 0.0031 | 3.19 | 0.0045 |
| 117 | 1.48 | 2.48 | 0.00442 | 3.07 | 0.00546 |
| 84 | 1.35 | 1.83 | 0.00408 | 3.01 | 0.00672 |
| 59 | 1.28 | 1.94 | 0.00544 | 2.93 | 0.00822 |
| 42 | 1.45 | 1.96 | 0.00688 | 3.37 | 0.0119 |
| 30 | 1.37 | 2.13 | 0.00942 | 3.18 | 0.014 |

## J1359−6038 (threshold 23.79; retrospective curve)

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 319 | 903 | 1.34×10³ | 1.22 | 7.25×10³ | 6.62 |
| 255 | 345 | 497 | 0.528 | 2.61×10³ | 2.77 |
| 205 | 193 | 275 | 0.338 | 1.27×10³ | 1.56 |
| 167 | 118 | 179 | 0.252 | 572 | 0.804 |
| 135 | 76.4 | 113 | 0.184 | 311 | 0.504 |
| 109 | 53.7 | 76.1 | 0.142 | 177 | 0.33 |
| 88 | 33.3 | 52.8 | 0.114 | 86.5 | 0.187 |
| 71 | 26.7 | 42.6 | 0.106 | 54.8 | 0.136 |
| 57 | 20.9 | 31.9 | 0.0918 | 37.2 | 0.107 |
| 46 | 19.8 | 28.3 | 0.094 | 31.6 | 0.105 |
| 37 | 16.5 | 22 | 0.0842 | 26.8 | 0.103 |
| 30 | 16.2 | 20.9 | 0.0923 | 25.1 | 0.111 |

## J0908−4913 (threshold 25.37; retrospective curve)

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 302 | 1.59×10³ | 2.68×10³ | 2.54 | 1.48×10⁴ | 14 |
| 243 | 747 | 1.35×10³ | 1.47 | 5.94×10³ | 6.51 |
| 197 | 435 | 634 | 0.8 | 2.91×10³ | 3.67 |
| 161 | 266 | 428 | 0.617 | 1.39×10³ | 2.01 |
| 130 | 192 | 291 | 0.484 | 781 | 1.3 |
| 106 | 129 | 207 | 0.394 | 357 | 0.681 |
| 85 | 88 | 149 | 0.327 | 245 | 0.538 |
| 69 | 74.2 | 110 | 0.278 | 135 | 0.342 |
| 57 | 52.5 | 73.4 | 0.212 | 98.7 | 0.286 |
| 46 | 48.3 | 82.3 | 0.275 | 82.3 | 0.275 |
| 37 | 45.3 | 68.4 | 0.263 | 77.2 | 0.297 |
| 30 | 42.5 | 57.4 | 0.254 | 65.8 | 0.291 |

## J1048−5832 (threshold 24.69; retrospective curve)

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 202 | 3.09×10³ | 4.76×10³ | 5.9 | 2.66×10⁴ | 33 |
| 173 | 1.87×10³ | 2.9×10³ | 3.97 | 1.59×10⁴ | 21.8 |
| 141 | 1.03×10³ | 1.54×10³ | 2.42 | 8.71×10³ | 13.7 |
| 119 | 692 | 985 | 1.73 | 4.41×10³ | 7.76 |
| 102 | 464 | 658 | 1.29 | 2.76×10³ | 5.41 |
| 85 | 353 | 461 | 1.02 | 1.45×10³ | 3.2 |
| 72 | 231 | 327 | 0.808 | 915 | 2.26 |
| 60 | 162 | 265 | 0.738 | 563 | 1.57 |
| 50 | 135 | 210 | 0.656 | 352 | 1.1 |
| 42 | 121 | 157 | 0.551 | 251 | 0.879 |
| 36 | 114 | 166 | 0.651 | 199 | 0.783 |
| 30 | 95.1 | 140 | 0.618 | 172 | 0.76 |

## J1327−6222 (threshold 23.26; retrospective curve)

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 321 | 6.36×10³ | 1.53×10⁴ | 13.9 | 6.85×10⁴ | 62.4 |
| 257 | 3.03×10³ | 4.54×10³ | 4.8 | 2.71×10⁴ | 28.6 |
| 214 | 2.1×10³ | 2.76×10³ | 3.29 | 1.55×10⁴ | 18.5 |
| 165 | 1.23×10³ | 1.72×10³ | 2.44 | 7.19×10³ | 10.2 |
| 134 | 870 | 1.18×10³ | 1.92 | 3.95×10³ | 6.43 |
| 109 | 569 | 857 | 1.6 | 2.12×10³ | 3.95 |
| 88 | 403 | 552 | 1.19 | 1.18×10³ | 2.53 |
| 71 | 282 | 384 | 0.956 | 589 | 1.47 |
| 57 | 201 | 278 | 0.799 | 389 | 1.12 |
| 46 | 153 | 209 | 0.694 | 294 | 0.974 |
| 37 | 113 | 172 | 0.659 | 209 | 0.8 |
| 30 | 110 | 166 | 0.735 | 176 | 0.78 |

## Rebuilt curves: J2043+1711, J1738+0333, J1012+5307, J1752−2806

Owner instruction "Proceed with the three steps you've outlined" (step 1).
The four consumed preparations could no longer be loaded, so each target was
prepared again from its committed config in a fresh development root,
calibrated and given a curve, on simulated data only. Each fresh calibration
reproduces the consumed run's threshold (23.00, 22.10, 40.56, 23.06), and the
prepared inputs have the same hash, so the curves describe the runs that were
made. The development roots must not be frozen or run.

### J2043+1711 (threshold 23.00; one global white scale, as run)

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 1,653 | 0.354 | 0.653 | 0.000218 | 15.3 | 0.0051 |
| 1,181 | 0.199 | 0.361 | 0.000151 | 7.7 | 0.00321 |
| 787 | 0.138 | 0.317 | 0.000174 | 2.66 | 0.00146 |
| 551 | 0.109 | 0.156 | 0.000108 | 1.17 | 0.000815 |
| 403 | 0.146 | 0.268 | 0.000229 | 1.08 | 0.000924 |
| 267 | 0.0952 | 0.13 | 0.000146 | 0.417 | 0.00047 |
| 188 | 0.117 | 0.177 | 0.000252 | 0.325 | 0.000462 |
| 129 | 0.0888 | 0.123 | 0.000225 | 0.171 | 0.000313 |
| 89 | 0.0824 | 0.122 | 0.000286 | 0.182 | 0.000424 |
| 62 | 0.0939 | 0.124 | 0.000368 | 0.163 | 0.000483 |
| 43 | 0.0878 | 0.125 | 0.000474 | 0.148 | 0.00056 |
| 30 | 0.086 | 0.119 | 0.000576 | 0.178 | 0.000858 |

The September crossing was at 37.48 days with about 0.09 µs. That is close to
the 50% amplitude here (0.09 µs at 43 days) and below the 95% amplitude
(0.12 µs), so the second-stage non-detection does not exclude a real signal
of that size; it only fails to support one.

### J2043+1711 under the fixed white-noise model (threshold 21.33)

The same target recalibrated with per-receiver white scales and floors (430
MHz and L-wide, each pooling ASP and PUPPI) and a joint white-and-red chain
generator (`config/j2043-joint-noise-receiver-white.json`; 3,150 family
members). The threshold falls from 23.00 to 21.33 and the calibration holds.
The limits barely move: 13–19% lower beyond 700 days, within 7% elsewhere.

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 1,653 | 0.332 | 0.528 | 0.000176 | 14.4 | 0.00481 |
| 1,181 | 0.187 | 0.314 | 0.000131 | 7.24 | 0.00302 |
| 787 | 0.136 | 0.267 | 0.000146 | 2.61 | 0.00143 |
| 551 | 0.105 | 0.15 | 0.000104 | 1.13 | 0.000783 |
| 403 | 0.145 | 0.268 | 0.000229 | 1.06 | 0.000903 |
| 267 | 0.0942 | 0.129 | 0.000145 | 0.417 | 0.00047 |
| 188 | 0.119 | 0.177 | 0.000252 | 0.304 | 0.000433 |
| 129 | 0.0888 | 0.132 | 0.00024 | 0.181 | 0.000331 |
| 89 | 0.0833 | 0.122 | 0.000284 | 0.182 | 0.000424 |
| 62 | 0.091 | 0.124 | 0.000368 | 0.177 | 0.000526 |
| 43 | 0.0874 | 0.125 | 0.000475 | 0.152 | 0.000577 |
| 30 | 0.0889 | 0.121 | 0.000583 | 0.167 | 0.000807 |

The statement about the September crossing is unchanged: 0.09 µs is still
the 50% amplitude near 37 days and below the 95% amplitude.

### J1738+0333 (threshold 22.10)

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 1,960 | 4.29 | 7.58 | 0.00226 | 36.2 | 0.0108 |
| 1,307 | 1.72 | 3.44 | 0.00134 | 13.1 | 0.00512 |
| 933 | 1.01 | 2.21 | 0.00108 | 4.39 | 0.00215 |
| 632 | 0.579 | 0.947 | 0.0006 | 1.45 | 0.000916 |
| 426 | 0.625 | 0.852 | 0.000702 | 1.17 | 0.000964 |
| 293 | 0.593 | 0.812 | 0.00086 | 0.953 | 0.00101 |
| 200 | 0.6 | 0.847 | 0.00116 | 0.976 | 0.00133 |
| 137 | 0.589 | 0.806 | 0.00141 | 1.01 | 0.00177 |
| 94 | 0.547 | 0.913 | 0.00206 | 0.913 | 0.00206 |
| 64 | 0.567 | 0.828 | 0.00241 | 0.877 | 0.00256 |
| 44 | 0.537 | 0.77 | 0.00289 | 0.891 | 0.00334 |
| 30 | 0.518 | 0.767 | 0.00371 | 0.819 | 0.00396 |

### J1012+5307 (threshold 40.56)

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 2,000 | 2.6 | 3.8 | 0.00112 | 156 | 0.0459 |
| 1,339 | 2.21 | 3.05 | 0.00117 | 82.3 | 0.0316 |
| 940 | 2.05 | 2.7 | 0.00131 | 54.4 | 0.0264 |
| 642 | 1.78 | 2.38 | 0.00149 | 28.6 | 0.0179 |
| 435 | 1.8 | 2.28 | 0.00185 | 18.4 | 0.015 |
| 298 | 1.54 | 2.02 | 0.00211 | 11.6 | 0.0122 |
| 202 | 1.34 | 1.92 | 0.0026 | 7.03 | 0.00951 |
| 138 | 1.27 | 1.77 | 0.00309 | 4.37 | 0.00762 |
| 94 | 1.26 | 1.82 | 0.0041 | 3.18 | 0.00717 |
| 64 | 1.18 | 1.61 | 0.00467 | 2.27 | 0.00659 |
| 44 | 1.22 | 1.59 | 0.00597 | 2.34 | 0.00875 |
| 30 | 1.4 | 1.85 | 0.00894 | 3.01 | 0.0145 |

### J1752−2806 (threshold 23.06)

| Period (days) | 50% amplitude (µs) | 95% amplitude (µs) | 95% minimum mass (M⊕) | 95% amplitude, worst generator (µs) | 95% minimum mass, worst generator (M⊕) |
|---:|---:|---:|---:|---:|---:|
| 301 | 1.26×10³ | 2.69×10³ | 2.56 | 1.16×10⁴ | 11.1 |
| 241 | 1.05×10³ | 1.81×10³ | 1.99 | 7.84×10³ | 8.63 |
| 196 | 763 | 1.27×10³ | 1.61 | 5.5×10³ | 6.95 |
| 161 | 692 | 891 | 1.28 | 3.29×10³ | 4.74 |
| 130 | 530 | 734 | 1.22 | 2.28×10³ | 3.79 |
| 105 | 483 | 758 | 1.45 | 1.62×10³ | 3.1 |
| 86 | 412 | 609 | 1.34 | 1.19×10³ | 2.62 |
| 69 | 346 | 471 | 1.19 | 864 | 2.18 |
| 56 | 320 | 465 | 1.35 | 546 | 1.58 |
| 46 | 267 | 353 | 1.18 | 445 | 1.49 |
| 37 | 232 | 316 | 1.21 | 380 | 1.46 |
| 30 | 195 | 273 | 1.21 | 294 | 1.3 |

## Evidence

`results/research/detection-limits-20261119/` (`limits-other-targets.json`,
`limits-j1453-consumed-run.json`, `limits-j1453.json`, `limits-j1752.json`,
`limits-binaries.json`, `limits-j2043-receiver-white.json`), computed by
`tools/detection_limits.py` from the curves in
`results/research/joint-noise-stage-20261118/` and
`results/research/joint-noise-receiver-white-20261119/j1453/` and
`results/research/retrospective-curves-20261119/`.
