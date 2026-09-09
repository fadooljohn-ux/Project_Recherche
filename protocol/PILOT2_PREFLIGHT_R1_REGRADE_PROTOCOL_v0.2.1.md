# Pilot 2 preflight R1 deterministic regrade protocol v0.2.1

## Purpose

Regrade the 50 immutable B1937+21 R1 preflight case artifacts after two grading
implementation defects produced a false overall failure. This operation loads
only JSON records. It does not load TOAs or timing models, generate random
values, fit a model, scan a vector, download a file, or rerun a case.

## Frozen corrections

The application-integrity gate uses
`toa_adjustment_maximum_absolute_error_microseconds`, matching the established
v0.1 benchmark gate and its unchanged 0.001-microsecond limit. The
`uncentered_toa_residual_target_maximum_absolute_error_microseconds` value
remains reported as a numerical diagnostic and is not substituted for that
gate.

The exact warning that the controlled `time_ao.dat` overrides the global
`time_ao.dat` is dispositioned as an expected controlled release-clock
override. This is the Arecibo counterpart of the already accepted `time_gbt.dat`
and `tai2tt_bipm2019.clk` override warnings. No other warning is reclassified.

## Source and gates

The source summary must match SHA-256
`b007205c4751e9171c5ab04c54ce02ed7b5e48bc4ed2d219e1477db7542d8d6a`.
Every one of its 50 case-artifact hashes must verify. The regrader then applies
the original counts, solver tolerances, resource caps, reproduction gates, and
scope prohibitions. No threshold, recovery criterion, seed, case, fit result,
or scientific diagnostic may change.

Passing this regrade means the bounded preflight passes. It permits preparation
of a separately frozen target-specific full-calibration design; it does not
authorize calibration or an observed search.
