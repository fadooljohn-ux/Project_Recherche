# Pilot 2 Gate 2 contract-qualification closeout

Date: 2026-08-16

Qualification completed UTC: `2026-08-16T10:09:20Z`

Gate outcome: **PASS**

Attempt: **Gate 2 contract closeout attempt 1 — terminal**

## 1. Authority and scope

The owner authorized this bounded closeout with `Proceed` after the exact stage
was stated: commit the accepted one-file roadmap clarification, run the two
focused zero-science contract test files once, create one closeout receipt, and
commit it. Gate 3, real-root access, manifests, freezes, audit, operational
launch, and science remained outside the authority.

The controlling clarification is Section 12 of
`docs/PROJECT_RECHERCHE_OPERATIONAL_IOC_PLAN_2026-08-15.md`. It makes Gate 2 a
pre-execution contract-qualification gate. Actual scientific-path parity is
retained for Gate 6, and sealed scorecard-content review is retained for Gate 7.

## 2. Qualified identity

- branch: `agent/pilot2-v028-design`
- science-binding implementation commit:
  `6b2e831f5e5d8b92741a06ce5dd0c74c518964d6`
- roadmap-clarification commit:
  `3f958c66545b145e4a11b52f3b37ff09d9e1f2f5`
- roadmap-clarification tree:
  `f1bc5f14f16570d26157a8dba86d9cb17c2fd38c`
- roadmap SHA-256:
  `e1a1d97cfeb3482bb413feee53ce7d2426ff7f9542b2f51cb271ad0b8bd19ec9`

Bound implementation and test hashes:

| Path | SHA-256 |
|---|---|
| `src/pulsar_pilot/pilot2_ioc_harness.py` | `efa024cb5d6665e3969dbdb33475a0522b8a895a44b7195fd57cfff7dd315ca0` |
| `src/pulsar_pilot/pilot2_science_module.py` | `e97b1f87cfbf633ea70721d9dba73fb2ae95fa72e32a5f1901bbd8860cf37d1f` |
| `src/pulsar_pilot/pilot2_release_contract.py` | `3821a73c0cc30a9ce4600e567796086817505a7467b6b35d70ca56b9123dcdc6` |
| `src/pulsar_pilot/pilot2_runtime_core.py` | `b99a2c440ee759e0dcf4136e21c3130f8d63a01181b80bc993c5f08355969942` |
| `tests/test_pilot2_ioc_harness.py` | `107ea76a288fc172345a93b98d7d645d0e90c6c4dbc4649f3b6fa49ad2efc22f` |
| `tests/test_pilot2_science_module.py` | `180feaf6d23fc4de39d18b315a99d2bd49cdf8d73629cb6945efa869fe3b659e` |
| `pixi.toml` | `b4d190ee09a878c93ae5e3e74bd3ca630754b9343ba7f62d5b52f4d32f5c1613` |
| `pixi.lock` | `7412baa7d224dfdc419066b706f27257684931df9a0ad0f57949e1fe31cf68c8` |

The sole authoritative route remains:

`pilot2_ioc_harness run -> pilot2_science_module:SCIENCE_MODULE.run ->
pilot2_runtime_core.execute`

## 3. Terminal qualification result

The exact command was invoked once from the repository root:

```text
PYTHONPATH=src pixi run --as-is pytest -q tests/test_pilot2_ioc_harness.py tests/test_pilot2_science_module.py
```

Terminal output:

```text
...............................                                          [100%]
31 passed in 9.45s
```

Subprocess exit code: `0`.

Retries: `0`.

Full-suite invocations: `0`.

The finite suite qualified exact authority and root binding, fresh-only and
no-resume behavior, pre-root failure, operator-stop and operational-failure
terminalization, outcome-free receipts, exact workload accounting, evidence
closure, and the health-only status boundary.

## 4. Zero-science boundary

- designated or observed data-root access: `0`
- unpatched calls to `pilot2_runtime_core.execute`: `0`
- scientific cases constructed or executed: `0`
- primary fits: `0`
- solver audits: `0`
- reported `network_requests` boundary counter: `0`
- network-capable calls invoked by the selected test code: `0`
- operational Pilot 2 launches: `0`
- project execution freezes created: `0`
- retries or resumptions: `0`

All exercised roots were pytest temporary roots or deliberately absent test
roots. Adapter execution cases used bounded test doubles; runtime freshness and
terminalization checks exercised control helpers without entering the
scientific engine. The absent successor execution freeze remains absent.
The network statement is bounded to the selected source and contract evidence;
it is not presented as an operating-system packet-capture result.

The declared contract accounting remains exactly 344 cases, 688 primary fits,
and 35 solver audits. Those are contract identities here, not claims that the
scientific workload ran.

## 5. Disposition and stop boundary

Gate 2 is **PASS for pre-execution science-module contract qualification**.
This does not establish actual PINT construction parity, execute a scientific
case, validate a terminal scientific scorecard, authorize a real root, create
manifests or freezes, or authorize Gate 6. Those requirements remain assigned
to their later gates by the controlling roadmap.

Gate 3 is the next roadmap gate and is **not started**. Its future scope is a
narrow conformance closeout of the existing minimalist harness, not another
harness redesign. Authority for Gate 3 and every later gate is absent until the
owner separately authorizes a precisely bounded stage.
