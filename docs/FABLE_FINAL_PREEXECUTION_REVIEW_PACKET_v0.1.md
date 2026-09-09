# Fable final pre-execution review packet v0.1

## Review request

Independently review the exact hash-bound one-shot package for the PSR
J1744-1134 observed-residual circular-signal search. This is a final
pre-execution review only. Do not inspect, calculate, request, or infer the
observed periodic residual content.

The review must determine whether the implementation satisfies every condition
C1–C7 in the accepted Fable disposition and whether the package is safe to
present to the user for a separate, explicit one-shot execution authorization.

## Identity of the package under review

- Package manifest SHA-256:
  `1efe2878789299dfa017146740f6c0f8d2cba8fd6ebca4e86f0d65c4792f4235`
- One-shot freeze SHA-256:
  `49baf0314e1daf0d1d0ca0b54a2d600246978aed023abc85a4d8e81a78bf017b`
- Implementation SHA-256:
  `61c7998f725a601f897b0eed466e5eeca3b6542394e71f9c46538751f8c474cd`
- Candidate-report schema SHA-256:
  `f827593bcdd562e7fb8edbfa217cd3755967af90c39b721f3c6da9b2b0df9db3`

The authoritative inventory is
`manifests/pilot1_one_shot_final_review_v0.1.sha256`. Verify every listed file,
then separately verify `protocol/PILOT1_ONE_SHOT_SEARCH_FREEZE_v0.1.json`
against the freeze hash above.

## Required review files

1. `docs/FABLE_PREEXECUTION_DISPOSITION_v0.1.md`
2. `docs/FABLE_PREEXECUTION_DISPOSITION_ACCEPTANCE_v0.1.md`
3. `protocol/PILOT1_ONE_SHOT_SEARCH_PROTOCOL_v0.1.md`
4. `protocol/PILOT1_ONE_SHOT_CANDIDATE_DISPOSITION_CONTRACT_v0.1.md`
5. `config/pilot1_one_shot_search_v0.1.yaml`
6. `src/pulsar_pilot/one_shot_search.py`
7. `protocol/PILOT1_ONE_SHOT_CANDIDATE_REPORT_SCHEMA_v0.1.json`
8. `results/pilot1/one_shot_plan_v0.1.json`
9. `tests/test_one_shot_search.py`
10. `protocol/PILOT1_ONE_SHOT_SEARCH_FREEZE_v0.1.json`
11. `manifests/pilot1_one_shot_final_review_v0.1.sha256`

The actual sign-off and user-authorization records must be absent during this
review. Their schemas are included in the package only to define the required
future records.

## Required determinations

Return PASS only if all of the following are true:

- C1: deletion checks are advisory and cannot change candidate disposition;
- C2: all 433 paired-row and 316 UTC-day units are inventory-hash bound;
- C3: no reroll, recovery redraw, automatic retry, or second scan is allowed;
- C4: all borderline tail and deletion-cost history is mandatory in every
  result;
- C5: robust refitting and alternate detection branches are absent;
- C6: threshold, range, grid spacing, mask mapping, and strongest-unmasked-cell
  semantics are unchanged;
- C7: observed access is false until both a hash-matched Fable PASS and a
  separate explicit user authorization exist;
- the immutable intent sentinel is written before observed-residual access and
  blocks any automatic retry;
- the runtime verifier walks every manifest entry and all external prerequisite
  hashes before authorization;
- the candidate-report contract makes no discovery claim and preserves the
  advisory/integrity boundary; and
- all 98 repository tests and static checks pass without any observed search.

Any condition, ambiguity, or requested change is a non-PASS disposition. Do
not issue a conditional PASS. Changes require a new package, new hashes, and a
new final review.

## Required machine-readable response

If and only if the package passes without conditions, create
`protocol/FABLE_FINAL_PREEXECUTION_SIGNOFF_v0.1.json` with exactly this
structure and these package hashes:

```json
{
  "reviewer": "Claude Fable 5",
  "review_date": "YYYY-MM-DD",
  "verdict": "PASS",
  "no_conditions_remaining": true,
  "observed_periodic_content_inspected": false,
  "package_manifest_sha256": "1efe2878789299dfa017146740f6c0f8d2cba8fd6ebca4e86f0d65c4792f4235",
  "one_shot_freeze_sha256": "49baf0314e1daf0d1d0ca0b54a2d600246978aed023abc85a4d8e81a78bf017b",
  "implementation_sha256": "61c7998f725a601f897b0eed466e5eeca3b6542394e71f9c46538751f8c474cd",
  "candidate_schema_sha256": "f827593bcdd562e7fb8edbfa217cd3755967af90c39b721f3c6da9b2b0df9db3"
}
```

If the package does not pass, provide a written FAIL disposition listing each
specific defect. Do not create the PASS record.

## Authority after review

A valid Fable PASS does not itself authorize execution. The user must still
explicitly authorize the exact hash-bound one-shot package. Until that second
record exists, the runner remains locked and observed residuals remain
inaccessible.
