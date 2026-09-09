# Pilot 1 calibration-null execution freeze v0.1

## Authorized work

This gate authorizes the 990 calibration-null trigger scans that were not part
of the successful corrective first-50 benchmark. Ten completed calibration
scans are reused only after their case IDs, seeds, paths, and SHA-256 hashes
match this freeze. Together they form the exact frozen population of 1,000.

Each new null is generated from the released full covariance at the actual
J1744-1134 wideband epochs and scanned over the unchanged 30–2,000 day
covariance-whitened GLS grid. Per-case artifacts and a resumable ledger remain
under `RECHERCHE_DATA_ROOT`.

## Threshold disposition

The run calculates the conservative nearest-rank 99th percentile: rank 990 of
the sorted 1,000 global maximum delta-chi-squared values. A later trigger must
be strictly greater than this value. The calibration run reports this as a
proposed threshold only. A distinct version-controlled record must lock the
value before the sealed evaluation can be authorized.

## Stop conditions

Progression stops if the case split, source hashes, artifact ledger, covariance
diagnostics, warnings, memory, or storage gate fails. The sealed 500 evaluation
nulls, observed residuals, discovery claims, and initial-v0.1 promotion all
remain unauthorized by this freeze.
