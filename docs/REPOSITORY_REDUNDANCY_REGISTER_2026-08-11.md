# Project Recherche preservation-aware redundancy register

Date: 2026-08-11

Audit target: `a1eeb553b69e9c8ee5a3bf1e4fd9b62da231d730`

Disposition: **No tracked-file deletion authorized or recommended**

## Inventory conclusion

The audited checkout contains 424 tracked files. No exact duplicate tracked
blobs were found. The repository is evidence-heavy by design: the largest file
groups are protocols, results, documentation, source, tests, and configuration.
The primary redundancy risk is repeated version lineages without one active
state index, not byte-for-byte duplication.

Six versioned Pilot 2 runners and six matching test modules total 10,349 lines:
6,940 runner lines and 3,409 test lines. v0.2.6 and v0.2.7 remain close in
structure, and the v0.2.5-v0.2.7 executor shims differ mainly in identity.
Those files are still evidence and, in some cases, live imports.

## Disposition register

| Class | Files or group | Disposition |
|---|---|---|
| Keep active | `README.md`, packaging/environment definitions, common non-versioned code, this roadmap and current-state pointers | Maintain prospectively under normal change control |
| Keep immutable evidence | All historical Pilot 2 protocols, freezes, audit records, incidents, terminal results, configs, versioned source, and versioned tests | Do not edit, move, or delete during science-stage work |
| Keep immutable evidence and live dependency | v0.2.2 grading helpers, generic/v0.2.3 executor and remediation modules imported by v0.2.7 | Do not treat version number as obsolescence |
| Logical archive candidate | Closed v0.2.4-v0.2.7 release bundles after a complete release index and tag exist | Index or export only; do not relocate paths used by verifiers |
| Consolidate prospectively | Future runner mechanics, ledger engine, version shims, test fixtures, freeze/audit templates | New shared core plus thin immutable release contracts |
| Delete candidate | None among tracked files | No deletion supported by the audit evidence |

## Environment directories

Ignored local caches are not repository evidence, but deletion is not part of
this audit. `.pytest_cache` and `.ruff_cache` are disposable after all processes
stop. `.pixi` and `.venv` are much larger environment installations and may be
needed to reproduce historical behavior; keeping both also creates interpreter
ambiguity. Select one governed environment prospectively only after recording
the current package manifests and proving the replacement.

## Prospective consolidation rules

1. Never refactor or move an already frozen historical module.
2. Create a new shared runtime core for successor versions.
3. Keep version-specific files declarative: identity, closed inputs, schema,
   accepted counts, output paths, and resource caps.
4. Separate current qualification tests from historical-contract tests without
   deleting the latter.
5. Add an active release index that maps version, commit, status, freeze hashes,
   audit disposition, incident, successor, and whether execution is prohibited.
6. Generate a current release manifest instead of relying on the obsolete
   Pilot-1-only execution-freeze index.
7. Do not archive a release until repository-relative verifier assumptions and
   all hash links have been mapped.

## Recommended forward-only layout

```text
docs/
  PROJECT_STATE.md
  PROJECT_RECHERCHE_TWO_STAGE_ROADMAP.md
  release-index/
    pilot2-v0.2.1-through-v0.2.7.md
src/pulsar_pilot/
  pilot2_next/
    offline_context_preflight.py
    runtime_core.py
    durable_ledger.py
    release_contract.py
tests/
  current/
  historical/
releases/
  pilot2/
    successor-version/
```

This is a prospective organization. Historic paths must remain where they are
unless a separately audited migration proves that no verifier, freeze, import,
or evidence reference depends on them.
