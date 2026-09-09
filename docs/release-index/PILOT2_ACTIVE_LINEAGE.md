# Pilot 2 active release lineage

Effective: 2026-08-11

Current successor: **v0.2.8 design only**

Current execution state: **LOCKED**

## Authoritative routing

| Version | Disposition | Science-state consequence | Successor rule |
|---|---|---|---|
| v0.2.1 | Terminal scientific hard stop after its frozen injection evaluation | Preserved; no rerun or regrade | Its threshold, retained results, and failure audit remain predecessors only |
| v0.2.2 | Terminal implementation crash after one attempt was consumed | Entire v0.2.2 case and seed namespace retired | Never reuse `p2r2-inj-main-p00-a00-h00-n00`, seed `2691995251659989168`, or any v0.2.2 inventory member |
| v0.2.3 | Never executed; Sol HOLD | Its replacement 344-case inventory remains unconsumed | Inventory may carry forward unchanged; implementation may not |
| v0.2.4 | Never executed; Sol HOLD | No case or seed consumed | Preserve audit evidence |
| v0.2.5 | Never executed; Sol HOLD | No case or seed consumed | Preserve audit evidence |
| v0.2.6 | Never executed; Sol HOLD | No case or seed consumed | Preserve audit evidence |
| v0.2.7 | Terminal startup failure before first attempt journal | 0/344 cases; no random draw, fit, scan, promotion, or observed-data access | Never resume, repair, rerun, retune, reroll, replace, or regrade |
| v0.2.8 | S1-M0 rebaseline and S1-M1/S1-M2 design | Design only; no implementation or execution authority | Implement only after separate user direction |

## Active inventory disposition

The v0.2.8 successor retains the exact never-executed v0.2.3 inventory:

- inventory SHA-256:
  `811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`;
- 240 main cases;
- 60 phase-reference cases;
- 28 annual cases;
- 16 boundary cases;
- 344 total cases; and
- 35 deterministic solver-audit selections.

No case ID, seed, family, period, amplitude, phase, covariance realization, or
solver-audit selection may change. Retaining the inventory avoids seed churn
because v0.2.3 through v0.2.7 consumed none of its members. The v0.2.2
namespace remains retired independently.

## Active gate

The only completed v0.2.8 work is the prospective remediation design. No
v0.2.8 source, tests, implementation freeze, readiness freeze, audit, execution
freeze, data-root mutation, or science artifact exists at this gate.

The next permissible stage is a separately directed zero-science implementation
of the frozen v0.2.8 design. It must close ASM-001 through ASM-007 before a
readiness package may be considered.
