# Pilot 1 calibration-null result v0.1

The frozen calibration population passed all 13 gates. Ten hash-bound scans
from the corrective benchmark and 990 newly executed scans produced exactly
1,000 global maximum delta-chi-squared values. Null whitening, lag correlation,
warning hygiene, artifacts, memory, and storage passed.

The conservative nearest-rank 99th percentile is **23.33426855482562** at rank
990. Under the frozen strict-greater-than rule, ten calibration values exceed
that threshold. The exact value and its source-summary hash are locked in
`PILOT1_THRESHOLD_LOCK_v0.1.json` before any sealed result is generated.

No sealed evaluation case or observed residual was inspected during
calibration.
