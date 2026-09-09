# Pilot 2 B1937+21 injection execution readiness v0.2.2

## Outcome

The versioned v0.2.2 injection runner is **implementation-ready and execution
locked**. The repository passes 193 tests and lint. The standalone zero-case
dry run passes every integrity, recovery, heartbeat, and authorization-ordering
gate while executing no science case, random draw, model fit, or periodic scan.

This readiness result does not authorize execution.

## Scorecard

| Gate | Outcome | Evidence |
|---|---:|---|
| v0.2.1 immutability | PASS | Terminal result and ledger SHA-256 unchanged |
| Passed predecessor bindings | PASS | Threshold, sealed, and structured-tail hashes verified |
| Failed-injection reuse boundary | PASS | v0.2.1 injection records excluded from acceptance |
| Independent v0.2.2 paths | PASS | Ledger, health, dashboard, cases, log, and result are versioned |
| Prospective inventory | PASS | 344 cases and 35 audits |
| Case and seed disjointness | PASS | No v0.2.1 overlap |
| Execution order | PASS | Main, phase reference, annual groups, boundary |
| Canonical TOA gate | PASS | Legacy-only metric fails closed |
| Phase-reference gate | PASS | 60 controls; unchanged 0.1-radian p90 limit |
| Main phase diagnostic boundary | PASS | Reported, not substituted for detection grading |
| Resume binding | PASS | Inventory, implementation, execution, and artifact hashes required |
| Checkpoints | PASS | Every 25 cases |
| Corruption detection | PASS | Altered recorded artifact blocks resume |
| Terminal hard stop | PASS | Failed grade persists and prevents restart |
| Heartbeat | PASS | 30 seconds; stale after 90 seconds |
| Passive review interval | PASS | 30 minutes |
| Health-only record | PASS | No threshold, trigger, candidate, fit, or phase outcome |
| Manual refresh and dashboard | PASS | Recorded command and 30-second refresh |
| Resource envelope | PASS | 3.234-hour projection versus six-hour cap |
| Full repository tests | PASS | 193 passed, zero failed |
| Lint | PASS | Zero errors |
| Science execution | LOCKED | Separate execution freeze absent |

## Execution boundary

The runner checks the execution freeze before loading predecessor artifacts or
the timing-model context. With the authorization file absent, the gate reports
`locked`, predecessor loading remains false, and the runner raises before its
science executor can be reached.

If separately authorized later, the runner will reuse only the hash-bound
passed predecessor results and locked threshold, create a new v0.2.2 ledger,
and execute the 344 disjoint cases. It will not run promotion or access observed
residuals.

## Required next gate

Execution requires a new
`protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.2.json` that binds the exact
implementation hash, inventory hash, readiness freeze, predecessor hashes, and
the user's explicit authorization. Package verification must pass again before
the first case.

No science execution is authorized by this readiness record.
