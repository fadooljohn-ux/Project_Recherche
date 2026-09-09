# Pilot 1 one-shot observed-residual search result v0.1

## Outcome

The single authorized PSR J1744-1134 observed-residual search completed
successfully. No candidate exceeded the frozen detection threshold.

The strongest eligible grid cell was at 59.9641335 days with delta chi-square
16.4990614. The locked threshold was a strict delta chi-square greater than
23.3342686. The full-grid maximum was the same unmasked cell, so the null
disposition did not depend on the annual mask.

## Scorecard

| Control | Outcome |
|---|---:|
| Frozen package, Fable sign-off, and user authorization | PASS |
| Immutable intent written and one-shot permission consumed | PASS |
| Exactly one 941-cell observed scan | PASS |
| Locked threshold and strongest-unmasked rule | PASS |
| Candidate rule applied correctly | PASS — no candidate |
| Warning hygiene | PASS |
| Resource envelope | PASS |
| Result/report integrity | PASS |
| Additional search, retry, or retuning | NOT AUTHORIZED |
| Overall post-execution integrity | **12/12 PASS** |

Candidate-only ordinary, joint, and full-covariance refits were not executed
because the threshold did not trigger. For the same reason, the 749 advisory
deletion diagnostics were not executed. This is the required behavior, not
missing analysis.

## Claim boundary

The supported conclusion is narrow: no circular-signal candidate exceeded the
frozen threshold in this one authorized 30–2,000-day strongest-unmasked search.

This does not establish that every possible companion or timing signal is
absent. It does not cover the three annual masked grid cells, periods outside
the frozen range, signals below calibrated sensitivity, or signal families not
represented by the circular model. It is not a discovery or mass measurement.

The borderline clustered-day tail result and failed deletion hard-veto cost
tests remain part of the permanent calibration context. They do not change the
null classification and cannot be used to justify a rerun or threshold change.

## Record identity

- intent SHA-256:
  `cd76bab246979e4aaa1e5513c10ba8c2951242054ce27271c6c1be429821c8ee`;
- result SHA-256:
  `720f3604058121ddc4aa7ff5a0be159089b28ca279328b18addd4d1904ce06bc`;
- log SHA-256:
  `efafe93f6dab0c2ba1894da87a3628e5fcee8e93696094d6056686e3d4dd5079`.

The detailed records remain outside Git in the controlled data root. The
tracked result summary contains only the bounded outcome and record hashes.

## Next gate

Perform an independent post-execution audit of the result record, the one-shot
boundary, and the claim language. After that audit, close v0.1 as a completed
null pilot and decide separately whether a scientifically distinct v0.2 is
warranted. v0.2 cannot be a retry or retuning of this consumed search.
