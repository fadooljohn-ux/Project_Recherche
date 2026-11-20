# Post-release science plan — 9 September 2026

The owner authorized the recommended sequence: sensitivity atlas, a small
pulsar–white-dwarf binary pilot, and pursuit of available follow-up observations.
Proceed through preparation, calibration and execution when the bounded adapter
checks pass. Preserve v0.1.0 and original results; no broad qualification rerun.

1. Build a dataset-separated atlas from existing, hash-verified periodograms and
   calibration curves. Retain masks, best/worst phase, conditional 95% detection
   definition and overlap. Convert amplitude to minimum companion mass assuming
   a 1.4-solar-mass isolated pulsar. Exclude invalid imports and separate known
   companion benchmarks. Do not claim population occurrence limits.
2. Implement a bounded NG15 PINT wideband binary adapter, initially ELL1 systems
   with white-dwarf companions. Select three using published binary properties,
   coverage and model support before examining their search periodograms.
   Preserve the released binary model and project its free derivatives jointly
   with timing/DM/instrument nuisance parameters. Check derivatives, local
   linearity and a bounded injected-signal recovery. Use one shared 1% conditional
   allowance and per-target calibration. Search only hierarchical circular outer
   orbits: minimum period max(30 days, 10 binary periods), maximum min(2000 days,
   half the observation span). This is a restricted additional-companion model,
   not arbitrary triple-system dynamics or a stability proof. Run each once when
   the adapter checks pass; review any valid compelling crossing.
3. Check public source availability for complete UTMOST-NS packages and independent
   candidate follow-up. Record specific gaps and useful requests. Do not send
   messages to researchers or create monitoring without separate authorization.

Update the canonical master after each closeout, including holds or failures.
Keep public-facing paths relative. New results remain on the local development
branch until their publication is authorized; the existing public release stays
unchanged.

## Closeout

All three steps are closed within available inputs: the isolated-target
[atlas](SENSITIVITY_ATLAS_2026-09-09.md) contains 342 curves from 273 identities;
the [binary pilot](BINARY_PILOT01_2026-09-09.md) completed two NO_TRIGGER searches
and one explicit model hold; the [follow-up check](FOLLOWUP_AVAILABILITY_2026-09-09.md)
did not resolve the external combined-timing input gap. The master preserves all
351 earlier Search rows and adds two new rows. No science job is active.
