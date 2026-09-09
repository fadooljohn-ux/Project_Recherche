# Worlds worth looking for

Saved at the owner's request on 9 September 2026 as a source of motivation.
These are hypothetical interpretations of four timing features, not detected
planets. Their current grades remain inconclusive and noise-sensitive.

If the saved timing features were entirely due to circular planetary orbits
around 1.4-solar-mass pulsars, their fitted periods and amplitudes would imply:

| Pulsar | Orbital period | Orbital distance | Minimum mass | Illustrative rocky diameter |
|---|---:|---:|---:|---:|
| J1453+1902 | 118.87 days | 0.529 AU | 0.00268 Earth masses, about 22% of the Moon | 1,800–2,200 km |
| J1939+2134 | 577.5 days, 1.58 years | 1.518 AU | 0.00111 Earth masses, about 9% of the Moon | 1,300–1,600 km |
| J1327-6222 | 63.51 days | 0.349 AU | 0.376 Earth masses, about 3.5 Mars masses | 9,200–11,300 km |
| J1752-2806 | About 81.7 days | 0.412 AU, about 61.7 million km | 0.28–0.31 Earth masses, about 2.6–2.9 Mars masses | 8,300–10,600 km |

The first two would be small, dwarf-planet-scale worlds. The third would be a
larger, sub-Earth-mass world. One AU is the Earth–Sun distance. The J1939 orbit
would lie at roughly Mars's distance from its host, and J1327's slightly inside
Mercury's distance. J1752 would be another sub-Earth world with an approximately
82-day year and a projected pulsar wobble of only 37–41 km. These distance
analogies do not imply similar environments.

Timing constrains approximately m sin(i), so the table assumes edge-on orbits
and gives minimum masses. At an inclination of 30 degrees, masses would double.
The diameters additionally assume bulk densities of 3–5.5 g/cm3 at those minimum
masses. They are illustrative calculations, not measurements or confidence
intervals. J1752's mass range spans the three joint noise-model fits, not a
statistical confidence interval. Timing alone does not determine physical radius
or composition.

## Calculation and retained inputs

For timing semiamplitude A, pulsar mass M and orbital period P:

    a = [G M (P / 2 pi)^2]^(1/3)
    m sin(i) approximately c A M / a
    diameter = 2 [3 m / (4 pi density)]^(1/3)

The approximation neglects the very small companion-to-pulsar mass ratio.
Constants used: c = 299792458 m/s, nominal solar GM = 1.3271244e20 m3/s2,
nominal Earth GM = 3.986004e14 m3/s2, G = 6.67430e-11 SI,
AU = 149597870700 m. The Moon/Earth mass ratio used is 0.0123000371.

Saved fitted period/amplitude pairs (days, microseconds):

- J1453: 118.86682633580926, 1.5199940751980152.
  Source: `results/research/j1453-human-review-20260908-step1.json`, `refined`.
- J1939: 577.5, 1.7974493861776404.
  Source: `results/research/j1939-deep-review-20260909/step1.json`, `refined`.
  This is the original roughly 567-day candidate after local refinement,
  not the separate 67-day residual feature.
- J1327: 63.51198491255098, 140.4013912563928.
  Source: `results/research/j1327-deep-review-20260909/step1.json`, `refined`.

- J1752: 81.7609080000426, 138.08839480731402 (12 modes);
  81.67022464228042, 122.34974891898109 (32 modes);
  81.73460541023141, 126.90841485862137 (64 modes).
  Source: `results/research/j1752-focused-review-20260909/joint.json`, each model's `fit`.
  Exact minimum masses span 0.27732–0.31276 Earth masses; the illustrative
  density-based diameters span 8,316–10,594 km. Saved at the owner's request.

References: [pulsar companion timing method](https://academic.oup.com/mnras/article/512/2/2446/6542453),
[solar-system physical comparisons](https://ssd.jpl.nasa.gov/planets/phys_par.html),
[IAU conversion constants](https://arxiv.org/abs/1510.07674).

Keep this reference separate from [candidate evidence grades](CANDIDATE_GRADING.md).
It neither raises those grades nor supplies period seeds for future searches.
