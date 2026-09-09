# Data boundary

## Authorized pattern

All downloaded and derived pulsar-timing data must be beneath the single path
supplied in `RECHERCHE_DATA_ROOT`. The repository stores no default absolute
path. A data root is accepted only after it contains the marker created by
`pulsar-pilot init-data-root`.

For the MacBook pilot, the selected root is beneath the previously authorized
astronomy-data parent on the external volume. The exact path is supplied only
through the environment and run records. It is not embedded in portable
configuration or result tables.

## GitHub boundary

Git contains code, frozen configuration, protocols, provenance manifests,
tests, and compact summary results only. It must not contain:

- downloaded archives, TOAs, timing models, clock files, or profile templates;
- credentials, tokens, local environment files, or absolute data-root paths;
- bulk residuals, covariance products, MCMC chains, or binary analysis files.

## Portability

Migration consists of copying the controlled data root, verifying its hashes,
recreating the locked Pixi environment, and changing `RECHERCHE_DATA_ROOT`.
No source-code edit should be required.
