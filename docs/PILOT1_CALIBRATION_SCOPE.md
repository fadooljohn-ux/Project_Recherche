# Pilot 1 calibration scope

- **Status:** design frozen for review; execution is not authorized.
- **Target:** PSR J1744-1134 only, using the controlled NANOGrav 15-year
  v2.1.0 wideband data already under `RECHERCHE_DATA_ROOT`.
- **Purpose:** turn the validated Pilot 0 transfer machinery into a calibrated
  single-target circular-signal detector with measured false-positive and
  recovery behavior.
- **Promotion target:** initial Project Recherche v0.1.

## Why this phase exists

Pilot 0 established that a known circular signal can be transferred through a
compatible timing model and independently reproduced with explicit full
covariance. It also showed that the diagonal residual periodogram is not a
calibrated detector and that a one-year signal is nearly singular with
astrometry. Pilot 1 addresses those limitations directly.

Published work supports this architecture. Coles et al. show that correlated
timing residuals require a covariance transformation applied to both the data
and timing model. Behrens et al. calibrate pulsar-planet thresholds with
noise-only simulations and injection recovery, while both Behrens et al. and
Niţu et al. identify a one-year sensitivity loss caused by fitting astrometry.
Modern planet searches fit deterministic, noise, and planet components
simultaneously and treat quasi-periodic red-noise alternatives as a candidate
disposition problem. The controlled evidence is recorded under
`research/pilot1/`.

## Detector architecture

1. **Trigger:** a covariance-whitened generalized-least-squares circular scan.
   It projects the frozen timing design matrix and uses the complete released
   white-noise plus `PLRedNoise` covariance. Its statistic is the maximum
   delta-chi-squared over the frozen period range.
2. **Threshold:** the conservative nearest-rank 99th percentile of 1,000
   calibration-null global maxima. A trigger must be strictly greater than the
   locked threshold.
3. **Sealed evaluation:** 500 disjoint nulls, generated from another frozen
   seed, measure the actual family-wise false-positive rate without retuning.
4. **Grader:** `ProjectCircularSignal` is jointly fitted with the release timing
   model at the proposed frequency. `WaveX` remains prohibited.
5. **Audit:** the lowest SHA-256-ranked ten percent of injection case IDs are
   repeated with explicit full covariance.

The nulls are Gaussian realizations of the frozen release covariance at the
actual TOA epochs. This tests the search under the released stochastic model;
it does not prove that the model captures every real nonstationary or
quasi-periodic process.

## Frozen workload

| Workload | Construction | Cases |
|---|---|---:|
| Calibration nulls | Released covariance, seed 17441135 | 1,000 |
| Sealed evaluation nulls | Released covariance, seed 17441136 | 500 |
| Main injection grid | 5 periods × 4 amplitudes × 4 phases × 3 noise realizations | 240 |
| Annual identifiability map | 7 periods × 1 amplitude × 4 phases | 28 |
| Search-boundary map | 2 periods × 2 amplitudes × 4 phases | 16 |
| Full-covariance audit | Deterministic 10% of all injections | 29 |

The main grid uses periods of 50, 100, 200, 500, and 1,000 days and amplitudes
of 0.5, 1, 2, and 5 microseconds. The annual map spans 300–450 days with an
explicit 365.25-day point. Boundary diagnostics use 30 and 2,000 days.

## Empirical eligibility mask

A period is ineligible for a real-signal claim if either:

- the maximum absolute correlation between the circular coefficients and
  astrometric parameters is at least 0.8; or
- the ordinary timing model absorbs at least 80% of the injected waveform.

The mask is inferred period by period from the annual grid. Masked periods are
reported as sensitivity gaps; they are not silently removed and cannot produce
a candidate. This replaces an arbitrary fixed-width one-year exclusion with a
measured identifiability boundary.

## Resource estimate

The plan contains 1,784 trigger scans, 568 primary timing fits, and 29 explicit
full-covariance audits. Applying the measured Pilot 0 per-fit costs plus a
conservative trigger allowance gives a planning estimate of **1.58 hours**.
The frozen MacBook caps are four hours, 16 GiB peak memory, and 5 GiB for the
complete data root.

This estimate is provisional until the trigger implementation is benchmarked.
If the first 50-case benchmark projects above four hours, execution stops for
optimization or migration planning; the scientific thresholds do not change.

## Boundaries

- Pilot 1 is a circular-orbit calibration; eccentric or multi-planet models are
  omitted.
- No blind search of the observed residuals occurs during calibration.
- No candidate, anomaly outreach, upper-limit publication, or discovery claim
  is authorized by this design.
- Passing Pilot 1 promotes the tool to initial v0.1. It does not itself execute
  a real-data search; that requires a separately frozen initial-v0.1 run.
