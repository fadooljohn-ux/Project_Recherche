# Combined limit on planets around isolated pulsars

**19 November 2026. Owner instruction "Proceed with the three steps you've
outlined" (step 3: combine per-pulsar limits into a population statement).
Computed from the saved sensitivity atlas; no observations read, no search
run.**

## Statement

Across 271 isolated pulsars searched with no confirmed detection:

- **Planets of 10 Earth masses or more with periods of 30–240 days orbit
  fewer than about 1.3% of these pulsars** (95% confidence). This holds even
  if every search needed three times the amplitude its saved curve claims.
- **Earth-mass planets (1 M⊕ or more) at 30–240 days orbit fewer than about
  2%** if the published noise models are right, and fewer than about 5% with
  the threefold allowance.
- **At 240–400 days** the limit is 2–3% for 10 M⊕ or more (137 pulsars reach
  that far).
- **Beyond 400 days** only about 20 pulsars were searched, so the limit is
  weak: fewer than about 15–17%. The long-period curves are also the least
  trustworthy (see limits below).

Masses are minimum masses (m sin i) for a 1.4 M☉ pulsar.

## Tables

Each cell: 95% upper limit on the fraction of pulsars hosting such a
companion, with the effective number of pulsars covering that cell in
brackets. "—" means too few pulsars to state a limit.

**Saved curves as they stand (margin 1).**

| Period (days) | 0.03 M⊕ | 0.1 M⊕ | 0.3 M⊕ | 1 M⊕ | 3 M⊕ | 10 M⊕ | 100 M⊕ |
|---|---:|---:|---:|---:|---:|---:|---:|
| 30–60 | 12.3% (24) | 10.1% (30) | 5.6% (55) | 2.2% (140) | 1.3% (232) | 1.2% (264) | 1.2% (271) |
| 60–120 | 11.9% (25) | 8.8% (34) | 4.1% (76) | 1.7% (188) | 1.3% (249) | 1.2% (266) | 1.2% (271) |
| 120–240 | 12.4% (24) | 8.7% (35) | 3.4% (91) | 1.5% (203) | 1.3% (245) | 1.2% (257) | 1.2% (259) |
| 240–400 | 17.4% (17) | 13.5% (22) | 6.3% (49) | 2.8% (110) | 2.4% (131) | 2.3% (137) | 2.3% (137) |
| 400–1,000 | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) |
| 1,000–2,000 | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) |

**Every curve multiplied by three (margin 3).** This allows for the extra
amplitude a noise-fitting second stage needs; the measured cost was 1.2–1.5
times at short periods and 2–10 times beyond about 450 days on quiet pulsars.

| Period (days) | 0.03 M⊕ | 0.1 M⊕ | 0.3 M⊕ | 1 M⊕ | 3 M⊕ | 10 M⊕ | 100 M⊕ |
|---|---:|---:|---:|---:|---:|---:|---:|
| 30–60 | 13.7% (22) | 12.2% (24) | 10.1% (30) | 5.3% (58) | 2.2% (140) | 1.3% (236) | 1.2% (270) |
| 60–120 | 12.9% (23) | 11.9% (25) | 8.8% (34) | 3.7% (84) | 1.7% (188) | 1.2% (251) | 1.2% (270) |
| 120–240 | 13.5% (22) | 12.4% (24) | 8.7% (35) | 3.2% (99) | 1.5% (203) | 1.3% (247) | 1.2% (258) |
| 240–400 | 18.7% (16) | 17.4% (17) | 13.5% (22) | 5.6% (56) | 2.8% (110) | 2.4% (132) | 2.3% (137) |
| 400–1,000 | 15.4% (19) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) |
| 1,000–2,000 | 18.1% (16) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) |

## How it is computed

- Source: `outputs/sensitivity-atlas-20260909/atlas.json` (342 dataset
  searches, 273 pulsars; SHA-256 `7d9a447c24c6fc20…`). Each curve is
  the minimum mass detected with 95% probability at the worst orbital phase.
- A pulsar counts toward a cell over the fraction of the period bin where its
  best curve is at or below the mass. Masked or unsearched periods do not
  count.
- A hosting fraction f is excluded when the chance of no detection anywhere,
  ∏(1 − 0.95 f cᵢ), falls below 5%.
- The seven datasets whose fixed-noise search crossed its threshold are left
  out (not counted as clean, not counted as detections); 2 pulsars drop out
  as a result. All ten crossings recorded so far fell below the second-stage
  threshold.

## Limits

- Margin 1 assumes each published noise model is correct. It is not a
  second-stage result; only ten targets have been through the second stage.
- Circular orbits on the searched period grids only. Most searches cover
  30–400 days.
- The pulsars are not a random sample: they were selected as isolated, with
  enough span and epochs. Most are young pulsars (MeerTime, UTMOST: 276 of the 342
  dataset searches); the sub-Earth-mass cells rest on the 25–35 most
  precisely timed pulsars, mainly from the timing-array releases.
- Unknown inclination means true masses are larger than the minimum mass.
- This is a sensitivity-based limit, not a posterior or an occurrence-rate
  measurement.

## Evidence

`results/research/population-limits-20261119/population-limits.json`,
computed by `tools/recherche population-limits --atlas … --out …`
(`tools/population_limits.py`, `tests/test_population_limits.py`).

## Update 2026-11-20: the 18 MeerKAT binaries added

**Owner instruction "Yes update it". Computed from saved results; no
observations read, no search run.** The 18 MeerKAT binaries searched for an
outer body (batches [01](MPTA_BINARY01_2026-11-19.md),
[02](MPTA_BINARY02_2026-11-19.md), [03](MPTA_BINARY03_2026-11-20.md),
[04](MPTA_BINARY04_2026-11-20.md); all `NO_TRIGGER`) are added to the 271
isolated pulsars: 289 pulsars in all. The isolated-only tables above are
unchanged and reproduce exactly.

What changes:

- **Sub-Earth masses, 60–240 days: the limit tightens by about a third.**
  At 0.1 M⊕ it goes from about 8.7% to 6.2–6.6%; at 0.03 M⊕ from about 12%
  to about 8%. These cells rested on the 25–35 most precise pulsars, and
  the binaries add 12–15 more.
- **Earth mass and above: almost no change** (10 M⊕ at 30–240 days: 1.2–1.3%
  → 1.1–1.2%). Those cells were already covered by about 250 pulsars.
- **30–60 days and 240–400 days gain less**: only 7–8 of the 18 binaries
  cover those ranges (inner-orbit harmonics exclude short periods for some;
  cells above about 300 days were not eligible).
- **Beyond 400 days: no change.** No binary search reached that far.

**All 289 pulsars, saved curves as they stand (margin 1).**

| Period (days) | 0.01 M⊕ | 0.03 M⊕ | 0.1 M⊕ | 0.3 M⊕ | 1 M⊕ | 3 M⊕ | 10 M⊕ | 100 M⊕ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 30–60 | 11.2% (27) | 9.5% (32) | 8.1% (37) | 5.0% (62) | 2.1% (148) | 1.3% (240) | 1.2% (272) | 1.1% (278) |
| 60–120 | 8.6% (35) | 8.1% (37) | 6.6% (47) | 3.5% (89) | 1.6% (200) | 1.2% (261) | 1.1% (278) | 1.1% (283) |
| 120–240 | 8.3% (37) | 7.9% (39) | 6.2% (50) | 2.9% (106) | 1.4% (218) | 1.2% (260) | 1.2% (272) | 1.1% (274) |
| 240–400 | 13.1% (23) | 12.5% (24) | 10.3% (30) | 5.5% (56) | 2.7% (117) | 2.3% (139) | 2.2% (144) | 2.2% (145) |
| 400–1,000 | 15.4% (19) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) |
| 1,000–2,000 | 18.1% (16) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) |

**All 289 pulsars, every curve multiplied by three (margin 3).**

| Period (days) | 0.01 M⊕ | 0.03 M⊕ | 0.1 M⊕ | 0.3 M⊕ | 1 M⊕ | 3 M⊕ | 10 M⊕ | 100 M⊕ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 30–60 | 18.2% (16) | 11.2% (27) | 9.5% (32) | 8.1% (37) | 4.7% (66) | 2.1% (148) | 1.3% (244) | 1.1% (277) |
| 60–120 | 13.5% (22) | 8.6% (35) | 8.1% (37) | 6.6% (47) | 3.2% (96) | 1.6% (200) | 1.2% (264) | 1.1% (282) |
| 120–240 | 10.5% (29) | 8.3% (37) | 7.9% (39) | 6.2% (50) | 2.7% (114) | 1.4% (218) | 1.2% (262) | 1.1% (273) |
| 240–400 | 14.7% (21) | 13.1% (23) | 12.5% (24) | 10.3% (30) | 4.9% (63) | 2.7% (117) | 2.2% (140) | 2.2% (145) |
| 400–1,000 | 15.5% (19) | 15.4% (19) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) | 14.7% (20) |
| 1,000–2,000 | 19.3% (15) | 18.1% (16) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) | 17.1% (17) |

**The 18 binaries alone (margin 1).** An outer body at any mass from 0.03 M⊕
up orbits fewer than about 35% (30–60 d), 23% (60–120 d), 20% (120–240 d)
and 40% (240–400 d) of them. Eighteen pulsars cannot say more than that.

Things to know:

- **Two different populations are being added together.** Isolated pulsars
  (mostly young) and millisecond pulsars with a white-dwarf or very
  low-mass companion have different histories. The combined figure is a
  limit on "pulsars searched by this project", not on one physical class.
- Binary masses assume a total inner mass of 1.6 M☉ (isolated: 1.4 M☉), for
  a body orbiting the inner pair; they scale as that mass to the power 2/3.
- The binary curves are fixed-noise, first-stage sensitivities, like the
  atlas; margin 3 is the cautious reading.
- Not included: the NANOGrav binaries searched in September and November
  (their curves are not in the atlas format), and the 14 held MeerKAT
  binaries, which were not searched.

Evidence: `results/research/population-limits-20261120/`
(`binary-curves.json` from `tools/binary_curves.py`; `population-limits.json`
from `tools/recherche population-limits --atlas … --extra …`, which holds the
combined, isolated-only and binaries-only tables). Tests:
`tests/test_binary_curves.py`, `tests/test_population_limits.py`.

## Update 2026-11-21: all 43 binary searches added

**Owner instruction "Yes update it". Computed from saved results; no
observations read, no search run.** Added since the 20 November update:
seven NANOGrav binaries ([batch](NG15_BINARY01_2026-11-20.md)) and the
eighteen Parkes and European ones ([batch](PTA_BINARY01_2026-11-21.md)).
The binary set is now 43 searches of 39 pulsars, all `NO_TRIGGER`; with the
271 isolated pulsars that is **310 pulsars**. The isolated-only tables
reproduce exactly. This table supersedes the 20 November one.

What changes against 20 November (289 pulsars):

- **Long periods improve most.** 400–1,000 days: 14.7% → **8.8%**;
  1,000–2,000 days: 17.1% → **9.5%**, at every mass from 0.03 M⊕ up. The
  number of pulsars covering those ranges goes from about 20 to about 33.
- **Sub-Earth masses at 60–240 days** tighten again: 0.1 M⊕ from 6.2–6.6%
  to 4.9–5.6%.
- **240–400 days**: 0.1 M⊕ from 10.3% to 7.7%; 10 M⊕ from 2.2% to 2.0%.
- **Earth mass and above at 30–240 days**: essentially unchanged
  (1.1–1.5% for 3 M⊕ and up).

**All 310 pulsars, saved curves as they stand (margin 1).**

| Period (days) | 0.01 M⊕ | 0.03 M⊕ | 0.1 M⊕ | 0.3 M⊕ | 1 M⊕ | 3 M⊕ | 10 M⊕ | 100 M⊕ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 30–60 | 9.9% (30) | 8.4% (36) | 7.3% (42) | 4.6% (67) | 2.0% (152) | 1.3% (244) | 1.1% (276) | 1.1% (283) |
| 60–120 | 7.1% (43) | 6.7% (46) | 5.6% (55) | 3.2% (97) | 1.5% (208) | 1.2% (270) | 1.1% (287) | 1.1% (291) |
| 120–240 | 6.1% (50) | 5.9% (52) | 4.9% (63) | 2.6% (119) | 1.4% (231) | 1.1% (273) | 1.1% (285) | 1.1% (287) |
| 240–400 | 9.2% (33) | 8.9% (34) | 7.7% (40) | 4.7% (67) | 2.5% (127) | 2.1% (149) | 2.0% (155) | 2.0% (155) |
| 400–1,000 | 9.1% (33) | 8.8% (34) | 8.8% (34) | 8.8% (34) | 8.8% (34) | 8.8% (34) | 8.8% (34) | 8.8% (34) |
| 1,000–2,000 | 9.8% (31) | 9.5% (32) | 9.5% (32) | 9.5% (32) | 9.5% (32) | 9.5% (32) | 9.5% (32) | 9.5% (32) |

**All 310 pulsars, every curve multiplied by three (margin 3).**

| Period (days) | 0.01 M⊕ | 0.03 M⊕ | 0.1 M⊕ | 0.3 M⊕ | 1 M⊕ | 3 M⊕ | 10 M⊕ | 100 M⊕ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 30–60 | 16.1% (18) | 9.9% (30) | 8.4% (36) | 7.3% (42) | 4.4% (70) | 2.0% (152) | 1.3% (248) | 1.1% (282) |
| 60–120 | 10.8% (28) | 7.1% (43) | 6.7% (46) | 5.6% (55) | 3.0% (105) | 1.5% (208) | 1.2% (272) | 1.1% (290) |
| 120–240 | 7.6% (40) | 6.1% (50) | 5.9% (52) | 4.9% (63) | 2.5% (127) | 1.4% (231) | 1.1% (275) | 1.1% (286) |
| 240–400 | 10.0% (31) | 9.2% (33) | 8.9% (34) | 7.7% (40) | 4.3% (73) | 2.5% (127) | 2.1% (150) | 2.0% (155) |
| 400–1,000 | 9.1% (33) | 9.1% (33) | 8.8% (34) | 8.8% (34) | 8.8% (34) | 8.8% (34) | 8.8% (34) | 8.8% (34) |
| 1,000–2,000 | 10.1% (30) | 9.8% (31) | 9.5% (32) | 9.5% (32) | 9.5% (32) | 9.5% (32) | 9.5% (32) | 9.5% (32) |

**The 39 binaries alone (margin 1).** An outer body of 0.03 M⊕ or more
orbits fewer than about 24% (30–60 d), 14% (60–120 d), 11% (120–240 d),
17% (240–400 d), 20% (400–1,000 d) and 19% (1,000–2,000 d) of them.

Things to know, in addition to the 20 November notes (two populations
combined; 1.6 M☉ inner mass; fixed-noise first-stage curves):

- **The long-period figures are the least robust.** Margin 3 was chosen
  from short-period experience; the measured cost of fitting noise was 2
  to 10 times beyond about 450 days on quiet pulsars. Read the 8.8% and
  9.5% as "if the released noise models are right".
- A pulsar searched in several releases counts once, through its best
  curve at each period.
- Four of the binary searches cover only a handful of trial periods
  (J0614−3329, J2302+4442, Parkes J0900−3144 and J1643−1224); they add
  almost nothing and are included as they are.
- Still not included: the NANOGrav binaries searched in September and by
  the nonlinear method in November (curves in a different format).

Evidence: `results/research/population-limits-20261121/`
(`binary-curves.json`, `population-limits.json`).
