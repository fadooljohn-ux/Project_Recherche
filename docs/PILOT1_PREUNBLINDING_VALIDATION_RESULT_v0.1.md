# Pilot 1 pre-unblinding validation result v0.1

## Outcome

**FAIL — 14/15 criteria passed.** The structured-tail readiness trip-wires did
not fire, but both proposed deletion-dependence hard vetoes rejected too many
genuine synthetic recoveries. The vetoes therefore remain advisory and the
observed-residual search remains unauthorized.

No seed, threshold, grid, trip-wire, veto bound, or result was changed after
execution. No observed residual was loaded or scanned.

## Scorecard

| Test | Frozen criterion | Outcome |
|---|---:|---:|
| Execution freeze and external prerequisites | Exact hashes | PASS |
| Timing-block contaminated nulls | Wilson lower not above 1% | PASS — 2/1,000 |
| DM-block contaminated nulls | Wilson lower not above 1% | PASS — 4/1,000 |
| Clustered-UTC-day contaminated nulls | Wilson lower not above 1% | PASS, BORDERLINE — 16/1,000; lower 0.987% |
| Exact deterministic replay | Zero mismatches across 160 cases | PASS |
| Paired-row hard-veto cost | Rate <=1%; Wilson upper <=5% | **FAIL — 5/125; 4.0%; upper 9.02%** |
| UTC-day hard-veto cost | Rate <=1%; Wilson upper <=5% | **FAIL — 6/125; 4.8%; upper 10.08%** |
| Artifact ledgers and warnings | Zero failures | PASS |
| Runtime, memory, storage | Within MacBook caps | PASS |
| Continued blinding | No observed periodic access | PASS |
| Overall | All 15 criteria | **FAIL — 14/15** |

## Structured-tail interpretation

The timing-only and DM-only variants were comfortably below the frozen
rebaseline trip-wire. The clustered-day variant produced 16 false positives in
1,000 cases. Its Wilson 95% interval is 0.987%–2.583%; because the lower bound
is not strictly above 1%, it formally passes the predeclared rule. This is a
narrow, borderline pass and is presented to the independent reviewer without
rerolling or changing the rule.

## Deletion-veto interpretation

All deletion-cost failures occurred in the weakest 0.2-microsecond injection
cell. None was caused by frequency instability: deletion reduced the global
statistic below threshold while the recovered frequency remained stable. This
supports the interpretation that the proposed all-deletions-must-remain-
significant rule is too costly for marginal real signals, rather than evidence
that those signals were single-point artifacts.

That interpretation is contextual only. The frozen false-veto gates failed and
cannot be revised from these results. Both deletion checks remain advisory.

## Resources and provenance

- Wall time: 0.0539 hours.
- Peak memory: 0.584 GiB.
- Complete controlled data root: 0.821 GiB.
- Execution freeze SHA-256:
  `ed4a7fbc91d289105ecf1d2153d5dbb5c2c328ea2db67a7458216d6d52fcb866`.
- Full synthetic result SHA-256:
  `50ee11b6532470f2a72c195ba5fa5389a49015a992c5046c0569b38fea4da469`.

## Decision

Do not re-run or amend this evaluation. Prepare the hash-bound failure packet
for Claude Fable 5. Fable must decide whether the failed deletion rule should
remain advisory under a defensible candidate-review framework, whether a
different robust statistic must be prospectively calibrated, or whether the
detector requires rebaseline. No one-shot execution freeze may advance before
that disposition.
