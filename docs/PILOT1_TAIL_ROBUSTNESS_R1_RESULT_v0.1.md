# Pilot 1 tail-robustness R1 result v0.1

## Decision

**PASS — all 22 R1 hard gates passed.** The original 20/22 failure remains
preserved and was not regraded.

R1 generated 2,000 new contamination calibration nulls and 1,000 new,
disjoint evaluation nulls. Its 99.5th-percentile contamination threshold was
23.2674, below the initial-v0.1 threshold of 23.3343. The frozen maximum rule
therefore retained 23.3343 without changing the detector threshold.

The R1 evaluation produced 7 false positives in 1,000 trials: 0.7%, with a
Wilson 95% upper bound of 1.4378%. Both pass the frozen 1% and 2.5% limits.
The failed original 500-case evaluation set was not used for R1 grading.

For context only, the two disjoint tail evaluations together contain 14 false
positives in 1,500 cases: 0.9333%, with Wilson 95% upper bound 1.5606%. This
post-hoc combined estimate is descriptive and is not an R1 gate.

## Recovery under the retained threshold

All 160 immutable contaminated recovery cases were hash-verified and regraded
without regenerating data or repeating fits. Frequency recovery among triggers
remained 100%. All five periods remained monotonic and bracketed both 50% and
90% crossings. The 90% crossings were 0.320, 0.330, 0.320, 0.326, and 0.485
microseconds at 50, 100, 200, 500, and 1,000 days respectively.

All 16 complete refits and all four independent full-covariance audits retained
their passing outcomes.

## Interpretation

The excess-kurtosis advisory is real and remains a limitation, but the expanded
disjoint stress test does not support raising the current 23.3343 threshold.
The original 7/500 failure is consistent with the sampling uncertainty exposed
by its small evaluation set; R1 improves precision without erasing that result.

## Boundary and next authorization

R1 did not access the observed residual vector, reuse the failed evaluation set
for grading, or execute an observed periodic search. Passing authorizes only
preparation of a separately reviewed one-shot observed-residual search freeze.
It does not authorize executing that search or making a candidate claim.
