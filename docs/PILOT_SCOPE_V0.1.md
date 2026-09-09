# Project Recherche — MacBook pulsar-timing pilot v0.1

- **Status:** authorized for the bounded first working session.
- **Scientific framing:** development and validation of a real research
  analysis tool through published timing-model reproduction and controlled
  injection/refit transfer tests. This pilot stage is not yet a planet survey
  or discovery-capable analysis.
- **Target:** PSR J1744-1134, NANOGrav 15-year v2.1.0 wideband data.

## Purpose

Show that the current MacBook can reproducibly load, fit, perturb, refit, and
grade one public millisecond-pulsar timing data set, while measuring enough
runtime, memory, and storage information to design a later Mac mini/NAS setup.

## Frozen cases

| Case | Period | Timing amplitude | Disposition |
|---|---:|---:|---|
| C0 | none | 0 us | matched null |
| C1 | 100 d | 20 us | required positive recovery |
| C2 | 100 d | 5 us | boundary diagnostic |
| C3 | 365.25 d | 20 us | annual absorption stress test |

The fixed phase and seed are recorded in `config/injections.yaml`. Timing
amplitude, not inferred planet mass, is the controlled injection variable.

## Gates

1. **G0 data boundary:** one marked `RECHERCHE_DATA_ROOT`, outside Git.
2. **G1 environment:** locked x86_64 environment under Rosetta; NumPy
   `longdouble` precision exceeds `float64`; PINT imports and fits an example.
3. **G2 reproduction:** required clocks and ephemeris are present; fitted
   parameters agree within the larger of three published standard deviations
   or a frozen numerical tolerance; weighted RMS agrees within 5 percent; all
   material warnings are dispositioned.
4. **G3 injection/refit:** C1 is recovered at the injected frequency within one
   independent Fourier bin and improves the fit; achieved/recovered amplitude
   and absorption are measured for all cases.
5. **G4 migration:** only after G1-G3 pass may measured costs be extrapolated to
   3, 5, and 20 pulsars. No multi-pulsar run is authorized.

Failure of G2 blocks all injection work. Failure of G1 after four focused hours
moves the environment to the future Mac mini or a controlled Linux system.

## Caps and exclusions

- 1 GB network download; 5 GB local pilot data.
- Less than 16 GB peak memory; less than 60 minutes per job.
- No MCMC, TEMPO2 requirement, additional pulsars, anomaly investigation,
  calibrated false-alarm surface, completeness surface, or planet claim.

## First working session

Initialize the repository, lock and validate the environment, download and hash
the single controlled archive, extract only J1744-1134 support files, and stop
after a successful load-and-residual smoke test. Injection work begins only
after the G2 reproduction report passes review.
