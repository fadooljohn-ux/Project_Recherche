# Pilot 1 tail-robustness result v0.1

## Decision

**FAIL — 20 of 22 hard gates passed.** The result is preserved and must not be
regraded with the same evaluation set.

The one-percent scale-mixture stress evaluation produced 7 false positives in
500 disjoint nulls: 1.4%, with Wilson 95% upper bound 2.8613%. These exceed the
frozen limits of 1% and 2.5%, respectively. The contaminated calibration
99th-percentile threshold was 22.1103, below the initial-v0.1 threshold of
23.3343, so the frozen maximum rule retained 23.3343.

## What passed

- Exact 1,000 calibration and 500 evaluation null inventories.
- Exact 160 contaminated recovery cases.
- Five of five periods showed monotonic response and bracketed 50%/90%
  crossings.
- Frequency recovery among threshold triggers was 100%.
- All 16 complete ordinary/joint refit audits converged.
- All four independent full-covariance audits passed.
- All ledgers, warnings, hashes, runtime, memory, and storage controls passed.
- No observed residual was scanned at any frequency.

## Tail localization

The combined projected excess-kurtosis result reproduced at 1.26214. The timing
block had absolute excess kurtosis 2.04994 and the DM block 0.68721. The largest
projected coordinate was in the DM block, but removing it reduced the combined
kurtosis by only 36.7%; no single coordinate explains the advisory. The top
five coordinates contained 8.70% of projected squared energy.

Whitening and timing projection mix coordinates, so metadata associated with a
projected coordinate is an influence locator rather than proof that a named
measurement is the physical cause.

## Corrective authorization

The failure authorizes a separately frozen R1 threshold rebaseline using new,
disjoint calibration and evaluation seeds. The failed 500-case evaluation set
must not be reused for grading. The 160 recovery artifacts may be regraded at a
new threshold because their synthetic inputs, scan statistics, fits, and
artifact hashes are immutable and threshold-independent.

The observed-residual periodic search remains unauthorized.
