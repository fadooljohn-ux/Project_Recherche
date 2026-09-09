"""Three bounded follow-up checks; completed stages are read, never rerun."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import chi2, ncx2

import j1453_review as common
import mpta_batch as mpta
import target_calibration as cal

REPO = mpta.REPO
ROOT = REPO.parent / 'Project Recherche Data/j1752-focused-review-20260909'
OUT = REPO / 'results/research/j1752-focused-review-20260909'
SOURCE = ROOT.parent / 'utmost-batch04-20260909/J1752-2806'
FIRST = ROOT.parent / 'j1752-deep-review-20260909'
TPA = ROOT.parent / 'tpa-batch09-20260908/J1752-2806'


def save(name, value):
    value = {**value, 'completed_utc': mpta.now(), 'code_sha256': cal.digest(__file__)}
    cal.write(ROOT / name, value)
    cal.write(OUT / name, value)
    return value


def inputs():
    profile, a = cal.load_profile(SOURCE / 'profile/profile.json')
    common.REFERENCE = profile['reference_epoch_mjd_tdb']
    y = np.load(SOURCE / 'prepared/observed.npz')['residuals']
    meta = np.load(SOURCE / 'prepared/metadata.npz')
    noise = cal.read(SOURCE / 'prepared/receipt.json')['noise_parameters']
    return a, y, meta, noise


def ensure_scope():
    _, _, _, noise = inputs()
    old = cal.read(FIRST / 'scope.json')
    paths = [SOURCE / 'run01/result.json', SOURCE / 'profile/profile.json',
             SOURCE / 'prepared/observed.npz', SOURCE / 'profile/arrays.npz',
             SOURCE / 'prepared/metadata.npz', TPA / 'profile/profile.json',
             TPA / 'profile/arrays.npz', TPA / 'prepared/observed.npz',
             FIRST / 'step3.json', FIRST / 'review-arrays.npz']
    scope = dict(target='J1752-2806', modes=[int(noise['TNREDC']), 32, 64],
                 log10_amplitude_bounds=[float(noise['TNREDAMP'])-1, float(noise['TNREDAMP'])+1],
                 gamma_bounds=[0., 7.], period_bounds=old['local_period_days'],
                 profile_points=161, starts='Published amplitude/slope; slope+1; amplitude-0.5 dex',
                 null_generators=['released', 'published_red64', 'continuous_best_null'],
                 null_count_each=512, null_seed=2026091752, propagation_seed=2026091753,
                 propagation_draws_per_basis=2048,
                 frozen_family=old['noise_family'], first_review_seed=old['seed'],
                 reuse='First review steeper-red64 null realizations reused without rerun',
                 objective='Timing-marginalized Gaussian objective; same timing prior measure; sinusoid coefficients profiled',
                 propagation='Uniform local-period grid weighted by exp(-profile delta objective/2); conditional Gaussian coefficients at each period; plug-in noise fit; not posterior draws',
                 inputs={str(p): cal.digest(p) for p in paths},
                 limitations='White noise fixed. Local candidate period only. No global significance, new blind search, binary model or full noise posterior.')
    if (ROOT / 'scope.json').exists():
        previous = cal.read(ROOT / 'scope.json')
        assert all(previous[k] == v for k, v in scope.items()), 'Bound scope changed'
    else:
        save('scope.json', scope)
    return scope


def covariance(t, white, modes, pars):
    return np.diag(white) + mpta.red_covariance(t, pars[0], pars[1], modes)


def joint_fits(scope):
    if (ROOT / 'joint.json').exists():
        return cal.read(ROOT / 'joint.json')
    a, y, meta, noise = inputs()
    t, x, white = a['times'], a['design'], meta['white_variance']
    initial = np.array([float(noise['TNREDAMP']), float(noise['TNREDGAM'])])
    bounds = [scope['log10_amplitude_bounds'], scope['gamma_bounds']]
    periods = np.linspace(*scope['period_bounds'], scope['profile_points'])
    starts = [initial, initial + [0, 1], initial + [-.5, 0]]
    records = []
    for modes in scope['modes']:
        checkpoint = ROOT / f'joint-m{modes}.json'
        if checkpoint.exists():
            records.append(cal.read(checkpoint))
            continue

        def evaluate(pars, period=None, details=False):
            g = common.GLS(covariance(t, white, modes, pars), x)
            null = float(np.sum(g.project(y)**2) + g.offset)
            fit = None if period is None else g.fit(y, t, period)
            q = null if fit is None else null - fit['delta_chi2']
            return (q, fit) if details else q

        def optimize(period, candidates):
            attempts = [minimize(lambda p: evaluate(p, period), np.clip(s, np.array(bounds)[:, 0], np.array(bounds)[:, 1]),
                                 method='L-BFGS-B', bounds=bounds,
                                 options={'ftol': 1e-12, 'gtol': 1e-5, 'maxiter': 120}) for s in candidates]
            successful = [v for v in attempts if v.success and np.isfinite(v.fun)]
            if not successful:
                raise RuntimeError(f'No converged fit: modes={modes}, period={period}: {[v.message for v in attempts]}')
            r = min(successful, key=lambda v: v.fun)
            return r, [dict(success=bool(v.success), objective=float(v.fun), message=str(v.message)) for v in attempts]

        null, attempts = optimize(None, starts)
        profiles = []
        for index, period in enumerate(periods):
            r, _ = optimize(period, [null.x, initial])
            q, fit = evaluate(r.x, period, True)
            profiles.append(dict(period_days=float(period), objective=q, noise=r.x.tolist(), fit=fit))
        k = int(np.argmin([p['objective'] for p in profiles]))
        # Refine the best sampled basin jointly in period and noise parameters.
        pbounds = [periods[max(0, k-1)], periods[min(len(periods)-1, k+1)]]
        fine = minimize(lambda z: evaluate(z[:2], z[2]), profiles[k]['noise']+[float(periods[k])],
                        method='L-BFGS-B', bounds=bounds+[pbounds],
                        options={'ftol': 1e-12, 'gtol': 1e-5, 'maxiter': 160})
        if not fine.success:
            raise RuntimeError(f'Joint refinement failed for {modes}: {fine.message}')
        q, fit = evaluate(fine.x[:2], fine.x[2], True)
        support = periods[np.array([p['objective'] for p in profiles]) <= q+3.841458820694124]
        record = dict(modes=modes, shortest_red_fourier_period_days=float(np.ptp(t)/modes),
                      null_noise=null.x.tolist(), null_objective=float(null.fun), null_attempts=attempts,
                      signal_noise=fine.x[:2].tolist(), signal_objective=q,
                      joint_statistic=float(null.fun-q), fit=fit, profile=profiles,
                      local_delta_3_84_envelope_days=[float(support.min()), float(support.max())],
                      profile_support_reaches_edge=bool(support.min()==periods[0] or support.max()==periods[-1]),
                      null_at_bound=bool(np.any(np.minimum(abs(null.x-np.array(bounds)[:,0]), abs(null.x-np.array(bounds)[:,1]))<1e-4)),
                      signal_at_bound=bool(np.any(np.minimum(abs(fine.x[:2]-np.array(bounds)[:,0]), abs(fine.x[:2]-np.array(bounds)[:,1]))<1e-4)))
        save(checkpoint.name, record)
        records.append(record)
        print('JOINT', modes, 'stat', record['joint_statistic'], 'period', fit['period_days'], 'null', null.x, flush=True)
    ni = int(np.argmin([r['null_objective'] for r in records]))
    si = int(np.argmin([r['signal_objective'] for r in records]))
    return save('joint.json', dict(models=records, best_null_modes=records[ni]['modes'],
                                 best_signal_modes=records[si]['modes'],
                                 family_joint_statistic=records[ni]['null_objective']-records[si]['signal_objective'],
                                 significance='Not calibrated; local continuous-profile diagnostic only'))


def null_generators(scope, joint):
    if (ROOT / 'null-generators.json').exists():
        return cal.read(ROOT / 'null-generators.json')
    a, y, meta, noise = inputs()
    t, x, white, radio = a['times'], a['design'], meta['white_variance'], meta['radio']
    first = cal.read(FIRST / 'step3.json')
    prior_arrays = np.load(FIRST / 'review-arrays.npz')
    original = np.load(SOURCE / 'run01/periodogram.npz')
    refined = cal.read(FIRST / 'step1.json')['refined']['period_days']
    periods = np.unique(np.r_[1/original['frequencies'][original['eligible']], prior_arrays['periods'], refined])
    h = common.template(t, periods, len(t))
    models = []
    for name, modes, scale, dgamma, chrom in scope['frozen_family']:
        if name == 'released':
            c = a['covariance']
        else:
            red = mpta.red_covariance(t, float(noise['TNREDAMP'])+np.log10(scale), float(noise['TNREDGAM'])+dgamma, modes)
            weight = (835./radio)**chrom
            c = np.diag(white)+red*weight[:,None]*weight[None,:]
        g = common.GLS(c, x)
        models.append((g, g.bank(h)))
    def statistic(samples):
        bestnull = np.full(samples.shape[1], np.inf)
        bestsignal = bestnull.copy()
        for g, (z, inv) in models:
            yp = g.project(samples)
            q = np.sum(yp*yp, axis=0)+g.offset
            cross = (z.reshape(len(t), -1).T@yp).reshape(len(periods), 2, samples.shape[1])
            score = np.einsum('fik,fij,fjk->fk', cross, inv, cross, optimize=True)
            bestnull = np.minimum(bestnull, q)
            bestsignal = np.minimum(bestsignal, q-np.max(score, axis=0))
        return bestnull-bestsignal
    np.testing.assert_allclose(statistic(y[:,None])[0], first['global_family_statistic'], rtol=1e-9)
    best = next(r for r in joint['models'] if r['modes']==joint['best_null_modes'])
    generators = [a['covariance'], covariance(t, white, 64, [float(noise['TNREDAMP']),float(noise['TNREDGAM'])]),
                  covariance(t, white, best['modes'], best['null_noise'])]
    records = []
    arrays = {'previous_steeper64': prior_arrays['simulation_statistic'][:512]}
    reused = dict(name='previous_steeper64', reused=True, null_count=512, null_exceedances=first['null_exceedances'],
                  diagnostic_p_plus_one=first['diagnostic_p_plus_one'], source_sha256=cal.digest(FIRST/'step3.json'))
    records.append(reused)
    threshold = first['candidate_family_statistic']
    for i, (name, cov) in enumerate(zip(scope['null_generators'], generators)):
        checkpoint = ROOT/f'null-{name}.json'
        if checkpoint.exists():
            records.append(cal.read(checkpoint))
            arrays[name] = np.load(ROOT/f'null-{name}.npy')
            continue
        rng = np.random.default_rng(scope['null_seed']+i)
        sim = statistic(np.linalg.cholesky(cov)@rng.standard_normal((len(t),512)))
        arrays[name] = sim
        count = int(np.sum(sim>=threshold))
        np.save(ROOT/f'null-{name}.npy', sim)
        record = save(checkpoint.name, dict(name=name, reused=False, seed=scope['null_seed']+i,
                      null_count=512, null_exceedances=count, diagnostic_p_plus_one=(count+1)/513,
                      observed_candidate_statistic=threshold,
                      q50_q90_q99=np.quantile(sim,[.5,.9,.99]).tolist()))
        records.append(record)
        print('NULL', name, count, '/512', flush=True)
    np.savez_compressed(ROOT/'null-arrays.npz', **arrays)
    worst = max(records, key=lambda r:r['diagnostic_p_plus_one'])
    return save('null-generators.json', dict(generators=records, observed_candidate_statistic=threshold,
                selected_generator_for_summary=worst['name'], null_count=512,
                null_exceedances=worst['null_exceedances'], diagnostic_p_plus_one=worst['diagnostic_p_plus_one'],
                summary_rule='Largest conditional plus-one tail among four declared generators; counts not pooled',
                limitations='Sensitivity analysis of the FIRST review statistic. No continuous refitting in these simulations; no global FAP calibration.'))


def propagate(scope, joint):
    if (ROOT/'propagation.json').exists():
        return cal.read(ROOT/'propagation.json')
    a, y, _, _ = inputs()
    _, ta = cal.load_profile(TPA/'profile/profile.json')
    ty = np.load(TPA/'prepared/observed.npz')['residuals']
    gt = common.GLS(ta['covariance'], ta['design'])
    original_period = cal.read(FIRST/'step1.json')['refined']['period_days']
    checkpoints = np.array([min(ta['times']),np.median(ta['times']),max(ta['times'])])
    n = scope['propagation_draws_per_basis']
    output = []
    arrays = {}
    for mi, model in enumerate(joint['models']):
        profiles = model['profile']
        q = np.array([r['objective'] for r in profiles])
        weights = np.exp(-.5*(q-q.min())); weights /= weights.sum()
        rng = np.random.default_rng(scope['propagation_seed']+mi)
        indexes = rng.choice(len(profiles), n, p=weights)
        periods = np.array([profiles[i]['period_days'] for i in indexes])
        beta = np.zeros((n,2)); power=np.zeros(n); contrasts=np.zeros(n)
        for i in np.unique(indexes):
            mask = indexes==i; f=profiles[i]['fit'];p=f['period_days']
            cov = np.array(f['coefficient_covariance_us2'])
            draws = rng.multivariate_normal(f['sin_cos_us'],cov,int(mask.sum()))
            beta[mask] = draws
            b = gt.bank(common.template(ta['times'],[p],len(ty)))
            gram = np.linalg.pinv(b[1][0],rcond=1e-12)*1e-12
            noncentrality = np.einsum('ni,ij,nj->n',draws,gram,draws)
            power[mask] = ncx2.sf(chi2.isf(.01,2),2,np.maximum(noncentrality,0))
            tf = gt.fit(ty,ta['times'],p)
            tc = np.linalg.inv(np.array(tf['coefficient_covariance_us2']))
            diff = draws-np.array(tf['sin_cos_us'])
            contrasts[mask] = np.einsum('ni,ij,nj->n',diff,tc,diff)
        phase = 2*np.pi*(checkpoints[None,:]-common.REFERENCE)/periods[:,None]
        predictions = beta[:,0,None]*np.sin(phase)+beta[:,1,None]*np.cos(phase)
        phase_angle = (phase+np.arctan2(beta[:,1],beta[:,0])[:,None])%(2*np.pi)
        coherence = abs(np.mean(np.exp(1j*phase_angle),axis=0))
        key=f'm{model["modes"]}'
        arrays.update({key+'_periods':periods,key+'_beta_us':beta,key+'_power':power,key+'_predictions_us':predictions})
        record=dict(modes=model['modes'],draws=n,seed=scope['propagation_seed']+mi,
                    period_q05_q50_q95_days=np.quantile(periods,[.05,.5,.95]).tolist(),
                    amplitude_q05_q50_q95_us=np.quantile(np.linalg.norm(beta,axis=1),[.05,.5,.95]).tolist(),
                    conditional_power_q05_q50_q95=np.quantile(power,[.05,.5,.95]).tolist(),
                    waveform_us_q05_q50_q95_at_tpa_dates=np.quantile(predictions,[.05,.5,.95],axis=0).tolist(),
                    phase_resultant_length_at_tpa_dates=coherence.tolist(),
                    fraction_drawn_waveforms_inside_TPA_95pct_coefficient_ellipse=float(np.mean(contrasts<=chi2.isf(.05,2))),
                    local_profile_edge_weight=float(weights[0]+weights[-1]))
        output.append(record)
        print('PROPAGATE',key,'power quantiles',record['conditional_power_q05_q50_q95'],flush=True)
    np.savez_compressed(ROOT/'propagation-arrays.npz',**arrays)
    return save('propagation.json',dict(models=output,tpa_dates_mjd=checkpoints.tolist(),
                utmost_toas=len(y),tpa_toas=len(ty),original_refined_period_days=original_period,
                method=scope['propagation'],
                interpretation='Quantiles summarize a profile-weighted local uncertainty approximation. Ellipse overlap is not a calibrated p-value or planet probability. TPA covariance fixed; non-overlapping observing spans.'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['all','joint','nulls','propagate'])
    args=parser.parse_args()
    ROOT.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
    scope=ensure_scope()
    joint=joint_fits(scope)
    if args.stage in ('all','nulls'):null_generators(scope,joint)
    if args.stage in ('all','propagate'):propagate(scope,joint)


if __name__=='__main__':
    main()
