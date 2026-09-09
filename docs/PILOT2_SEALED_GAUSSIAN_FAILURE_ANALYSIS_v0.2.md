# Pilot 2 Sealed Gaussian Failure Analysis v0.2

## Disposition

The frozen 500-case sealed Gaussian evaluation remains a binding failure. Seven
cases exceeded the locked threshold, giving a 1.4% empirical false-positive rate
and failing both preregistered gates. Nothing in this analysis retunes the threshold,
rerolls a case, or authorizes downstream execution.

## Integrity boundary

The analysis opened the 1,000 calibration records and 500 sealed records read-only.
Every file matched its ledgered byte count and SHA-256 before analysis. A second
complete pass found every hash, size, and modification time unchanged. Calibration
and sealed case IDs and seeds remain disjoint. No random draw, model fit, covariance
realization, periodic scan, or observed-residual access was performed.

## Deterministic findings

The exact two-sample Kolmogorov-Smirnov statistic is 0.04 with p=0.656. The median
and 99th-percentile statistics are also close. This test therefore does not detect a
global distribution shift, although it cannot prove that the distributions are
identical. The seven exceedances span peak periods from about 33 to 637 days and do
not identify one isolated annual or boundary-grid failure mode.

Seven or more false positives occur with 23.7% probability in 500 trials when the
true false-positive probability is exactly 1%. More importantly, the original rule
passes only when at most five events occur. Its pass probability at a true 1% rate is
61.6%, so it falsely rejects 38.4% of correctly calibrated experiments at the design
boundary.

The empirical nearest-rank threshold adds uncertainty. For rank 990 of 1,000, the
implied continuous-population tail probability has a Beta(11, 990) sampling model,
mean 1.099%, and central 95% interval from 0.550% to 1.831%. Integrating over that
uncertainty gives a 32.5% predictive probability of seven or more sealed exceedances
and only a 54.7% predictive probability of passing the original gate.

## Diagnosis

The failure is compatible with finite-sample variability and a fragile acceptance
design; it is not strong evidence that the Gaussian detector distribution changed.
The result nevertheless remains FAIL because the rules were frozen in advance.
Using the sealed outcomes to raise the existing threshold would be invalid.

## Recommended clean revision

A v0.2.1 protocol should start from entirely new preregistered seeds and preserve the
existing 1,500 cases as historical diagnostics only.

The recommended threshold stage uses 5,000 Gaussian calibration cases and order
statistic 4,962. This is a distribution-free one-sided tolerance construction with
95.34% confidence that the locked threshold is at or above the population 99th
percentile. Its expected tail probability is approximately 0.780%, providing room
for finite-sample threshold uncertainty without silently targeting an excessively
small false-positive rate.

The recommended sealed stage uses 2,000 new cases and one primary gate: the Wilson
95% upper bound must not exceed 2.5%. That permits at most 36 false positives and has
99.96% pass probability when the true rate is 1%. The raw false-positive rate remains
a reported estimate, not a redundant second hard gate centered exactly on the null
boundary. This design tests the 2.5% guardrail while the tolerance-limit calibration
controls the 1% target.

Structured-tail and injection work should remain blocked until the revised Gaussian
calibration and sealed stages pass. Sensitivity must then be measured again because
the revised threshold will change detection efficiency.
