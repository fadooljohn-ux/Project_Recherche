# J1802-2124 source/model clarification — 10 September 2026

**The missing Shapiro parameters are a documented release choice, not a Recherche
import loss. The preparation hold remains.** No timing fit, calibration or
observed search was performed. This closes the source/provenance question and
identifies a bounded engineering route; it does not qualify that route.

## Released-file comparison

We inspected the pinned NANOGrav 15-year v2.1.0 archive, checking 22 extracted
files against saved SHA-256 bindings. The primary wideband PAR/TIM hashes also
match the preceding ELL1H assessment. Five model variants were inspected: main
narrowband, main wideband, narrowband Tempo2, NoRedNoise and predictive.

| Property | Main narrowband | Main wideband |
| --- | --- | --- |
| Retained TOAs | 6,796 | 126, all with paired DM measurements |
| Site-MJD observing days | 69 | 70 |
| Span | 1,262.62 days (3.46 years) | 1,262.62 days (3.46 years) |
| Binary model | ELL1H, NHARMS 7 | ELL1H, NHARMS 7 |
| H3, H4, STIGMA, M2, SINI | Absent | Absent |
| Released red terms | RNAMP 1.5767122663, RNIDX −1.4712131085 | Absent |
| Configured orbital-phase exclusion | 0.15–0.35 | 0.15–0.35 |
| Arrivals labelled eclipsing in retained excision file | 748 | 14 |

RNAMP/RNIDX above are raw PAR conventions, not log10 amplitude or a fitted
Recherche noise estimate. Day counts are text inventory counts, not barycentric
fit epochs. Narrowband and wideband reduce overlapping observations; the large
TOA-count difference does not represent thousands of independent observing days
or independent confirmation. The excision files are intermediate provenance;
we use the final main TIM files for retained counts.

The alternate Tempo2 model uses **ELL1**, also without Shapiro terms. Neither
NoRedNoise nor predictive contains a missing Shapiro solution. The release
README assigns these latter variants to folding applications; they are not
substitutes for the main timing/noise model. The release's change log describes
v2.1.0 as adding narrowband residual products, not repairing J1802 parameters.
[Release and associated files](https://zenodo.org/records/16051178).

## Why the parameters are absent

The wideband YAML explicitly records **“REMOVE: H3/H4 due to F-test”** on
2023-02-08. The narrowband YAML separately records **“REMOVE: H3, H4”**.
That narrowband entry is dated 2021-01-19 despite appearing after December 2021
entries; we preserve the supplied date and do not infer a corrected chronology.
Both configurations omit Shapiro terms from their free-parameter lists.
The target-specific numeric F statistic/p-value is not supplied in these files.

The timing paper describes nested-model parameter selection with a p < 0.0027
inclusion criterion, including Shapiro terms. It also describes cutting
conjunction-region arrivals for potentially eclipsing systems. Both J1802
configurations retain an orbital-phase cut of 0.15–0.35; the narrowband history
says it was added to remove potentially affected arrivals. These are documented
processing choices, not our independent diagnosis that J1802 eclipses.
[Agazie et al. 2023, Sections IV.1 and Appendix A](https://arxiv.org/html/2306.16217).

**Inference:** removing conjunction coverage can weaken Shapiro constraints.
The retained phase cut, short baseline and differing noise choices make the
omission understandable, but this inspection does not measure each factor's
contribution or reproduce NANOGrav's F-test. It does not show the physical
Shapiro delay is absent or negligible for a planet search.

## Relation to the earlier mass measurement

Ferdman et al. measured Shapiro delay using an earlier, different observing
campaign: concentrated GBT sessions supplemented by Parkes and Nancay data.
Ten GBT sessions lasted 6–8 hours to improve orbital coverage. Their reported
white-dwarf mass was 0.78 ± 0.04 solar masses. That physical measurement is not
contradicted by a later reduction omitting poorly supported timing parameters;
its dedicated sampling is not the final NG15 sampling reviewed here.
[Ferdman et al. 2010, Sections II–IV](https://arxiv.org/html/1002.0514v1).
We have not acquired or reanalysed those earlier arrivals in this task.

## Supported next route

Recommend one **target-specific omitted-Shapiro ELL1H preparation**, preserving
the final wideband model and its published phase cuts. This needs a narrow
extension of the existing omitted-in-release machinery; the current H3-only
branch requires fitted H3 and NHARMS 3 and correctly rejects this input.
The preparation should:

1. Explicitly recognize the source-documented omission and verify the native
   ELL1H zero-Shapiro convention and timing derivatives without inventing H3,
   converting the model label, or inserting masses from a paper.
2. Check real-TOA timing/DM design rank, orbital stability, phase coverage and
   existing omitted-Shapiro harmonic diagnostics on the retained data. Keep
   the released exclusions. A failed adequacy check retains the hold.
3. Assess wideband noise adequacy with the narrowband red-noise discrepancy
   as a declared model-comparison question. Do not transplant narrowband noise
   amplitudes directly or treat no published wideband red term as no red noise.
4. Report preparation compatibility and a prospective 30–631.31-day range.
   Only a successful preparation supports a later target-specific calibration;
   there is no threshold or launch-ready package today.

This is a preparation proposal, not authorization exercised during this review.
A broader physical Shapiro uncertainty treatment remains a separate route if
these bounded checks fail. The four earlier nonlinear measured-Shapiro holds
remain unchanged. No author contact or additional source campaign is needed to
answer the provenance question now resolved.

## Evidence and closeout

[Machine comparison](../results/research/j1802-model-review-20260910/comparison.json)
binds every inspected file, model field, cut count and the inventory script.
Run `python3 tools/j1802_model_review.py --data DATA_DIR --output NEW_JSON` to
repeat the read-only comparison with the preserved extraction under
`RECHERCHE_DATA/j1802-model-review-20260910`; an existing output is refused.
No raw release models, institutional paths or credentials are added to Git.

Three Work log entries record the release diagnosis, sampling/noise limits and
closeout. The canonical master remains **783 registered targets, 286 observed
identities, 360 search/refinement records and eight candidate grades**. All
historical cells and the 71 publication-source bindings are preserved. No worker
was launched; monitoring remains paused. Changes are saved in a local development
commit, with no push or release in this scope. See the accompanying workbook
receipt and closeout manifest for hashes and verification.
