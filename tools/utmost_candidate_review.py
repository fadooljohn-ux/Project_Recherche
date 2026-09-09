"""Bounded review of a consumed UTMOST candidate using saved source-separated data."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import chi2,ncx2
import mpta_batch as mpta
import target_calibration as cal
import j1453_review as common
import argparse

REPO=mpta.REPO
ROOT=SOURCE=EVIDENCE=TPA=None
TARGET=None
SEED=None


def save(name,value):
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    value={**value,'completed_utc':mpta.now(),'code_sha256':cal.digest(__file__),'gls_code_sha256':cal.digest(common.__file__)}
    cal.write(ROOT/name,value);cal.write(EVIDENCE/name,value)
    return value


def main():
    if (ROOT/'step3.json').exists(): raise FileExistsError('Completed review simulations are consumed')
    profile,a=cal.load_profile(SOURCE/'profile/profile.json')
    result=cal.read(SOURCE/'run01/result.json')
    t,c,x=a['times'],a['covariance'],a['design']
    y=np.load(SOURCE/'prepared/observed.npz')['residuals']
    meta=np.load(SOURCE/'prepared/metadata.npz');white=meta['white_variance'];radio=meta['radio']
    common.REFERENCE=profile['reference_epoch_mjd_tdb']
    noise=cal.read(SOURCE/'prepared/receipt.json')['noise_parameters']
    released_modes=int(noise['TNREDC'])
    low=max(profile['policy']['minimum_period_days'],.9*result['peak_period_days'])
    high=min(profile['policy']['maximum_period_days'],1.1*result['peak_period_days'])
    harmonic_period=365.25/max(1,round(365.25/result['peak_period_days']))
    specs=[('released',released_modes,1.,0.,0),('red32',32,1.,0.,0),('red64',64,1.,0.,0),
           ('red64_half_amp',64,.5,0.,0),('red64_double_amp',64,2.,0.,0),
           ('red64_flatter',64,1.,-1.,0),('red64_steeper',64,1.,1.,0),('chromatic64_nu4',64,1.,0.,4)]
    scope={'target':TARGET,'original_result_sha256':cal.digest(SOURCE/'run01/result.json'),
           'profile_sha256':cal.digest(SOURCE/'profile/profile.json'),'local_period_days':[low,high],'local_grid_points':301,'annual_harmonic_days':harmonic_period,
           'noise_family':specs,'nulls':512,'injections':256,'seed':SEED,
           'checks':'Local refinement; all observing-day deletions; early/late joint contrast; clock anomaly deletion; original eligible grid union local grid; noise family reselected under null and signal in each simulation; fixed-period independent TPA check only',
           'binary_support':False,'tpa_profile_sha256':cal.digest(TPA/'profile/profile.json'),
           'tpa_observed_sha256':cal.digest(TPA/'prepared/observed.npz'),
           'limits':'Single-band chromatic covariance is a degeneracy diagnostic, not separation of propagation from orbital delay. No updated batch discovery p-value.'}
    if not (ROOT/'scope.json').exists(): save('scope.json',scope)
    else:
        old=cal.read(ROOT/'scope.json')
        assert all(old[k]==json.loads(json.dumps(v)) for k,v in scope.items())
    local=np.linspace(low,high,301)
    g=common.GLS(c,x);h=common.template(t,local,len(t));scores,_=g.scan(y,g.bank(h));j=int(np.argmax(scores))
    optimized=minimize_scalar(lambda p:-g.fit(y,t,p)['delta_chi2'],bounds=(local[max(0,j-1)],local[min(len(local)-1,j+1)]),method='bounded')
    period=float(optimized.x);fit=g.fit(y,t,period)
    check=g.fit(y,t,result['peak_period_days'])
    np.testing.assert_allclose(check['delta_chi2'],result['peak_statistic'],rtol=1e-8)
    days=np.floor(t).astype(int);loo=[]
    for day in np.unique(days):
        keep=np.flatnonzero(days!=day);sg=common.GLS(c[np.ix_(keep,keep)],x[keep])
        f=sg.fit(y[keep],t[keep],period)
        loo.append({'removed_day':int(day),'statistic':f['delta_chi2'],'amplitude_us':f['amplitude_us']})
    harmonic=g.fit(y,t,harmonic_period)
    joint=common.template(t,[period,harmonic_period],len(t)).reshape(len(t),4)
    z=g.project(joint);u,s,_=np.linalg.svd(z,full_matrices=False)
    rank=int(np.sum(s>s[0]*1e-12));jointscore=float(np.sum((u[:,:rank].T@g.project(y))**2))
    save('step1.json',{'original_reproduced':check,'refined':fit,'leave_one_day_out':loo,
                       'nearest_annual_harmonic':harmonic,'candidate_added_after_harmonic':jointscore-harmonic['delta_chi2']})
    print('STEP1',period,fit['delta_chi2'],'minimum deletion',min(v['statistic'] for v in loo),flush=True)
    early=t<=np.median(np.unique(days));subsets=[]
    for mask in (early,~early):
        k=np.flatnonzero(mask);subsets.append(common.GLS(c[np.ix_(k,k)],x[k]).fit(y[k],t[k],period))
    orbit=common.template(t,[period],len(t))[:,0]
    split=np.column_stack([orbit*early[:,None],orbit*(~early)[:,None]])
    z=g.project(split);u,s,_=np.linalg.svd(z,full_matrices=False);rank=int(np.sum(s>s[0]*1e-12))
    extra=float(np.sum((u[:,:rank].T@g.project(y))**2))-fit['delta_chi2']
    k=np.flatnonzero((days<58105)|(days>58108));clock=common.GLS(c[np.ix_(k,k)],x[k]).fit(y[k],t[k],period)
    save('step2.json',{'early_late_fits':subsets,'joint_split_extra_chi2':extra,'extra_dof':rank-2,
                      'fixed_period_consistency_p':float(chi2.sf(extra,rank-2)),
                      'clock_window_removed_toas':len(t)-len(k),'without_clock_window':clock,
                      'radio_range_mhz':[float(radio.min()),float(radio.max())],
                      'independent_radio_split':'Unavailable: effectively one observing band'})
    original=np.load(SOURCE/'run01/periodogram.npz')
    periods=np.unique(np.r_[1/original['frequencies'][original['eligible']],local,period])
    h=common.template(t,periods,len(t));noise=cal.read(SOURCE/'prepared/receipt.json')['noise_parameters']
    amp=float(noise['TNREDAMP']);gamma=float(noise['TNREDGAM']);models=[];observed=[]
    for name,modes,scale,dgamma,chrom in specs:
        if name=='released':cov=c
        else:
            red=mpta.red_covariance(t,amp+np.log10(scale),gamma+dgamma,modes)
            weight=(835./radio)**chrom
            cov=np.diag(white)+red*weight[:,None]*weight[None,:]
        gg=common.GLS(cov,x);bank=gg.bank(h);sc,_=gg.scan(y,bank)
        null=float(gg.project(y)@gg.project(y)+gg.offset);kk=int(np.argmax(sc))
        observed.append({'name':name,'null_objective':null,'signal_objective':null-float(sc[kk]),
                         'peak':gg.fit(y,t,periods[kk]),'at_candidate':gg.fit(y,t,period)})
        models.append((gg,bank))
    ni=int(np.argmin([v['null_objective'] for v in observed]));si=int(np.argmin([v['signal_objective'] for v in observed]))
    global_statistic=observed[ni]['null_objective']-observed[si]['signal_objective']
    candidate_objectives=[v['null_objective']-v['at_candidate']['delta_chi2'] for v in observed]
    ci=int(np.argmin(candidate_objectives))
    statistic=observed[ni]['null_objective']-candidate_objectives[ci]
    rng=np.random.default_rng(scope['seed']);samples=models[ni][0].L@rng.standard_normal((len(t),768))
    samples[:,512:]+=orbit@(np.array(fit['sin_cos_us'])*1e-6)[:,None]
    bestnull=np.full(768,np.inf);bestsignal=np.full(768,np.inf);recovered=np.zeros(768)
    for (name,*_),(gg,(z,inv)) in zip(specs,models):
        yp=gg.project(samples);null=np.sum(yp*yp,axis=0)+gg.offset
        cross=(z.reshape(len(t),-1).T@yp).reshape(len(periods),2,768)
        sc=np.einsum('fik,fij,fjk->fk',cross,inv,cross,optimize=True)
        ks=np.argmax(sc,axis=0);signal=null-sc[ks,np.arange(768)]
        changed=signal<bestsignal;recovered[changed]=periods[ks[changed]]
        bestnull=np.minimum(bestnull,null);bestsignal=np.minimum(bestsignal,signal)
    simulation=bestnull-bestsignal;exceed=int(np.sum(simulation[:512]>=statistic))
    save('step3.json',{'models':observed,'selected_null':specs[ni][0],'selected_signal':specs[si][0],
                      'candidate_family_statistic':statistic,'global_family_statistic':global_statistic,
                      'selected_candidate_signal':specs[ci][0],'null_generator':specs[ni][0],
                      'diagnostic_definition':'Refined original candidate profiled across noise models versus each noise-only global maximum across the declared period union; conditional candidate-specific diagnostic',
                      'null_count':512,'null_exceedances':exceed,'diagnostic_p_plus_one':(exceed+1)/513,
                      'injection_count':256,'injection_amplitude_us':fit['amplitude_us'],
                      'injection_period_recovered_within_2_days':int(np.sum(abs(recovered[512:]-period)<=2)),
                      'injection_exceeds_observed':int(np.sum(simulation[512:]>=statistic)),
                      'selection_repeated':'Same noise family and period union reselected under null and signal in every simulation',
                      'method':'Chi-square plus logdet(C) plus logdet(Xscaled.T C^-1 Xscaled); same linear-timing prior measure',
                      'limit':'Plug-in finite diagnostic family, not a recalibrated discovery significance'})
    np.savez_compressed(ROOT/'review-arrays.npz',periods=local,statistic=scores,simulation_statistic=simulation,recovered_periods=recovered)
    print('STEP3 family statistic',statistic,'null exceedances',exceed,'/512',flush=True)


def independent():
    if (ROOT/'step4.json').exists(): raise FileExistsError('Independent comparison already completed')
    profile,a=cal.load_profile(TPA/'profile/profile.json')
    y=np.load(TPA/'prepared/observed.npz')['residuals']
    receipt=cal.read(TPA/'prepared/receipt.json')
    original=cal.read(SOURCE/'profile/profile.json');common.REFERENCE=original['reference_epoch_mjd_tdb']
    refined=cal.read(ROOT/'step1.json')['refined'];period=refined['period_days']
    g=common.GLS(a['covariance'],a['design']);fit=g.fit(y,a['times'],period)
    h=common.template(a['times'],[period],len(y))[:,0];signal=h@(np.array(refined['sin_cos_us'])*1e-6)
    expected=g.project(signal);power=float(ncx2.sf(chi2.isf(.01,2),2,float(expected@expected)))
    diff=np.array(fit['sin_cos_us'])-np.array(refined['sin_cos_us'])
    covariance=np.array(fit['coefficient_covariance_us2'])+np.array(refined['coefficient_covariance_us2'])
    contrast=float(diff@np.linalg.solve(covariance,diff))
    _,ua=cal.load_profile(SOURCE/'profile/profile.json')
    save('step4.json',{'source':'Saved public TPA DR1 observations','source_path':str(TPA),'toas':receipt['toas'],
                      'observing_days':len(np.unique(np.floor(a['times']))),'span_days':float(np.ptp(a['times'])),
                      'tpa_mjd_range':[float(a['times'].min()),float(a['times'].max())],
                      'utmost_mjd_range':[float(ua['times'].min()),float(ua['times'].max())],
                      'fixed_period_fit':fit,'fixed_period_p':float(chi2.sf(fit['delta_chi2'],2)),
                      'conditional_power_for_UTMOST_waveform_at_fixed_period_alpha_01':power,
                      'coefficient_contrast_chi2':contrast,'conditional_coefficient_contrast_p':float(chi2.sf(contrast,2)),
                      'blind_search_executed':False,'preparation_sha256':cal.digest(TPA/'prepared/receipt.json'),
                      'profile_sha256':cal.digest(TPA/'profile/profile.json'),'observed_sha256':cal.digest(TPA/'prepared/observed.npz'),
                      'limit':'Different observations already searched in the earlier TPA campaign; fixed-period comparison only. Conditional known-noise and exact-period waveform prediction, not an independent discovery probability.'})
    print('STEP4 TPA',fit['delta_chi2'],'amplitude',fit['amplitude_us'],'power',power,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--target',required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--tpa',type=Path,required=True)
    parser.add_argument('--seed',type=int,required=True)
    args=parser.parse_args()
    TARGET=args.target;SEED=args.seed;SOURCE=args.data.resolve()/TARGET
    ROOT=args.out.resolve();TPA=args.tpa.resolve();EVIDENCE=REPO/'results/research'/ROOT.name
    if TARGET not in cal.read(args.data/'selection.json')['selected']:parser.error('Target outside selection')
    if not cal.read(SOURCE/'run01/result.json')['candidate']:parser.error('No consumed candidate result')
    ROOT.mkdir(exist_ok=True)
    main();independent()
