# Pilot 1 tail-robustness R1 protocol v0.1

## Reason for correction

The original frozen tail gate failed 20/22 because its disjoint 500-null stress
evaluation produced 7 false positives at the retained 23.3343 threshold. The
observed rate was 1.4% and the Wilson 95% upper bound was 2.8613%, exceeding the
frozen 1% and 2.5% limits. That failure remains authoritative.

## Independence rule

R1 must not grade against, tune on, or otherwise reuse the failed 500-case
evaluation set. It uses new seeds for exactly 2,000 calibration nulls and 1,000
evaluation nulls. The seeds and case identifiers must be disjoint from each
other and from both original tail-gate null sets.

## Corrected threshold rule

Use the same frozen one-percent, unit-variance Gaussian scale mixture with
theoretical excess kurtosis 1.262140834554768. Estimate its 99.5th-percentile
global synthetic scan statistic with the conservative nearest-rank estimator.
Lock the R1 threshold to the larger of that value and the initial-v0.1 value.
Do not retune after examining the 1,000 disjoint R1 evaluation cases.

The higher quantile is a prospective conservative response to model-tail risk;
the larger calibration and evaluation samples improve tail resolution and
binomial precision. Passing still requires evaluation false-positive rate at
most 1% and Wilson 95% upper bound at most 2.5%.

## Recovery regrade

The 160 original tail-stress recovery artifacts are immutable and bind their
synthetic inputs, scan statistics, complete refits, and independent covariance
audits. R1 may reapply only the newly locked threshold to those stored scan
statistics. It must not regenerate an injection, refit a case, change a peak,
or read an observed residual.

Require frequency recovery at least 95% among R1 threshold triggers, monotonic
response at three or more periods, bracketed 50%/90% crossings at three or
more periods, zero complete-refit failures, and zero full-covariance-audit
failures.

## Boundary and decision

R1 is entirely synthetic and must not calculate, load, or scan the observed
residual vector. A pass authorizes preparation of a separately reviewed
one-shot observed-residual search freeze only. A failure requires a detector
rebaseline or robust-statistic replacement before any observed search.
