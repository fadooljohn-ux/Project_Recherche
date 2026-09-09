# Pilot 2 v0.2.3 dedicated Sol audit disposition

## Disposition

**HOLD.** The dedicated Sol audit identified four P1 fail-closed defects and
one P2 validation gap. The primary agent independently reproduced all five
findings from the frozen source and validation evidence.

The positive v0.2.3 findings remain valid: version separation, inventory and
seed disjointness, current hashes, the PINT correlation-object correction,
predecessor integrity, health-only records, and the absent execution freeze all
passed. Those passes do not overcome the fail-closed defects.

## Confirmed findings

| Finding | Severity | Primary verification | Execution effect |
|---|---:|---|---|
| Interrupted case can be recomputed before durable ledger commit | P1 | Confirmed | Blocks execution |
| Invalid execution freeze can cause predecessor loading and lacks full contract verification | P1 | Confirmed | Blocks execution |
| Readiness verifier does not require `execution_readiness: pass` | P1 | Confirmed | Blocks execution |
| Exceptions after `begin_stage` but before the protected block escape hard-stop handling | P1 | Confirmed | Blocks execution |
| Tests do not exercise these recovery and authorization boundaries | P2 | Confirmed | Readiness claim unsupported |

## Authority state

- v0.2.3 execution remains locked.
- No v0.2.3 execution freeze may be created from the present package.
- No science case, random draw, fit, scan, promotion, or observed-data access
  occurred during the audit.
- The audit is advisory and does not authorize remediation or execution.

## Required remediation direction

A new zero-science version must durably journal a case attempt before
computation, define consumed-attempt recovery behavior, validate the complete
execution-freeze contract before predecessor loading, require a passed
readiness semantic, move all post-stage activation work inside the terminal
exception boundary, and add integration tests plus a machine-readable test
manifest.

The next gate is separate user authorization for a v0.2.4 zero-science
remediation package. A new dedicated Sol subagent must audit that frozen package
before any later science-execution authorization.
