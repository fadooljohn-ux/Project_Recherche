# What remains to search in public data

**19 November 2026. Owner instruction "Proceed with the three steps you've
outlined" (step 2: widen the search across public data; a ranked list is
proposed for approval before anything is searched). Inventory only: no
preparation, calibration or search was run.**

## Correction

The earlier remark that only "a handful" of pulsars had been searched was
wrong. The workbook holds 360 search records on 286 pulsars. Every source in
the [source queue](FUTURE_DATA_SOURCES.md) has had its eligible
isolated-pulsar pool searched: MeerTime 191, UTMOST 85, MeerKAT timing array
18, NANOGrav 17, IPTA 14, EPTA 8, Parkes 7, InPTA 3. There is no untouched
pool of isolated pulsars left in the data on disk.

## What is left

| Group | Pulsars | Why not searched | What it would take |
|---|---:|---|---|
| MeerKAT timing array, known binaries, no other exclusion | 32 | The isolated-pulsar search does not model an orbit | The binary procedure used for the NANOGrav white-dwarf binaries (inner orbit fitted, outer period searched), then the second stage for any crossing |
| MeerKAT timing array, binaries with published scattering or chromatic structure | 23 | As above, plus extra chromatic terms | As above plus chromatic support; lower priority |
| NANOGrav 15-year binaries | about 22 | Orbit models not supported (12 DD, 1 BT), missing orbital terms (5), black widows (3), inclination outside range (2) | New model support for each class |
| MeerTime, UTMOST exclusions | about 400 | Too short or too few epochs, glitches | New data releases; nothing to do now |
| UTMOST-NS | 11 | Combined timing inputs not available | Inputs from the observers |

Counts are from the Targets sheet of the master workbook.

## Proposed first batch (for approval; nothing has been run)

The 32 MeerKAT binaries with no other exclusion, ranked by timing precision.
All have 3.5–4.5 years of data, so the outer-period search would cover about
30–400 days. They are millisecond pulsars, so each would reach well below an
Earth mass and would add to the cells of the
[population limit](POPULATION_LIMITS_2026-11-19.md) that currently rest on
the fewest pulsars.

| Rank | Pulsar | Precision proxy (µs) | Epochs | Span (years) | Published red noise |
|---:|---|---:|---:|---:|---|
| 1 | J1909−3744 | 0.01 | 232 | 4.5 | no |
| 2 | J2241−5236 | 0.02 | 107 | 4.4 | no |
| 3 | J0125−2327 | 0.05 | 101 | 4.3 | no |
| 4 | J1811−2405 | 0.05 | 197 | 4.3 | no |
| 5 | J1216−6410 | 0.07 | 102 | 4.4 | no |
| 6 | J1614−2230 | 0.08 | 99 | 4.3 | no |
| 7 | J2145−0750 | 0.12 | 96 | 4.3 | no |
| 8 | J1446−4701 | 0.12 | 97 | 4.4 | no |
| 9 | J1946−5403 | 0.14 | 91 | 4.0 | no |
| 10 | J1903−7051 | 0.15 | 109 | 4.4 | no |
| 11 | J1125−5825 | 0.15 | 102 | 4.4 | no |
| 12 | J1732−5049 | 0.15 | 147 | 4.5 | no |
| 13 | J1036−8317 | 0.16 | 94 | 4.1 | no |
| 14 | J2234+0944 | 0.18 | 91 | 3.7 | yes |
| 15 | J1933−6211 | 0.20 | 127 | 4.4 | no |
| 16 | J1435−6100 | 0.20 | 127 | 4.4 | no |
| 17 | J1012−4235 | 0.23 | 104 | 4.3 | no |
| 18 | J2317+1439 | 0.25 | 91 | 3.7 | yes |
| 19 | J1751−2857 | 0.25 | 95 | 4.3 | no |
| 20 | J0101−6422 | 0.26 | 55 | 3.8 | no |
| 21 | J2322−2650 | 0.26 | 76 | 3.8 | no |
| 22 | J1101−6424 | 0.26 | 116 | 4.3 | no |
| 23 | J1547−5709 | 0.30 | 95 | 4.2 | no |
| 24 | J2039−3616 | 0.30 | 96 | 4.0 | no |
| 25 | J1455−3330 | 0.30 | 97 | 4.3 | yes |
| 26 | J1653−2054 | 0.33 | 85 | 4.3 | no |
| 27 | J1514−4946 | 0.33 | 59 | 3.6 | no |
| 28 | J1719−1438 | 0.33 | 100 | 4.3 | no |
| 29 | J1543−5149 | 0.34 | 99 | 4.4 | no |
| 30 | J2229+2643 | 0.36 | 89 | 3.7 | yes |
| 31 | J1327−0755 | 0.41 | 74 | 3.5 | no |
| 32 | J2236−5527 | 0.45 | 68 | 4.3 | yes |

Notes:

- J2145−0750 and J2317+1439 were already searched once in NANOGrav data;
  MeerKAT data would be an independent telescope for them. J1719−1438 and
  J2322−2650 host known planetary-mass companions and were used as recovery
  benchmarks.
- Orbit model types were not read for this list. Each target must first pass
  the binary procedure's compatibility check; some will be held, as happened
  with the NANOGrav binaries.
- Under the standing rules each target gets one pre-declared, frozen search;
  any fixed-noise crossing then goes once through the second stage.

Approved by the owner on 19 November 2026 ("I approve the MeerKat binary list.
Start on the most precise targets."). The first six were taken up in
[batch 01](MPTA_BINARY01_2026-11-19.md): two searched, four held; the other 26 in
[batch 02](MPTA_BINARY02_2026-11-19.md): five searched, 21 held. Note that
J1909−3744 and J1614−2230 were also searched once in NANOGrav data in September.

## Evidence

`../Project Recherche Data/mpta-batch01-20260908/selection.json` (inventory
rows with exclusion reasons and precision proxy); master workbook Targets
sheet.

## Update 2026-11-20

The [orbit re-expression](ORBIT_REEXPRESSION_2026-11-20.md) is built. In a
development check (no search) it clears J1933−6211 and J2322−2650; the other
five near-circular targets remain held for Shapiro-delay or period-range
reasons. Searching the two needs a new owner instruction.

[Batch 03](MPTA_BINARY03_2026-11-20.md) (owner: "Yes search both") searched
those two: both `NO_TRIGGER`. The approved list stands at 9 searched, 23 held.

The [nonlinear Shapiro treatment](SHAPIRO_BASIS_2026-11-20.md) is built. In a
development check (no search) it clears nine of the twelve Shapiro-held
targets; searching them needs a new owner instruction.

[Batch 04](MPTA_BINARY04_2026-11-20.md) (owner: "Yes search all 9.") searched
those nine: all `NO_TRIGGER`. The approved list stands at 18 searched, 14 held.
