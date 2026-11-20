# Project Recherche in plain language

**20 November 2026. Written for a reader with a hobbyist's interest in
astronomy. Every number here comes from the project's own records; the
linked write-ups hold the detail.**

## The idea

A pulsar is a collapsed star that spins many times a second and sweeps a
radio beam past Earth on every turn. The pulses arrive so regularly that
the best pulsars rival atomic clocks.

If something orbits the pulsar, the pulsar itself moves in a small circle
in response. When it is on the near side of that circle its pulses arrive
slightly early; on the far side, slightly late. A planet therefore shows up
as a gentle, repeating early-late-early wobble in the arrival times. The
first planets ever found outside the Solar System were found this way, in
1992, around the pulsar B1257+12.

Recherche asks one question of public pulsar-timing data: **is there a
repeating wobble that the published timing model does not already explain?**

## How small a wobble we can see

The most precise pulsars are timed to well under a millionth of a second.
At that level the search is sensitive to objects far lighter than Earth:
for the best targets, down to about a thousandth of an Earth mass, which is
less than a tenth of the mass of the Moon and a few times the mass of
Ceres, the largest asteroid. For the noisier, younger pulsars the reach is more like one to
ten Earth masses.

## What we built

1. **A search.** For each pulsar it tries a few dozen to a few hundred
   trial orbital periods, usually between 30 and 400 days, and measures how
   much a wobble at each period improves the fit.
2. **A threshold set in advance.** Before looking at the real data, the
   search is run on thousands of simulated noise-only data sets to learn how
   strong a peak chance alone can produce. The threshold is set so that a
   false alarm is expected about once in a hundred batches.
3. **One look only.** Each search is frozen (settings and code
   fingerprinted) and then run exactly once. Nothing is tuned after seeing
   the result. This is what keeps a "nothing found" or a "something found"
   honest.
4. **A sensitivity measurement.** Fake planets are injected into simulated
   data to measure how small a planet would have been caught 95% of the
   time. That turns "we saw nothing" into "nothing bigger than X is there".
5. **A second opinion on any alarm.** A peak above the threshold is only a
   trigger. It is then re-tested while letting the pulsar's own noise be
   re-fitted, because slow random wandering in a pulsar's spin can imitate
   a wobble.
6. **Handling pulsars that already have a companion.** Many of the best
   pulsars orbit a white dwarf. That known orbit has to be removed
   precisely before looking for a second, outer body. Two refinements were
   added this week: a better way of writing nearly circular orbits, and a
   careful treatment of the Shapiro delay (the tiny extra delay when pulses
   pass through the companion's gravity). When the method cannot be shown
   to be accurate for a pulsar, that pulsar is **held**, not searched.

## Does it actually work?

Yes, on known cases:

- **B1257+12**: the two larger of its three known planets were recovered
  from independent telescope data. The third (about twice the mass of the Moon)
  was below what that data set could reach.
- **J1719−1438, J2322−2650 and J1544+4937**: their known very low-mass
  companions were recovered.
- Fake planets injected into simulated data are recovered at the rates the
  sensitivity figures claim; this is rechecked for every target.

## What we searched

| What | Count |
|---|---:|
| Searches of isolated pulsars and earlier binaries (through 19 November) | 360 searches of 286 pulsars |
| MeerKAT pulsars in binaries, searched for an outer body (19–20 November) | 18 |
| MeerKAT binaries held because the method could not be verified for them | 14 |

Data came from public releases of MeerKAT, UTMOST, NANOGrav, the European,
Indian, Parkes and International timing arrays.

## What we found

**No new planet.**

- A handful of searches produced a peak above the first threshold. Ten
  such triggers were put through the second-stage test. **None survived
  it.** They are graded "inconclusive, noise-sensitive": most likely the
  pulsar's own noise.
- One deserves a caveat. **J2043+1711** showed a peak near 37.5 days. It
  fell below the second-stage threshold, but the signal is so small that
  the second stage would only catch it about half the time. So it is
  neither confirmed nor ruled out. Settling it needs data from a different
  telescope; no request has been made.
- All 18 MeerKAT binary searches, including the nine run today, came back
  with no trigger.

## What that tells us

A well-measured "nothing" is a result. Combining the isolated pulsars:

- **Planets of 10 Earth masses or more, with periods of 30–240 days, orbit
  fewer than about 1.3% of these pulsars** (95% confidence).
- **Earth-mass planets at those periods orbit fewer than about 2%**, or
  about 5% under a more cautious allowance for noise.
- For the eighteen MeerKAT binaries, a second body down to roughly
  0.001–0.02 Earth masses (depending on the pulsar and period) in a 30–300
  day orbit would have been caught 95% of the time. None was.

In short: pulsar planets are rare. B1257+12 remains an exception, not the
rule. That matches what professional surveys have concluded, and here it is
reached independently, over several hundred pulsars, with stated limits.

## What we learned about doing this well

- **Noise is the real opponent.** Every first-stage alarm so far has been
  explained by the pulsar's noise once that noise was allowed to flex. The
  first threshold alone is not enough.
- **Long periods are hard.** Beyond about 400 days a planet's wobble looks
  too much like slow pulsar noise, and only about 20 pulsars have long
  enough records. The limits there are weak (below about 15%).
- **Holding is better than guessing.** When a pulsar's orbit could not be
  modelled to the required accuracy, it was set aside and the reason
  recorded. The most precise pulsar on the MeerKAT list, J1909−3744, is
  still held for that reason.
- **The discipline matters as much as the mathematics.** Thresholds fixed
  beforehand, one look per search, and every run fingerprinted are what
  make the limits trustworthy.

## What these results do not say

- They cover **circular orbits** at the periods searched, mostly 30–400
  days. Very short, very long or strongly elongated orbits are not covered.
- Masses are **minimum masses**: the orbit's tilt is unknown, so a real
  object would be somewhat heavier.
- The limits assume the published noise models are right, except where the
  second stage was run.
- The pulsars are not a random sample: they are the ones with enough
  good public data.
- Adding the 18 MeerKAT binaries to the combined figure (done later the
  same day) barely moves the Earth-mass numbers above, but tightens the
  limit on much smaller bodies: objects of a tenth of an Earth mass at
  60–240 days orbit fewer than about 6–7% of the 289 pulsars (was about
  9%). Isolated pulsars and binaries are different kinds of system, so
  that combined figure describes "pulsars this project searched".
- This is a private project and has not been peer reviewed.

## Update, 21 November 2026

Since this was written, 25 more pulsars in binaries were searched (seven
in NANOGrav data, twelve in Parkes data and six in European data), again
with nothing found. With every search so far the tally is 310 pulsars.
The biggest gain is at long periods: planets with periods of 400 to 2,000
days now orbit fewer than about 9–10% of the pulsars searched (it was
about 15–17%), if the published noise models are right. The Earth-mass
figures at shorter periods are unchanged.

## Where the detail is

[Population limit](POPULATION_LIMITS_2026-11-19.md) ·
[per-pulsar limits](DETECTION_LIMITS_2026-11-19.md) ·
[second-stage test](JOINT_NOISE_STAGE_2026-11-18.md) ·
[what remains](REMAINING_TARGETS_2026-11-19.md) ·
[today's nine searches](MPTA_BINARY04_2026-11-20.md)
