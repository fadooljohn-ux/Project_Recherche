# Downloads, the model translation step and the release adapters

**20–21 November 2026. Owner instruction: "4. Proceed with downloading the
Parkes binary arrival times and small open sets from SUPERB V/GBNCC. Build a
model translation step and adapter for the Parkes, Europeans, and
International releases". Nothing was calibrated, frozen or searched; the
adapter checks below are preparation-only development checks.**

## Status at a glance

| Item | State |
|---|---|
| Parkes binary arrival times | Downloaded, verified against the September files |
| SUPERB V | Downloaded |
| GBNCC | Downloaded |
| Model translation step | Built and tested |
| Parkes and European adapter | Built and tested; first real-data check shows open problems |
| International (IPTA DR2) adapter | **Not built** |

## Downloads

All under `../Project Recherche Data/`, each with `acquisition.json` (URLs,
sizes, sha256, commit, licence) and `inventory.json`. Done by a subagent;
the recording agent checked that the folders exist and that one Parkes par
file is byte-identical to its September copy, and did not re-verify the
rest.

| Folder | Content | Licence |
|---|---|---|
| `ppta-dr3-binaries-20261120` | Arrival times, timing models, noise files and clock files for the 23 Parkes binaries, from CSIRO Data Access Portal collection 59374 (the source September used); 90,719 arrival times. Also the GitHub repository archive at commit `fdbe6eb1`. | CC BY-SA 4.0 (CSIRO, from the September listing); the GitHub repository states none |
| `superb-v-20261120` | 23 pulsars, arrival times and timing models, 2,135 arrival times; one binary | CC BY 4.0 |
| `gbncc-20261120` | 150 pulsars with timing models, 104 with arrival times (29,202); 25 binaries; commit `1af36ace` | CC BY 4.0 |

Notes:

- The subagent was told to use the GitHub repository; it found that
  September took the Parkes arrival times from CSIRO and fetched both. The
  23 CSIRO noise-fit timing models are byte-identical to September's; the
  GitHub ones are a different product and are not used.
- J1741+1351 has no arrival-time file in the main Parkes folder; its file
  was taken from the release's wide-band-receiver folder.
- The CSIRO clock file `tai2tt_bipm2021.clk` differs from the September
  copy (different repository). The adapter uses the September clock set.
- Leftovers outside the project that a safety check would not let the
  agents delete: 64 extracted par files in the session scratch folder.
- SUPERB V and GBNCC have not been inventoried against the search's
  requirements (span, cadence, model type). That is the next step for
  them and needs no new download.

## Model translation step

`tools/orbit_translate.py` (`tests/test_orbit_translate.py`, 14 tests).
`BINARY T2` and `BT` are renamed to the supported model that carries the
same parameters; no value is changed:

| Parameters in the file | Becomes |
|---|---|
| TASC, EPS1, EPS2 | ELL1 (ELL1H if the Shapiro delay is given as H3) |
| T0, ECC, OM | DD (DDH if the Shapiro delay is given as H3) |
| BT without Shapiro terms | DD |

Refused: KOM/KIN, a second orbit, orbital-frequency derivatives, SHAPMAX,
MTOT, both parameter sets at once, both Shapiro forms at once.

No timing package that implements `T2` natively is installed, so there is
no direct numerical comparison with the release's own software. The
translation is confirmed by the timing library's independent guess of the
model, and then by the null fit and orbit-shift checks at preparation.
**That second check is doing real work: see the European results below.**

## Parkes and European adapter

`tools/pta_binary.py` (`tools/recherche pta-binary
select|prepare|calibrate|freeze|run --data ROOT`; `tests/test_pta_binary.py`).
It is the September preparation for the isolated pulsars of these releases
(`tools/pta_campaign.py`: released white and correlated noise, band noise,
clock chains) with the binary procedure: automatic translation, opt-in
re-expression and Shapiro basis, the orbit checks of the MeerKAT tool.
`--development` roots cannot be calibrated, frozen or run.

### European check (`epta-binary-dev-20261121`): 5 of 11 pass

| Target | Outcome |
|---|---|
| J0900−3144, J1804−2717 | pass (translated) |
| J1751−2857, J1910+1256 | pass (translated, re-expressed) |
| J1918−0642 | pass (re-expressed, Shapiro basis) |
| J0613−0200 | held: orbit shift of 10 checked uncertainties (size and one eccentricity term) |
| J0751+1807 | held: orbit shift of 4.2 |
| J1909−3744 | held: orbit shift of 8.3 (rate of change of orbit size) |
| J1857+0943 | held: data prefer Shapiro values outside the checked region (9.3 against 9) |
| J1738+0333 | held: pulse numbering ambiguous (0.51 of a turn) |
| J1012+5307 | failed on a clock file: two preparations running at once wrote the same derived clock file. Fixed in the tool (each preparation now keeps its own); not rerun |

**Open problem.** J0613−0200 and J0751+1807 give the Shapiro delay as
H3 with STIG or H4 inside a `T2` model. The shifts they need are in
exactly the parameters that absorb the first two Shapiro harmonics. The
likely cause is a difference in convention between tempo2's `T2` and the
timing library's ELL1H for which harmonics the Shapiro terms include. If
so, the translation needs a harmonic re-centring step for that case (the
September tool has one for a related case). Not diagnosed further. The
checks held these targets, as they should.

### Parkes check (`ppta-binary-dev-20261121`): 0 of 16 pass

| Reason | Targets |
|---|---|
| The released timing model gives no parameter uncertainties | 15 |
| Position parameter missing after loading | J0613−0200 |

**The Parkes noise-fit timing models carry no uncertainties** for the
orbital or Shapiro parameters. The orbit checks define their neighbourhood
as three times the larger of the released uncertainty and the uncertainty
under the search covariance, and refuse when the released one is absent.
The Shapiro basis also needs a released uncertainty. Options, for the
owner:

1. Use the uncertainty under the search covariance alone when the release
   gives none. Same formula with one term missing; it is a rule change and
   should be the owner's decision.
2. Take uncertainties from another source (the release's paper tables or
   its other timing-model files, which also lack them on a first look).
3. Leave the Parkes binaries.

J1741+1351 was left out of this check (its arrival times sit in a
different folder).

## International adapter

Not built. IPTA DR2 has its own preparation (`tools/ipta_prepare.py`) and
combines European, Parkes and NANOGrav 9-year data, so a binary adapter
for it should follow once the Parkes and European questions above are
settled; most of its `T2` cases are the same ones.

## What is needed to finish

1. Owner decision on the Parkes uncertainty rule.
2. Diagnose the H3-in-T2 convention and add the re-centring if confirmed.
3. Rerun the European check for J1012+5307; look at J1738+0333's pulse
   numbering.
4. Build the International adapter.
5. Inventory SUPERB V and GBNCC against the search's requirements.

## Evidence

`tools/orbit_translate.py`, `tools/pta_binary.py` and their tests;
development roots `epta-binary-dev-20261121` and `ppta-binary-dev-20261121`
under `../Project Recherche Data/` (not to be calibrated, frozen or run);
download records in the three download folders.

## Update: recommended steps carried out

**Owner instruction, 20 November 2026: "Proceed with all recommended steps
and yes yes the searches own".** Preparation-only development checks; nothing
was calibrated, frozen or searched. This section supersedes the two check
tables and the "open problem" above.

### What changed

1. **Parkes uncertainty rule (owner's decision).** Where a release gives
   no uncertainty for an orbital or Shapiro parameter, the uncertainty
   under the search covariance is used. It never replaces one the release
   gives, and each receipt lists the parameters it was used for.
2. **Shapiro convention found and corrected.** The tempo2 source
   (`T2model.C`, `ELL1Hmodel.C`, read from its public repository) applies
   only the third and higher harmonics of the Shapiro delay when it is
   given as H3 with STIG; the first two stay in the fitted orbit. The
   pinned timing library applies all harmonics. The translation now
   re-centres the orbit for that case
   (`orbit_translate.recentre_orthometric`: A1′ = A1 − 4rς, with matching
   changes to the eccentricity terms). A test reproduces the tempo2
   formula to 0.1 ns; uncorrected, the difference is microseconds. Two
   real targets that were held with exactly this signature now pass
   (European J0613−0200, Parkes J1545−4550).
3. **Refinement of re-expressed orbits** (`tools/orbit_refine.py`,
   `--refine`): after the change of variables the re-expressed parameters
   are adjusted so the model reproduces the released model's delays (model
   against model). J1640+2224 goes from 0.83 µs to 0.003 µs and now passes.
4. **Parallel preparations** no longer share a derived clock file.

### Third-round results

| Release | Pass | Held |
|---|---|---|
| Parkes (16 checked) | 14: J0125−2327, J0900−3144, J1545−4550, J1933−6211, J1902−5105, J1045−4509, J1446−4701, J1603−7202, J2129−5721, J1643−1224, J0614−3329, J1125−6014, J1857+0943, J1909−3744 | J2145−0750 (orbit shift of 3.3 in an eccentricity rate); J0613−0200 (the released file has no ecliptic latitude) |
| European (11 checked) | 6: J0613−0200, J0900−3144, J1751−2857, J1804−2717, J1910+1256, J1918−0642 | J0751+1807 (orbit shift 4.2); J1909−3744 (orbit shift 8.3); J1857+0943 (Shapiro region, 9.3 against 9); J1738+0333 (pulse numbering); J1012+5307 (arrival times beyond the end of a clock file) |
| NANOGrav (refinement test) | J1640+2224, J1643−1224, J2229+2643 | — |

Null reduced chi-square is 0.82–1.03 for the Parkes and European passes.
Ten of the Parkes passes and four of the European ones would reach 2,000
days. Twelve of the passing pulsars have never been searched by this project:
ten in the Parkes data (J0614−3329, J0900−3144, J1045−4509, J1125−6014,
J1446−4701, J1545−4550, J1603−7202, J1643−1224, J1902−5105, J2129−5721) and
J1751−2857, J1804−2717 and J1910+1256 in the European data (J0900−3144
passes in both). The others would be longer records of pulsars searched
before in other data.

### Corrections to what was written above

- **tempo2 is installed** in the isolated runtime the International
  adapter uses (`ipta-adapter01-20260909/runtime`). The statement that no
  package implementing `T2` is available was wrong. A direct numerical
  comparison of translated models against tempo2 is therefore possible; it
  has **not** been done and is the strongest remaining check on the
  translation.
- The earlier J1012+5307 failure was not only the parallel clash: its
  arrival times run past the end of one European clock file.

### What this implies for earlier MeerKAT work

The MeerKAT timing models were also fitted with tempo2. For ELL1H targets
with H3 and STIG the same convention difference applies. It does **not**
change any search result: the two harmonics involved are exactly the
orbit-size and eccentricity columns the search projects out, and every
searched target passed the orbit-shift and linearity checks. It may,
however, explain some MeerKAT **holds** (for example J1435−6100, held on an
eccentricity-term shift of 8.2). `tools/mpta_binary.py` does not apply the
re-centring; adding it would need a new MeerKAT preparation check and is
not done.

### Still open

- **International adapter: not built.** It runs on tempo2 itself, so it
  needs no translation, but its export step must be extended to supply
  the linearity checks and the Shapiro basis. That is a separate piece of
  work.
- Direct tempo2 comparison of the translation (above).
- J0751+1807 and J1909−3744 (European), J2145−0750 (Parkes): causes of
  the orbit shifts not diagnosed.
- J1741+1351 (Parkes) not checked: its arrival times are in a different
  folder of the release.

Evidence: `results/research/pta-binary-dev-20261121/closeout.json`;
development roots `ppta-binary-dev3-20261121`, `epta-binary-dev3-20261121`,
`ng15-binary-dev4-20261121` (earlier `dev` and `dev2` roots superseded).
None may be calibrated, frozen or run.
