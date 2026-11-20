# Other public pulsar-timing data: what could be added

**20 November 2026. Web research by a subagent on the owner's instruction
("Do both"). Nothing was downloaded into the project and no contact was
made. The recording agent did not re-check the sources; items the subagent
could not verify are marked. Any download or request is the owner's
decision.**

## Finding

There is no large, ready-to-use release of arrival times and timing models
for pulsars beyond those already searched. What exists falls into three
kinds: small ready-made sets; large sets that would need arrival times
built from raw data; and large sets available only on request.

## Publicly downloadable now

| Data set | Pulsars, span | What is posted | Kind of pulsar | Use to us |
|---|---|---|---|---|
| Fermi-LAT gamma-ray timing array ([Zenodo 6374291](https://zenodo.org/record/6374291), arXiv:2204.05226) | 35, 12.5 years | Arrival times and timing models (file formats inside the archives not inspected); CC BY 4.0 | Millisecond pulsars, heavy overlap with ours | Independent telescope, no gaps; precision tens of microseconds, so only for Earth-mass-and-up limits at long periods |
| Fermi third pulsar catalogue ([data page](https://fermi.gsfc.nasa.gov/ssc/data/access/lat/3rd_PSR_catalog)) | about 294, up to 14 years | Timing models and photon files; **no arrival times** — they would have to be built from photons | Young (many radio-quiet) and millisecond | Many pulsars nobody times in radio; needs a new photon-to-arrival-time step |
| Parkes young-pulsar programme P574 (CSIRO Data Access Portal; Lower et al. 2021, arXiv:2109.07612) | about 260 monitored roughly monthly since 2007 | Raw folded observations only, per semester; no arrival-time release found | Isolated young pulsars | The largest untouched pool, but arrival times must be made from raw data: a large new pipeline |
| GBNCC survey discoveries ([GitHub](https://github.com/GBNCC/data); McEwen et al. 2024, arXiv:2312.07471) | 128 timed in the paper; about 23 seen in the listing | Timing models for all, arrival times for many but not all (not confirmed for the 128) | Mostly isolated slow pulsars | Ready-made and new to us; spans and precision to be checked |
| SUPERB V ([Zenodo 3900980](https://zenodo.org/records/3900980), arXiv:2006.13637) | 23 | Arrival times and timing models; CC BY 4.0 | Mostly isolated slow pulsars | Ready-made, small; spans likely short |
| LOFAR solar-wind set ([Zenodo 4247553](https://zenodo.org/records/4247553), Tiburzi et al. 2021) | not stated | Arrival times and timing models; CC BY 4.0 | Likely the timing-array millisecond pulsars | Independent low-frequency data; overlap to be checked |
| I-LOFAR ecliptic pulsars (Zenodo 10.5281/zenodo.14865192, arXiv:2505.09549) | 7, 2–3 years | Arrival times and timing solutions | 4 slow, 3 millisecond, including B1257+12 | Small; B1257+12 is already our benchmark |
| I-LOFAR 150 MHz (arXiv:2605.22516) | 17, 2020–2023 | Said to be on Zenodo; not confirmed | Slow pulsars | Small, unverified |
| IPTA DR1 ([GitLab](https://gitlab.com/IPTA/DR1)) | 2015 combination | Live | Millisecond | Superseded by IPTA DR2, which we hold |

## On request only, or not public

- **Jodrell Bank, about 800 pulsars** (Niţu et al. 2022, arXiv:2203.01136,
  itself a planet search): "available upon reasonable request". This is
  the single largest relevant data set.
- **Jodrell Bank 366-pulsar timing-noise sample** (Hobbs et al.): no public
  release found.
- **CHIME/Pulsar**: no public arrival-time release found.
- **FAST (CPTA DR1 and survey timing)**: arrival times not confirmed
  public; raw data open after a one-year proprietary period.
- **Nanshan 26-m** (87 pulsars, 2002–2014), **NenuFAR**, **EPTA
  low-frequency**, **MeerKAT Magellanic Cloud timing**: no public release
  found.
- Not found in this pass and not exhaustively checked: LOTAAS, AO327, GBT
  350 MHz drift, GMRT, Effelsberg, Hartebeesthoek, Mount Pleasant, MeerKAT
  globular clusters and relativistic binaries.
- Timing models only, no arrival times: PALFA (72 pulsars, Zenodo
  5646566), EPTA DR1 tables on VizieR.

## Forthcoming

- **NANOGrav 20-year**: described as forthcoming; no date.
- **IPTA DR3** (would combine EPTA, NANOGrav, PPTA, InPTA, MeerKAT and
  FAST) and **EPTA DR3** (about 60 pulsars, 24.5 years): not public; no
  date.
- **MeerKAT**: no timing release beyond those we hold was found.

## Reading

1. The quickest genuinely new pulsars are the small ready-made sets (GBNCC,
   SUPERB V): a few tens of slow pulsars, sensitivity of roughly Earth to
   Jupiter masses, to be checked for span before anything else.
2. The largest untouched pools (Parkes P574, Fermi) need arrival times
   built from raw data. That is a new, sizeable piece of engineering with
   its own validation.
3. The largest ready-made pool (Jodrell Bank, 800 pulsars) needs a request
   and has already been searched for planets by its owners.
4. For the precise millisecond pulsars, the binaries already on disk
   ([inventory](BINARY_INVENTORY_2026-11-20.md)) are the nearer step.

## Acquisition order (owner, 20 November 2026)

**Owner instruction: "Keep new sources in our back pocket and prioritize
future acquisition of said data by accessibility."** Nothing here is to be
acquired now. When the owner next authorizes an acquisition, take sources
in this order, easiest first; each step is a separate owner decision and
starts with an inventory, not a search.

| Order | Source | Access | What it takes |
|---:|---|---|---|
| 1 | Parkes PPTA DR3 arrival times for its binaries | Open repository already used for the isolated pulsars | Download only; feeds the [binary inventory](BINARY_INVENTORY_2026-11-20.md) |
| 2 | SUPERB V (Zenodo 3900980) | Open download, arrival times and models, CC BY 4.0 | Download; check spans and cadence |
| 3 | GBNCC discoveries (GitHub) | Open download; arrival times for many pulsars | Download; confirm which pulsars have arrival times and the licence |
| 4 | Fermi gamma-ray timing array (Zenodo 6374291) | Open download, CC BY 4.0 | Download; inspect formats; coarse precision |
| 5 | LOFAR solar-wind set, I-LOFAR sets (Zenodo) | Open download | Download; check overlap and spans |
| 6 | Fermi third pulsar catalogue | Open, but photons and models only | Build arrival times from photons: new pipeline and validation |
| 7 | Parkes young-pulsar programme P574 | Open, but raw observations only | Build arrival times from raw data: large new pipeline |
| 8 | Jodrell Bank (about 800 pulsars), CHIME, FAST, Nanshan and others | On request | A request written by the owner; outcome uncertain |
| 9 | NANOGrav 20-year, EPTA DR3, IPTA DR3 | Not yet released | Wait; re-check when announced |

Accessibility is the ordering rule, not scientific value: the largest pools
(7 and 8) are the hardest to reach.

## Caveats from the researcher

- Zenodo's search interface failed, so the Zenodo sweep relied on web
  search and is not exhaustive.
- Archive contents were confirmed by file name only.
- The fetch tool saved a copy of arXiv:2203.01136 to a temporary session
  folder outside the project; nothing else was downloaded.
