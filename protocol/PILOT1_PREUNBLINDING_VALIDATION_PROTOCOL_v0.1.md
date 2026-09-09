# Pilot 1 pre-unblinding validation protocol v0.1

## Purpose and authority

This protocol incorporates the independent Fable audit before any observed
periodic search. It authorizes only deterministic synthetic validation against
the already released detector. It does not authorize loading or scanning the
observed residual vector.

## Preserved sequential evidence

The original contaminated evaluation failure remains 7/500 and the disjoint
R1 evaluation remains 7/1,000. Both must be reported together. The descriptive
14/1,500 pool is contextual only and is never a gate. No further tail set may
be generated after seeing a failure. Any failure in this protocol goes to
rebaseline or independent disposition, never another re-roll.

## Locked detector

The threshold remains delta chi-square 23.33426855482562 with a strict greater-
than comparison. The 30–2,000-day grid and one-fifth-independent-bin spacing
remain unchanged. Structured stresses measure performance at this threshold;
they may not recalibrate, lower, or otherwise tune it.

## Structured synthetic tail readiness gates

Run exactly 1,000 seed-disjoint evaluation nulls for each of three variants:

1. contamination restricted to native timing-block innovations, with the
   scale-mixture multiplier analytically matched to excess kurtosis 2.0499443;
2. contamination restricted to native DM-block innovations, matched to
   0.6872127; and
3. contamination clustered by UTC observing day, applying one shared day mask
   to the paired timing and DM coordinates while preserving unit marginal
   variance and the 1.2621408 kurtosis target.

Native innovation labels describe the ordering before multiplication by the
released covariance Cholesky factor. Because covariance whitening and timing
projection mix coordinates, each result must report achieved timing-block,
DM-block, and combined projected moments; the analytic targets are not claims
that projected sample kurtosis will equal them exactly.

No calibration sample is permitted. At the locked threshold, a variant
requires rebaseline if its Wilson 95% lower bound on the false-positive rate is
strictly greater than 1%. Variant outcomes may not be pooled, and a failed
variant may not be rerun with new seeds.

## Deterministic deletion-stability cost

Reconstruct the exact 160 original tail-recovery cases using the original case
identifiers, seeds, scale-mixture draws, and injections. Do not alter or replace
the immutable source artifacts. This replay exists because the stored peak
summaries do not contain deletion-level scans.

For every originally triggered and frequency-recovered case, test:

- deletion of each paired wideband observation row, meaning its timing and DM
  components together; and
- deletion of all rows sharing each integer UTC MJD day.

For every deletion, rebuild the reduced covariance, timing-design projection,
and scanner, then scan the complete unchanged frequency grid. Stability means
the strongest post-deletion peak remains strictly above the locked threshold
and within one independent Fourier bin of the injected frequency.

Each proposed veto may become hard only if its observed false-veto rate is at
most 1%, its Wilson 95% upper bound is at most 5%, and there are zero integrity
failures. Otherwise that check remains advisory and search execution stays
blocked for independent disposition. Do not adapt the veto after seeing its
cost.

## Annual-mask semantics

The future one-shot search scans the complete frozen grid once. It selects the
strongest unmasked cell and compares it with the unchanged full-grid-calibrated
threshold. A masked annual cell is a sensitivity gap only; it cannot suppress
a distinct unmasked candidate. The complete mask and this selection rule must
be hash-bound before unsealing.

## Candidate disposition classes

Integrity failures, nonconvergence, excessive solver disagreement, and an
unexpected material warning are hard aborts. Single-row and single-day
dependence are hard vetoes only after passing the frozen synthetic cost gate.
Backend concentration, post-candidate kurtosis, half-span amplitude/phase
stability, pooled tail context, and the Behrens ratio are advisory only.
Advisory findings cannot create, rescue, or veto a candidate.

## Independent final sign-off

5.6 Sol is the pipeline operator and may prepare and verify the packet but may
not provide independent approval. Claude Fable 5 is the planned independent
reviewer. After synthetic validation passes, Fable must review the exact
hash-bound results and proposed one-shot execution freeze without inspecting
observed periodic content. The returned sign-off must satisfy the frozen
sign-off contract. A missing, conditional, mismatched, or failing sign-off
leaves execution unauthorized.

## Stop rule

This phase ends after publishing the synthetic validation result and reviewer
packet. It must not construct or invoke an observed-periodic-search command.
