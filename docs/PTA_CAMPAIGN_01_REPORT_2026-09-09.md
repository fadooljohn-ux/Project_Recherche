# A source-separated search of PPTA, EPTA and InPTA timing data

Project Recherche · Campaign 01 · 9 September 2026

## Abstract

We searched 18 public timing datasets covering 12 isolated pulsars. The seven PPTA DR3, eight EPTA DR2full and three InPTA DR2 datasets were calibrated with a shared 1% conditional false-alarm allowance. 17 datasets produced no qualifying trigger and 1 crossed their frozen thresholds. No planet is confirmed by this campaign.

## Data and method

Each source was processed separately with its released timing model, clock corrections and available noise terms. EPTA DR2full+ was excluded to avoid including its InPTA observations twice. The latest Parkes revision was reconciled against the original files; all seven selected PAR/TIM pairs were identical. InPTA DR2 was pinned to its source commit. All original observations remain outside Git, with input and output hashes in the campaign receipts.

A circular sinusoidal timing delay was searched from 30 days to the smaller of 2,000 days and half the observing span. Timing, astrometry and dispersion/instrument nuisance parameters were projected with the existing covariance GLS runtime. For each dataset, 4,096 fixed-noise simulations established calibration diagnostics. The trigger threshold is at least 2 ln(18 F / 0.01), where F is the full number of grid frequencies; a larger empirical threshold is retained if necessary. This union bound does not require the 18 datasets to be independent. Projection masks and sensitivity were frozen before the observed searches.

The quoted amplitude sensitivity is the median worst-phase circular on-grid amplitude needed for 95% detection probability under the fixed covariance. It is not a posterior upper limit on planets. No observed peak was used to select the original period grids or thresholds.

Three initial EPTA attempts were invalidated by an import defect found during review: uppercase-C excluded rows were accepted as observations, and two released J1730 site-arrival offsets were ignored. J1730-2304, J1744-1134 and J1911+1347 were re-prepared, calibrated and searched in separate replacement directories using the corrected Tempo2 conventions. The 18 valid results below use those replacements. All three original attempts, including their two spurious threshold crossings, remain unchanged in the evidence and workbook history. The correction is based on source syntax, not observed-peak selection; the period policy and 18-dataset allowance remain fixed.

## Dataset results

| Source | Pulsar | TOAs | Peak period (d) | Statistic | Threshold | Peak amplitude (µs) | Null reduced χ² | Outcome |
|---|---|---:|---:|---:|---:|---:|---:|---|
| PPTA | J0711-6830 | 5538 | 47.204 | 16.451 | 28.972 | 0.1832 | 1.013 | NO_TRIGGER |
| PPTA | J1730-2304 | 3306 | 87.223 | 9.359 | 28.970 | 0.1697 | 0.969 | NO_TRIGGER |
| PPTA | J1744-1134 | 5401 | 44.404 | 16.154 | 28.970 | 0.0850 | 0.989 | NO_TRIGGER |
| PPTA | J1824-2452A | 1284 | 74.602 | 16.360 | 28.850 | 0.8028 | 0.858 | NO_TRIGGER |
| PPTA | J1832-0836 | 385 | 157.868 | 7.419 | 27.607 | 0.3520 | 0.901 | NO_TRIGGER |
| PPTA | J1939+2134 | 2456 | 46.568 | 19.875 | 28.934 | 0.0500 | 0.829 | NO_TRIGGER |
| PPTA | J2124-3358 | 3411 | 33.988 | 10.215 | 28.972 | 0.3190 | 1.015 | NO_TRIGGER |
| EPTA | J0030+0451 | 4069 | 56.950 | 9.863 | 29.359 | 0.1611 | 0.996 | NO_TRIGGER |
| EPTA | J1730-2304 | 1315 | 53.697 | 11.129 | 28.739 | 0.1204 | 0.978 | NO_TRIGGER |
| EPTA | J1744-1134 | 1946 | 30.495 | 15.775 | 29.537 | 0.0870 | 0.989 | NO_TRIGGER |
| EPTA | J1801-1417 | 449 | 39.157 | 8.018 | 28.419 | 0.6043 | 1.023 | NO_TRIGGER |
| EPTA | J1843-1113 | 893 | 36.734 | 11.725 | 28.825 | 0.1805 | 0.988 | NO_TRIGGER |
| EPTA | J1911+1347 | 882 | 44.412 | 14.944 | 28.489 | 0.1516 | 0.988 | NO_TRIGGER |
| EPTA | J2124-3358 | 2018 | 91.198 | 10.818 | 28.729 | 0.2460 | 0.980 | NO_TRIGGER |
| EPTA | J2322+2057 | 804 | 208.845 | 5.292 | 28.555 | 0.5042 | 1.004 | NO_TRIGGER |
| INPTA | J1730-2304 | 5585 | 125.223 | 14.655 | 27.119 | 2.7420 | 0.835 | NO_TRIGGER |
| INPTA | J1939+2134 | 18191 | 567.405 | 149.353 | 26.713 | 1.7861 | 0.215 | CANDIDATE |
| INPTA | J2124-3358 | 5153 | 35.816 | 7.963 | 26.713 | 2.6991 | 0.513 | NO_TRIGGER |

The peak is the strongest eligible grid cell, including for NO_TRIGGER datasets. A large null reduced chi-square flags a mismatch with the fixed noise/timing model and limits interpretation of its conditional threshold.

## Candidate review

### J1939+2134 (INPTA)

Disposition: **UNCONFIRMED_PERIODIC_CANDIDATE**. The original grid peak is 567.405 days. We held this period fixed and fitted the time halves, radio-frequency subsets, and a sample excluding the day containing the largest whitened null residual. These are diagnostic fits, with no new grid search or re-use of the full-data threshold for a subset.

| Diagnostic | TOAs | Statistic | Amplitude (µs) |
|---|---:|---:|---:|
| first half | 6572 | 10.133 | 4.8600 |
| second half | 11619 | 68.015 | 1.5576 |
| below 1400 MHz | 18088 | 166.800 | 1.9852 |
| at or above 1400 MHz | 103 | UNIDENTIFIABLE | — |
| remove largest whitened residual day | 18067 | 152.683 | 1.8126 |

The removed day was TDB MJD 59994 (124 TOAs). A candidate remains unconfirmed; these diagnostics do not establish a planetary orbit.

## Cross-source comparison

The 18 datasets represent 12 distinct pulsars. Source overlap is retained in the workbook as separate search records, not as additional unique targets.

| Pulsar | Candidate source / period (d) | Other source | Nearest saved cell (d) | Statistic / threshold | Eligible |
|---|---|---|---:|---|---|
| J1939+2134 | INPTA / 567.405 | PPTA | 566.699 | 0.891 / 28.934 | True |

Different durations, sampling and sensitivity can produce different outcomes. Nearest-grid comparisons are descriptive and do not establish phase coherence or an independent planet confirmation.

## Interpretation of J1939+2134

The remaining InPTA crossing is an **unconfirmed periodic candidate** near 567.405 days, with fitted amplitude 1.786 microseconds and statistic 149.353 against threshold 26.713. The PPTA saved grid at 566.699 days gives statistic 0.891 against 28.934, providing no same-period corroboration. The observing windows differ, so this comparison alone is not an exclusion of every time-variable explanation.

The InPTA source model supplies EFAC and projected DMX estimates but lacks a complete correlated-noise model. Its null reduced chi-square is 0.215, so the fixed covariance has not been independently established as an adequate stochastic description. The small subset at or above 1400 MHz has no residual degrees of freedom after timing projection and cannot provide an identifiable radio-frequency check. These limits prevent interpreting the conditional crossing as evidence sufficient to claim a planet. A future focused follow-up should establish a defensible correlated-noise model and compare receiver-band behavior and timing coherence across sources before making a stronger claim.

## Limits and reproducibility

Noise amplitudes and spectral slopes are treated as fixed. InPTA DMX models provide EFAC scaling but no complete correlated-noise model; its thresholds are therefore conditional on a more limited noise description. PINT uses approximate TCB-to-TDB conversion followed here by linear nuisance projection, rather than a newly converged nonlinear timing solution. Those limitations matter especially for any flagged candidate.

The adapter normalizes Tempo2 formatting and phase flags, retains the source-specific clock corrections, handles Parkes band noise, converts EPTA DM amplitude units, and implements the published EFAC/EQUAD ordering. Preparation errors and earlier preparation artifacts were retained. Direct covariance checks and noiseless circular-signal recovery checks verify the new adapter; historical formal qualification was not rerun.

All 252 historical JSON result/evidence files in the intake baseline retain their original hashes. The campaign freeze, 18 valid terminal records plus three retained invalid import attempts and any diagnostic reviews are retained. The master workbook preserves prior searches, including the J1453+1902 noise-sensitive candidate review.

## References

- [PPTA DR3 data and analysis](https://github.com/danielreardon/PPTA-DR3); [CSIRO data release](https://doi.org/10.25919/j4xr-wp05).
- [EPTA DR2 data, noise and clock files](https://doi.org/10.5281/zenodo.8164425); [customised noise models](https://arxiv.org/abs/2306.16225).
- [InPTA DR2](https://github.com/inpta/InPTA.DR2), commit e2806fcb2c238ec38dd80784dfcb1e6c82f54728.
- [Campaign method and compatibility notes](PTA_CAMPAIGN_01_2026-09-09.md).
