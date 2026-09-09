# Pilot 2 B1937+21 injection remediation design v0.2.8

Status: **Frozen zero-science design; implementation and execution unauthorized**

North Star scope: S1-M0 rebaseline plus S1-M1/S1-M2 remediation design

## 1. Rebaseline disposition

v0.2.8 is a new control-plane successor to the terminal v0.2.7 startup
failure. It does not amend or resume v0.2.7. The rebaseline begins from commit
`5e9e3ca517a78eab88c7f43abeb75ae00e971478`, where the top-down assembly
disposition is HOLD and science is locked.

The exact v0.2.3 replacement inventory remains applicable with SHA-256
`811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`.
No v0.2.3 through v0.2.7 case entered an attempt journal. Reusing the same 344
case IDs, seeds, families, periods, amplitudes, phases, covariance realizations,
and 35 solver-audit selections therefore preserves the preregistration and
avoids unjustified seed churn. The entire v0.2.2 inventory remains retired,
including its consumed first case and seed.

No v0.2.8 implementation, readiness, audit, execution freeze, or data-root
artifact is authorized by this design.

## 2. Design principles

1. One control definition must be used by validation and live execution.
2. Every value that can change scientific behavior must be inside a closed,
   exact, hash-bound set.
3. Offline means resources resolve from a project-owned local repository with
   zero network attempts, not merely that a warm cache happens to exist.
4. A ledger is a state machine, not an arbitrary JSON dictionary.
5. Atomic file replacement does not replace a single-writer process lock.
6. Committed case artifacts are immutable; derived group decisions receive
   their own durable artifact.
7. Historical frozen modules remain untouched. v0.2.8 uses new forward-only
   components and a thin release contract.

## 3. Proposed v0.2.8 component boundary

Prospective implementation files:

- `pilot2_trusted_data.py`: duplicate-rejecting JSON and YAML loaders plus
  exact typed-schema validation;
- `pilot2_offline_resources.py`: manifest verification, local PINT resource
  repository installation, resource-open tracing, and network-attempt denial;
- `pilot2_release_contract.py`: exact implementation, readiness, audit, and
  execution-freeze contracts;
- `pilot2_durable_ledger.py`: typed state machine, terminal verification,
  durable artifacts, and single-writer locking;
- `pilot2_runtime_core.py`: shared future execution mechanics;
- `pilot2_injection_runner_v028.py`: thin immutable v0.2.8 identity and path
  binding; and
- `test_pilot2_injection_runner_v028.py` plus focused resource, contract,
  ledger, and concurrency tests.

These are design names, not files created by this stage.

## 4. S1-M1 offline resource closure

### 4.1 Why the prior method failed

PINT 1.1.5 checks the global clock-correction `Index` even when
`PINT_CLOCK_OVERRIDE` supplies the requested observatory clock. The v0.2.7
preflight seeded only the cached URL for `time_ao.dat`; it did not provide or
redirect `index.txt`. Cache presence was therefore mistaken for dependency
closure.

### 4.2 Local resource repository

v0.2.8 will use a project-owned local file repository installed before any PINT
observatory, TOA, or timing-model load. Its manifest will include every opened
clock, index, ephemeris, and IERS resource with logical name, controlled
relative path, provenance, license status, byte count, SHA-256, consumer, and
resolution role.

The initial candidate set is `index.txt`, `time_ao.dat`, `gps2utc.clk`,
`tai2tt_bipm2019.clk`, the DE440 kernel, and the exact IERS tables used by the
environment. This list is deliberately not declared complete at design time.
Completeness is established only when an instrumented context construction
produces a resource-open trace exactly equal to the frozen manifest allowlist.

The preferred implementation is a PINT local file-URL repository whose base
and mirrors are set to the controlled local directory before PINT loads. The
existing controlled `PINT_CLOCK_OVERRIDE` remains the authority for exact
release clock values. HTTP/HTTPS resolution and an unmanifested Astropy cache
entry are fatal. If PINT cannot be made deterministic through its supported
local repository hooks, the fallback is a small hash-bound resolver adapter
that routes both `pint.observatory.find_clock_file` call sites to the controlled
allowlist. Modifying installed PINT source in place is prohibited.

### 4.3 Exact context preflight

The successor will expose one context-construction function used unchanged by
both the preflight and science runner. The preflight must not mock or replace
it. Under separate later authorization it will:

1. acquire the same version lock used by execution;
2. verify root identity, environment, resource, input, and science-control
   manifests;
3. deny and count socket, DNS, HTTP, and HTTPS connection attempts;
4. construct the exact B1937+21 PINT model, TOAs, fitter, covariance, design
   matrix, frequency grid, and scanner objects;
5. record only identities, shapes, ranks, resource trace, warnings, and hashes;
6. destroy the context without invoking an executor; and
7. assert zero cases, random draws, model fits, periodic scans, observed access,
   and science artifacts.

It must pass twice: once from a fresh or restored resource/cache state and once
from the resulting stable local state. The two attestations must agree in every
bound field.

### 4.4 Environment closure

The frozen environment manifest will bind:

- `pixi.lock`, `pixi.toml`, and `pyproject.toml` hashes;
- Python executable identity and version;
- complete resolved package name/version/build/channel records;
- macOS version, kernel architecture, process architecture, and pointer width;
- the extended-precision report and critical numeric-library versions;
- PINT/Astropy/NumPy/SciPy versions and critical installed-module hashes;
- the environment-variable allowlist and their logical, sanitized values; and
- the resource manifest hash.

The current MacBook observation is evidence for design only: Python 3.11.15,
PINT 1.1.5, Astropy 8.0.1, NumPy 2.4.6, SciPy 1.17.1, an arm64 kernel with an
x86_64 process, and a passing extended-precision gate. These values gain no
future execution authority until generated and frozen by the implementation.

## 5. S1-M2 science-control and authorization closure

### 5.1 Closed science-control set

The base calibration YAML, v0.2.3 remediation YAML, v0.2.8 runner contract,
resource manifest, and environment manifest form one exact set. Every member is
included in the implementation aggregate, implementation freeze, readiness
freeze, execution freeze, and live execution binding. The live gate must call
the remediation-freeze verifier.

JSON and YAML loaders reject duplicate members recursively before mapping
construction. Schemas reject missing, extra, wrong-type, and non-finite values.
Concrete types matter: booleans do not satisfy integer fields.

### 5.2 Exact execution-freeze contract

The execution freeze will require and verify:

- schema, freeze identity, version, status, scope, and user authorization;
- audit identity, audit artifact hashes, and semantic PASS disposition;
- exact inventory, case counts, fit counts, and solver-audit counts;
- implementation, readiness, remediation, science-control, environment,
  resource, predecessor, and threshold hashes;
- stable data-root identity and marker hash;
- launch module, command, managed-session mode, and supervision policy;
- no-reroll, no-retune, observed-data, promotion, and discovery boundaries;
- stop rule and exact repository hash allowlist.

An absolute filesystem path will not be committed as authorization. Launch
receives an explicit path, verifies the stable marker identity and hash, and
records the resolved mount/path/device information in a sanitized runtime
attestation. Repository authorization must pass before the external root is
read.

### 5.3 Ledger state machine and terminal verification

The ledger schema will have exact keys and typed nested structures. Valid state
transitions are explicit: `pending -> running -> pass|fail`. Resume is permitted
only from a valid `running` state with no contradictory terminal fields.

A PASS requires:

- exactly 344 unique inventory case IDs and no unknown case;
- verified byte count and SHA-256 for every case artifact;
- no active attempt and no unresolved attempt history;
- verified terminal result and annual-mask artifacts;
- the expected gate set and all required PASS statuses;
- matching inventory, implementation, science-control, environment, resource,
  predecessor, and execution-binding hashes; and
- no hard stop.

Artifact verification includes all `stage_results`, not only completed cases.
`already_complete` is returned only after the complete terminal verifier passes.
Malformed or impossible combinations fail closed and cannot be repaired in
place.

### 5.4 Single-writer and durable-write contract

The runner acquires a nonblocking exclusive `fcntl.flock` on a
root-and-version-specific lock file before the first setup, ledger, health, log,
or case-directory mutation. The descriptor remains open for the process
lifetime. PID, host, process start, and release identity are informational
metadata written while the lock is held; they never substitute for the OS lock.

Process death releases the advisory lock. A leftover lock file is not deleted
to recover; the next process must acquire the OS lock and then record a recovery
attestation. Simultaneous launch must fail before mutation.

Atomic writes use unique same-directory temporary files created exclusively,
then file sync, macOS full sync where supported, atomic replace, and parent
directory sync. No version may share a fixed `.tmp` path.

### 5.5 Durable annual-identifiability mask

Case artifacts remain immutable after commit. After all cases for one annual
period are verified, the runner appends a durable period entry to a separate
annual-mask artifact. Each entry binds thresholds, contributing case IDs and
artifact hashes, maximum signal/astrometry correlation, maximum ordinary-model
absorption, and the eligibility decision. The terminal result binds the final
mask SHA-256.

This makes the observed-search prerequisite contemporaneous and reproducible
without rewriting case records or performing an unspecified post-run derivation.

## 6. Required zero-science validation matrix

Implementation cannot advance to readiness until tests prove:

- missing, extra, duplicate, wrong-type, and non-finite JSON/YAML fields fail;
- every science-control mutation changes a bound hash and locks execution;
- audit HOLD, wrong root, marker, launch contract, environment, resource, or
  predecessor identity fails before external-root science loading;
- missing/corrupt stage results, false-complete ledgers, wrong case counts,
  duplicate cases, active-attempt PASS, and mismatched bindings fail;
- simultaneous launch admits one writer and rejects the other before mutation;
- interrupted owner and leftover lock-file recovery preserve attempt semantics;
- resource missing, extra, stale, malformed, wrong-hash, or network-requested
  conditions fail closed;
- the same context function serves preflight and execution;
- annual-mask incremental commit and recovery preserve exact source bindings;
- one current full test command passes with zero failures and no ad hoc
  deselections; and
- temporary-root dry run counters remain zero.

No real-root context preflight belongs to implementation validation without its
own later authorization.

## 7. Exit and next gate

This design closes S1-M0 and defines S1-M1/S1-M2 acceptance; it does not close
the assembly findings in software. The next gate is separate user direction to
implement v0.2.8 without science. That implementation must then pass the full
zero-science validation matrix before implementation/readiness freezing is
considered.
