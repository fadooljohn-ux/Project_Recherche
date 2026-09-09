# Pilot 1 first-50 corrective replay freeze v0.2

- **Corrective benchmark:** `pilot1-first-50-corrective-replay-v0.2`.
- **Authorized cases:** the same 50 IDs, seeds, and order as v0.1.
- **Scientific thresholds:** unchanged.
- **Sealed evaluation:** not authorized.
- **Observed-residual search:** not authorized.

## Reason for replay

Benchmark v0.1 passed 16 of 17 hard gates. Its application-accuracy metric
compared PINT's default mean-subtracted TOA residuals against an uncentered
requested residual vector. That counted the fitted constant offset as waveform
error and produced a 1.462-microsecond maximum against the 0.001-microsecond
gate.

## Frozen correction

The synthetic construction now requests uncentered PINT TOA residuals while
removing the release residual and measuring the resulting residual target as a
diagnostic. The hard injection gate itself measures the actual high-precision
MJD adjustment against the requested adjustment, matching the Pilot 0
round-trip method.

The corrected runner uses new output, ledger, log, and summary paths. It cannot
resume from or overwrite the v0.1 artifacts. Its execution identity binds the
corrected implementation hash to the unchanged case-order hash.

## Authorization boundary

This freeze authorizes one deterministic replay of the same 50 cases. It does
not authorize new case IDs, remaining calibration nulls, sealed evaluation,
the complete injection matrix, threshold locking, promotion, or a candidate
claim. Any failed replay row again stops progression.
