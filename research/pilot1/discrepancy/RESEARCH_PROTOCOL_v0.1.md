# Pilot 1 published-reference discrepancy protocol v0.1

## Decision

Determine why the frozen Pilot 1 100-day, 90%-recovery result is at least
6.95 times more sensitive in projected mass than the 0.56-lunar-mass value
reported for PSR J1744-1134 by Behrens et al. (2020), and decide whether a
lower-amplitude extension is scientifically justified.

This is a targeted evidence audit, not a systematic review.

## Frozen questions

1. What exactly does the published 0.56-lunar-mass value represent: target,
   data release, orbital convention, recovery convention, timing refit, noise
   construction, threshold, and any empirical correction?
2. Does the Pilot 1 timing-amplitude-to-projected-mass conversion implement the
   circular, low-companion-mass Keplerian relation correctly?
3. Are the published and Pilot 1 sensitivity values comparable enough to serve
   as a factor-of-three promotion gate?
4. Without a blind periodic search of observed residuals, does the released
   covariance model reproduce predeclared, non-periodic residual diagnostics?

## Evidence and provenance

- Primary peer-reviewed papers, their public manuscripts, official release
  documentation, and controlled project artifacts are eligible.
- Decisive literature claims require a PDF page locator and direct inspection
  of that page.
- Controlled PDFs remain immutable under `RECHERCHE_DATA_ROOT`; Git stores
  citations, hashes, page locators, calculations, and conclusions only.
- Search and version/correction checks end on 2026-08-09 (Asia/Taipei).

## Predeclared calculations

- Re-derive projected companion mass from the light-travel timing amplitude,
  Kepler's third law, and the center-of-mass relation.
- Compare 1.4- and 1.5-solar-mass assumptions and the exact two-body solution.
- Decompose the reference ratio into data-span, timing-refit, noise-model,
  threshold/recovery, and conversion effects where the sources permit.
- Evaluate observed J1744 residuals only through global, non-periodic checks:
  whitened variance, chi-square per projected degree of freedom, distribution
  shape, and predeclared lag-correlation summaries. No frequency scan,
  periodogram, peak search, or candidate inference is authorized.

### Frozen residual-diagnostic design

- Generate 1,000 covariance realizations with seed `17441138` at the released
  J1744 epochs, whiten and timing-project them exactly as the frozen detector
  does, and compare the equivalently processed observed release residual
  vector with that reference ensemble.
- Hard metrics are projected whitened energy per residual degree of freedom,
  maximum absolute projected whitened residual, and maximum absolute lag
  correlation over lags 1–16 calculated separately within the TOA and DM
  blocks. Each must lie inside the empirical central 99% interval.
- Advisory metrics are projected whitened variance, absolute skewness,
  absolute excess kurtosis, and median absolute deviation. Two or more advisory
  metrics outside their empirical central 99% intervals constitute a hard
  covariance-adequacy failure.
- Quantile bounds use NumPy's `inverted_cdf` estimator. The observed residuals
  are evaluated once after this design is recorded.

## Decision rules

- **Reference verified and comparable:** retain the hard gate; an amended
  injection grid may proceed only if residual diagnostics also pass.
- **Reference verified but not comparable:** remove it as a numerical promotion
  gate through a reviewed protocol amendment; retain it as contextual evidence.
- **Conversion defect:** correct the implementation and replay every dependent
  result before considering an amended grid.
- **Covariance adequacy fails:** do not extend the synthetic grid; first amend
  the null/noise protocol.
- **Covariance adequacy passes and no conversion defect exists:** freeze a
  lower-amplitude extension sized to bracket 50% and 90% recovery.

Initial v0.1 remains unauthorized unless every resulting hard benchmark passes.

## Stopping rule

Stop when each frozen question has direct evidence or is explicitly marked
unresolved; the decisive PDF pages have been inspected; the version/correction
check is recorded; the calculation is independently reproduced; and the
predeclared residual diagnostics have either passed or failed. Two successive
search passes must add no new load-bearing method category.
