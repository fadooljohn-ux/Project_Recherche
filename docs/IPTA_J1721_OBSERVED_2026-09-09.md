# J1721−2457 IPTA observed search — 2026-09-09

The owner's **Launch** instruction authorized one observed search of the
previously prepared and calibrated J1721−2457 IPTA DR2 Version B dataset.
The search completed with **NO_TRIGGER**, no execution failure and no
noise-adequacy flag. This is a bounded null result, not evidence that the pulsar
has no planets.

| Quantity | Result |
|---|---:|
| Observed arrivals / observing days | 150 / 150 |
| Dataset span | 4,661.158711 days |
| Circular search range | 30–2,000 days |
| Grid cells / eligible cells | 767 / 760 |
| Strongest eligible period | 42.24720597 days |
| Peak Δχ² | 9.12410705 |
| Frozen threshold | 22.49531397 |
| Fitted peak timing amplitude | 6.78390710 µs |
| Null χ² / degrees of freedom | 134.54193571 / 137 |
| Reduced χ² | 0.98205792 |
| Independent full-design post-fit χ² | 125.41782866 |

The fixed released white/red/DM covariance and all 13 timing columns are from
the compatible attempt03 preparation. The original calibration was reused
without new null simulations or threshold adjustment. Its seven masked annual
grid cells remain excluded, and its conditional 1% allowance applies to this
one fixed grid under the assumed Gaussian noise model. No unmasked alternative
search was performed. The peak does not warrant a candidate deep review.

Median worst-phase 95% on-grid timing sensitivity is 14.926488 µs, ranging from
13.335615 to 46.689782 µs over eligible cells. These are fixed-model analytical
sensitivity estimates, not observed planet-mass upper limits. The fitted peak
amplitude above does not establish a companion.

## Execution and evidence

`tools/recherche ipta-search` is a thin adapter that binds compatible prepared
inputs and an existing verified calibration cache to the unchanged observed
GLS runner. It creates a distinct freeze and refuses an existing run01
destination. The wrapper updates the canonical workbook after execution;
bookkeeping can be repaired separately without repeating science.

The execution freeze SHA256 is
`8d133064687e033ca35b1b7979c53637470299def8b898588d31d27c0b27ae7e`.
The calibration key is
`ea90776235fca7ce4ed6894a928e89d72c5651a3ae34d72cec8fbb3018bb1b32`.
Frozen scientific inputs, the one saved grid, independent peak verification,
terminal result, workbook receipts and preservation checks are retained in
`results/observed/ipta-batch01-20260909-J1721-2457-run01/`.
Full operational inputs remain outside Git in
`../Project Recherche Data/ipta-batch01-20260909/`.

The canonical workbook now has 338 search/refinement records for 277 observed
target identities. J1721's earlier MPTA NO_TRIGGER record remains intact; the
IPTA dataset adds old Nançay/Westerbork coverage, not a new pulsar identity.
All 13 other IPTA coverage candidates remain unprepared. No background run
remains active. Further searches require a new owner-directed scope.

Preparation: [adapter](IPTA_BOUNDED_ADAPTER_2026-09-09.md),
[calibration](IPTA_J1721_CALIBRATION_2026-09-09.md),
[source queue](FUTURE_DATA_SOURCES.md).
