# Pilot 1 null-result sensitivity interpretation protocol v0.1

## Purpose

Translate the completed v0.1 null search into bounded sensitivity statements
using only the already frozen injection/recovery summaries. This analysis reads
the published one-shot result record but never loads the observed residual
vector, executes a period search, changes the threshold, or generates new
randomness.

## Recovery surface

Use the immutable combined recovery surface at 50, 100, 200, 500, and 1,000
days. Each amplitude cell contains 12 cases formed from four fixed phases and
three covariance-noise realizations per phase. Recovery means both exceeding
the locked global threshold and locating the peak within one independent
Fourier bin of the injected frequency.

Retain the frozen linearly interpolated 50% and 90% empirical crossings as
point estimates. Do not interpolate between periods.

## Finite-sample uncertainty

For every sampled cell, calculate the two-sided 95% Wilson interval for its
recovered count. This interval is an uncertainty diagnostic for the finite
stratified case set; it is not a guarantee over an unrestricted population of
signals, phases, or noise states.

For conservative grid summaries, identify the smallest sampled amplitude whose
Wilson lower bound is at least 50% or 90%. Do not interpolate this conservative
quantity. If no sampled amplitude qualifies, report `null` rather than
extrapolating.

Because each cell has only 12 cases, even 12/12 recovery has a two-sided 95%
Wilson lower bound below 90%. Therefore the empirical 90% crossings cannot be
reported as formal 95%-confidence exclusion limits.

## Projected-mass conversion

Convert timing amplitudes to projected companion masses using the frozen
1.4-solar-mass, low-companion-mass circular-orbit convention. These are
`m sin(i)`-like projected quantities, not true masses. Report conversions only
at calibrated periods and never interpolate a mass limit across period.

## Annual and model gaps

Retain 350, 365.25, and 380 days as explicit sensitivity gaps. Eligibility
checks at 300, 330, 400, and 450 days do not supply lower-amplitude recovery
crossings. The interpretation also does not cover periods outside 30–2,000
days, signals below the tested grid, eccentric or nonstationary families, or
signals absorbed differently than the frozen circular model.

## Authorized claims

The result may report:

- the observed null under the exact frozen detector;
- empirical 50% and 90% crossing point estimates at five calibrated periods;
- cell counts and Wilson uncertainty diagnostics;
- conservative sampled-grid 50% recovery thresholds; and
- the absence of a sampled amplitude supporting a 90% Wilson lower bound.

It may not call the empirical crossings formal upper limits, claim 95%
exclusion, rerun the observed search, tune the threshold, or generalize beyond
the calibrated circular-signal family.
