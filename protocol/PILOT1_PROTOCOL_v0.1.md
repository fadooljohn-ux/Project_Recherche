# Pilot 1 calibration protocol v0.1

## State

This document and `config/pilot1.yaml` define a review-only design. The
configuration deliberately records `execution_authorized: false`. A later
freeze record must hash the final implementation and explicitly authorize
execution before the first synthetic Pilot 1 realization is generated.

## P1-A — implement and preflight

1. Implement the covariance-whitened GLS scan using the released white-noise
   and `PLRedNoise` covariance and the projected timing design matrix.
2. Verify numerical equivalence at frozen frequencies against direct
   `ProjectCircularSignal` joint fits.
3. Implement covariance-null generation at the actual TOA epochs and validate
   ensemble whitening before using any null statistic.
4. Implement deterministic matrix enumeration, per-case seeds, resumable
   records, and external artifact hashes.
5. Benchmark 50 cases. Stop if projected runtime exceeds four hours or if any
   numerical/warning gate fails.

## P1-B — threshold calibration

1. Generate exactly the frozen 1,000 calibration nulls.
2. Run the complete trigger period range on each null and retain its global
   maximum statistic.
3. Lock the conservative nearest-rank 99th-percentile threshold and its hash;
   only statistics strictly greater than it trigger.
4. Do not inspect or run the sealed evaluation set before the threshold record
   is committed.

## P1-C — sealed false-positive evaluation

1. Generate the 500 evaluation nulls from the distinct frozen seed.
2. Apply the locked threshold without adjustment.
3. Record the empirical family-wise false-positive rate and a Wilson 95%
   binomial interval.
4. Fail promotion if the observed rate exceeds 1% or its 95% upper bound
   exceeds 2.5%.

## P1-D — injection calibration

1. Enumerate all 284 frozen injection cases before execution.
2. Add each delay to authoritative high-precision TOAs, then execute the
   ordinary refit, trigger, and compatible joint grader.
3. Record application error, trigger statistic/frequency, fit improvement,
   amplitude and phase error, timing-model absorption, astrometric covariance,
   warnings, runtime, memory, and hashes.
4. Run the 29 injection case IDs with the lowest SHA-256 ranks through the
   explicit full-covariance audit.
5. Construct detection-fraction and amplitude-bias surfaces. Do not interpolate
   a 50% or 90% sensitivity crossing unless the sampled amplitudes bracket it.

## P1-E — annual mask and external check

1. At each annual-map period, measure the maximum circular-to-astrometric
   correlation and ordinary-model absorption.
2. Mark every period reaching either frozen 0.8 threshold as ineligible.
3. Convert the 100-day timing-amplitude sensitivity to projected mass under the
   frozen circular 1.4-solar-mass convention.
4. Compare it with the Behrens et al. J1744-1134 90%-recovery reference of 0.56
   lunar masses. A ratio outside 1/3–3 blocks promotion and requires a
   discrepancy dossier; it is not automatically a method failure.

## P1-F — promotion review

Evaluate `docs/V0.1_PROMOTION_SCORECARD.md` using the machine-readable
promotion grader. Publish the complete scorecard even on failure. Only a full
pass authorizes preparation of a separately frozen initial-v0.1 observed-data
run. It never authorizes a discovery claim.
