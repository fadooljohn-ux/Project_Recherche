# Pilot 2 B1937+21 injection runner protocol v0.2.7

## Authority and scope

This protocol defines an isolated zero-science remediation of the preserved
v0.2.6 HOLD. It closes SOL-V026-001 without modifying v0.2.6 or authorizing
injection execution, random draws, timing-model fits, periodic scans,
observed-residual access, promotion, or discovery claims.

The project sequence is governed by
`docs/PILOT2_SCIENCE_STAGE_NORTH_STAR.md`. The exact never-executed v0.2.3
inventory remains applicable: 344 cases with SHA-256
`811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`.
The consumed v0.2.2 seed namespace remains retired.

## Duplicate-free trusted JSON

All JSON that participates in a v0.2.7 trust decision is parsed with an
`object_pairs_hook` before dictionary construction. The hook checks every
object, including nested objects, and raises a trusted-JSON error when a member
name repeats. No last-value or first-value interpretation is permitted.

The strict entrypoint covers:

- implementation and readiness freezes;
- any future execution freeze and its authorization controls;
- the data-root identity marker;
- predecessor ledger, crash-audit, and threshold-lock controls;
- the version-local active ledger;
- interrupted case artifacts considered for adoption; and
- completed case artifacts considered during resume.

Malformed or duplicate-bearing repository authorization returns a fail-closed
result before predecessor loading. Duplicate-bearing predecessor controls fail
before context setup. A duplicate-bearing active ledger raises before stage
state can be trusted. A duplicate-bearing interrupted or resumed artifact is
never adopted or graded.

## Retained v0.2.6 controls

The v0.2.6 exact typed live-context binding remains unchanged. Each record must
be recursively identical in value and concrete type to the invocation context,
whose canonical SHA-256 is stored in the attempt journal and incorporated in
the execution binding.

Every newly created case-directory entry is synchronized through its immediate
parent before the next child is created. All four family directories exist
durably before an executor call. File commits retain language flush, `fsync`,
macOS `F_FULLFSYNC`, atomic replace, and final-directory `fsync`.

An interrupted seed is either reconciled to a complete duplicate-free, typed,
hash-bound artifact without recomputation or preserved as consumed with a
terminal hard stop.

## Validation boundary

Exploit-shaped tests place a passing value last after a contradictory duplicate
in authorization, readiness, nested input binding, ledger, and data-root marker
documents. Each document must fail before its retained final value can be used.
A source-level guard requires the runner to contain only the single
duplicate-rejecting `json.loads` call.

All execution-path tests replace the science executor before any random draw or
fit. Validation may use only temporary initialized roots and repository-local
files. It may run one focused module and one applicable repository suite with
the three documented historical v0.2.2 deselections.

## Next gate

After zero-science validation, the implementation and readiness packages are
frozen with execution explicitly unauthorized. This authorized stage stops
there. A later stage may obtain one fresh read-only Sol audit. Only an audit
PASS may advance to separate execution-freeze construction under the North
Star roadmap.
