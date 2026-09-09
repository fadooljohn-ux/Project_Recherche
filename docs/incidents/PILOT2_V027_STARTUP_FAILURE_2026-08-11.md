# Pilot 2 v0.2.7 startup failure — preserved terminal record

## Disposition

The authorized v0.2.7 run passed repository and real-root gates, then failed
during release-context setup before the first attempt journal or case executor.
The process exited with code 1 and the runner wrote a terminal hard stop.

v0.2.7 is preserved. It was not restarted, repaired, rerolled, retuned, or
regraded.

## Cause

PINT requested its global clock-correction index while loading the frozen
release. The runner's network-denial boundary rejected that request with:

```text
RuntimeError: Network access is disabled for the Pilot 2 preflight
```

This is a startup dependency failure, not a scientific result and not a case
failure. The required clock-correction resource was not locally available to
the frozen environment in the form PINT expected.

## Integrity scorecard

| Control | Outcome |
|---|---|
| Repository execution authorization | PASS |
| Real-root predecessor gate | PASS |
| Context setup | FAIL — clock index requested network access |
| First attempt journal | Not reached |
| Case executor | Not reached |
| Completed cases | 0/344 |
| Case directory root | Not created |
| Random draws | 0 |
| Timing-model fits | 0 |
| Periodic scans | 0 |
| Partial scientific metrics | None |
| Observed residual access | None |
| Promotion grading | Not executed |
| Terminal hard stop | Present |
| Restart or remediation | None |

## Preserved evidence

The external ledger, health record, terminal result, and setup log are bound by
SHA-256 in
`results/pilot2/injection_v027_startup_failure_audit.json`. The version ledger
reports a failed injection stage, zero completed records, no active attempt,
and a stopped runtime.

## Next gate

Wait for user guidance. Any remediation must preserve v0.2.7 and use a new
version with a zero-science, fail-closed clock-resource preflight before a new
execution authorization is considered.
