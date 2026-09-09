# Fable pre-execution failure review packet v0.1

## Requested review

Claude Fable 5 is asked to independently disposition the failed frozen
pre-unblinding validation. This is not a request to inspect observed periodic
content, tune a threshold, approve a re-roll, or overlook a failed gate. No
observed-periodic result exists.

The packet manifest SHA-256 is
`8d5e7cad0b7e42707f58394c7e3a9026108c6cde621695c4e29db3c3fd9074ca`.
Verify every entry in
`manifests/preunblinding_validation_result_v0.1.sha256` before review.

## Execution identity

- Preparation freeze:
  `00faa4a0f202c8ca452af6ddaf1f0c170303b382eac3ac1843d427fff4153e35`
- Execution freeze:
  `ed4a7fbc91d289105ecf1d2153d5dbb5c2c328ea2db67a7458216d6d52fcb866`
- Execution implementation:
  `ab2128b54e907a522619c1602e836b734ff006216a7ac79e53e57332a8856c9d`
- Complete synthetic result:
  `50ee11b6532470f2a72c195ba5fa5389a49015a992c5046c0569b38fea4da469`
- Compact result:
  `20f8b0878c95cbd3e23b80ca75bce31242c56eba91d2f4316143241c45f60065`

## Frozen outcome

Overall: **FAIL, 14/15**.

| Test | Result |
|---|---|
| Timing-block tail | PASS — 2/1,000; Wilson upper 0.726% |
| DM-block tail | PASS — 4/1,000; Wilson upper 1.024% |
| Clustered-day tail | FORMAL PASS, BORDERLINE — 16/1,000; Wilson 0.987%–2.583% |
| Exact 160-case replay | PASS — zero mismatches |
| Paired-row hard-veto cost | FAIL — 5/125 false vetoes; 4.0%; Wilson upper 9.02% |
| UTC-day hard-veto cost | FAIL — 6/125 false vetoes; 4.8%; Wilson upper 10.08% |
| Integrity, warnings, resources, blinding | PASS |

The clustered-day result did not cross the exact frozen trip-wire because its
Wilson lower bound, 0.987%, is not strictly greater than 1%. Its 1.6% point
rate is nevertheless above the design target. This set must not be rerolled or
pooled with a new set.

All deletion failures were confined to 0.2-microsecond injections. Every
failure was caused by the statistic falling below threshold; none lost the
injected frequency. Five cases failed the paired-row rule and six failed the
UTC-day rule. This suggests that an all-deletions-must-remain-significant hard
veto removes marginal genuine signals at non-negligible cost. That
interpretation is contextual and does not erase the failed frozen gate.

## Questions requiring independent disposition

1. Does the clustered-day result, although a formal pass, require detector
   rebaseline because its point rate is 1.6% and its lower interval bound is
   only narrowly below the trip-wire?
2. May the deletion checks remain prospectively frozen **advisory diagnostics**
   that cannot create, rescue, or veto a candidate, or does their hard-veto
   cost failure require a new robust detection statistic before unblinding?
3. If advisory deletion diagnostics are acceptable, what exact predeclared
   reporting and escalation rule prevents subjective post-candidate
   disposition without treating marginal-signal threshold crossing as a hard
   veto?
4. Is an ordinary-versus-robust candidate refit acceptable as a predeclared
   advisory comparison, and if so, what quantitative agreement fields must be
   reported without creating another detection branch?
5. Based solely on this packet, choose exactly one disposition:

   - `REBASELINE_REQUIRED`;
   - `NEW_PROSPECTIVE_ROBUST_STATISTIC_VALIDATION_REQUIRED`; or
   - `ONE_SHOT_FREEZE_PREPARATION_MAY_RESUME_WITH_DELETION_CHECKS_ADVISORY`.

Explain the statistical and process-integrity basis for the selection. A
conditional or ambiguous answer leaves the search blocked.

## Blinding and authority boundary

The reviewer must state whether any observed-residual periodic content was
provided or inspected. The answer must be no. This packet cannot authorize the
observed search. If Fable permits freeze preparation to resume, a later exact
one-shot freeze and result-independent candidate-disposition contract must
still receive Fable's separate final hash-bound pre-execution sign-off and the
user's explicit authorization.
