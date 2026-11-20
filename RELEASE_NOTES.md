# v0.2.0 — 21 November 2026

Second publication edition. It replaces the v0.1.0 snapshot with the project's
state at 21 November 2026.

**Results**

- 403 registered searches of 320 pulsars, plus four nonlinear-orbit searches.
  **No new planet is confirmed.**
- A second-stage joint-noise test was applied to all ten fixed-noise threshold
  crossings; none survived. J2043+1711 remains inconclusive and needs
  independent data.
- Pulsars in binaries: 18 MeerKAT, 20 NANOGrav, 12 Parkes and 6 European
  searches for an outer companion, with holds recorded where a model could not
  be verified.
- Per-pulsar detection limits and a combined limit on companion frequency over
  310 pulsars, with tables and stated caveats.

**New capabilities**

- Second-stage joint-noise test with per-receiver white noise, a required
  sensitivity curve, and a standing rule that a crossing is only a trigger
  until it passes.
- Nonlinear orbit statistic for binaries whose orbit cannot be treated
  linearly.
- Binary procedures for MeerKAT, NANOGrav, Parkes and European releases:
  small-eccentricity re-expression with refinement, a verified Shapiro-delay
  nuisance basis, a leakage test for omitted Shapiro delays, translation of
  tempo2 `T2`/`BT` models with the tempo2 Shapiro-convention correction, and a
  numerical comparison against tempo2.
- Detection-limit and population-limit tools; binary and small-data-set
  inventories.
- Qualification 03 of the core search (21 of 21 gates) on the current host.
- Code-audit fixes, an environment binding, and GitHub Actions restricted to
  manual runs.

**Edition notes**

- As in v0.1.0, personal paths are replaced by relative or symbolic paths and
  the chronological owner-instruction log is replaced by current operating
  instructions; see docs/PUBLICATION_PROVENANCE.md. Files unchanged since
  v0.1.0 are byte-identical to that edition.
- No search, calibration or qualification was rerun to produce this edition.
  Raw timing inputs and large runtime products are acquired separately.
- Scientific execution requires Intel macOS Python 3.11 (Rosetta on Apple
  Silicon). Qualification applies to the recorded host and inputs and is not
  transferred by this release.

# v0.1.0 — 9 September 2026

First versioned publication edition of Project Recherche.

- Pulsar-timing companion searches, automatic target calibration and supported
  source adapters; observed benchmarks and three detailed candidate reports.
- Master register: 754 targets, 277 observed identities, 351 search/refinement
  records and seven retained candidate identities. No new planet is confirmed.
- Harness-independent agent guide, pinned macOS bootstrap and portable workbook
  closeout backend; citation metadata and contribution guidance.
- Personal paths and email metadata removed from the publication snapshot.
  Original history/evidence retained in a separate private archive; publication
  hashes and transformations documented explicitly.

Scientific execution requires Intel macOS Python 3.11 (Rosetta on Apple Silicon).
Raw timing inputs and large runtime/data products are acquired separately.
Qualification 02 is historical evidence for its original installation; this
release does not transfer that qualification to a new host. Six source changes
only replace paths in diagnostic commands; no numerical algorithms were changed
and no scientific searches were rerun for publication.
