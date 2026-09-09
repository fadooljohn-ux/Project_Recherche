# Pilot 2 B1937+21 Calibration Revision Design v0.2.1

## Status

This is a non-executing clean revision. It does not modify, rehabilitate, or supersede
the recorded v0.2 failure. The 1,500 completed v0.2 null cases and their threshold
remain immutable historical diagnostics and are excluded from every v0.2.1 case set.

## Reason for revision

The v0.2 sealed evaluation failed its frozen 1% empirical-rate and 2.5% Wilson-upper
gates. Deterministic analysis found no detectable whole-distribution shift and showed
that the original acceptance rule falsely rejects 38.4% of experiments operating at
exactly a 1% false-positive rate. The empirical rank-990-of-1,000 threshold also had
material tail-probability uncertainty.

The revision separates two statistical roles:

1. A distribution-free tolerance order statistic controls the 1% population-tail
   target during threshold construction.
2. A larger independent sealed sample checks that the realized implementation stays
   below the preregistered 2.5% guardrail.

## New inventory

All 10,284 case IDs and seeds are new and disjoint from v0.2:

- 5,000 Gaussian threshold-calibration nulls.
- 2,000 independently seeded sealed Gaussian nulls.
- 1,000 cases for each of the three structured-tail variants.
- 240 main injections, 28 annual-map injections, and 16 boundary injections.
- 29 deterministic full-covariance audits selected from the 284 injections.

The structured-tail and injection designs retain their scientific definitions but use
new case identities and seeds. They remain blocked until both revised Gaussian stages
pass.

## Threshold construction

The threshold is the 4,962nd ascending statistic among 5,000 calibration maxima.
For a continuous null distribution, this is the least order-statistic rank whose
one-sided confidence of lying at or above the population 99th percentile is at least
95%; the exact confidence is 95.343%. Its expected population-tail probability is
approximately 0.780%.

The threshold must be committed as a hashed lock before any sealed case. It may not
be changed after the sealed set is opened.

## Sealed evaluation

The sealed set contains 2,000 new cases. Its single primary acceptance gate is a
Wilson 95% upper bound no greater than 2.5%, equivalent to no more than 36 false
positives. The observed false-positive fraction remains prominently reported but is
not a second hard gate centered exactly at the 1% design boundary.

At a true 1% rate, the sealed gate passes with 99.961% probability. This low false-
rejection rate is intentional: the 1% target is controlled by the tolerance-limit
calibration, while the sealed stage detects gross implementation or distribution
failures against the 2.5% guardrail.

## Resource projection

The revised full workload is projected at 2.679 hours including 25% contingency,
below the six-hour MacBook ceiling. The additional 5,500 Gaussian scans add little
wall time because injection refits and full-covariance audits dominate. No download
is required.

## Authority boundary

This design authorizes no random draw, fit, scan, threshold construction, sealed-case
opening, observed-residual access, or observed periodic search. Execution requires a
new implementation package, zero-case verification, a separate execution freeze, and
explicit user authorization.
