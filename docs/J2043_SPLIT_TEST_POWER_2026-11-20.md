# J2043+1711: would a split test tell us anything? (simulation)

**20 November 2026. Owner instruction "Simulate the split test". Simulated
data only: no observed residuals were read, nothing was frozen and no
observed test was run or is authorized by this.**

## Question

The 37.48-day feature in J2043+1711 (0.089 µs at the fixed-noise stage) is
neither confirmed nor excluded. A real companion moves the pulsar the same
way at every radio frequency and throughout the record. Could a test that
fits the feature separately in two parts of the Arecibo data, and asks
whether the parts agree, separate a companion from the alternatives?

## What was simulated

- Real observing times, uncertainties, receivers and timing model of the
  consumed J2043 preparation (459 wideband TOAs, 9.05 years; orbit
  linearised), with simulated noise.
- Two splits: **receiver** (430 MHz, 220 TOAs, against L-wide, 239) and
  **time** (epochs up to MJD 57609, 233 TOAs, against later ones, 226).
- Statistic: with the timing model shared, the cosine and sine of the
  37.48-day sinusoid are fitted separately in the two parts; D is the
  chi-square (2 degrees of freedom) of their difference. "Inconsistent"
  means D above its 99% point, 9.21.
- Four cases, 4,000 simulations each, all built so that the whole-data fit
  shows 0.089 µs: a **companion** (same signal in both parts); a **noise
  fluke** (noise only, drawn conditional on the whole-data fit showing the
  feature); and a signal living in **one part only** (each part in turn).
- Noise: released white noise alone; plus red noise at the second stage's
  fitted values (log10 A −14.60, slope 4), at its declared reference
  (−14.10, slope 3), and stronger and steeper (−13.60, slope 4). The test
  was evaluated assuming white only, the reference red and the fitted red.

## Result

Amplitude uncertainty at 37.48 days (reference-red analysis): whole data
0.020 µs; 430 MHz alone 0.44 µs; L-wide alone 0.049 µs; first half 0.026 µs;
second half 0.032 µs.

Fraction called inconsistent (analysis with the reference red model; noise
generated at or below that strength):

| Case | Receiver split | Time split |
|---|---:|---:|
| Companion (should be about 1%) | 0.8–1.1% | 0.6–0.9% |
| Noise fluke | 0.8–1.1% | 0.7–0.9% |
| Signal in the first part only (430 MHz / first half) | 20–21% | 78–79% |
| Signal in the second part only (L-wide / second half) | 0.8–1.1% | 99% |

What this says:

- **Neither split can tell a companion from a stationary noise
  fluctuation.** A noise fluke that produced the whole-data feature passes
  the consistency test exactly as often as a companion does. This is a
  property of the test, not of the data: for stationary noise, how a
  fluctuation divides between the parts is independent of its total.
- **The receiver split has no useful power.** The 430 MHz data alone
  measure the amplitude to 0.44 µs, five times the feature. Nearly all the
  timing information is in L-wide and in the two receivers together (which
  is what separates dispersion from timing).
- **The time split is a good veto for one thing only:** a feature confined
  to one half of the record (a transient, or an instrumental era). It would
  catch that 78–99% of the time while wrongly rejecting a companion about
  1% of the time.
- **It depends on the red-noise model.** If the true red noise were the
  strongest case simulated and the test assumed the reference model, 11% of
  real companions would be called inconsistent (16% of flukes); assuming
  white noise only, 14–96%. Any observed test would have to assume the
  reference red model or stronger, declared in advance.

## Reading

A time-split test on the observed data could only **remove** the feature
(if it lives in one half). A pass would rule out a one-era artefact but
would not raise the feature's standing against ordinary pulsar noise, which
is the leading explanation. Independent telescope data remains the only
route that can confirm or exclude it
([options](INDEPENDENT_DATA_SOURCES_2026-11-19.md)).

## Limits

- One period and one amplitude (those of the September crossing, taken
  from the consumed result; no residuals read). No period search.
- Gaussian noise, stationary power-law red noise, linear timing model. A
  non-stationary noise process was represented only by the one-part cases.
- A chromatic signal was not simulated separately; the wideband dispersion
  columns are in the timing model.

## Evidence

`results/research/split-test-power-20261120/power.json` (every analysis
model and generator), from `tools/split_test_power.py` with
`config/j2043-split-test-power.json`; tests in
`tests/test_split_test_power.py`.
