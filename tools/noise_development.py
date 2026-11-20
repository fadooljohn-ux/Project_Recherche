"""Prepare/run the authorized two-target joint-noise development, never a survey."""
import argparse
import itertools
from pathlib import Path
import traceback

import numpy as np
from scipy.stats import beta as beta_distribution

import binary_noise_coverage as coverage
import j1453_review as common
import joint_noise
import mpta_batch as mpta
import target_calibration as cal

REPO = Path(__file__).resolve().parents[1]
SOURCES = {'J1012+5307': 'binary-pilot03-20260909/J1012+5307',
           'J1752-2806': 'utmost-batch04-20260909/J1752-2806'}


def code_binding():
    return {str(Path(p).relative_to(REPO)): cal.digest(p) for p in
            [__file__, joint_noise.__file__, coverage.__file__, common.__file__, mpta.__file__, cal.__file__]}


def fields(path):
    return {v[0]: v[1:] for line in path.read_text().splitlines()
            if (v := line.split()) and not line.startswith('#')}


def prepare(data, output, target):
    root = output / target
    if root.exists():
        raise FileExistsError('Prepared development destination exists; read or run it')
    source = data / SOURCES[target]
    profile, a = cal.load_profile(source/'profile/profile.json')
    result = cal.read(source/'run01/result.json')
    grid = np.load(source/'run01/periodogram.npz')
    times = a['times']; n = len(times)
    references = [source/'profile/profile.json', source/'profile/arrays.npz',
                  source/'prepared/observed.npz', source/'run01/result.json',
                  source/'run01/periodogram.npz']
    if target == 'J1012+5307':
        model = source/'prepared/timing-model.par'; p = fields(model)
        amplitude = np.log10(float(p['RNAMP'][0]) /
                            ((86400*365.24*1e6)/(2*np.pi*np.sqrt(3))))
        gamma = -float(p['RNIDX'][0]); modes = 30
        old_red = mpta.red_covariance(times, amplitude, gamma, modes)
        base = a['covariance'].copy(); base[:n, :n] -= old_red
        reference = data/'j1012-review-20260909/noise-inputs.npz'
        meta = np.load(reference); radio = meta['radio']
        c128 = base.copy(); c128[:n, :n] += mpta.red_covariance(times, amplitude, gamma, 128)
        relative = float(np.linalg.norm(c128-meta['red128'])/np.linalg.norm(meta['red128']))
        np.testing.assert_allclose(c128, meta['red128'], rtol=1e-7, atol=1e-22)
        chromatic = [0., .3]
        references += [model, reference]
    else:
        receipt = source/'prepared/receipt.json'; meta_path = source/'prepared/metadata.npz'
        noise = cal.read(receipt)['noise_parameters']; meta = np.load(meta_path)
        amplitude = float(noise['TNREDAMP']); gamma = float(noise['TNREDGAM']); modes = int(noise['TNREDC'])
        base = np.diag(meta['white_variance']); radio = meta['radio']
        original = base + mpta.red_covariance(times, amplitude, gamma, modes)
        relative = float(np.linalg.norm(original-a['covariance'])/np.linalg.norm(a['covariance']))
        np.testing.assert_allclose(original, a['covariance'], rtol=1e-10, atol=1e-20)
        chromatic = [0.]  # Single-band data cannot identify a second propagation process.
        references += [receipt, meta_path]
    plan = coverage.mode_plan(float(np.ptp(times)), profile['policy']['minimum_period_days'], modes)
    slopes = sorted(set(float(np.clip(gamma+d, 0, 7)) for d in [-1, 0, 1, 2]))
    family = [{'log10_amplitude': float(amplitude+da), 'gamma': slope, 'chromatic_rms_us': chrom}
              for da, slope, chrom in itertools.product([-.5, 0., .5], slopes, chromatic)]
    generators = [dict(name='published_extended', log10_amplitude=float(amplitude), gamma=gamma, chromatic_rms_us=0.),
                  dict(name='between_grid_stronger_steeper', log10_amplitude=float(amplitude+.25),
                       gamma=float(min(gamma+.5, 7)), chromatic_rms_us=0.),
                  dict(name='steeper_with_chromatic_if_identifiable', log10_amplitude=float(amplitude),
                       gamma=float(min(gamma+1, 7)), chromatic_rms_us=chromatic[-1])]
    periods = 1/grid['frequencies'][grid['eligible']]
    injection_periods = [float(periods[np.argmin(abs(periods/p-1))]) for p in
                         [60., result['peak_period_days'], 300. if target=='J1012+5307' else 200.]]
    root.mkdir(parents=True)
    np.savez_compressed(root/'inputs.npz', times=times, base_covariance=base, design=a['design'],
                        released_covariance=a['covariance'], radio=radio, periods=periods)
    scope = {'target': target, 'source': SOURCES[target], 'scope': 'Exposed-data development reanalysis; not a new blind search',
             'reference_epoch': profile['reference_epoch_mjd_tdb'], 'coverage': plan,
             'old_covariance_relative_error': relative, 'family': family, 'generators': generators,
             'amplitude_offsets_dex': [-.5, 0., .5], 'gamma_grid': slopes,
             'released_log10_amplitude': float(amplitude), 'released_gamma': gamma,
             'calibration_nulls_each': 256, 'validation_nulls_each': 256, 'alpha': .01,
             'injection_periods_days': injection_periods, 'injection_amplitude_factors': [1., 5.],
             'injections_each_cell': 16, 'injection_reference_amplitude_us': result['peak_amplitude_us'],
             'candidate_period_days': result['peak_period_days'],
             'seed': 2026091001 if target=='J1012+5307' else 2026091002,
             'objective': 'Timing-marginalized Gaussian objective with covariance determinant; discrete noise and circular coefficients profiled separately under null/signal',
             'threshold': 'Maximum 1% finite-sample order threshold across three declared generators; independent validation ensembles; no original threshold reused',
             'limits': 'Finite grid, fixed white noise and linear timing model; no noise posterior or survey-wide FAP. Boundary fits flag limited scope. Single-band chromatic ambiguity retained.',
             'inputs': {str(p.relative_to(data)): cal.digest(p) for p in references},
             'prepared_sha256': cal.digest(root/'inputs.npz'), 'code': code_binding()}
    cal.write(root/'scope.json', scope)
    print('PREPARED', target, 'modes', plan['selected_modes'], 'models', len(family), flush=True)


def red(a, scope, pars):
    times = a['times']
    r = mpta.red_covariance(times, pars['log10_amplitude'], pars['gamma'], scope['coverage']['selected_modes'])
    if pars['chromatic_rms_us']:
        scale = (1400/a['radio'])**4 * pars['chromatic_rms_us']*1e-6
        r += np.outer(scale, scale)*np.exp(-abs(times[:, None]-times[None, :])/100.)
    return r


def interval(k, n):
    return [0. if k==0 else float(beta_distribution.ppf(.025, k, n-k+1)),
            1. if k==n else float(beta_distribution.ppf(.975, k+1, n-k))]


def run(data, output, target):
    root = output/target; scope = cal.read(root/'scope.json')
    if (root/'result.json').exists():
        raise FileExistsError('Completed development result exists; do not rerun')
    if scope['code'] != code_binding() or scope['prepared_sha256'] != cal.digest(root/'inputs.npz'):
        raise ValueError('Prepared implementation/input binding changed')
    for path, digest in scope['inputs'].items():
        if cal.digest(data/path) != digest:
            raise ValueError('Historical input changed: '+path)
    a = np.load(root/'inputs.npz'); source = data/scope['source']
    y = np.load(source/'prepared/observed.npz')['residuals']
    contrast = joint_noise.Contrast(a['base_covariance'], a['design'], len(a['times']))
    common.REFERENCE = scope['reference_epoch']
    full_h = common.template(a['times'], a['periods'], len(y))
    h = (contrast.B @ full_h.reshape(len(y), -1)).reshape(contrast.dimension, -1, 2)
    observed = contrast.data(y)
    # One direct GLS comparison validates compression, signal coefficients and
    # relative determinant/objective across different noise covariances.
    verification = []
    previous = None
    for pars in scope['generators'][:2]:
        r = red(a, scope, pars); c = a['base_covariance'].copy(); n=len(a['times']); c[:n,:n] += r
        compressed = joint_noise.evaluate(contrast.covariance(r), h, observed[:,None])
        g = common.GLS(c, a['design']); bank = g.bank(full_h)
        scores, beta = g.scan(y, bank)
        np.testing.assert_allclose(compressed['score'][:,0], scores, rtol=1e-6, atol=1e-7)
        q = float(np.sum(g.project(y)**2)+g.offset)
        pair = (q, float(compressed['null'][0]))
        if previous:
            np.testing.assert_allclose(pair[0]-previous[0], pair[1]-previous[1], rtol=1e-7, atol=1e-6)
        verification.append({'generator':pars['name'], 'maximum_score_error':float(np.max(abs(compressed['score'][:,0]-scores)))})
        previous = pair
    cal.write(root/'verification.json', {'comparisons':verification, 'input_dimension':len(y),
              'contrast_dimension':contrast.dimension, 'timing_rank':contrast.timing_rank,
              'fixed_noise_only_dimensions_removed':contrast.discarded_dimension})
    batches = [observed[:,None]]; segments = []; cursor=1
    for gi, pars in enumerate(scope['generators']):
        rng = np.random.default_rng(scope['seed']+gi*100)
        l = np.linalg.cholesky(contrast.covariance(red(a,scope,pars)))
        for kind, count in [('calibration',scope['calibration_nulls_each']),('validation',scope['validation_nulls_each'])]:
            batches.append(l@rng.standard_normal((contrast.dimension,count)))
            segments.append({'generator':gi,'kind':kind,'start':cursor,'stop':cursor+count});cursor+=count
        for period, factor in itertools.product(scope['injection_periods_days'],scope['injection_amplitude_factors']):
            count=scope['injections_each_cell']; index=int(np.argmin(abs(a['periods']-period)))
            phases=rng.uniform(0,2*np.pi,count)
            coefficients=scope['injection_reference_amplitude_us']*factor*1e-6*np.array([np.cos(phases),np.sin(phases)])
            samples=l@rng.standard_normal((contrast.dimension,count))+h[:,index]@coefficients
            batches.append(samples)
            segments.append({'generator':gi,'kind':'injection','period_days':period,'factor':factor,
                             'start':cursor,'stop':cursor+count});cursor+=count
    samples=np.column_stack(batches)
    null=np.full(cursor,np.inf); signal=null.copy(); ni=np.zeros(cursor,int);si=ni.copy();peaks=ni.copy()
    candidate=int(np.argmin(abs(a['periods']/scope['candidate_period_days']-1)))
    candidate_signal=np.inf; candidate_model=None; candidate_beta=None
    model_records=[]
    for i, pars in enumerate(scope['family']):
        checkpoint=root/f'model-{i:02d}.npz'
        if checkpoint.exists():
            result=dict(np.load(checkpoint))
        else:
            result=joint_noise.evaluate(contrast.covariance(red(a,scope,pars)),h,samples)
            np.savez_compressed(checkpoint, **result)
        mask=result['null']<null;null[mask]=result['null'][mask];ni[mask]=i
        mask=result['signal']<signal;signal[mask]=result['signal'][mask];si[mask]=i;peaks[mask]=result['peak'][mask]
        cs=float(result['null'][0]-result['score'][candidate,0])
        if cs<candidate_signal:
            candidate_signal=cs;candidate_model=i;candidate_beta=result['observed_beta_grid'][candidate]
        model_records.append({'model':i,**pars,'observed_null_objective':float(result['null'][0]),
                              'observed_signal_objective':float(result['signal'][0]),
                              'peak_period_days':float(a['periods'][result['peak'][0]])})
        print('MODEL',target,i+1,'/',len(scope['family']),flush=True)
    statistic=null-signal
    thresholds=[joint_noise.order_threshold(statistic[s['start']:s['stop']],scope['alpha'])
                for s in segments if s['kind']=='calibration']
    threshold=max(thresholds);candidate_statistic=float(null[0]-candidate_signal)
    results=[]
    for s in segments:
        sl=slice(s['start'],s['stop']);count=s['stop']-s['start']
        row={**s,'count':count,'threshold_crossings':int(np.sum(statistic[sl]>threshold))}
        if s['kind']=='validation':
            k=int(np.sum(statistic[sl]>threshold));tail=int(np.sum(statistic[sl]>=candidate_statistic))
            row.update(false_alarm_rate=k/count,false_alarm_interval95=interval(k,count),
                       candidate_exceedances=tail,candidate_p_plus_one=(tail+1)/(count+1))
        if s['kind']=='injection':
            located=abs(a['periods'][peaks[sl]]/s['period_days']-1)<.05
            k=int(np.sum((statistic[sl]>threshold)&located))
            row.update(recovered=k,recovery_fraction=k/count,recovery_interval95=interval(k,count))
        results.append(row)
    boundary=lambda i: bool(scope['family'][i]['log10_amplitude'] in
                           [scope['released_log10_amplitude']-.5,scope['released_log10_amplitude']+.5] or
                           scope['family'][i]['gamma'] in [min(scope['gamma_grid']),max(scope['gamma_grid'])])
    out={'status':'BOUNDED_DEVELOPMENT_COMPLETE','target':target,'completed_utc':mpta.now(),
         'scope_sha256':cal.digest(root/'scope.json'),'code':scope['code'],'models':model_records,
         'threshold':threshold,'per_generator_calibration_thresholds':thresholds,
         'original_candidate':{'period_days':scope['candidate_period_days'],'joint_statistic':candidate_statistic,
                               'amplitude_us':float(np.linalg.norm(candidate_beta)*1e6),'signal_model':candidate_model,
                               'crosses_development_threshold':bool(candidate_statistic>threshold)},
         'global_development_peak':{'period_days':float(a['periods'][peaks[0]]),'statistic':float(statistic[0]),
                                    'noise_only_model':int(ni[0]),'signal_model':int(si[0])},
         'null_at_grid_boundary':boundary(ni[0]),'signal_at_grid_boundary':boundary(si[0]),
         'experiments':results,'interpretation':'Conditional development only. Historical candidate grades and survey thresholds unchanged. No independent planet confirmation.',
         'limits':scope['limits']}
    np.savez_compressed(root/'ensemble-results.npz',statistic=statistic,peak_index=peaks,null_model=ni,signal_model=si)
    out['ensemble_sha256']=cal.digest(root/'ensemble-results.npz')
    cal.write(root/'result.json',out)
    print('COMPLETE',target,'candidate',candidate_statistic,'threshold',threshold,flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','run']);p.add_argument('--data',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--target',choices=list(SOURCES),required=True)
    args=p.parse_args();data=args.data.resolve();output=args.output.resolve()
    try:
        (prepare if args.action=='prepare' else run)(data,output,args.target)
    except Exception:
        root=output/args.target
        if root.exists() and not (root/'result.json').exists():
            failures=list(root.glob('failure-*.json'))
            cal.write(root/f'failure-{len(failures)+1:02d}.json',{'action':args.action,'code':code_binding(),'traceback':traceback.format_exc()})
        raise


if __name__=='__main__':
    main()
