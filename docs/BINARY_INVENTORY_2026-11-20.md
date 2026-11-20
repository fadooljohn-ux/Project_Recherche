# Binaries in the timing-array releases on disk: what the current tools could take

**20 November 2026. Owner instruction "Do both" (inventory of binaries on
disk; research on new public data, recorded separately in
[NEW_DATA_SOURCES_2026-11-20.md](NEW_DATA_SOURCES_2026-11-20.md)).
Par files (timing models) only were read: no TOAs, no residuals, nothing
prepared, calibrated or searched. This is a proposal list, not an approved
target list.**

## What was done

Every par file with a `BINARY` line in five releases already on disk was
screened against what the binary search can now do: ELL1-type orbits
directly; nearly circular DD-type orbits through the
[re-expression](ORBIT_REEXPRESSION_2026-11-20.md); free Shapiro parameters
through the [Shapiro basis](SHAPIRO_BASIS_2026-11-20.md).

## Result

| Release | Binaries | Orbit form the tools take as written | Take with the two November treatments | Need a model translation first | Blocked |
|---|---:|---:|---:|---:|---:|
| NANOGrav 15-year (wideband) | 50 | 11 | 28 | 1 | 10 |
| PPTA DR3 | 23 | 5 | 1 | 11 | 6 |
| EPTA DR2 (full) | 16 | 0 | 1 | 10 | 5 |
| IPTA DR2 (version B) | 44 | 3 | 6 | 25 | 10 |
| InPTA DR2 | 19 | 0 | 0 | 0 | 19 |

Across the releases there are **71 different binary pulsars**:

- **62 pass the screen in at least one release.** Of these, **44 have
  never been searched by this project** and 18 have (in MeerKAT or NANOGrav
  data).
- Of the 44 new ones, **30 pass in a release that needs no model
  translation** (25 of them in NANOGrav 15-year), and 9 need no new
  treatment at all.
- **30 of the 44 would reach beyond 1,000 days and 17 beyond 2,000 days**
  (rough upper bound: half the data span). That is the range where the
  current population limit is weakest.
- **9 are blocked in every release**: J1713+0747, J1017−7156 and
  J2241−5236 (extra orbital terms); J0636+5128 and J1705−1903 (black
  widows, orbital-period derivatives); J1903+0327, J1946+3417, J2234+0611
  and J0621+1002 (eccentric orbits).

"Model translation" means the release writes the orbit in tempo2's general
`T2` model (73 of the 152 par files) or `BT`. The parameters inside are
the same ELL1-type or DD-type ones; a translation step with an equivalence
check, like the re-expression, would be needed. It is not built.

InPTA DR2 is blocked throughout because its par files hold the orbital
parameters fixed; the search needs them fitted.

## Limits of this screen

- **It is a model-level screen.** In the MeerKAT list, 14 of 32 targets
  that looked compatible were held at preparation. Expect holds here too,
  especially for the Shapiro and re-expression classes.
- **Only the MeerKAT binary tool carries the two November treatments.**
  NANOGrav has a binary adapter from September, without them. PPTA, EPTA
  and IPTA have adapters for isolated pulsars only. Each release needs its
  noise model and clock chain wired into the binary procedure, with tests,
  before any preparation.
- **PPTA DR3 TOA files for the binaries are not on disk** (only the eight
  isolated pulsars' were fetched in September). Getting them is a download
  and so the owner's decision.
- **IPTA DR2 is not independent** of EPTA, PPTA and NANOGrav 9-year data;
  it combines them. A pulsar should be searched in one of the overlapping
  sets, not each.
- Period ranges are rough: lower end the larger of 30 days and ten inner
  periods (as in the MeerKAT batches), upper end half the span. Real
  eligible ranges will be narrower.
- "Searched before" comes from the master workbook (Searches sheet plus
  targets marked as searched once).

## The 44 new pulsars (best release for each)

Classes: N as written; R re-expression; S Shapiro basis; T model
translation. Periods in days, rough.

| Pulsar | Best release | Class | Rough outer periods |
|---|---|---|---|
| J0023+0923 | IPTA DR2 | N | 30–421 |
| J0034−0534 | IPTA DR2 | T | 30–2,469 |
| J0218+4232 | IPTA DR2 | T | 30–3,209 |
| J0406+3039 | NANOGrav 15 | N | 70–651 |
| J0437−4715 | NANOGrav 15 | R | 57–868 |
| J0605+3757 | NANOGrav 15 | R | 557–615 |
| J0610−2100 | IPTA DR2 (NANOGrav 15: N, 30–615) | T | 30–1,262 |
| J0614−3329 | PPTA DR3 | T+R+S | 536–582 |
| J0709+0458 | NANOGrav 15 | R | 44–834 |
| J0751+1807 | EPTA DR2 | T+S | 30–4,417 |
| J0900−3144 | EPTA DR2 (PPTA DR3: N, 187–509) | T | 187–2,492 |
| J1012−4235 | NANOGrav 15 | R+S | 380–614 |
| J1022+1001 | NANOGrav 15 | R | 78–1,014 |
| J1045−4509 | PPTA DR3 | T | 41–3,301 |
| J1125−6014 | PPTA DR3 | T+S | 88–2,593 |
| J1312+0051 | NANOGrav 15 | T+R | 385–833 |
| J1446−4701 | PPTA DR3 | T | 30–2,026 |
| J1455−3330 | NANOGrav 15 | R | 762–2,862 |
| J1545−4550 | PPTA DR3 | N | 62–1,980 |
| J1600−3053 | NANOGrav 15 | R+S | 143–2,278 |
| J1603−7202 | PPTA DR3 | T | 63–3,302 |
| J1630+3734 | NANOGrav 15 | R+S | 125–632 |
| J1640+2224 | NANOGrav 15 | R+S | 1,755–2,825 |
| J1643−1224 | IPTA DR2 | T+R | 1,470–3,678 |
| J1741+1351 | NANOGrav 15 (PPTA DR3: N, 163–467) | S | 163–1,653 |
| J1745+1017 | NANOGrav 15 | N | 30–830 |
| J1751−2857 | EPTA DR2 | T+R | 1,107–2,683 |
| J1802−2124 | IPTA DR2 (NANOGrav 15: N, 30–631) | T+S | 30–1,322 |
| J1804−2717 | EPTA DR2 | T | 111–2,690 |
| J1811−2405 | NANOGrav 15 | S | 63–631 |
| J1853+1303 | NANOGrav 15 | R+S | 1,157–1,647 |
| J1902−5105 | PPTA DR3 | S | 30–520 |
| J1910+1256 | EPTA DR2 | T+R | 585–2,779 |
| J1911−1114 | IPTA DR2 | T | 30–1,606 |
| J1918−0642 | EPTA DR2 | R+S | 109–3,600 |
| J1949+3106 | IPTA DR2 | S | 30–228 |
| J1955+2908 | NANOGrav 15 | R | 1,173–1,652 |
| J2017+0603 | NANOGrav 15 | S | 30–1,520 |
| J2019+2425 | IPTA DR2 | T+R | 765–1,669 |
| J2033+1734 | IPTA DR2 | T+R | 563–1,446 |
| J2129−5721 | PPTA DR3 | T | 66–3,241 |
| J2214+3000 | IPTA DR2 | N | 30–378 |
| J2229+2643 | IPTA DR2 | T+R | 930–1,503 |
| J2302+4442 | NANOGrav 15 | R+S | 1,259–1,485 |

Several of these are MeerKAT binaries that are held or excluded there
(J1811−2405, J1751−2857, J1446−4701, J1012−4235, J1455−3330, J2229+2643):
another release may offer a form the tools can take.

The 18 already-searched pulsars also have longer records here (for example
J1909−3744 to about 3,300 days in PPTA DR3, J1012+5307 and J0613−0200 beyond
4,000 days in EPTA DR2). Those would be new searches of known targets at
longer periods, not new pulsars.

## Evidence

`results/research/binary-inventory-20261120/inventory.json` (every par file
with its class, blocker and rough range) and `config.json` (release paths,
searched list); `tools/binary_inventory.py`,
`tests/test_binary_inventory.py`.
