"""Second-stage joint signal-and-noise test for a target that crossed its fixed-noise threshold.

The noise is profiled on a declared finite grid (red power-law strength and slope,
plus one scale on the TOA white-noise block) separately under the noise-only and
noise-plus-signal hypotheses. The threshold is the largest 1% order threshold
over several declared null generators that do not sit on the grid. The grid and
the generators are fixed from the sampling and the released noise only; nothing
here reads a periodogram to choose them.

Actions: prepare, calibrate (no observed residuals), freeze, run (once). Freeze
requires the sensitivity curve written by joint_noise_sensitivity.py.
"""
import argparse
import itertools
from pathlib import Path

import numpy as np
from scipy.stats import beta as beta_distribution

import binary_noise_coverage as coverage
import j1453_review as common
import joint_noise
import mpta_batch as mpta
import target_calibration as cal

REPO = Path(__file__).resolve().parents[1]
RNAMP_UNIT = (86400 * 365.24 * 1e6) / (2 * np.pi * np.sqrt(3))
NO_RED = None


def code_binding():
    files = [__file__, joint_noise.__file__, coverage.__file__, common.__file__, mpta.__file__, cal.__file__,
             Path(__file__).with_name("joint_noise_sensitivity.py")]
    return {str(Path(p).relative_to(REPO)): cal.digest(p) for p in files}


def released_red(source, spec):
    """(log10 amplitude, slope, modes) of the released red power law, or None; and the files read."""
    adapter = spec["adapter"]
    if adapter == "none":
        return None, []
    if adapter == "par_rnamp":
        path = source / "prepared/timing-model.par"
        fields = {v[0]: v[1:] for line in path.read_text().splitlines() if (v := line.split())}
        amplitude = float(np.log10(float(fields["RNAMP"][0]) / RNAMP_UNIT))
        return (amplitude, -float(fields["RNIDX"][0]), int(spec["modes"])), [path]
    if adapter == "receipt_tnred":
        path = source / "prepared/receipt.json"
        noise = cal.read(path)["noise_parameters"]
        return (float(noise["TNREDAMP"]), float(noise["TNREDGAM"]), int(noise["TNREDC"])), [path]
    raise ValueError("Unknown released-noise adapter: " + adapter)


def nonlinear_source(source):
    """Profile of a nonlinear-orbit preparation with the orbit linearised at the published values."""
    profile = cal.read(source / "profile/profile.json")
    if profile.get("schema") != "recherche-nonlinear-profile-v1" or profile.get("observed_residuals_included") is not False:
        raise ValueError("Unsupported nonlinear profile")
    if cal.digest(source / "profile/arrays.npz") != profile["arrays_sha256"]:
        raise ValueError("Profile arrays changed")
    with np.load(source / "profile/arrays.npz", allow_pickle=False) as z:
        orbit = z["surrogate_coefficients"][:, :len(z["orbit_lower"])]
        if not np.array_equal(z["surrogate_exponents"][:orbit.shape[1]], np.eye(orbit.shape[1], dtype=int)):
            raise ValueError("Surrogate does not lead with its linear terms")
        arrays = {"times": z["times"], "covariance": z["covariance"], "design": np.column_stack([z["nuisance"], orbit])}
    return profile, arrays, cal.read(source / "calibration/calibration.json")["median_worst_phase_amplitude_us"]


def chain_red(data, spec):
    """(log10 amplitude, slope) rows of a released noise chain after its first quarter; and its path."""
    path = data / spec["chain"]
    names = (data / spec["parameters"]).read_text().split()
    chain = np.loadtxt(path)
    columns = [next(i for i, name in enumerate(names) if name.endswith(suffix))
               for suffix in ("red_noise_log10_A", "red_noise_gamma")]
    return chain[len(chain) // 4:][:, columns], path


def tim_rows(path):
    """(error in microseconds, DM error, backend flag) for each TOA line of a wideband tim file, in file order."""
    rows = []
    for line in path.read_text().splitlines():
        v = line.split()
        if len(v) < 5 or v[0] in ("C", "#", "FORMAT", "MODE"):
            continue
        flags = dict(zip(v[5::2], v[6::2]))
        rows.append((float(v[3]), float(flags["-pp_dme"]), flags["-f"]))
    return tuple(np.array(column) for column in zip(*rows))


def white_variance(error_us, dm_error, backend, values):
    """Diagonal of the wideband white covariance: TOA rows (seconds squared), then DM rows.

    values: backend -> (EFAC, EQUAD in microseconds, DMEFAC, DMEQUAD).
    """
    toa, dm = np.empty(len(error_us)), np.empty(len(error_us))
    for name in np.unique(backend):
        efac, equad, dmefac, dmequad = values[name]
        rows = backend == name
        toa[rows] = efac ** 2 * (error_us[rows] ** 2 + equad ** 2) * 1e-12
        dm[rows] = dmefac ** 2 * (dm_error[rows] ** 2 + dmequad ** 2)
    return np.concatenate([toa, dm])


def released_white(data, spec, base):
    """Per-TOA errors and backends from the tim file, and the par white values, checked against the prepared covariance.

    spec: {"tim": path, "par": path}. The released values must reproduce the prepared white covariance.
    """
    error, dm_error, backend = tim_rows(data / spec["tim"])
    par = {}
    for line in (data / spec["par"]).read_text().splitlines():
        v = line.split()
        if v and v[0] in ("EFAC", "EQUAD", "DMEFAC", "DMEQUAD"):
            par.setdefault(v[2], {})[v[0]] = float(v[3])
    released = white_variance(error, dm_error, backend,
                              {k: (v["EFAC"], v["EQUAD"], v["DMEFAC"], v["DMEQUAD"]) for k, v in par.items()})
    if np.count_nonzero(base - np.diag(np.diag(base))) or len(released) != len(base):
        raise ValueError("Joint chain draws need a diagonal wideband white covariance")
    mismatch = float(np.max(abs(released / np.diag(base) - 1)))
    if mismatch > 1e-6:
        raise ValueError("Released white noise does not reproduce the prepared covariance: %g" % mismatch)
    return error, dm_error, backend, par, mismatch


def chain_joint(data, spec, base):
    """Joint white-and-red chain draws: (log10 amplitude, slope) and each draw's white variance diagonal."""
    error, dm_error, backend, par, mismatch = released_white(data, spec["joint_white"], base)
    path = data / spec["chain"]
    names = (data / spec["parameters"]).read_text().split()
    chain = np.loadtxt(path)
    chain = chain[len(chain) // 4:]
    chain = chain[np.linspace(0, len(chain) - 1, spec["draws"]).astype(int)]
    column = lambda suffix: chain[:, next(i for i, name in enumerate(names) if name.endswith(suffix))]
    white = np.array([white_variance(error, dm_error, backend, {
        k: (column(k + "_efac")[i], 10 ** column(k + "_log10_t2equad")[i] * 1e6,
            column(k + "_dmefac")[i], 10 ** column(k + "_log10_dmequad")[i]) for k in par})
        for i in range(len(chain))])
    red = np.column_stack([column("red_noise_log10_A"), column("red_noise_gamma")])
    return red.tolist(), white, mismatch, [path, data / spec["joint_white"]["tim"], data / spec["joint_white"]["par"]]


def chain_samples(data, spec, span_years):
    """Evenly thinned chain draws; with strongest_fraction, only from the draws with most power at 1/span."""
    red, path = chain_red(data, spec)
    if "strongest_fraction" in spec:
        power = 2 * red[:, 0] + red[:, 1] * np.log10(span_years)
        red = red[np.sort(np.argsort(power)[-int(np.ceil(spec["strongest_fraction"] * len(red))):])]
    return red[np.linspace(0, len(red) - 1, spec["draws"]).astype(int)].tolist(), path


def chain_bound(data, spec, slopes):
    """Largest log10 amplitude the chain allows at each grid slope: a quantile over draws with nearby slope."""
    red, path = chain_red(data, spec)
    bound = {}
    for slope in slopes:
        near = red[abs(red[:, 1] - slope) <= spec["gamma_half_width"], 0]
        if len(near) < spec["minimum_draws"]:
            raise ValueError("Too few chain draws near slope %g" % slope)
        bound[slope] = float(np.quantile(near, spec["quantile"]))
    return bound, path


def generator_factors(contrast, a, modes, pars):
    """Cholesky factors of one generator: a single covariance, or one per chain draw."""
    draws = pars.get("samples") or [[pars["log10_amplitude"], pars["gamma"]]]
    if "white_key" in pars:
        # Joint draws: each draw has its own white diagonal on every row, plus its red term on the TOA block.
        n, factors = len(a["times"]), []
        for (amplitude, gamma), white in zip(draws, a[pars["white_key"]]):
            covariance = np.diag(white)
            covariance[:n, :n] += mpta.red_covariance(a["times"], amplitude, gamma, modes)
            factors.append(np.linalg.cholesky(contrast.B @ covariance @ contrast.B.T))
        return factors
    return [np.linalg.cholesky(contrast.covariance(variable_covariance(
        a, modes, {"log10_amplitude": amplitude, "gamma": gamma, "white_scale": pars["white_scale"]})))
        for amplitude, gamma in draws]


def coloured(factors, rng, dimension, count):
    """Noise columns; successive columns cycle through the generator's factors."""
    white = rng.standard_normal((dimension, count))
    return np.column_stack([factors[i % len(factors)] @ white[:, i] for i in range(count)])


def white_equivalent_amplitude(times, variance, gamma, modes):
    """log10 amplitude at which the red variance per TOA equals the median white variance."""
    unit = float(np.mean(np.diag(mpta.red_covariance(times, 0.0, gamma, modes))))
    return float(0.5 * np.log10(np.median(variance) / unit))


def grid_slopes(gamma, declared):
    return sorted({float(np.clip(gamma + d, 0, 7)) for d in declared["gamma_offsets"]})


def members(reference, declared, bound=None):
    """Noise members as dicts; log10_amplitude None means no red term.

    bound: per-slope largest allowed log10 amplitude (from a released chain), or None for the full grid.
    With receiver_white in the declaration, each receiver group has its own white scale (group_scales)
    in place of the single global one.
    """
    amplitude, gamma = reference
    slopes = grid_slopes(gamma, declared)
    reds = [(NO_RED, NO_RED)] if declared["include_no_red"] else []
    reds += [(float(amplitude + d), s) for d, s in itertools.product(declared["amplitude_offsets_dex"], slopes)
             if bound is None or amplitude + d <= bound[s]]
    if not reds:
        raise ValueError("The chain bound leaves no noise member")
    if "receiver_white" in declared:
        spec = declared["receiver_white"]
        labels = sorted(set(spec["groups"].values()))
        # Optional additive floor per group (microseconds), for chains that allow a large EQUAD.
        floors = [spec.get("equads_us", {}).get(label, [0.0]) for label in labels]
        whites = [{"white_scale": 1.0, "group_scales": [float(x) for x in scales],
                   "group_equads_us": [float(x) for x in equads]}
                  for scales in itertools.product(spec["scales"], repeat=len(labels))
                  for equads in itertools.product(*floors)]
    else:
        whites = [{"white_scale": float(s)} for s in declared["white_scales"]]
    return [{"log10_amplitude": a, "gamma": g, **white} for (a, g), white in itertools.product(reds, whites)], slopes


def subspace(times, base, design, periods, epoch, modes):
    """Exact reduction for a diagonal covariance.

    Returns R (rows: an orthonormal basis, in whitened units, of every timing, red-noise
    and signal column) and the whitening weights. In that basis the base covariance is the
    identity; the data outside it see only the white scale and enter as one extra term.
    """
    if len(base) != len(times) or np.count_nonzero(base - np.diag(np.diag(base))):
        raise ValueError("Subspace compression needs a diagonal TOA-only covariance")
    weight = 1 / np.sqrt(np.diag(base))
    seconds = (times - times.min()) * 86400.0
    phase = 2 * np.pi * seconds[:, None] * np.arange(1, modes + 1) / np.ptp(seconds)
    common.REFERENCE = epoch
    columns = weight[:, None] * np.column_stack([
        design, np.sin(phase), np.cos(phase), common.template(times, periods, len(times)).reshape(len(times), -1)])
    columns /= np.linalg.norm(columns, axis=0)
    q = np.linalg.qr(columns)[0]
    if np.abs(columns - q @ (q.T @ columns)).max() > 1e-9:
        raise ValueError("Subspace does not hold its own columns")
    return q.T * weight, weight


def variable_covariance(arrays, modes, pars):
    """TOA-block covariance added to the fixed base for one noise member."""
    out = (pars["white_scale"] ** 2 - 1) * arrays["base_toa"]
    if "group_scales" in pars:
        scale = np.array(pars["group_scales"])[arrays["white_group"]]
        floor = (np.array(pars.get("group_equads_us", [0.0] * len(pars["group_scales"])))[arrays["white_group"]] * 1e-6) ** 2
        released = np.diag(arrays["base_toa"])
        out = out + np.diag(scale ** 2 * (released + floor) - released)
    if pars["log10_amplitude"] is not None:
        red = mpta.red_covariance(arrays["times"], pars["log10_amplitude"], pars["gamma"], modes)
        if "reduction" in arrays:
            red = arrays["reduction"] @ red @ arrays["reduction"].T
        out = out + red
    return out


def on_boundary(pars, scope):
    family = scope["family_declaration"]
    if "group_scales" in pars:
        scales = family["receiver_white"]["scales"]
        edge = any(s in (min(scales), max(scales)) for s in pars["group_scales"])
        labels = sorted(set(family["receiver_white"]["groups"].values()))
        for label, floor in zip(labels, pars.get("group_equads_us", [])):
            edge |= floor > 0 and floor == max(family["receiver_white"]["equads_us"][label])
    else:
        edge = pars["white_scale"] in (min(family["white_scales"]), max(family["white_scales"]))
    if pars["log10_amplitude"] is not None:
        lowest = scope["reference_log10_amplitude"] + min(family["amplitude_offsets_dex"])
        # The upper edge is the strongest member kept at this slope (the grid edge, or a chain bound below it).
        highest = max(m["log10_amplitude"] for m in scope["family"] if m["gamma"] == pars["gamma"])
        edge |= bool(np.isclose(pars["log10_amplitude"], [lowest, highest]).any())
        edge |= pars["gamma"] in (min(scope["gamma_grid"]), max(scope["gamma_grid"]))
    return bool(edge)


def interval(k, n):
    return [0.0 if k == 0 else float(beta_distribution.ppf(0.025, k, n - k + 1)),
            1.0 if k == n else float(beta_distribution.ppf(0.975, k + 1, n - k))]


def prepare(data, root, config_path):
    if root.exists():
        raise FileExistsError("Destination exists; read it or continue with calibrate")
    config = cal.read(config_path)
    source = data / config["source"]
    result = cal.read(source / "run01/result.json")
    grid = np.load(source / "run01/periodogram.npz")
    references = [source / "profile/profile.json", source / "profile/arrays.npz", source / "run01/result.json",
                  source / "run01/periodogram.npz", source / "prepared/observed.npz"]
    if config.get("source_kind", "linear") == "nonlinear_orbit":
        profile, a, amplitude = nonlinear_source(source)
        references.append(source / "calibration/calibration.json")
    else:
        profile, a = cal.load_profile(source / "profile/profile.json")
        amplitude = result.get("sensitivity_median_worst_phase_us", result.get("sensitivity_median_worst_phase_amplitude_us"))
    times, n = a["times"], len(a["times"])
    released, extra = released_red(source, config["released_noise"])
    references += extra
    base = a["covariance"].copy()
    if released:
        base[:n, :n] -= mpta.red_covariance(times, *released)
    np.linalg.cholesky(base)
    if len(base) > n and np.abs(base[:n, n:]).max() > 0:
        raise ValueError("TOA and auxiliary rows are correlated; a TOA-only white scale is not supported")
    declared = config["family"]
    modes = coverage.mode_plan(float(np.ptp(times)), profile["policy"]["minimum_period_days"],
                               released[2] if released else 1)
    if released:
        reference = [released[0], released[1]]
    else:
        gamma = float(declared["reference_gamma_without_released_red"])
        reference = [white_equivalent_amplitude(times, np.diag(base)[:n], gamma, modes["selected_modes"]), gamma]
    bound = None
    if "chain_bound" in declared:
        bound, path = chain_bound(data, declared["chain_bound"], grid_slopes(reference[1], declared))
        references.append(path)
    family, slopes = members(reference, declared, bound)
    generators, joint = [], {}
    if "receiver_white" in declared:
        if released or config.get("compression"):
            raise ValueError("Receiver white scales are supported for an uncompressed source without released red noise")
        spec = declared["receiver_white"]
        backend = released_white(data, spec, base)[2]
        references += [data / spec["tim"], data / spec["par"]]
        labels = sorted(set(spec["groups"].values()))
        joint["white_group"] = np.array([labels.index(spec["groups"][name]) for name in backend])
    for g in config["generators"]:
        if "joint_white" in g:
            if released or config.get("compression"):
                raise ValueError("Joint chain draws are supported for an uncompressed source without released red noise")
            samples, white, mismatch, paths = chain_joint(data, g, base)
            references += paths
            joint["white__" + g["name"]] = white
            generators.append({"name": g["name"], "white_scale": 1.0, "samples": samples,
                               "white_key": "white__" + g["name"], "released_white_mismatch": mismatch})
            continue
        if "chain" in g:
            samples, path = chain_samples(data, g, float(np.ptp(times)) / 365.25)
            references.append(path)
            generators.append({"name": g["name"], "white_scale": 1.0, "samples": samples})
            continue
        red = g["amplitude_offset_dex"] is not None
        generators.append({"name": g["name"], "white_scale": float(g["white_scale"]),
                           "log10_amplitude": float(reference[0] + g["amplitude_offset_dex"]) if red else None,
                           "gamma": float(np.clip(reference[1] + g["gamma_offset"], 0, 7)) if red else None})
    periods = 1 / grid["frequencies"][grid["eligible"]]
    injection_periods = sorted({float(periods[np.argmin(abs(periods / p - 1))]) for p in config["injection_periods_days"]})
    root.mkdir(parents=True)
    outside = 0
    if config.get("compression") == "diagonal_subspace":
        reduction, weight = subspace(times, base, a["design"], periods, profile["reference_epoch_mjd_tdb"],
                                     modes["selected_modes"])
        identity = np.eye(len(reduction))
        outside = n - len(reduction)
        np.savez_compressed(root / "inputs.npz", times=times, base_covariance=identity, base_toa=identity,
                            design=reduction @ a["design"], periods=periods, reduction=reduction, whitening=weight)
    else:
        np.savez_compressed(root / "inputs.npz", times=times, base_covariance=base, base_toa=base[:n, :n],
                            design=a["design"], periods=periods, **joint)
    cal.write(root / "scope.json", {
        "target": config["target"], "source": config["source"], "config_sha256": cal.digest(config_path),
        "stage": "Second-stage joint-noise test of a fixed-noise crossing or a declared development control",
        "reference_epoch": profile["reference_epoch_mjd_tdb"], "coverage": modes,
        "released_red": None if not released else dict(zip(["log10_amplitude", "gamma", "modes"], released)),
        "reference_log10_amplitude": reference[0], "reference_gamma": reference[1],
        "reference_rule": "released red power law" if released else "white-equivalent amplitude at the declared slope",
        "family_declaration": declared, "gamma_grid": slopes, "family": family, "generators": generators,
        "chain_bound_log10_amplitude_by_slope": None if bound is None else {"%g" % k: v for k, v in bound.items()},
        "calibration_nulls_each": config["calibration_nulls_each"],
        "validation_nulls_each": config["validation_nulls_each"], "alpha": config["alpha"], "seed": config["seed"],
        "injection_periods_days": injection_periods, "injection_amplitude_factors": config["injection_amplitude_factors"],
        "injections_each_cell": config["injections_each_cell"], "injection_reference_amplitude_us": amplitude,
        "fixed_noise_peak_period_days": result["peak_period_days"],
        "fixed_noise_statistic": result["peak_statistic"], "fixed_noise_threshold": result["threshold"],
        "objective": "Timing-marginalised Gaussian objective with covariance determinant; noise grid and circular "
                     "coefficients profiled separately under null and signal",
        "threshold": "Largest finite-sample order threshold at alpha across the declared generators",
        "source_kind": config.get("source_kind", "linear"), "outside_dimension": outside,
        "limits": ("Noise grid cut at a released chain's amplitude bound: the threshold holds only for red noise "
                   "the chain allows. " if bound else "") + "Finite noise grid; one global TOA white-noise scale; linear timing model (a nonlinear orbit is "
                  "linearised at its published values and checked separately); no chromatic process; "
                  "no noise posterior or survey-wide false-alarm probability.",
        "inputs": {str(p.relative_to(data)): cal.digest(p) for p in references},
        "prepared_sha256": cal.digest(root / "inputs.npz"), "code": code_binding(),
        "observed_residuals_read": False})
    print("PREPARED", config["target"], "members", len(family), "modes", modes["selected_modes"], flush=True)


def load(data, root):
    scope = cal.read(root / "scope.json")
    if scope["code"] != code_binding() or scope["prepared_sha256"] != cal.digest(root / "inputs.npz"):
        raise ValueError("Prepared implementation or input binding changed")
    for path, digest in scope["inputs"].items():
        if cal.digest(data / path) != digest:
            raise ValueError("Source input changed: " + path)
    a = dict(np.load(root / "inputs.npz"))
    rows = len(a["base_covariance"])
    contrast = joint_noise.Contrast(a["base_covariance"], a["design"], len(a["base_toa"]))
    common.REFERENCE = scope["reference_epoch"]
    if "reduction" in a:
        full = np.einsum("rn,nfk->rfk", a["reduction"], common.template(a["times"], a["periods"], len(a["times"])))
    else:
        full = common.template(a["times"], a["periods"], rows)
    templates = (contrast.B @ full.reshape(rows, -1)).reshape(contrast.dimension, -1, 2)
    return scope, a, contrast, full, templates


def profile_family(scope, a, contrast, templates, samples, label, outside=None):
    """Best null and signal objective over the family for every sample column.

    outside: per-sample whitened squared norm outside a compressed subspace, or None.
    """
    count = samples.shape[1]
    best = {"null": np.full(count, np.inf), "signal": np.full(count, np.inf),
            "null_member": np.zeros(count, int), "signal_member": np.zeros(count, int), "peak": np.zeros(count, int)}
    per_member = []
    for i, pars in enumerate(scope["family"]):
        r = joint_noise.evaluate(contrast.covariance(variable_covariance(a, scope["coverage"]["selected_modes"], pars)),
                                 templates, samples)
        shift = 0.0 if outside is None else (
            scope["outside_dimension"] * 2 * np.log(pars["white_scale"]) + outside / pars["white_scale"] ** 2)
        null, signal = r["null"] + shift, r["signal"] + shift
        better = null < best["null"]
        best["null"][better], best["null_member"][better] = null[better], i
        better = signal < best["signal"]
        best["signal"][better], best["signal_member"][better] = signal[better], i
        best["peak"][better] = r["peak"][better]
        per_member.append((float(null[0]), r["score"][:, 0].copy(), r["observed_beta_grid"].copy()))
        if (i + 1) % 10 == 0 or i + 1 == len(scope["family"]):
            print(label, "member", i + 1, "/", len(scope["family"]), flush=True)
    best["statistic"] = best["null"] - best["signal"]
    return best, per_member


def calibrate(data, root):
    if (root / "calibration.json").exists():
        raise FileExistsError("Calibration exists; do not repeat it")
    scope, a, contrast, _, templates = load(data, root)
    modes = scope["coverage"]["selected_modes"]
    batches, segments, cursor, outside = [], [], 0, []
    dimension = scope.get("outside_dimension", 0)
    for gi, pars in enumerate(scope["generators"]):
        rng = np.random.default_rng(scope["seed"] + 100 * gi)
        factors = generator_factors(contrast, a, modes, pars)

        def outer(count):
            # Outside a compressed subspace the data are white at the generator's scale.
            return pars["white_scale"] ** 2 * rng.chisquare(dimension, count) if dimension else np.zeros(count)
        for kind in ("calibration", "validation"):
            count = scope[kind + "_nulls_each"]
            batches.append(coloured(factors, rng, contrast.dimension, count))
            outside.append(outer(count))
            segments.append({"generator": pars["name"], "kind": kind, "start": cursor, "stop": cursor + count})
            cursor += count
        for period, scale in itertools.product(scope["injection_periods_days"], scope["injection_amplitude_factors"]):
            count = scope["injections_each_cell"]
            index = int(np.argmin(abs(a["periods"] - period)))
            phases = rng.uniform(0, 2 * np.pi, count)
            amplitude = scope["injection_reference_amplitude_us"] * scale * 1e-6
            signal = templates[:, index] @ (amplitude * np.array([np.cos(phases), np.sin(phases)]))
            batches.append(coloured(factors, rng, contrast.dimension, count) + signal)
            outside.append(outer(count))
            segments.append({"generator": pars["name"], "kind": "injection", "period_days": period,
                             "amplitude_us": amplitude * 1e6, "start": cursor, "stop": cursor + count})
            cursor += count
    best, _ = profile_family(scope, a, contrast, templates, np.column_stack(batches), "CALIBRATE",
                             np.concatenate(outside) if dimension else None)
    statistic = best["statistic"]
    edge = np.array([on_boundary(p, scope) for p in scope["family"]])
    thresholds = {s["generator"]: joint_noise.order_threshold(statistic[s["start"]:s["stop"]], scope["alpha"])
                  for s in segments if s["kind"] == "calibration"}
    threshold = max(thresholds.values())
    rows, excess = [], []
    for s in segments:
        part = slice(s["start"], s["stop"])
        count = s["stop"] - s["start"]
        crossings = int(np.sum(statistic[part] > threshold))
        row = {**s, "count": count, "threshold_crossings": crossings,
               "null_fit_on_boundary_fraction": float(edge[best["null_member"][part]].mean()),
               "signal_fit_on_boundary_fraction": float(edge[best["signal_member"][part]].mean())}
        if s["kind"] == "validation":
            row.update(false_alarm_rate=crossings / count, false_alarm_interval95=interval(crossings, count))
            if row["false_alarm_interval95"][0] > scope["alpha"]:
                excess.append(s["generator"])
        if s["kind"] == "injection":
            located = abs(a["periods"][best["peak"][part]] / s["period_days"] - 1) < 0.05
            recovered = int(np.sum((statistic[part] > threshold) & located))
            row.update(recovered=recovered, recovery_fraction=recovered / count)
        rows.append(row)
    np.savez_compressed(root / "calibration-ensemble.npz", statistic=statistic, peak_index=best["peak"],
                        null_member=best["null_member"], signal_member=best["signal_member"])
    cal.write(root / "calibration.json", {
        "status": "JOINT_NOISE_HOLD" if excess else "JOINT_NOISE_CALIBRATED", "holds": [
            "VALIDATION_FALSE_ALARM_EXCESS:" + name for name in excess],
        "target": scope["target"], "threshold": threshold, "per_generator_thresholds": thresholds,
        "threshold_rule": scope["threshold"], "alpha": scope["alpha"], "members": len(scope["family"]),
        "contrast_dimension": contrast.dimension, "timing_rank": contrast.timing_rank,
        "eligible_cells": len(a["periods"]), "experiments": rows,
        "scope_sha256": cal.digest(root / "scope.json"),
        "ensemble_sha256": cal.digest(root / "calibration-ensemble.npz"),
        "observed_residuals_read": False, "created_utc": mpta.now()})
    print("CALIBRATED", scope["target"], "threshold", threshold, "holds", excess, flush=True)


def freeze(data, root):
    if (root / "execution-freeze.json").exists():
        raise FileExistsError("Already frozen")
    scope = cal.read(root / "scope.json")
    calibration = cal.read(root / "calibration.json")
    if calibration["status"] != "JOINT_NOISE_CALIBRATED" or calibration["scope_sha256"] != cal.digest(root / "scope.json"):
        raise ValueError("Calibration is held or belongs to another scope")
    if scope["code"] != code_binding():
        raise ValueError("Implementation changed since preparation")
    # Every frozen test states what it could detect: the sensitivity curve is required and bound.
    sensitivity = cal.read(root / "sensitivity.json")
    if (sensitivity["status"] != "SENSITIVITY_CURVE_COMPLETE" or sensitivity["retrospective"]
            or sensitivity["scope_sha256"] != cal.digest(root / "scope.json")
            or sensitivity["calibration_sha256"] != cal.digest(root / "calibration.json")):
        raise ValueError("Sensitivity curve is missing, retrospective or belongs to another calibration")
    observed = data / scope["source"] / "prepared/observed.npz"
    cal.write(root / "execution-freeze.json", {
        "target": scope["target"], "threshold": calibration["threshold"], "scope_sha256": cal.digest(root / "scope.json"),
        "calibration_sha256": cal.digest(root / "calibration.json"),
        "sensitivity_sha256": cal.digest(root / "sensitivity.json"), "observed_sha256": cal.digest(observed),
        "code": code_binding(), "search": "One joint-noise profile over the fixed-noise eligible cells; single execution",
        "created_utc": mpta.now()})
    print("FROZEN", scope["target"], flush=True)


def run(data, root):
    frozen = cal.read(root / "execution-freeze.json")
    scope, a, contrast, full, templates = load(data, root)
    observed_path = data / scope["source"] / "prepared/observed.npz"
    if (frozen["code"] != code_binding() or frozen["scope_sha256"] != cal.digest(root / "scope.json")
            or frozen["calibration_sha256"] != cal.digest(root / "calibration.json")
            or frozen["sensitivity_sha256"] != cal.digest(root / "sensitivity.json")
            or frozen["observed_sha256"] != cal.digest(observed_path)):
        raise ValueError("Frozen binding changed")
    out = root / "run01"
    out.mkdir(exist_ok=False)
    y = np.load(observed_path)["residuals"]
    outside = None
    if "reduction" in a:
        white = a["whitening"] * y
        y = a["reduction"] @ y
        outside = np.array([white @ white - y @ y])
    n, modes = len(a["base_toa"]), scope["coverage"]["selected_modes"]
    # Direct full-dimensional generalised least squares at two generators checks the compression.
    checks, previous = [], None
    for pars in [g for g in scope["generators"] if "samples" not in g][:2]:
        extra = variable_covariance(a, modes, pars)
        covariance = a["base_covariance"].copy()
        covariance[:n, :n] += extra
        compressed = joint_noise.evaluate(contrast.covariance(extra), templates, contrast.data(y)[:, None])
        direct = common.GLS(covariance, a["design"])
        scores, _ = direct.scan(y, direct.bank(full))
        np.testing.assert_allclose(compressed["score"][:, 0], scores, rtol=1e-6, atol=1e-7)
        pair = (float(np.sum(direct.project(y) ** 2) + direct.offset), float(compressed["null"][0]))
        if previous:
            np.testing.assert_allclose(pair[0] - previous[0], pair[1] - previous[1], rtol=1e-7, atol=1e-6)
        previous = pair
        checks.append({"generator": pars["name"], "maximum_score_error": float(np.max(abs(compressed["score"][:, 0] - scores)))})
    best, per_member = profile_family(scope, a, contrast, templates, contrast.data(y)[:, None], "RUN", outside)
    candidate = int(np.argmin(abs(a["periods"] / scope["fixed_noise_peak_period_days"] - 1)))
    # The family member equal to the released noise should give back the fixed-noise statistic.
    released = scope["released_red"] or {"log10_amplitude": None, "gamma": None}
    same = [i for i, m in enumerate(scope["family"]) if m["white_scale"] == 1.0
            and all(x == 1.0 for x in m.get("group_scales", [])) and not any(m.get("group_equads_us", []))
            and m["log10_amplitude"] == released["log10_amplitude"] and m["gamma"] == released["gamma"]]
    at_candidate = [null - score[candidate] for null, score, _ in per_member]
    member = int(np.argmin(at_candidate))
    statistic, threshold = float(best["statistic"][0]), frozen["threshold"]
    profile = best["null"][0] - np.min([null - score for null, score, _ in per_member], axis=0)
    np.savez_compressed(out / "periodogram.npz", periods=a["periods"], joint_statistic=profile)
    ensemble = np.load(root / "calibration-ensemble.npz")["statistic"]
    tails = {s["generator"]: (int(np.sum(ensemble[s["start"]:s["stop"]] >= statistic)) + 1) / (s["count"] + 1)
             for s in cal.read(root / "calibration.json")["experiments"] if s["kind"] == "validation"}
    null_pars, signal_pars = scope["family"][int(best["null_member"][0])], scope["family"][int(best["signal_member"][0])]
    cal.write(out / "result.json", {
        "status": "JOINT_NOISE_CROSSING" if statistic > threshold else "BELOW_JOINT_NOISE_THRESHOLD",
        "target": scope["target"], "threshold": threshold, "peak_statistic": statistic,
        "peak_period_days": float(a["periods"][best["peak"][0]]),
        "fixed_noise_period_days": float(a["periods"][candidate]),
        "statistic_at_fixed_noise_period": float(best["null"][0] - at_candidate[member]),
        "amplitude_at_fixed_noise_period_us": float(np.linalg.norm(per_member[member][2][candidate]) * 1e6),
        "fixed_noise_statistic": scope["fixed_noise_statistic"], "fixed_noise_threshold": scope["fixed_noise_threshold"],
        "released_noise_member_statistic_at_fixed_noise_period": float(per_member[same[0]][1][candidate]) if same else None,
        "outside_dimension": scope.get("outside_dimension", 0),
        "null_noise": null_pars, "signal_noise": signal_pars,
        "null_fit_on_boundary": on_boundary(null_pars, scope), "signal_fit_on_boundary": on_boundary(signal_pars, scope),
        "validation_tail_plus_one_by_generator": tails, "direct_fit_checks": checks,
        "sensitivity_sha256": frozen["sensitivity_sha256"],
        "half_detection_amplitude_by_period": cal.read(root / "sensitivity.json")["summary"],
        "execution_freeze_sha256": cal.digest(root / "execution-freeze.json"),
        "periodogram_sha256": cal.digest(out / "periodogram.npz"),
        "interpretation": "Conditional on the declared finite noise grid and generators; not a detection, a global "
                          "false-alarm probability or independent confirmation",
        "completed_utc": mpta.now()})
    print("COMPLETE", scope["target"], "statistic", statistic, "threshold", threshold, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "calibrate", "freeze", "run"])
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    data, root = args.data.resolve(), args.root.resolve()
    if args.action == "prepare":
        prepare(data, root, args.config.resolve())
    else:
        {"calibrate": calibrate, "freeze": freeze, "run": run}[args.action](data, root)


if __name__ == "__main__":
    main()
