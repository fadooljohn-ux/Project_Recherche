"""Reusable, offline calibration of prepared pulsar timing datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import tempfile
from pathlib import Path

import numpy as np
import scipy
from scipy.linalg import eigvalsh
from scipy.optimize import brentq
from scipy.stats import ncx2

from pulsar_pilot.pilot1_runtime import (
    build_search_frequency_grid,
    prepare_covariance_gls_scanner,
)

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = REPO.parent / "Project Recherche Data/calibration-cache"
SCHEMA = "recherche-target-calibration-v1"
DEFAULT_POLICY = {
    "minimum_period_days": 10.0,
    "maximum_period_days": 400.0,
    "oversampling": 5,
    "false_alarm_probability": 0.01,
    "search_count": 1,
    "null_count": 4096,
    "seed": 19371257,
    "minimum_retained_power": 0.2,
    "maximum_condition_number": 1e10,
    "detection_probability": 0.95,
}


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def implementation():
    paths = [Path(__file__), *(REPO / "src").rglob("*.py")]
    return {
        "files": {p.relative_to(REPO).as_posix(): digest(p) for p in sorted(paths)},
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "machine": platform.machine(),
        "longdouble_mantissa": int(np.finfo(np.longdouble).nmant),
    }


def validate_policy(policy):
    if set(policy) != set(DEFAULT_POLICY):
        raise ValueError("Calibration policy has missing or unknown fields")
    if any(isinstance(v, bool) or not np.isfinite(v) for v in policy.values()):
        raise ValueError("Calibration policy values must be finite numbers")
    for key in ("oversampling", "search_count", "null_count", "seed"):
        if not isinstance(policy[key], int):
            raise TypeError(f"{key} must be an integer")
    if not 0 < policy["minimum_period_days"] < policy["maximum_period_days"]:
        raise ValueError("Period bounds must be positive and increasing")
    if min(policy[k] for k in ("oversampling", "search_count", "null_count")) < 1:
        raise ValueError("Counts must be positive")
    if policy["seed"] < 0 or policy["maximum_condition_number"] <= 1:
        raise ValueError("Invalid seed or condition-number limit")
    for key in ("false_alarm_probability", "minimum_retained_power", "detection_probability"):
        if not 0 < policy[key] < 1:
            raise ValueError(f"{key} must be between zero and one")
    if policy["null_count"] * policy["false_alarm_probability"] < 10:
        raise ValueError("Use enough nulls to expect at least ten samples in the selected tail")
    if policy["detection_probability"] <= policy["false_alarm_probability"]:
        raise ValueError("Detection probability must exceed false-alarm probability")


def validate_arrays(arrays):
    if set(arrays) != {"times", "covariance", "design", "baseline_design"}:
        raise ValueError("Prepared arrays require times, covariance, design, baseline_design")
    # Use names explicitly; dictionaries loaded from external NPZ need not be ordered.
    t, c, d, b = (
        np.asarray(arrays[k], dtype=float)
        for k in ("times", "covariance", "design", "baseline_design")
    )
    if any(not np.all(np.isfinite(a)) for a in (t, c, d, b)):
        raise ValueError("Prepared arrays contain nonfinite values")
    if t.ndim != 1 or len(t) < 3 or np.ptp(t) <= 0:
        raise ValueError("At least three TOAs spanning positive time are required")
    if c.ndim != 2 or c.shape[0] != c.shape[1] or c.shape[0] < len(t):
        raise ValueError("Covariance must be square with at least one row per TOA")
    for name, a in (("design", d), ("baseline_design", b)):
        if a.ndim != 2 or a.shape[0] != len(c) or not 0 < a.shape[1] < len(c):
            raise ValueError(f"{name} has incompatible dimensions")
    if not np.allclose(c, c.T, rtol=1e-10, atol=1e-18):
        raise ValueError("Covariance must be symmetric")
    np.linalg.cholesky(c)
    return dict(zip(("times", "covariance", "design", "baseline_design"), (t, c, d, b)))


def create_profile(output, target, arrays, provenance, policy=None, reference_epoch=None):
    """Store only calibration inputs; never copy observed residuals into a profile."""
    arrays = validate_arrays(arrays)
    policy = {**DEFAULT_POLICY, **(policy or {})}
    validate_policy(policy)
    if (
        not target.strip()
        or not provenance.get("noise_model")
        or not provenance.get("timing_model")
    ):
        raise ValueError("Target, noise-model description and timing-model provenance are required")
    epoch = float(np.mean(arrays["times"]) if reference_epoch is None else reference_epoch)
    if not np.isfinite(epoch):
        raise ValueError("Reference epoch must be finite MJD TDB")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output / "arrays.npz", **arrays)
    profile = {
        "schema": SCHEMA,
        "target": target,
        "arrays": "arrays.npz",
        "arrays_sha256": digest(output / "arrays.npz"),
        "reference_epoch_mjd_tdb": epoch,
        "policy": policy,
        "provenance": provenance,
        "layout": "first len(times) rows are TOA seconds; remaining rows are auxiliary measurements",
        "observed_residuals_included": False,
    }
    write(output / "profile.json", profile)
    return output / "profile.json"


def load_profile(path):
    path = Path(path).resolve()
    profile = read(path)
    if profile.get("schema") != SCHEMA or profile.get("observed_residuals_included") is not False:
        raise ValueError("Unsupported calibration profile")
    validate_policy(profile["policy"])
    if profile["arrays"] != "arrays.npz":
        raise ValueError("Profile arrays must be its local arrays.npz")
    arrays_path = path.parent / profile["arrays"]
    if digest(arrays_path) != profile["arrays_sha256"]:
        raise ValueError("Profile arrays changed; ingest the revised dataset into a new profile")
    with np.load(arrays_path, allow_pickle=False) as archive:
        arrays = validate_arrays({k: archive[k] for k in archive.files})
    if not np.isfinite(profile["reference_epoch_mjd_tdb"]):
        raise ValueError("Invalid reference epoch")
    return profile, arrays


def projection_map(scanner, baseline, policy):
    """Additional timing loss after dispersion/instrument separation, at every grid cell."""
    # The baseline must be a subspace of the full design for a retention ratio to be meaningful.
    q = scanner.timing_projection_basis
    b = baseline.timing_projection_basis
    if np.linalg.norm(b - q @ (q.T @ b)) > 1e-7 * max(1, np.linalg.norm(b)):
        raise ValueError("Baseline nuisance design is not contained in the full timing design")
    retained = np.zeros(len(scanner.frequencies_per_day))
    for i, (before, after) in enumerate(
        zip(
            baseline.projected_whitened_templates.transpose(1, 0, 2),
            scanner.projected_whitened_templates.transpose(1, 0, 2),
            strict=True,
        )
    ):
        gram = before.T @ before
        if np.linalg.cond(gram) < policy["maximum_condition_number"]:
            try:
                retained[i] = np.clip(eigvalsh(after.T @ after, gram)[0], 0, 1)
            except np.linalg.LinAlgError:
                pass  # An unidentifiable baseline cell is excluded, not assigned sensitivity.
    eligible = (
        (retained > policy["minimum_retained_power"])
        & np.isfinite(scanner.template_condition_numbers)
        & (scanner.template_condition_numbers < policy["maximum_condition_number"])
    )
    return eligible, retained


def null_calibration(scanner, eligible, policy):
    generator = np.random.default_rng(policy["seed"])
    maxima = []
    for start in range(0, policy["null_count"], 128):
        size = min(128, policy["null_count"] - start)
        white = generator.standard_normal((len(scanner.covariance_cholesky), size))
        rhs = np.einsum("nfi,nb->fib", scanner.projected_whitened_templates, white)
        stat = np.einsum("fib,fij,fjb->fb", rhs, scanner.template_gram_pseudoinverse, rhs)
        maxima.extend(np.max(stat[eligible], axis=0).tolist())
    alpha = policy["false_alarm_probability"]
    empirical = float(np.quantile(maxima, 1 - alpha, method="higher"))
    # Count the full grid, conservatively retaining masked cells in the union bound.
    bound = float(2 * np.log(policy["search_count"] * len(eligible) / alpha))
    return np.asarray(maxima), {
        "threshold": max(empirical, bound),
        "empirical_quantile": empirical,
        "analytical_bound": bound,
        "false_alarm_probability": alpha,
        "null_count": len(maxima),
        "seed": policy["seed"],
        "noise_assumption": "Gaussian with fixed supplied covariance and timing design",
        "scope": "fixed linear searches; does not establish FAP after adaptive orbit fitting",
    }


def sensitivity(scanner, eligible, threshold, probability):
    """Phase extrema of on-grid circular amplitude needed for the requested detection probability."""
    upper = max(1.0, threshold)
    while ncx2.sf(threshold, 2, upper) < probability:
        upper *= 2
    noncentrality = brentq(lambda x: ncx2.sf(threshold, 2, x) - probability, 0, upper)
    grams = np.einsum(
        "nfi,nfj->fij", scanner.projected_whitened_templates, scanner.projected_whitened_templates
    )
    eigenvalues = np.linalg.eigvalsh(grams)
    best = np.full(len(eligible), np.nan)
    worst = best.copy()
    usable = eligible & (eigenvalues[:, 0] > 0)
    best[usable] = np.sqrt(noncentrality / eigenvalues[usable, 1]) * 1e6
    worst[usable] = np.sqrt(noncentrality / eigenvalues[usable, 0]) * 1e6
    return best, worst


def verify_cache(root, binding):
    receipt = read(root / "receipt.json")
    if receipt["binding"] != binding or receipt["status"] != "CALIBRATED_CONDITIONAL":
        raise ValueError("Cached calibration binding differs")
    expected_files = {"calibration.json", "projection-and-sensitivity.npz", "null-maxima.npy"}
    if set(receipt["artifacts"]) != expected_files:
        raise ValueError("Cached calibration inventory is incomplete")
    for name, expected in receipt["artifacts"].items():
        if digest(root / name) != expected:
            raise ValueError(f"Cached calibration changed: {name}")
    return receipt


def run(profile_path, cache=DEFAULT_CACHE):
    profile, arrays = load_profile(profile_path)
    binding = {"profile": profile, "implementation": implementation()}
    key = hashlib.sha256(canonical(binding)).hexdigest()
    cache = Path(cache).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / key
    if destination.exists():
        receipt = verify_cache(destination, binding)
        return {"cache_hit": True, "path": str(destination), **receipt["summary"]}
    policy = profile["policy"]
    times = arrays["times"]
    frequencies, grid = build_search_frequency_grid(
        times, policy["minimum_period_days"], policy["maximum_period_days"], policy["oversampling"]
    )
    make = prepare_covariance_gls_scanner
    args = (times, frequencies, profile["reference_epoch_mjd_tdb"])
    scanner = make(arrays["covariance"], arrays["design"], *args)
    baseline = make(arrays["covariance"], arrays["baseline_design"], *args)
    eligible, retained = projection_map(scanner, baseline, policy)
    if not np.any(eligible):
        raise ValueError(
            "No identifiable frequency remains; inspect timing design and period range"
        )
    print(
        f"Calibrating {profile['target']}: {len(frequencies)} cells, "
        f"{policy['null_count']} fixed-noise nulls",
        flush=True,
    )
    maxima, calibration = null_calibration(scanner, eligible, policy)
    best, worst = sensitivity(
        scanner, eligible, calibration["threshold"], policy["detection_probability"]
    )
    summary = {
        "status": "CALIBRATED_CONDITIONAL",
        "target": profile["target"],
        "cache_key": key,
        "threshold": calibration["threshold"],
        "frequency_count": len(frequencies),
        "eligible_cells": int(eligible.sum()),
        "excluded_cells": int((~eligible).sum()),
        "timing_rank": scanner.timing_design_rank,
        "median_worst_phase_amplitude_us": float(np.nanmedian(worst)),
        "observed_search_executed": False,
    }
    # Publish only a complete cache entry; interrupted work cannot be mistaken for a hit.
    with tempfile.TemporaryDirectory(prefix=".pending-", dir=cache) as temporary:
        root = Path(temporary)
        np.save(root / "null-maxima.npy", maxima)
        np.savez_compressed(
            root / "projection-and-sensitivity.npz",
            frequencies=frequencies,
            eligible=eligible,
            retained_power=retained,
            best_phase_amplitude_us=best,
            worst_phase_amplitude_us=worst,
        )
        write(
            root / "calibration.json",
            {
                **calibration,
                "grid": grid,
                "summary": summary,
                "sensitivity": {
                    "detection_probability": policy["detection_probability"],
                    "definition": "on-grid circular signal, best/worst phase at each eligible period",
                    "limitations": "fixed linear timing/noise model; excludes off-grid loss and nonlinear multi-planet confusion",
                    "excluded_cell_amplitudes": "NaN; not a finite sensitivity estimate",
                },
            },
        )
        write(
            root / "receipt.json",
            {
                "schema": SCHEMA,
                "status": summary["status"],
                "binding": binding,
                "summary": summary,
                "artifacts": {p.name: digest(p) for p in sorted(root.iterdir())},
            },
        )
        if destination.exists():
            verify_cache(destination, binding)
        else:
            root.rename(destination)
    return {"cache_hit": False, "path": str(destination), **summary}


def import_npz(args):
    """Generic ingestion contract, independent of pulsar identity and known companions."""
    with np.load(args.context, allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in ("times", "covariance", "design")}
        if "baseline_design" in archive:
            arrays["baseline_design"] = archive["baseline_design"]
        elif args.baseline_columns:
            indices = [int(i) for i in args.baseline_columns.split(",")]
            if len(set(indices)) != len(indices) or any(i < 0 for i in indices):
                raise ValueError("Baseline columns must be unique nonnegative indices")
            arrays["baseline_design"] = arrays["design"][:, indices]
        else:
            raise ValueError(
                "Provide baseline_design or --baseline-columns (offset and DM/instrument columns)"
            )
    return create_profile(
        args.output,
        args.target,
        arrays,
        {
            "context_sha256": digest(args.context),
            "timing_model": args.timing_model,
            "noise_model": args.noise_model,
            "source_context": str(args.context.resolve()),
        },
        {"minimum_period_days": args.minimum_period, "maximum_period_days": args.maximum_period},
    )


def import_b1257(data, output):
    context = data / "prepared/context.npz"
    receipt = read(data / "prepared/receipt.json")
    if digest(context) != receipt["context_sha256"]:
        raise ValueError("B1257 prepared context differs from its receipt")
    with np.load(context, allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in ("times", "covariance", "design")}
    arrays["baseline_design"] = np.column_stack(
        [np.ones(len(arrays["times"])), arrays["design"][:, -receipt["epoch_dm_columns"] :]]
    )
    return create_profile(
        output,
        receipt["target"],
        arrays,
        {
            "timing_model": "B1257 no-planets TDB model with per-epoch DM",
            "noise_model": "supplied TOA errors scaled by sqrt(1.2785), independent Gaussian",
            "preparation_receipt": receipt,
        },
        {"search_count": 3, "seed": 1257122026},
    )


def import_b1937(data, output):
    """Export the existing wideband preparation, with no observed scan or fit."""
    from pint.fitter import WidebandTOAFitter
    from recherche_operator import doctor

    from pulsar_pilot.pilot2_offline_resources import OfflineRuntimeBoundary
    from pulsar_pilot.pilot2_runtime_core import prepare_context

    doctor(data)
    resources = read(data / "metadata/resources.json")
    # Preparation logs go into this new calibration work area, outside historical run directories.
    with tempfile.TemporaryDirectory(prefix="calibration-preparation-", dir=data) as temporary:
        with OfflineRuntimeBoundary(data, resources) as boundary:
            context = prepare_context(
                data,
                [],
                resource_manifest=resources,
                resource_manifest_sha256=digest(data / "metadata/resources.json"),
                environment_manifest_sha256=digest(data / "metadata/development-environment.json"),
                setup_log_relative=str((Path(temporary) / "context.log").relative_to(data)),
                resource_boundary=boundary,
            )
            fitter = WidebandTOAFitter(context.toas, context.model)
            design = fitter.get_designmatrix()
            names = design.get_label_names(axis=1)
            indices = [
                i
                for i, name in enumerate(names)
                if name.lower().startswith(("offset", "dm", "jump"))
            ]
            if not indices:
                raise ValueError("Wideband dispersion/offset columns not identified")
            arrays = {
                "times": context.times,
                "covariance": fitter.get_noise_covariancematrix().matrix,
                "design": design.matrix,
                "baseline_design": design.matrix[:, indices],
            }
            trace = boundary.verify_trace()
            if trace["status"] != "pass":
                raise ValueError(f"Resource preparation failed: {trace['failures']}")
        profile = create_profile(
            output,
            "B1937+21",
            arrays,
            {
                "timing_model": "released B1937 wideband PINT model",
                "noise_model": "fixed full covariance from released wideband model",
                "input_binding": context.input_binding,
                "resource_trace": trace,
                "baseline_columns": [names[i] for i in indices],
            },
            {"minimum_period_days": 30.0, "maximum_period_days": 2000.0},
            reference_epoch=context.reference_epoch,
        )
        (profile.parent / "preparation.log").write_bytes(
            (Path(temporary) / "context.log").read_bytes()
        )
    return profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="create a target profile from prepared NPZ arrays")
    ingest.add_argument("--context", type=Path, required=True)
    ingest.add_argument("--target", required=True)
    ingest.add_argument("--timing-model", required=True)
    ingest.add_argument("--noise-model", required=True)
    ingest.add_argument("--baseline-columns")
    ingest.add_argument("--minimum-period", type=float, default=10)
    ingest.add_argument("--maximum-period", type=float, default=400)
    ingest.add_argument("--output", type=Path, required=True)
    for name in ("import-b1257", "import-b1937"):
        command = commands.add_parser(name, help="import an existing prepared target")
        command.add_argument("--data", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
    for name in ("run", "check"):
        command = commands.add_parser(name)
        command.add_argument("--profile", type=Path, required=True)
        command.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        if args.command == "ingest":
            result = {"profile": str(import_npz(args)), "status": "PREPARED"}
        elif args.command.startswith("import-"):
            importer = import_b1257 if args.command == "import-b1257" else import_b1937
            result = {
                "profile": str(importer(args.data.resolve(), args.output)),
                "status": "PREPARED",
            }
        elif args.command == "check":
            profile, _ = load_profile(args.profile)
            binding = {"profile": profile, "implementation": implementation()}
            key = hashlib.sha256(canonical(binding)).hexdigest()
            root = args.cache.resolve() / key
            receipt = verify_cache(root, binding)
            result = {"cache_hit": True, "path": str(root), **receipt["summary"]}
        else:
            result = run(args.profile, args.cache)
    except (ValueError, TypeError, OSError, KeyError, np.linalg.LinAlgError) as exc:
        parser.exit(2, f"Calibration error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
