# White-dwarf binary pilot 01 — 9 September 2026

The owner authorized the post-release sequence, including a small binary pilot.
The selection was fixed before looking at observed periodograms:
J0613−0200, J1614−2230 and J1909−3744 from NANOGrav 15-year v2.1.0 wideband.
All use published ELL1 timing models and have white-dwarf companions. The original
single-pulsar inventory excluded these targets, and none had a registered search.

Inputs are copied from the existing release archive and checked against the
pinned PAR/TIM intake hashes. The adapter retains released timing/noise parameters,
joint TOA/DM covariance, precision binding and offline resources. All free binary,
spin, astrometric, DM and instrumental columns are projected together. This
accounts for orbital uncertainty in the local linear approximation; it is not
an exact nonlinear triple-system inference.

Search bounds: max(30 days, 10 inner binary periods) to min(2000 days, half the
observation span), circular outer orbits. The three-target conditional 1% allowance
is retained even when a selected target is held. It does not become a two-target
allowance. The period-ratio cut selects hierarchical orbits but does not prove
dynamical stability or model short-term three-body interactions.

## Preparation diagnosis and repair

J0613−0200's three-sigma SINI interval enters a strongly nonlinear Shapiro-delay
regime: the Taylor remainder reaches 6.79 TOA standard deviations. Its first
attempt is retained as a hold; no observed search is permitted under this local
linear approximation. This is a model limitation, not a failed planet detection.

J1614−2230 exposed a derivative mismatch of about 0.001161 relative. Increasing
the finite-difference step by factors up to 1000 left it unchanged, ruling out
the initial numerical-cancellation explanation. Inspection of the pinned
[PINT 1.1.5 ELL1 implementation](https://raw.githubusercontent.com/nanograv/PINT/1.1.5/src/pint/models/stand_alone_psr_binaries/ELL1_model.py)
identified a missing cosine factor in the orbital-phase derivative of Shapiro
delay. For ΔS = −2r ln(1 − s sin φ), the correct phase derivative is
2rs cos φ / (1 − s sin φ).

`tools/binary_wideband.py` binds the corrected derivative only to the pilot model
instance, including fitter copies. The forward delay, installed PINT package,
qualified scanner and historical single-pulsar source are unchanged. Both failed
J1614 attempts remain preserved. The repaired preparation checks all eight free
binary derivatives, coordinate-wise three-sigma local linearity, full joint rank,
phase connection and fitted orbital shifts within the checked neighborhood.

Thresholds are not relaxed to accommodate failures. Calibrations use 4096 nulls
per compatible target, with the existing analytic union-bound floor. A bounded
three-period/two-phase injection diagnostic checks the new projected model.

## Operating procedure

Use the pinned Intel environment and the offline operator wrapper:

```sh
tools/recherche binary-pilot prepare --data "$DATA" --target J1614-2230
tools/recherche binary-pilot calibrate --data "$DATA"
tools/recherche binary-pilot freeze --data "$DATA"
tools/recherche binary-pilot run --data "$DATA" --target J1614-2230
```

Selection is an immutable pilot-specific list, not a general binary survey.
Use `select --help` for the archive/intake arguments. Do not rerun consumed
targets. Register each result in the master from saved evidence, including holds
and stopped attempts; review any valid compelling crossing before stronger claims.
Original full inputs and attempts live under the external `binary-pilot01-20260909`
data directory. Terminal evidence and final closeout are appended below.

## Terminal closeout

| Target | Search period, days | Strongest peak, days | Δχ² / threshold | Outcome |
|---|---:|---:|---:|---|
| J0613−0200 | Not searched | — | — | HELD: nonlinear Shapiro uncertainty |
| J1614−2230 | 86.866–2,000 | 765.367 | 12.694 / 22.318 | NO_TRIGGER |
| J1909−3744 | 30–2,000 | 33.767 | 11.278 / 25.099 | NO_TRIGGER |

Both observed results pass the independent full-design likelihood comparison.
Null reduced χ² is 0.967 and 1.012 respectively; neither has a noise-adequacy flag.
These are two searches for additional circular companions around pulsar–white-dwarf
systems, not attempts to rediscover their known inner white dwarfs. No new planet
is confirmed. Each run01 destination is consumed, and no job remains active.

The calibrations contain 8,192 null simulations total. The separate bounded
injection diagnostic recovered 90/96 and 91/96 injected signals; noiseless amplitude
errors were below 2e-15 relative. These are simulated checks on actual sampling,
not observed detections or a measured population occurrence rate. Median saved
worst-phase 95%-detection amplitudes are 0.335 and 0.0630 microseconds. The annual
masks exclude ten and eleven grid cells respectively.

J1909's first preparation exposed an unbound VLA clock. The adapter now reads
`vla2gps.clk` from the same pinned NG15 archive as a TEMPO2 UTC(VLA)-to-GPS
correction, retaining the existing GPS/BIPM2019 chain. The exact clock hash is in
its preparation receipt. Its failed attempt is preserved. Both compatible targets
were prepared against the final adapter before calibration and observed execution.
The selection command extracts and binds this clock for a fresh authorized pilot.

Saved [closeout and artifact hashes](../results/observed/binary-pilot01-20260909/closeout.json)
include unchanged results/periodograms, final preparation receipts, selection,
clock binding and retained preparation failures. Freeze and calibration-preparation
views replace local cache paths with relative paths and explicitly retain the
original SHA-256; the original frozen bytes remain external. The original fixed
noise models and qualified scanner were not changed.

The master was updated after each observed run. The operator wrapper now invokes
the portable closeout backend after `binary-pilot run`; it copies unchanged result
and periodogram evidence into the repository and registers the saved terminal
result. If bookkeeping fails, retry only:

```sh
RECHERCHE_WORKBOOK_BACKEND=portable tools/recherche master-workbook "$DATA" --binary-observed
```

Preparation holds are registered separately as work-log records, not nondetections.
Expanding the target list or implementing nonlinear Shapiro marginalization is
future work. The isolated-pulsar atlas remains its original 342-curve snapshot;
binary sensitivities are separate because their mass conversion requires the
inner system's total mass.
