# Sensitivity atlas — 9 September 2026

The first atlas is complete: **342 valid dataset searches across 273 pulsars**.
It reuses saved, hash-verified curves and performs no observed searches or new
calibrations. The canonical workbook records the closeout.

- [Interactive atlas](../outputs/sensitivity-atlas-20260909/index.html)
- [Overview figure](../outputs/sensitivity-atlas-20260909/sensitivity-overview.png)
- [All grid cells, compressed CSV](../outputs/sensitivity-atlas-20260909/sensitivity-cells.csv.gz)
- [Machine-readable provenance](../outputs/sensitivity-atlas-20260909/summary.json)

Each curve retains the dataset/run ID, original result and periodogram hashes,
calibration key, threshold scope, masks, noise flag and best/worst orbital phase.
Sensitivity means conditional 95% detection probability at an eligible injected
grid frequency, for a circular signal under the supplied fixed noise and linear
timing model. It does not include off-grid, eccentric or noise-model uncertainty.

The minimum-mass conversion assumes an isolated 1.4-solar-mass pulsar and sin(i)=1.
It solves the exact Kepler mass function using the projected orbital radius cA.
It was checked by reconstructing timing amplitudes from known masses across
terrestrial and giant-companion scales. Unknown inclination allows larger true
mass. These are detection sensitivities, not posterior mass upper limits.

All three superseded EPTA imports are excluded, including the invalid J1911+1347
nondetection. The four known-system benchmark identities and their five records,
plus the original B1937 legacy search, have no standard saved curve and are
listed separately. B1937/J1939 still appears through later compatible datasets.
The atlas's 273 identities plus four benchmark identities reconcile to the
277 observed identities in the release register.

Dataset overlap remains explicit: curves for the same pulsar are not independent
trials or confirmations. No population occurrence limit is inferred. A future
survey paper needs comparison with existing surveys and additional completeness
and selection accounting.

To rebuild from original evidence-bound local records:

```sh
.pixi/envs/default/bin/python tools/sensitivity_atlas.py \
  --master "$ORIGINAL_MASTER" --output "$NEW_ATLAS_DIRECTORY"
```

The original master points to preserved original result/periodogram bytes.
Publication derivatives retain original hashes but cannot replace those bytes
for this reconstruction. The distributed atlas itself is self-contained and
can be explored without the private archive.
