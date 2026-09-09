# Project Recherche initial v0.1

## Status

**PROMOTED — all 22 amended hard benchmarks pass.**

Initial v0.1 is a calibrated, reproducible, single-target research pipeline for
circular timing signals in PSR J1744-1134 between 30 and 2,000 days, subject to
the empirical annual-identifiability mask. It can prepare a separately frozen,
one-shot observed-residual analysis and report calibrated timing-amplitude
sensitivity.

## Included capability

- NANOGrav 15-year v2.1.0 wideband J1744-1134 controlled-data ingestion.
- PINT timing-model reproduction and covariance-aware refitting.
- Covariance-whitened, timing-design-projected circular-signal scanning.
- Empirical 1% global threshold from 1,000 calibration nulls.
- Sealed 500-null false-positive evaluation: 0.4%, Wilson upper 1.4466%.
- TOA-level injection/recovery calibration with compatible joint grading.
- Five-period 50% and 90% recovery sensitivity surface.
- Empirical annual astrometric/absorption mask.
- Immutable manifests, execution freezes, resumable ledgers, and external data
  boundary suitable for later Mac mini/NAS migration.

## Explicit exclusions

Initial v0.1 does not authorize a discovery claim, multi-pulsar survey,
eccentric-orbit search, population inference, or automatic candidate report.
It does not yet authorize the one-shot observed-residual periodic search. That
search requires a separate reviewed freeze fixing the exact input hashes,
detector, annual mask, output schema, candidate-disposition rules, and
unblinding procedure.

The single advisory limitation carried into v0.1 is excess kurtosis in the
non-periodic covariance diagnostic. It did not trip the predeclared failure
rule, but it must remain visible in any later scientific interpretation.
