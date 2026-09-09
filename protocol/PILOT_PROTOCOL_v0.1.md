# Pilot protocol v0.1

## State control

The target, dataset, fitting tolerances, injections, phase, and seed are frozen
before timing results are inspected. Changes require an entry in
`protocol/AMENDMENTS.md`, a reason, and a new freeze-record hash.

## Stage A — environment and source control

1. Recreate the Pixi lock without widening pinned PINT or Python versions.
2. Record architecture, NumPy/PINT versions, precision characteristics, and
   machine resources.
3. Preserve the archive unchanged; verify published MD5 and independently
   record SHA-256.
4. Extract only the target input, clock support, and release documentation.

## Stage B — published solution reproduction

1. Load the release `.par` and `.tim` inputs without suppressing warnings.
2. Use release clock and solar-system-ephemeris settings.
3. Record TOA count/span, fitted parameters and uncertainties, fit statistic,
   weighted RMS, whitened-residual diagnostics, wall/CPU time, and peak memory.
4. Compare with the release model under Gate G2. Stop on failure.

## Stage C — injection/refit transfer

Injection remains blocked until a committed G2 gate record says `pass`.
For every case, modify TOAs, refit the same allowed timing parameters, and
record achieved amplitude, recovered amplitude, absorption fraction, trigger
frequency, Fourier-bin offset, and fit improvement. The noise model remains
fixed; no false-alarm probability is assigned.

## Claim boundary

Project Recherche is intended for real scientific analysis. During this
validation pilot, however, any noninjected periodic feature is a diagnostic
artifact unless and until a future, separately authorized and calibrated
protocol establishes otherwise. A low prior probability of detection does not
weaken the evidentiary standard. This pilot has no anomaly or outreach lane.
