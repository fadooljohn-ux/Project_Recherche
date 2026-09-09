# Pilot 2 Calibration Revision Protocol v0.2.1

## Binding sequence

1. Verify the v0.2.1 design freeze, inventory hash, environment, controlled inputs,
   and zero-case implementation tests.
2. Execute exactly 5,000 Gaussian calibration cases in frozen order with checkpoints
   every 25 cases and a 30-second health heartbeat.
3. Reproduce rank 4,962, grade null-ensemble variance and lag correlation, and commit
   one immutable threshold-lock artifact.
4. Verify the threshold lock and then execute exactly 2,000 disjoint sealed Gaussian
   cases. No threshold changes are permitted.
5. Pass only if the Wilson 95% upper bound is at most 2.5%. Report the raw empirical
   false-positive rate without applying a second 1% hard gate.
6. On failure, hard-stop without reroll, retuning, structured-tail evaluation, or
   injection work.
7. On pass, separately freeze and authorize the three 1,000-case structured-tail
   variants.
8. Only after the tail gate passes may the 284-case injection and annual-map stage
   begin. Promotion still authorizes design preparation only, never an observed
   search.

## Historical-case prohibition

No v0.2 calibration or sealed case, seed, threshold, or outcome may enter v0.2.1
threshold construction or sealed validation. The old records may be cited only as
historical evidence explaining the revision.

## Failure semantics

The v0.2 failure remains part of the permanent audit trail. A v0.2.1 pass would show
that the revised protocol met its own preregistered gates; it would not retroactively
convert v0.2 into a pass.

## Execution status

Execution is not authorized by this protocol.
