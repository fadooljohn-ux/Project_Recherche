# Follow-up availability — 9 September 2026

The post-release public-source check did not identify a complete new UTMOST-NS
combined timing package that resolves the recorded intake gap. This is a bounded
availability finding, not proof that no suitable data exist elsewhere.

The [UTMOST-NS paper](https://arxiv.org/html/2506.22697v1) directs readers to the
Pulsar Portal or a reasonable request to the corresponding author. The current
[Molonglo organisation](https://github.com/Molonglo) exposes the earlier timing
release and a [NS clock repository](https://github.com/Molonglo/UTMOST-NS_clock).
The latter contains a clock and observatory coordinates, not the missing combined
PAR/TIM, accepted-observation and full-precision noise products. The existing
acquisition already obtained the NS clock and raw arrival times. No authenticated
portal access or credential was recreated during this check.

For J1752−2806, the paper includes timing-noise modelling and lists a vetoed
low-significance glitch feature. Those published summaries do not provide an
independent planetary confirmation or replace an analysis-ready timing package.
Retain Recherche's existing INCONCLUSIVE_NOISE_SENSITIVE disposition. A useful
follow-up would bind accepted newer TOAs, phase connection, instrument offsets,
noise and any glitch conventions before testing the saved candidate prediction.

The [IPTA official release index](https://www.ipta4gw.org/data-release/) still
links DR2 and DR1. A conference description of DR3 is not an acquired timing
release: no new DR3 package was verified here. Existing DR2 observations are
already reconciled, so they are not counted as new independent evidence.

The actionable missing inputs remain those in the
[unsent request draft](UTMOST_NS_DATA_REQUEST_DRAFT_2026-09-09.md): full-precision
combined PAR/TIM with pulse counts and fit flags; final accepted observations;
noise parameters and conventions; and clock/instrument/version bindings.
No researcher was contacted. No new source search or monitoring was launched.
The available next engineering route is the bounded binary extension; expanding
it beyond this first pilot requires a new target selection.
