# White-dwarf binary expansion 02 — 9 September 2026

The owner authorized inventory of the remaining NG15 exclusions, configurable
selection, preparation/calibration/search of up to five compatible white-dwarf
systems, and closeout with the master updated. The previous pilot and its
consumed observations remain preserved. No new publication or outreach is included.

The intake reconciles all 48 remaining exclusions: 47 explicit binary models
and J1024−0719's known wide-companion exclusion without a binary component in
this released PAR. Under the existing ELL1 adapter, the exclusive dispositions are:

| Intake disposition | Count |
|---|---:|
| DD model not supported | 22 |
| Required free orbital parameters absent | 14 |
| ELL1H model not supported | 3 |
| Published three-sigma SINI bounds leave the physical interval | 3 |
| DDK / BT / no binary component | 3 |
| Selected for full preparation checks | 3 |
| Total | 48 |

The three selections are J0740+6620, J1857+0943 (release alias B1855+09), and
J2043+1711. Each supplies PB, A1, TASC, EPS1, EPS2, M2 and SINI as fitted
parameters with positive uncertainties. Their SINI intervals remain physical;
this screening does not establish local linearity. There are only three
candidates under these rules, so the batch contains three rather than five.
The other 45 are inventory exclusions, not failed searches.

Companion context: [J0740](https://arxiv.org/abs/2104.00880),
[B1855](https://ueaeprints.uea.ac.uk/id/eprint/67589/1/Published_manuscript.pdf), and
[J2043](https://academic.oup.com/mnras/article/422/2/1294/1034885).
J2043 also has a [published anomalous-acceleration investigation](https://arxiv.org/abs/2407.06482)
considering a much wider third body. This batch does not claim that system is
unexplored or attempt to confirm the proposed long-period object.

Selection is fixed before observed periodograms. The adapter now accepts an
explicit JSON selection manifest and canonical J names, resolves release aliases,
and binds the actual selection count and new seed into preparation and freeze.
The numerical model and the pilot's derivative, local-linearity, rank and orbital
shift criteria are unchanged. Existing pilot hashes remain in its original
records and Git revision; no prior run is repeated.

For each compatible target the intended scope remains max(30 days, ten inner
binary periods) through min(2000 days, half the span), fixed published covariance,
joint free timing/orbital projection and a new shared 1% conditional allowance.
The selection count remains three even if one or more targets is held. Calibration
and observed execution are conditional on preparation passing.

## Operator command

```sh
tools/recherche binary-pilot select --data "$NEW_DATA" --archive "$NG15_ARCHIVE" \
  --inventory "$NG15_INVENTORY" --selection "$SELECTION_JSON"
```

The requested manifest contains `selected` (unique canonical J names), `seed`
and `references`. It should also record inventory dispositions and selection
rationale. `select` writes the immutable execution selection; the usual prepare,
calibrate, freeze and run commands read it. A completed target cannot be selected
again through this new-identity route. Holds must be registered separately.

## Preparation closeout

All three selected preparations are held. No calibration, injection campaign,
execution freeze or observed search was launched. No threshold or NO_TRIGGER
result exists for these cases.

| Target | Derivative relative error | Maximum three-sigma Taylor remainder / TOA σ | Disposition |
|---|---:|---:|---|
| J0740+6620 | 7.33e-6 | 0.924 | HELD_MODEL_NONLINEARITY |
| J1857+0943 | 7.94e-6 | 0.401 | HELD_MODEL_NONLINEARITY |
| J2043+1711 | 6.93e-6 | 1.814 | HELD_MODEL_NONLINEARITY |

Each reaches SINI with an accurate local derivative (required relative error
below 0.001), but exceeds the unchanged 0.1 TOA-σ limit on the finite three-sigma
Taylor remainder. The effect arises from curvature of the Shapiro delay across
the released inclination uncertainty. It is not the missing-cosine derivative
bug repaired in pilot01, a clock failure, or evidence for a planet. Shrinking the
checked uncertainty interval to admit the targets would change the model claim,
so the original checks and these failed attempts are retained.

The inventory therefore closes as 45 excluded plus three preparation holds,
zero compatible targets, and zero searches. Across both binary pilots, two targets
have NO_TRIGGER results and four are held for nonlinear Shapiro uncertainty.
The other 45 exclusions include model families and missing fitted terms that have
not been implemented in this adapter. This does not establish that binary pulsar
planet searches are unfruitful; it establishes the current adapter's narrow scope.

The next useful engineering assessment is to distinguish ELL1 white-dwarf systems
whose released models omit fitted Shapiro terms from interacting low-mass systems
in the 14 missing-parameter exclusions. Supporting the former requires explicit
conditional-model handling; it is not a reason to ignore missing terms silently.
Full nonlinear Shapiro/orbital inference remains a separate larger development.
Do not scale this adapter to batches of 25 on the present evidence.

The [saved inventory, selection and closeout](../results/observed/binary-pilot02-20260909/closeout.json)
retain hashes for all three failures and the 48-target assessment. The master
records each preparation hold and the batch closeout without adding Search rows.
All prior results and numerical scientific source remain unchanged. No job is active.

The master also adds 29 previously unregistered inventory identities, bringing
the register to 783 targets. Observed identities remain 279 and Search/refinement
records remain 353. An inventory addition is not an observed search. Existing
operator notes and historical scientific records are preserved.
