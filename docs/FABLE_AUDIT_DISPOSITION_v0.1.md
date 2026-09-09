# Fable audit disposition v0.1

## Decision

The independent Fable audit is accepted as **PASS WITH REQUIRED CHANGES** for
Project Recherche. It authorizes preparation and synthetic-only execution of a
pre-unblinding validation package. It does not authorize an observed-residual
periodic search.

The preserved audit is `docs/external_audits/FABLE_AUDIT_2026-08-09.md`, an
exact byte-for-byte copy of the report originally written in the sibling
Project Spectre working directory. Its SHA-256 is
`56abd941b678fc99d5b8de9919c1a6d0cd15ebeff4ad8c7ea60ec08676344800`.

## Disposition scorecard

| Finding | Disposition | Binding action |
|---|---|---|
| R1 resolves the 7/500 failure with conditions | Accepted | Ban any further tail re-roll and always report both evaluations. |
| Pooled 14/1,500 is contextual only | Accepted | Never use the pooled interval as a gate. |
| Tail model needs structured variants | Accepted | Freeze timing-only, DM-only, and clustered-UTC-day synthetic stresses. |
| Residuals indicate mild distributed misspecification | Accepted | Preserve the limitation; make no observed-data TOA edits. |
| Locked threshold 23.33426855482562 is defensible | Accepted | Retain it unchanged and permit no stress-result retuning. |
| Candidate checks need hard/advisory classification | Accepted with implementation correction | Measure false-veto cost by deterministic replay, not threshold-only regrading. |
| Proceed to freeze preparation | Accepted | Prepare synthetic readiness evidence and independent sign-off materials only. |

## Implementation corrections

### Deletion stability requires deterministic replay

The 160 immutable recovery records retain global scan summaries, refit results,
and provenance, but not the deletion-level scans required for a leave-one-row
or leave-one-day stability analysis. A threshold-only regrade cannot measure
that cost. The validation therefore regenerates the exact frozen synthetic
cases from their original identifiers and seeds, changes no random draw, and
performs the newly frozen deletion analysis. This is a deterministic replay,
not a third null evaluation or a re-roll.

### The pipeline operator is not the independent signatory

5.6 Sol prepared and operated the pipeline and may prepare and verify this
freeze, but cannot independently approve its own work. Claude Fable 5, or a
later explicitly named independent reviewer, must review the final
pre-unblinding result and hash-bound search-freeze packet. Fable is the planned
reviewer for v0.1. No execution authority exists until that separate sign-off
record is complete and passes automated verification.

## Clarified decision classes

- The structured synthetic tail variants are **pre-unblinding readiness
  gates**, because crossing their frozen trip-wire requires rebaselining.
- Deletion stability becomes a hard candidate veto only if its frozen
  injection-cost gate passes. Otherwise it remains advisory and observed
  execution stays blocked pending independent disposition.
- Backend, frontend, observing-system concentration, post-candidate kurtosis,
  half-span stability, the pooled tail estimate, and the Behrens comparison
  remain advisory. Advisory results cannot create, rescue, or veto a candidate.

## Annual-mask semantics

The future one-shot search will evaluate the frozen full frequency grid once.
Candidate selection will use the strongest unmasked grid cell against the
unchanged threshold calibrated from full-grid maxima. Masked annual cells are
reported only as sensitivity gaps and cannot suppress a distinct eligible
unmasked candidate. This is conservative relative to the calibrated global
false-positive rate.

## Authorization boundary

At this disposition:

- synthetic readiness planning: authorized;
- synthetic readiness execution after freeze verification: authorized;
- observed residual loading, projection, or periodic scanning: unauthorized;
- threshold, grid, or annual-mask adaptation: unauthorized;
- final search execution: unauthorized pending passing synthetic results and
  independent Fable sign-off.
