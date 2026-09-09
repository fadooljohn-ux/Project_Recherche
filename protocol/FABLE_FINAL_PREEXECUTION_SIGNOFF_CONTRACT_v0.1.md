# Fable final pre-execution sign-off contract v0.1

The final independent review record must be a Markdown or JSON artifact stored
in Project Recherche and must contain all fields below.

1. Reviewer identity: `Claude Fable 5`, or a newly approved independent
   reviewer named before receiving results.
2. Review date and explicit statement that the reviewer did not operate the
   pipeline phase being reviewed.
3. Explicit statement that no observed-residual periodic result was inspected
   and that no such result was supplied in the packet.
4. SHA-256 of the pre-unblinding freeze, validation protocol, configuration,
   implementation, complete synthetic result, result manifest, and proposed
   one-shot execution freeze.
5. A row-by-row scorecard covering the structured tail gates, no-reroll rule,
   deletion-veto cost, annual-mask semantics, integrity, resources, and
   continued blinding.
6. Exactly one verdict: `PASS`, `PASS_WITH_UNSATISFIED_CONDITIONS`, or `FAIL`.
7. For `PASS`, an explicit statement that no condition remains open and that
   the exact hash-bound one-shot execution freeze may advance to user
   authorization.

`PASS_WITH_UNSATISFIED_CONDITIONS` and `FAIL` do not authorize execution. A
changed hash after review invalidates the sign-off. This record is a
hash-bound reviewer attestation, not a cryptographic signature.
