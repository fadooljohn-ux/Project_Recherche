# Pilot 2 B1937+21 v0.2.2 first-case crash audit

## Disposition

The v0.2.2 execution gate passed, but the runner raised an `AttributeError`
while producing phase telemetry for the first deterministic injection case. No
case record or checkpoint was written. The attempted case ID
`p2r2-inj-main-p00-a00-h00-n00` and seed `2691995251659989168` are consumed and
must never be reused.

The v0.2.2 execution freeze, inventory, ledger, health record, setup log, and
prior predecessor artifacts remain historical evidence. v0.2.2 is not
resumable and may not be patched, rerun, retuned, or regraded.

## Root cause

`_phase_telemetry` called PINT's `get_parameter_correlation_matrix()` and
treated the return value as a `CorrelationMatrix`. In the installed PINT
version that method returns formatted text on this code path. The fitted
correlation object is instead available as `fitter.parameter_correlation_matrix`,
which is already the accessor used by the annual-correlation diagnostic.

The preexecution tests asserted the presence of phase telemetry and exercised
record grading, but they did not execute the real fitted PINT accessor. This
allowed an API-shape incompatibility to pass the implementation-readiness
suite.

## Secondary control failure

The unexpected exception occurred outside a terminal exception handler. The
heartbeat service correctly marked the process inactive, but the ledger
remained in a running stage without a hard stop. Future runners must convert
unexpected execution exceptions into a versioned terminal failure result and
hard stop while retaining orderly user interruptions as resumable.

## v0.2.3 requirements

1. Use a separate executor, runner, paths, ledger, health record, and result.
2. Use 344 new case IDs and seeds disjoint from both v0.2.1 and the entire
   frozen v0.2.2 inventory.
3. Treat the attempted v0.2.2 first case as consumed even though it wrote no
   record.
4. Validate the PINT accessor contract without generating a random draw,
   fitting a science case, or scanning data.
5. Terminalize unexpected exceptions with error type, message, active case ID,
   completed-case count, and immutable result binding; never include partial
   scientific metrics in the failure record.
6. Keep execution, promotion, observed residual access, and discovery claims
   locked behind separate future authorization.

## Audit boundary

This audit inspected process state, the traceback, source code, hashes, and
non-scientific ledger counts. It did not inspect an injection outcome,
candidate metric, trigger result, fit result, observed residual, or periodic
search result.
