# Pilot 2 Gate 3 minimalist-harness conformance closeout

Date: 2026-08-16

Qualification completed UTC: `2026-08-16T10:15:57Z`

Gate outcome: **PASS**

Attempt: **Gate 3 minimalist-harness conformance attempt 1 — terminal**

## 1. Authority and boundary

The owner's `Proceed` authorized only a Gate 3 conformance closeout of the
existing minimalist harness: rebind the clean Gate 2 baseline, audit the
existing code against every Gate 3 requirement, invoke the focused harness
synthetic/fault tests once, create and commit one terminal receipt, and stop.

No source or test edit, full-suite run, real-root access, manifest or freeze
creation, Gate 4 work, operational launch, or science was authorized.

The retired v0.2.9/v0.2.10 qualification attempts remain historical evidence.
This closeout uses the accepted minimal-harness reset and does not regrade or
resume any prior attempt.

## 2. Entry identity

- branch: `agent/pilot2-v028-design`
- Gate 2 closeout commit:
  `f54b74b2c863766e8cd834cc0e5c1a7a57368b28`
- Gate 2 closeout tree:
  `ea66a36eb2ea7344213e3286a9eeef2e21a6973a`
- roadmap SHA-256:
  `e1a1d97cfeb3482bb413feee53ce7d2426ff7f9542b2f51cb271ad0b8bd19ec9`
- Gate 2 receipt SHA-256:
  `018e3b52b003328041a1c45d181865d26c459331ed5024604dbc7f2a8ac3c8de`
- harness SHA-256:
  `efa024cb5d6665e3969dbdb33475a0522b8a895a44b7195fd57cfff7dd315ca0`
- science adapter SHA-256:
  `e97b1f87cfbf633ea70721d9dba73fb2ae95fa72e32a5f1901bbd8860cf37d1f`
- harness test SHA-256:
  `107ea76a288fc172345a93b98d7d645d0e90c6c4dbc4649f3b6fa49ad2efc22f`
- `pixi.toml` SHA-256:
  `b4d190ee09a878c93ae5e3e74bd3ca630754b9343ba7f62d5b52f4d32f5c1613`
- `pixi.lock` SHA-256:
  `7412baa7d224dfdc419066b706f27257684931df9a0ad0f57949e1fe31cf68c8`

The worktree was clean and no Pilot 2 or focused pytest process was active at
entry.

## 3. Gate 3 conformance matrix

| Requirement | Exact implementation and evidence | Result |
|---|---|---|
| Foreground operator launch and interrupt | `run_foreground` invokes the module synchronously; `KeyboardInterrupt` becomes a consumed `controlled_stop`; focused success and interrupt/fault tests exercise both paths. | PASS |
| Authority, identity, single writer, and pre-root failure | Exact authority/repository/module bindings are checked before execution; zero-science preflight precedes run-root creation; create-once `run.active` atomically admits one writer. | PASS |
| Exact science entry point | The CLI has one fixed adapter, `pulsar_pilot.pilot2_science_module:SCIENCE_MODULE`, and exposes no adapter-selection argument. | PASS |
| Complete operational status | The exact status contract contains state, stage, completed/total, checkpoint, elapsed time, PID and process start, CPU, RSS, error type, timestamp, and terminal state; `observe_status` adds process state and heartbeat age/state. | PASS |
| No scientific outcomes in status | The exact-key validator requires `science_outcomes_visible` to be false and rejects every extra field; the tamper test adds a scientific field and is rejected. | PASS |
| Duplicate and consumed-identity refusal | Run-root creation, persistent lock, atomic active marker, prepared-state check, and terminal-inventory check refuse reuse; focused tests cover prepare reuse and second run. | PASS |
| Stop and failure terminalization | Operator interruption and injected operational, evidence, receipt, path, and accounting failures produce a terminal state and inventory without masking the initiating cause. | PASS |
| Exact sealed evidence and terminal inventory | The harness validates the exact outcome-free science receipt, bound accounting and artifact paths, then hashes the run-root files into a create-once terminal inventory. | PASS |
| Minimal operator surface | Static inspection found exactly `verify-gate`, `preflight`, `prepare`, `run`, and `status`. | PASS |
| No second control plane | Static inspection found no daemon, service, scheduler, thread, server, automatic restart, automatic resume, or takeover surface. Status is read-only and the CLI has no AI write route. | PASS |

## 4. Terminal focused validation

The exact command was invoked once from the repository root:

```text
PYTHONPATH=src pixi run --as-is pytest -q tests/test_pilot2_ioc_harness.py
```

Terminal output:

```text
..............                                                           [100%]
14 passed in 8.94s
```

Subprocess exit code: `0`.

Retries: `0`.

Full-suite invocations: `0`.

## 5. Zero-science and anti-spiral accounting

- source files changed: `0`
- test files changed: `0`
- new harness or observer implementations: `0`
- new operator commands or control services: `0`
- designated or observed data-root accesses: `0`
- unpatched science-adapter/runtime executions: `0`
- scientific cases constructed or executed: `0`
- primary fits: `0`
- solver audits: `0`
- network operations requested by the selected harness/test path: `0`
- operational Pilot 2 launches: `0`
- project manifests or execution freezes created: `0`
- retries, resumptions, or automatic recovery actions: `0`

The tests used temporary Git repositories, temporary evidence/run roots, and a
bounded fake science module. They verified lifecycle and evidence behavior
without entering the scientific engine. The successor execution freeze remains
absent. The network count is bounded source/test-path evidence; process-level
network denial and its independent evidence remain Gate 4 requirements.

## 6. Disposition and stop boundary

Gate 3 is **PASS for finite synthetic/fault conformance of the existing
minimalist operational harness**. No further harness implementation is required
by this gate, and no design expansion was introduced.

Gate 4 — integrated zero-science qualification — is the next roadmap gate and
is **not started**. It requires separate owner authority because it introduces
the designated real root, process-level network denial, two independently
recorded context constructions, resource/environment manifests, host/storage
verification, and the backup/restore boundary. Gate 4 authority and all later
execution or science authority remain absent.
