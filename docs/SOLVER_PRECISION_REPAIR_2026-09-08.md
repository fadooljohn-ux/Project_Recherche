# Spin-phase precision repair and readiness

The owner authorized the bounded precision diagnosis, repair, verification and
readiness decision, plus another qualification run if readiness criteria pass.

## Demonstrated precision loss and repair

PINT evaluates a many-billion-turn spin polynomial in long double before
separating integer and fractional phase. Tiny delay changes can disappear in
that large intermediate value. Exact-arithmetic regression tests reproduce the
loss at unchanged inputs and show that splitting the result before conversion
preserves those changes.

The repair evaluates the same spin Taylor polynomial with 50-decimal-digit
arithmetic, using exact binary input ratios. Day conversion and delay subtraction
also retain that precision. Integer and fractional turns are passed separately
through PINT's existing phase-combination interface. This is a model-local binding
applied by the current context loader and retained by copied fit models. The
installed PINT package, covariance model, signal waveform, solver algorithms,
iteration settings and acceptance limits are unchanged.

A fixed-state probe on the two annual fixtures reduced the chi-square variation
from small weak-direction perturbations from roughly 0.002–0.004 to
0.00004–0.00008. The probe is diagnostic; its perturbations are not themselves an
acceptance test. The actual before/after fits and exact-arithmetic checks provide
the repair evidence. Direct least-squares comparison did not justify replacing
the existing linear solvers, and no new stopping-rule change was retained.

## Readiness evidence

The two retained annual development fixtures and the ordinary 1000-day control
passed both the isolated trial and the supported integration run. The integration
run used `tools/recherche develop --solver-check`, executed 3 cases, 6 primary fits
and 3 audits, and completed in 287.244 seconds. All fits converged, all audits
passed, and resource tracing verified zero network attempts.

| Integration fixture | Amplitude difference, microseconds | Frozen limit |
|---|---:|---:|
| Ordinary control | 0.00000004786 | 0.01 |
| Annual phase zero | 0.00031278 | 0.01 |
| Annual phase pi | 0.00015086 | 0.01 |

Phase and chi-square differences also pass their existing limits. All 13 terminal
artifacts match their recorded file set, sizes and hashes. The source hashes in
the development manifest match the repaired source.

Current release checks: 418 passed, eight historical checks deselected, 41.90 s.
Two additional historical hash assertions were verified on commit `6608085` before
being assigned to the existing historical-check mechanism (2 passed, 1.41 s).
They cover preserved historical source snapshots, not the current implementation.

Readiness is **PASS for the owner-authorized qualification attempt**. Development
evidence does not change the first formal FAIL or establish a formal PASS.
Both annual fixtures remain weakly identifiable; precise numerical agreement
does not make the annual signal scientifically eligible.

Receipt: `results/qualification/qualification02-readiness.json`.
Detailed evidence: `../Project Recherche Data/solver-precision-20260908/`.
Next execution record: [qualification 02](QUALIFICATION_02_2026-09-08.md).
