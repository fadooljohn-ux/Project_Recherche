# Pilot 1 pre-unblinding freeze result v0.1

## Outcome

**PASS — 15/15 freeze criteria.** The package authorizes implementation and
execution of the exact frozen synthetic validation only. It does not authorize
observed residual access or an observed periodic search.

## Scorecard

| Test | Outcome |
|---|---|
| Fable audit preserved byte-for-byte | PASS |
| Audit findings formally dispositioned | PASS |
| Threshold retained at 23.33426855482562 | PASS |
| Structured-tail inventory frozen at 3 × 1,000 cases | PASS |
| New case IDs and seeds unique and disjoint from prior tail sets | PASS |
| Original 160 recovery cases bound for deterministic replay | PASS |
| New recovery randomness prohibited | PASS |
| Any further tail re-roll prohibited | PASS |
| Structured-stress rebaseline trip-wire frozen | PASS |
| Deletion-veto false-cost bounds frozen | PASS |
| Full-grid/annual-mask candidate semantics frozen | PASS |
| Independent Fable final review required | PASS |
| Pipeline-operator self-signing prohibited | PASS |
| Repository tests | PASS — 82 |
| Lint and freeze-hash verification | PASS |

## Frozen work inventory

- 1,000 timing-block contamination evaluation nulls;
- 1,000 DM-block contamination evaluation nulls;
- 1,000 clustered-UTC-day contamination evaluation nulls; and
- deterministic deletion-stability replay of the exact 160 prior recovery
  cases, with no new noise or injection draw.

The freeze SHA-256 is
`00faa4a0f202c8ca452af6ddaf1f0c170303b382eac3ac1843d427fff4153e35`.

## Remaining authorization ladder

1. Implement the exact frozen synthetic validator.
2. Execute it without changing seeds, thresholds, trip-wires, or veto bounds.
3. Publish the complete synthetic result and reviewer packet.
4. Obtain a hash-bound final pre-execution sign-off from Claude Fable 5.
5. Prepare a separate one-shot observed-residual execution authorization for
   the user's explicit approval.

Steps 4 and 5 cannot be combined with synthetic execution. No observed search
command exists or is authorized in this phase.
