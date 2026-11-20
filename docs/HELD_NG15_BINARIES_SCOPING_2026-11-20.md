# Scoping the three held NANOGrav binaries

**20 November 2026. Owner instruction "3. Do the preliminary scoping work".
Scoping only: one model-to-model diagnostic was run (orbital delays of two
models compared on the real sampling; no residuals, no periodogram). Nothing
was built, prepared for search, calibrated or searched.**

## J1640+2224 — fixable; small, well-defined addition

**Why it is held.** After the re-expression the fit asks for a shift of 16
checked uncertainties in the time of ascending node.

**Diagnosis.** The re-expressed model is not wrong; its starting values
are slightly off. The re-expression uses the first-order relation between
the two parameter sets. For this orbit (eccentricity 8×10⁻⁴, 175-day
period, 55 light-seconds) the delay predicted by the re-expressed model
differs from the released one by 0.83 µs rms, but a small adjustment of the
re-expressed parameters (0.05 s in the time of ascending node, with period,
size and the two eccentricity terms) removes all but 0.002 µs. The same
diagnostic gives 0.005 µs for J2302+4442 and under 10⁻⁷ µs for J2229+2643.

**What it would take.** Add a refinement step to the re-expression: after
the change of variables, adjust the re-expressed parameters so the model
reproduces the released model's delays (model against model; no
observations enter), then run the existing equivalence and orbit checks
from that point. No threshold changes. About half a day including tests on
simulated orbits. It would also remove most of J2302+4442's 2.5-uncertainty
shift and makes the re-expression safe for other wide, slightly eccentric
orbits in the Parkes and European releases.

**Value.** Range about 1,755–2,000 days only (the inner period is 175
days). Low yield for this pulsar; the real benefit is to the method.

**Update, 21 November 2026.** Built (`tools/orbit_refine.py`, `--refine`). In a
preparation-only check J1640+2224 now passes: 0.83 µs to 0.003 µs, largest
orbit shift 0.62. Not searched.

## J1853+1303 — no clean route; recommend leaving held

**Why it is held.** The data prefer Shapiro values just outside the checked
region (expected chi-square change 10.2 against a limit of 9; companion
mass three widths high).

**Options.**

| Option | What it involves | Assessment |
|---|---|---|
| Widen the checked region | Change the limit from 9 | This is loosening a check to clear a hold. Not offered. |
| Full nonlinear orbit fit | The November nonlinear statistic (used for J1857+0943 and three others), applied after re-expression; needs its own verification on simulated data and about a day of computing | Possible, but the tool was verified for ELL1 orbits written that way in the release, not for re-expressed ones |
| Leave held | Nothing | Recommended |

**Value.** Range about 1,157–1,647 days. Low.

## J1802−2124 — a noise question, not an orbit question

**Why it is held.** September's adequacy hold: with the Shapiro delay
omitted there is residual structure at the orbital period and the red-noise
fit runs to the edge of its range; the September model comparison found no
validated interior solution
([record](ELL1H_J1802_PREPARATION_2026-09-10.md)). Today's preparation
agrees: null reduced chi-square 1.22.

**What has changed since September.** Two tools that did not exist then:
the Shapiro basis (a published Shapiro measurement is believed to exist
for this pulsar and could seed it; to be confirmed from the literature) and the second-stage noise family with
per-receiver white noise.

**What it would take.** A preparation-level study, no search: (1) put the
published Shapiro delay in as fixed values with the basis around it and
see whether the orbital structure goes; (2) fit the second-stage noise
family at preparation and see whether an interior noise optimum now
exists. About a day. If both come out clean the hold could be reviewed;
if not, it stands with a clearer reason.

**Value.** Range 30–631 days on a 3.5-year record with 126 TOAs. Modest.

## Recommendation

1. Build the J1640+2224 refinement. It is cheap and the other releases
   will need it.
2. Leave J1853+1303 held.
3. J1802−2124 only if the owner wants that pulsar specifically.

## Evidence

Diagnostic output is recorded in this document (delays of the released and
re-expressed models on the sampling of
`../Project Recherche Data/ng15-binary-dev3-20261120`). Hold reasons:
`results/research/ng15-binary-dev-20261120/closeout.json`.
