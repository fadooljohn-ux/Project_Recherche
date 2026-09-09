# Pilot 2 v0.2.9 qualification-harness Gate 1A erratum 1

- **Status:** approved Gate 1A erratum; Gate 1B execution remains separately governed
- **Date:** 2026-08-15
- **Controlling plan:** `PROJECT_RECHERCHE_OPERATIONAL_IOC_PLAN_2026-08-15.md`
- **Amended design:** `PILOT2_V029_QUALIFICATION_HARNESS_DESIGN_2026-08-15.md`
- **Scope:** pre-import bytecode suppression for the one governed command only

## 1. Reason for the erratum

Static Gate 1B review found that the approved `python -m` command can compile
the package or harness and write a `.pyc` file under the repository before the
harness module begins executing. That write would precede repository-identity
capture and contradict the approved no-cache, unchanged-repository boundary.

The owner approved this minimal correction by directing Gate 1B to proceed on
2026-08-15. The original design remains preserved byte-for-byte; this erratum
supersedes only its Section 4 command literal and the bindings that prove that
literal was used.

## 2. Corrected governed command

The sole operator command is now exactly:

```text
PYTHONPATH=src pixi run --as-is python -B -m pulsar_pilot.pilot2_qualification_harness_v029 qualify
```

`-B` is required before module resolution so CPython disables bytecode writes
before importing `pulsar_pilot` or the qualification harness. Formal
qualification must also prove `sys.dont_write_bytecode` is true and that the
Pixi parent command includes this exact `-B` token. Omitting or relocating the
token is `FAIL_AMBIENT_OPTION` or `FAIL_ENVIRONMENT_IDENTITY`; it is not an
equivalent command.

## 3. Finite implementation effect

Gate 1B may make only these command-related changes:

1. update the harness `GOVERNED_COMMAND` constant;
2. update the bound Pixi parent-process token ledger;
3. require pre-import bytecode suppression in formal mode;
4. update the exact-command acceptance literal and add a negative acceptance
   proving omission of `-B` is rejected; and
5. add this erratum to the exact Gate 1B candidate-addition and authority-hash
   ledger.

Child pytest lanes retain `PYTHONDONTWRITEBYTECODE=1`. No observer, route,
snapshot, failure-signature, accounting, environment package, boundary
counter, science, data-root, manifest, freeze, audit, or IOC scope changes are
authorized by this erratum.

## 4. Stop rule

This erratum restores the already-approved repository-preservation intent. It
does not itself authorize Gate 2, real-root access, manifests, freezes, audit,
the minimalist IOC harness, or science. Gate 1B must still pass disposable
acceptance before a clean candidate is committed, and its corrected governed
command may still be executed only once for that exact candidate.
