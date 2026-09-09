# Pilot 1 detector-method evidence brief

## Question and mode

- **Decision:** what minimum detector, calibration, annual-degeneracy, and
  candidate-disposition controls should govern Pilot 1 and promotion to
  initial v0.1?
- **Mode:** representative scoping scan, not a systematic review.
- **System:** public pulsar-timing searches for periodic/planet-like signals,
  with emphasis on high-precision MSP data and PSR J1744-1134.
- **Search end:** 2026-08-09 (Asia/Taipei).
- **Eligible evidence:** primary peer-reviewed articles and accessible author or
  repository copies; English-language methods and results.
- **Excluded:** gravitational-wave detection methods except where they directly
  establish pulsar-noise handling; secondary summaries; inaccessible full
  texts; non-pulsar exoplanet searches.
- **Stopping rule:** stop after the core covariance, empirical-calibration,
  modern joint-model, annual-degeneracy, and J1744-specific query families were
  represented and two successive passes produced no new load-bearing method
  category.

## Findings

1. **Verified:** a white-error periodogram is not an adequate final statistic
   when timing residuals are correlated. GLS/Cholesky methods whiten both the
   observations and timing design matrix and reduce parameter bias and invalid
   uncertainty estimates (SRC-002, PDF pp. 2–3; printed pp. 562–563).
2. **Verified:** a published NANOGrav planet search used 10,000 noise-only
   simulations per pulsar to set a maximum-power threshold and 1,000 injection
   trials per frequency to locate a 90%-recovery limit (SRC-001, PDF p. 4).
   Its white-noise null construction is useful precedent but is not adequate
   for this project because Pilot 0 and later literature demonstrate material
   correlated-noise behavior.
3. **Verified:** modern large-sample searches jointly model deterministic timing
   parameters, white noise, red noise, and planet parameters, and treat
   posterior flags as prompts for evidence and alternative-noise investigation
   rather than automatic discoveries (SRC-003, PDF pp. 3–5).
4. **Verified:** sensitivity near one year is lost through astrometric fitting.
   Behrens et al. describe near-erasure at 1 yr, while the EPTA analysis assigns
   a dedicated 340–390-day bin and excludes the region from its general mass
   limit statement (SRC-001, PDF pp. 3 and 5; SRC-004, PDF pp. 3 and 6).
5. **Verified:** J1744-1134 specifically has significant achromatic red noise in
   the EPTA analysis, and the periodic and quasi-periodic models both appear to
   compete for long-timescale power without clearly improving the model
   (SRC-004, PDF pp. 4–5 and 9). This makes noise-aware calibration and an
   explicit long-period disposition essential for this target.

## Design consequence

Pilot 1 therefore uses a covariance-whitened trigger, disjoint calibration and
evaluation nulls, simultaneous compatible grading, an empirical annual mask,
and a published-reference reconciliation. The evidence does not dictate the
project's exact null counts or pass thresholds; those are conservative design
choices sized to measure a 1% family-wise rate on the MacBook while retaining a
sealed evaluation set.

## Limitations

- The four-source corpus is deliberately narrow and representative.
- SRC-001 uses white-noise simulations and a different NANOGrav release; its
  J1744 mass limit is a sanity reference, not expected identity.
- SRC-003 primarily concerns ordinary pulsars, while SRC-004 supplies the more
  directly applicable MSP/J1744 context.
- The released Gaussian-process covariance may not reproduce nonstationary or
  quasi-periodic real noise. Passing simulated nulls cannot remove that model
  limitation.
