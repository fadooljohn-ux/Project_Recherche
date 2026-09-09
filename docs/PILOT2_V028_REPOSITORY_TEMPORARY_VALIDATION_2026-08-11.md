# Pilot 2 v0.2.8 repository and temporary-root validation

Status: **HOLD — implementation candidate; no freeze or science authority**

Recorded: 2026-08-11T03:58:42Z

This validation covers the authorized v0.2.8 control implementation and
repository/temporary-root zero-science checks. It did not access the controlled
external data root, construct the B1937+21 timing context, load predecessor
artifacts, generate a random draw, fit a model, scan a period, or execute a
science case.

## Outcome

The v0.2.8-focused suite passed 34/34. Two independently initialized temporary
roots each passed all 13 dry-run criteria with every science counter at zero.
The repository execution gate remained correctly locked because no v0.2.8
implementation, readiness, or execution freeze exists.

The required full current suite did not pass: 341 passed and 5 failed, with no
tests deselected. The five failures are historical-state conflicts:

- three frozen v0.2.2 tests still assert that the later v0.2.2 execution freeze
  is absent;
- one frozen v0.2.7 test still asserts that the later v0.2.7 execution freeze is
  absent; and
- the initial v0.1 verifier correctly detects that the current `README.md` no
  longer has its historical frozen hash.

The v0.2.2 and v0.2.7 test files are themselves hash-bound by their historical
implementation, readiness, and execution freezes. Editing them would corrupt
preserved evidence. Hiding them from the test command would violate the v0.2.8
design requirement of zero ad hoc deselections. Therefore the candidate is
held before implementation freeze and before any real-root context preflight.

## Control scorecard

| Control | Outcome |
|---|---|
| Duplicate-free strict JSON/YAML | PASS |
| Exact release, ledger, terminal, and audit schemas | PASS |
| Base/remediation/runner science-control binding | PASS |
| Audit PASS plus audit-artifact hash binding | PASS |
| Exact predecessor and threshold binding | PASS |
| Stable root-ID and marker contract | PASS |
| Live Pixi/package/platform/module/environment verifier | PASS |
| Local resource manifest and complete open trace | PASS |
| Network attempt deny and count | PASS |
| Nonblocking OS single-writer lock | PASS |
| Unique atomic replace plus file/directory sync | PASS |
| Ledger state machine and false-complete rejection | PASS |
| Exact 21-gate terminal PASS contract | PASS |
| Durable annual-mask contract | PASS |
| Two temporary-root zero-science dry runs | PASS |
| Full current suite, zero failures | HOLD — 341 passed, 5 failed |
| Real-root exact-context preflight | NOT AUTHORIZED / NOT RUN |
| Implementation/readiness/execution freeze | NOT CREATED |
| Science execution | LOCKED / NOT RUN |

## Binding and next gate

Candidate implementation SHA-256:
`28410aca9032ce5cf77e8243482607f72ebf2aff99b877e8e8b63d36ec46a523`

Candidate science-control SHA-256:
`433b30c70eae51aec1f2149dff4de4a5a128b09458d7f34ee57906b2a8a227d5`

The next gate is a prospective, preservation-safe disposition for the
historical-test harness conflict. No implementation freeze, real-root
preflight, independent audit, execution freeze, or science run may follow from
this validation record.
