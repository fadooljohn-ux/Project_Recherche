# Fable post-execution result review packet v0.1

## Review request

Independently audit the completed one-shot result and the proposed claim
boundary. This is a result-integrity review, not authorization for another
observed search, threshold change, or exploratory analysis.

The tracked review manifest is
`manifests/pilot1_one_shot_result_review_v0.1.sha256`, SHA-256
`3af51ff92a1f25d7081e4a2b51f19eb6ff930b38dddf26b2a36fb332a3481a21`.
Verify every listed repository file before reviewing the outcome.

## Records to verify

In the controlled data root, verify:

- `run_records/pilot1/one-shot-observed-search-v0.1-intent.json`, 659 bytes,
  SHA-256
  `cd76bab246979e4aaa1e5513c10ba8c2951242054ce27271c6c1be429821c8ee`;
- `run_records/pilot1/one-shot-observed-search-v0.1-result.json`, 3,999 bytes,
  SHA-256
  `720f3604058121ddc4aa7ff5a0be159089b28ca279328b18addd4d1904ce06bc`;
- `run_records/pilot1/one-shot-observed-search-v0.1.log`, 706 bytes, SHA-256
  `efafe93f6dab0c2ba1894da87a3628e5fcee8e93696094d6056686e3d4dd5079`.

In the repository, review:

1. `protocol/PILOT1_ONE_SHOT_SEARCH_FREEZE_v0.1.json`;
2. `protocol/PILOT1_ONE_SHOT_CANDIDATE_DISPOSITION_CONTRACT_v0.1.md`;
3. `protocol/PILOT1_ONE_SHOT_CANDIDATE_REPORT_SCHEMA_v0.1.json`;
4. `protocol/FABLE_FINAL_PREEXECUTION_SIGNOFF_v0.1.json`;
5. `protocol/USER_ONE_SHOT_EXECUTION_AUTHORIZATION_v0.1.json`;
6. `results/pilot1/one_shot_observed_search_result_v0.1.json`;
7. `docs/PILOT1_ONE_SHOT_OBSERVED_SEARCH_RESULT_v0.1.md`;
8. `protocol/FABLE_POSTEXECUTION_RESULT_DISPOSITION_SCHEMA_v0.1.json`; and
9. `manifests/pilot1_one_shot_result_review_v0.1.sha256`.

## Required determinations

Confirm or reject each point:

1. the intent record matches the reviewed package and both authorizations;
2. exactly one observed scan was executed on the frozen 941-cell grid;
3. the strongest unmasked statistic was 16.4990614 at 59.9641335 days;
4. the statistic was below the strict 23.3342686 threshold and therefore
   correctly produced no candidate;
5. the full-grid maximum was unmasked;
6. candidate-only refits and deletion diagnostics were correctly skipped;
7. warning, hash, resource, and report-integrity gates passed;
8. the one-shot permission is consumed and no retry or retuning is authorized;
9. the permanent calibration caveats remain disclosed; and
10. the proposed claim language does not overstate the null result.

Return an unconditional PASS only if all ten determinations pass. Otherwise
return FAIL with each specific defect. Any proposed new analysis must be
separately scoped and cannot alter or rerun the v0.1 result.

## Required machine-readable response

For an unconditional PASS, create
`protocol/FABLE_POSTEXECUTION_RESULT_DISPOSITION_v0.1.json` with exactly this
structure and the following record hashes:

```json
{
  "reviewer": "Claude Fable 5",
  "review_date": "YYYY-MM-DD",
  "verdict": "PASS",
  "no_conditions_remaining": true,
  "intent_sha256": "cd76bab246979e4aaa1e5513c10ba8c2951242054ce27271c6c1be429821c8ee",
  "result_sha256": "720f3604058121ddc4aa7ff5a0be159089b28ca279328b18addd4d1904ce06bc",
  "log_sha256": "efafe93f6dab0c2ba1894da87a3628e5fcee8e93696094d6056686e3d4dd5079",
  "exactly_one_observed_scan_confirmed": true,
  "null_disposition_correct": true,
  "claim_boundary_accepted": true,
  "additional_search_or_retry_authorized": false
}
```

For any failed or conditional determination, provide a written FAIL disposition
and do not create the PASS record.
