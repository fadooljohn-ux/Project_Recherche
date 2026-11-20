"""The second-stage noise family and its white-scale term, on synthetic data."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import j1453_review as common
import joint_noise
import joint_noise_stage as stage

DECLARED = {"amplitude_offsets_dex": [-1.0, 0.0, 1.0], "gamma_offsets": [-1.0, 0.0, 6.0],
            "include_no_red": True, "white_scales": [0.9, 1.0, 1.2]}


def problem():
    rng = np.random.default_rng(7)
    times = np.sort(rng.uniform(55000, 57000, 60))
    rows = 75
    base = np.diag(rng.uniform(0.5, 2.0, rows)) * 1e-12
    design = np.zeros((rows, 4))
    design[:60, 0], design[:60, 1], design[:60, 2] = 1.0, times - times.mean(), (times - times.mean()) ** 2
    design[60:, 3] = 1.0
    design[:60, 3] = rng.standard_normal(60)
    arrays = {"times": times, "base_toa": base[:60, :60], "base_covariance": base, "design": design}
    return arrays, rng.multivariate_normal(np.zeros(rows), base)


def test_family_has_no_red_member_and_clips_slopes():
    family, slopes = stage.members([-13.0, 3.0], DECLARED)
    assert slopes == [2.0, 3.0, 7.0]
    assert len(family) == (1 + 3 * 3) * 3
    assert sum(m["log10_amplitude"] is None for m in family) == 3


def test_boundary_marks_grid_edges_but_not_the_centre_or_no_red():
    scope = {"family_declaration": DECLARED, "reference_log10_amplitude": -13.0, "gamma_grid": [2.0, 3.0, 7.0],
             "family": stage.members([-13.0, 3.0], DECLARED)[0]}
    centre = {"log10_amplitude": -13.0, "gamma": 3.0, "white_scale": 1.0}
    assert not stage.on_boundary(centre, scope)
    assert not stage.on_boundary({"log10_amplitude": None, "gamma": None, "white_scale": 1.0}, scope)
    assert stage.on_boundary({**centre, "white_scale": 1.2}, scope)
    assert stage.on_boundary({**centre, "log10_amplitude": -12.0}, scope)
    assert stage.on_boundary({**centre, "gamma": 7.0}, scope)


def test_compressed_statistic_with_white_scale_and_red_matches_direct_fit():
    arrays, y = problem()
    n, rows = 60, 75
    contrast = joint_noise.Contrast(arrays["base_covariance"], arrays["design"], n)
    common.REFERENCE = 56000.0
    periods = np.array([90.0, 150.0, 400.0])
    full = common.template(arrays["times"], periods, rows)
    templates = (contrast.B @ full.reshape(rows, -1)).reshape(contrast.dimension, -1, 2)
    pairs = []
    for pars in ({"log10_amplitude": None, "gamma": None, "white_scale": 0.9},
                 {"log10_amplitude": -12.5, "gamma": 3.0, "white_scale": 1.2}):
        extra = stage.variable_covariance(arrays, 8, pars)
        covariance = arrays["base_covariance"].copy()
        covariance[:n, :n] += extra
        compressed = joint_noise.evaluate(contrast.covariance(extra), templates, contrast.data(y)[:, None])
        direct = common.GLS(covariance, arrays["design"])
        scores, _ = direct.scan(y, direct.bank(full))
        np.testing.assert_allclose(compressed["score"][:, 0], scores, rtol=1e-7)
        pairs.append((np.sum(direct.project(y) ** 2) + direct.offset, compressed["null"][0]))
    # The objective, determinant included, changes by the same amount in both forms.
    np.testing.assert_allclose(pairs[1][0] - pairs[0][0], pairs[1][1] - pairs[0][1], rtol=1e-7)


def test_chain_samples_drop_the_first_quarter_and_pick_the_red_columns(tmp_path):
    names = ["P_efac", "P_red_noise_gamma", "P_red_noise_log10_A"]
    (tmp_path / "pars.txt").write_text("\n".join(names) + "\n")
    chain = np.column_stack([np.arange(40.0), 3 + np.arange(40.0) / 100, -15 + np.arange(40.0) / 10,
                             np.zeros((40, 4))])
    np.savetxt(tmp_path / "chain.txt", chain)
    samples, path = stage.chain_samples(tmp_path, {"chain": "chain.txt", "parameters": "pars.txt", "draws": 4}, 10.0)
    assert path == tmp_path / "chain.txt"
    np.testing.assert_allclose(samples, [[-14.0, 3.1], [-13.1, 3.19], [-12.1, 3.29], [-11.1, 3.39]])
    # The strongest tenth by power at 1/span is the last three of the thirty kept rows.
    strongest, _ = stage.chain_samples(tmp_path, {"chain": "chain.txt", "parameters": "pars.txt", "draws": 2,
                                                  "strongest_fraction": 0.1}, 10.0)
    np.testing.assert_allclose(strongest, [[-11.3, 3.37], [-11.1, 3.39]])


def test_chain_bound_drops_members_the_chain_excludes_and_moves_the_edge(tmp_path):
    (tmp_path / "pars.txt").write_text("P_red_noise_gamma\nP_red_noise_log10_A\n")
    rng = np.random.default_rng(3)
    # Steeper slopes allow less amplitude: uniform up to -12 at slope 2, up to -13.2 at slope 3.
    gamma = np.repeat([2.0, 3.0, 7.0], 4000)
    top = np.repeat([-12.0, -13.2, -15.0], 4000)
    np.savetxt(tmp_path / "chain.txt", np.column_stack([gamma, rng.uniform(-20, top)]))
    spec = {"chain": "chain.txt", "parameters": "pars.txt", "quantile": 0.99, "gamma_half_width": 0.5,
            "minimum_draws": 500}
    bound, _ = stage.chain_bound(tmp_path, spec, [2.0, 3.0, 7.0])
    assert -12.2 < bound[2.0] < -12.0 and -13.4 < bound[3.0] < -13.2 and bound[7.0] < -15.0
    family, _ = stage.members([-13.0, 3.0], DECLARED, bound)
    kept = {(m["log10_amplitude"], m["gamma"]) for m in family}
    lowest = -13.0 + min(DECLARED["amplitude_offsets_dex"])
    assert (lowest, 3.0) in kept and (-13.0, 3.0) not in kept and (-13.0, 2.0) in kept
    assert not any(g == 7.0 for _, g in kept) and (None, None) in kept
    scope = {"family_declaration": DECLARED, "reference_log10_amplitude": -13.0, "family": family,
             "gamma_grid": [2.0, 3.0, 7.0]}
    strongest = max(a for a, g in kept if g == 2.0)
    assert stage.on_boundary({"log10_amplitude": strongest, "gamma": 2.0, "white_scale": 1.0}, scope)
    with pytest.raises(ValueError):
        stage.chain_bound(tmp_path, {**spec, "minimum_draws": 5000}, [2.0])


def test_chain_generator_cycles_one_covariance_per_column():
    arrays, _ = problem()
    contrast = joint_noise.Contrast(arrays["base_covariance"], arrays["design"], 60)
    pars = {"white_scale": 1.0, "samples": [[-20.0, 3.0], [-11.5, 4.0]]}
    factors = stage.generator_factors(contrast, arrays, 8, pars)
    assert len(factors) == 2
    noise = stage.coloured(factors, np.random.default_rng(1), contrast.dimension, 400)
    assert noise.shape == (contrast.dimension, 400)
    # Columns drawn with the strong red draw carry far more variance than the negligible one.
    assert noise[:, 1::2].var() > 5 * noise[:, 0::2].var()


def test_subspace_compression_gives_the_dense_objectives():
    """A diagonal problem reduced to its timing, red and signal subspace selects and scores identically."""
    rng = np.random.default_rng(11)
    n, modes, epoch = 400, 6, 56000.0
    times = np.sort(np.repeat(rng.uniform(55000, 57000, 40), 10) + rng.uniform(0, 0.1, n))
    base = np.diag(rng.uniform(0.5, 2.0, n)) * 1e-12
    design = np.column_stack([np.ones(n), times - times.mean(), (times - times.mean()) ** 2])
    periods = np.array([70.0, 90.0, 150.0, 400.0])
    family, _ = stage.members([-12.6, 3.0], DECLARED)
    y = np.linalg.cholesky(base + stage.mpta.red_covariance(times, -12.4, 3.5, modes)) @ rng.standard_normal(n) * 1.1

    def profiles(arrays, data, outside, dimension):
        scope = {"family": family, "coverage": {"selected_modes": modes}, "outside_dimension": dimension}
        rows = len(arrays["base_covariance"])
        contrast = joint_noise.Contrast(arrays["base_covariance"], arrays["design"], rows)
        common.REFERENCE = epoch
        full = common.template(times, periods, n)
        if "reduction" in arrays:
            full = np.einsum("rn,nfk->rfk", arrays["reduction"], full)
        templates = (contrast.B @ full.reshape(rows, -1)).reshape(contrast.dimension, -1, 2)
        return stage.profile_family(scope, arrays, contrast, templates, contrast.data(data)[:, None], "TEST", outside)

    dense, dense_members = profiles({"times": times, "base_covariance": base, "base_toa": base, "design": design}, y, None, 0)
    reduction, weight = stage.subspace(times, base, design, periods, epoch, modes)
    rows = len(reduction)
    assert rows == 3 + 2 * modes + 2 * len(periods)
    arrays = {"times": times, "base_covariance": np.eye(rows), "base_toa": np.eye(rows), "design": reduction @ design,
              "reduction": reduction}
    small = reduction @ y
    outside = np.array([(weight * y) @ (weight * y) - small @ small])
    reduced, reduced_members = profiles(arrays, small, outside, n - rows)
    np.testing.assert_allclose(reduced["statistic"], dense["statistic"], rtol=1e-8)
    for key in ("null_member", "signal_member", "peak"):
        assert reduced[key][0] == dense[key][0]
    # Objectives differ only by one constant shared by every member.
    offsets = [a[0] - b[0] for a, b in zip(reduced_members, dense_members)]
    np.testing.assert_allclose(offsets, offsets[0], rtol=0, atol=1e-6)
    np.testing.assert_allclose([a[1] for a in reduced_members], [b[1] for b in dense_members], rtol=1e-7, atol=1e-9)


def test_joint_chain_draws_reproduce_released_white_and_factor_in_contrast_space(tmp_path):
    rng = np.random.default_rng(11)
    mjd = np.sort(rng.uniform(55000, 57000, 30))
    error, dm_error = rng.uniform(0.5, 2.0, 30), rng.uniform(1e-4, 1e-3, 30)
    backend = np.where(np.arange(30) % 2, "A_X", "B_X")
    lines = ["FORMAT 1", "C comment"] + [
        "f%d 1400.0 %.10f %r ao -pp_dm 10.0 -pp_dme %r -f %s" % (i, mjd[i], float(error[i]), float(dm_error[i]), backend[i])
        for i in range(30)]
    (tmp_path / "x.tim").write_text("\n".join(lines) + "\n")
    values = {"A_X": (1.1, 0.2, 0.9, 1e-4), "B_X": (0.8, 0.05, 1.2, 3e-4)}
    (tmp_path / "x.par").write_text("".join(
        "%s -f %s %r\n" % (key, name, v[i]) for name, v in values.items()
        for i, key in enumerate(("EFAC", "EQUAD", "DMEFAC", "DMEQUAD"))))
    base = np.diag(stage.white_variance(error, dm_error, backend, values))
    names = [b + s for b in ("A_X", "B_X") for s in ("_efac", "_log10_t2equad", "_dmefac", "_log10_dmequad")]
    (tmp_path / "pars.txt").write_text("\n".join(names + ["P_red_noise_gamma", "P_red_noise_log10_A"]) + "\n")
    row = [1.1, np.log10(0.2e-6), 0.9, -4.0, 0.8, np.log10(0.05e-6), 1.2, np.log10(3e-4), 3.0, -14.0]
    chain = np.tile(row, (8, 1))
    chain[-1, 0] = 2.2                      # the last draw doubles one backend's EFAC
    np.savetxt(tmp_path / "chain.txt", chain)
    spec = {"chain": "chain.txt", "parameters": "pars.txt", "draws": 3, "joint_white": {"tim": "x.tim", "par": "x.par"}}
    red, white, mismatch, paths = stage.chain_joint(tmp_path, spec, base)
    assert mismatch < 1e-9 and len(paths) == 3 and red[0] == [-14.0, 3.0]
    np.testing.assert_allclose(white[0], np.diag(base), rtol=1e-9)
    odd = np.tile(np.arange(30) % 2 == 1, 2)
    np.testing.assert_allclose(white[2][:30][odd[:30]], 4 * np.diag(base)[:30][odd[:30]], rtol=1e-9)
    np.testing.assert_allclose(white[2][30:], np.diag(base)[30:], rtol=1e-9)
    with pytest.raises(ValueError):
        stage.chain_joint(tmp_path, spec, base * 1.01)
    design = np.zeros((60, 3))
    design[:30, 0], design[:30, 1], design[30:, 2] = 1.0, mjd - mjd.mean(), 1.0
    design[:30, 2] = rng.standard_normal(30)
    contrast = joint_noise.Contrast(base, design, 30)
    arrays = {"times": mjd, "base_toa": base[:30, :30], "base_covariance": base, "design": design, "white__g": white}
    joint = stage.generator_factors(contrast, arrays, 4, {"samples": red, "white_key": "white__g", "white_scale": 1.0})
    plain = stage.generator_factors(contrast, arrays, 4, {"samples": red[:1], "white_scale": 1.0})
    np.testing.assert_allclose(joint[0] @ joint[0].T, plain[0] @ plain[0].T, rtol=1e-7, atol=1e-9)
    assert np.trace(joint[2] @ joint[2].T) > np.trace(joint[0] @ joint[0].T)


def test_receiver_white_scales_act_on_their_own_group_only():
    declared = {**DECLARED, "receiver_white": {"groups": {"A_X": "a", "B_X": "b"}, "scales": [0.8, 1.0, 1.5]}}
    family, _ = stage.members([-13.0, 3.0], declared)
    assert len(family) == (1 + 3 * 3) * 9 and all(m["white_scale"] == 1.0 for m in family)
    floored = {**DECLARED, "receiver_white": {**declared["receiver_white"], "equads_us": {"a": [0.0, 2.0]}}}
    with_floor, _ = stage.members([-13.0, 3.0], floored)
    assert len(with_floor) == 2 * len(family)
    arrays, _ = problem()
    arrays["white_group"] = np.arange(60) % 2
    pars = {"log10_amplitude": None, "gamma": None, "white_scale": 1.0, "group_scales": [1.0, 1.5]}
    extra = np.diag(stage.variable_covariance(arrays, 8, pars))
    base = np.diag(arrays["base_toa"])
    np.testing.assert_allclose(extra[0::2], 0, atol=1e-30)
    np.testing.assert_allclose(extra[1::2], 1.25 * base[1::2])
    scope = {"family_declaration": declared, "reference_log10_amplitude": -13.0, "gamma_grid": [2.0, 3.0, 7.0],
             "family": family}
    assert stage.on_boundary(pars, scope)
    assert not stage.on_boundary({**pars, "group_scales": [1.0, 1.0]}, scope)
    floor = {**pars, "group_scales": [1.0, 1.0], "group_equads_us": [0.0, 2.0]}
    extra = np.diag(stage.variable_covariance(arrays, 8, floor))
    np.testing.assert_allclose(extra[0::2], 0, atol=1e-30)
    np.testing.assert_allclose(extra[1::2], 4e-12)
