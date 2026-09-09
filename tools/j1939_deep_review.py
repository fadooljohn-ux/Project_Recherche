"""Bounded, checkpointed follow-up of the consumed InPTA J1939 candidate.

Diagonal white covariance plus finite Fourier Gaussian processes permits exact
Woodbury likelihood evaluation without repeatedly factoring an 18k-square matrix.
This is a diagnostic noise family, not a replacement survey calibration.
"""
import argparse
import os
from pathlib import Path
import shutil
import numpy as np
from scipy.linalg import eigh, solve_triangular
from scipy.stats import chi2
import target_calibration as cal
import mpta_batch as mpta

ROOT = mpta.REPO.parent/'Project Recherche Data/j1939-deep-review-20260909'
CAMPAIGN = mpta.REPO.parent/'Project Recherche Data/pta-campaign01-20260908'
SOURCE = CAMPAIGN/'inpta/J1939+2134'
PPTA = CAMPAIGN/'ppta/J1939+2134'
EVIDENCE = mpta.REPO/'results/research/j1939-deep-review-20260909'
REFERENCE = 58999.99975414959


def save(name, value):
    value = {**value, 'completed_utc':mpta.now(), 'code_sha256':cal.digest(__file__)}
    cal.write(ROOT/name, value)
    if name != 'progress.json':
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        cal.write(EVIDENCE/name, value)
    return value


def pulse(stage, **fields):
    print(stage, fields, flush=True)
    save('progress.json', {'stage':stage, 'pid':os.getpid(), **fields})


def basis(x):
    norms=np.linalg.norm(x,axis=0);x=x[:,norms>0]/norms[norms>0]
    u,s,_=np.linalg.svd(x,full_matrices=False)
    return u[:,s>s[0]*1e-12]


def project(q,v):
    return v-q@(q.T@v)


def templates(t, periods):
    phase=2*np.pi*(t[:,None]-REFERENCE)/np.atleast_1d(periods)
    return np.stack([np.sin(phase),np.cos(phase)],axis=-1)


def score(gram, cross):
    inv=np.linalg.pinv(gram,rcond=1e-12)
    beta=np.einsum('fij,fj->fi',inv,cross)
    return np.einsum('fi,fi->f',cross,beta),beta,inv


def white_fit(t,y,sigma,x,period):
    q=basis(x/sigma[:,None]);z=project(q,templates(t,[period])[:,0]/sigma[:,None]);v=project(q,y/sigma)
    gram=z.T@z;rank=np.linalg.matrix_rank(gram,tol=np.linalg.norm(gram)*1e-10)
    if rank<2 or len(t)<=q.shape[1]:return {'status':'UNIDENTIFIABLE','toas':len(t)}
    inv=np.linalg.inv(gram);b=inv@(z.T@v)
    return {'status':'FIT','toas':len(t),'statistic':float(b@gram@b),'amplitude_us':float(np.linalg.norm(b)*1e6),
            'coefficients_us':(b*1e6).tolist(),'coefficient_covariance_us2':(inv*1e12).tolist(),
            'null_chi2':float(v@v),'dof':len(t)-q.shape[1]}


def prepare():
    ROOT.mkdir(parents=True,exist_ok=True)
    if (ROOT/'scope.json').exists():raise FileExistsError('Prepared review exists; use run or read its receipts')
    result=cal.read(SOURCE/'run01/result.json')
    with np.load(SOURCE/'profile/arrays.npz') as a:
        covariance=a['covariance'];n=len(covariance)
        assert np.count_nonzero(covariance)==n and np.all(np.diag(covariance)>0)
        data={'times':a['times'],'design':a['design'],'sigma':np.sqrt(np.diag(covariance))}
    with np.load(SOURCE/'prepared/observed.npz') as a:data['residuals']=a['residuals']
    with np.load(SOURCE/'prepared/metadata.npz') as a:data['radio']=a['radio']
    np.savez_compressed(ROOT/'data.npz',**data)
    variants=[('white',[]),('red2_1',[('red2',1)]),('red4_1',[('red4',1)]),('red4_2',[('red4',2)]),
              ('red4_4',[('red4',4)]),('dm2_1',[('dm2',1)]),('chrom4_1',[('chrom4',1)]),
              ('red_dm_chrom',[('red4',2),('dm2',1),('chrom4',1)])]
    family=[{'name':f'white{s:g}_{name}','white_scale':s,'components':components} for s in [1.,.5] for name,components in variants]
    save('scope.json',{'target':'J1939+2134','original_period_days':result['peak_period_days'],
         'original_result_sha256':cal.digest(SOURCE/'run01/result.json'),'ppta_result_sha256':cal.digest(PPTA/'run01/result.json'),
         'data_sha256':cal.digest(ROOT/'data.npz'),'source_arrays_sha256':cal.digest(SOURCE/'profile/arrays.npz'),
         'historical_hashes':{str(p):cal.digest(p) for p in (mpta.REPO/'results').rglob('*.json')},
         'local_period_days':[400.,800.,.5],'fourier_modes':30,'family':family,'seed':2026092401,'null_count':512,'injection_count':256,
         'injection_period_tolerance_days':30.,'receiver_boundary_mhz':1000.,
         'method':'Fixed 16-member family, 30 Fourier frequencies k/T. Spectral weights normalized to total RMS; gamma 2/4 achromatic, gamma 2 nu^-2 dispersion and nu^-4 chromatic at 400 MHz. White standard deviations scaled by 1 or 0.5. All alternatives selected separately under null and sinusoid in every simulation.',
         'scope':'Diagnostic search over original eligible grid union 400-800 d refinement. Preserve original threshold; no discovery p-value or planet posterior. All 157 observing days tested; actual receiver bands and overlapping PPTA data compared.'})
    pulse('PREPARED',toas=n,days=len(np.unique(np.floor(data['times']))),models=len(family))


def noise_basis(t,radio,name,modes):
    k=np.arange(1,modes+1);gamma=4 if name=='red4' else 2
    weights=k.astype(float)**(-gamma);weights/=weights.sum()
    phase=2*np.pi*(t[:,None]-REFERENCE)*k/np.ptp(t)
    f=np.stack([np.sin(phase),np.cos(phase)],axis=-1)*np.sqrt(weights)[None,:,None]*1e-6
    exponent=2 if name=='dm2' else 4 if name=='chrom4' else 0
    return f.reshape(len(t),-1)*(400/radio[:,None])**exponent


class Model:
    def __init__(self,spec,base,q,sigma,h,ht_h,dof):
        self.spec=spec;self.s=spec['white_scale'];self.n=len(sigma)
        self.u=np.column_stack([base[k]*a for k,a in spec['components']]) if spec['components'] else np.empty((self.n,0))
        self.b=project(q,self.u/sigma[:,None])
        a=np.eye(self.b.shape[1])+self.b.T@self.b/self.s**2
        self.ai=np.linalg.inv(a)
        self.offset=2*dof*np.log(self.s)+np.linalg.slogdet(a)[1]
        self.bh=self.b.T@h
        self.correction=self.bh.T@self.ai/self.s**4
        # Only the two columns at the same frequency enter its 2x2 Gram.
        gram=ht_h/self.s**2-np.einsum('fik,kfj->fij',self.correction.reshape(len(ht_h),2,self.b.shape[1]),self.bh.reshape(self.b.shape[1],len(ht_h),2))
        self.inverse=np.linalg.pinv(gram,rcond=1e-12)
        self.gram=gram

    def evaluate(self,y0,h_cross,y_norm):
        by=self.b.T@y0
        null=y_norm/self.s**2-np.sum(by*(self.ai@by),axis=0)/self.s**4+self.offset if y0.ndim==2 else y_norm/self.s**2-by@self.ai@by/self.s**4+self.offset
        cross=h_cross/self.s**2-self.correction@by
        if y0.ndim==1:
            sc,beta,_=score(self.gram,cross.reshape(-1,2));return null,sc,beta
        cross=cross.reshape(len(self.inverse),2,-1)
        sc=np.einsum('fik,fij,fjk->fk',cross,self.inverse,cross,optimize=True)
        return null,sc,None


def direct_check():
    # One small numerical equivalence check of the new likelihood algebra.
    rng=np.random.default_rng(713);n=90;x=rng.normal(size=(n,5));sigma=rng.uniform(.5,2,n)
    u=rng.normal(size=(n,4));y=rng.normal(size=n);h=rng.normal(size=(n,6));q=basis(x/sigma[:,None])
    y0=project(q,y/sigma);h0=project(q,h/sigma[:,None]);b=project(q,u/sigma[:,None]);s=.5
    ai=np.linalg.inv(np.eye(4)+b.T@b/s**2)
    null=y0@y0/s**2-(b.T@y0)@ai@(b.T@y0)/s**4
    covariance=np.diag((s*sigma)**2)+u@u.T;l=np.linalg.cholesky(covariance)
    qd=basis(solve_triangular(l,x,lower=True));yd=project(qd,solve_triangular(l,y,lower=True))
    hd=project(qd,solve_triangular(l,h,lower=True))
    np.testing.assert_allclose(null,yd@yd,rtol=1e-10)
    np.testing.assert_allclose(h0.T@h0/s**2-(b.T@h0).T@ai@(b.T@h0)/s**4,hd.T@hd,rtol=1e-10,atol=1e-10)
    offsets=[]
    for cov in [np.diag(sigma**2),covariance]:
        ci=np.linalg.inv(cov);offsets.append(np.linalg.slogdet(cov)[1]+np.linalg.slogdet(x.T@ci@x)[1])
    np.testing.assert_allclose(offsets[1]-offsets[0],2*(n-5)*np.log(s)+np.linalg.slogdet(np.eye(4)+b.T@b/s**2)[1],rtol=1e-10)
    return {'status':'PASS','scope':'90-row dense versus Woodbury nuisance-projected likelihood, template Gram and relative determinant; development verification only'}


def run():
    scope=cal.read(ROOT/'scope.json')
    assert cal.digest(ROOT/'data.npz')==scope['data_sha256']
    assert cal.digest(SOURCE/'run01/result.json')==scope['original_result_sha256']
    if (ROOT/'step3.json').exists():
        pulse('NUMERICAL_REVIEW_ALREADY_COMPLETE');return
    with np.load(ROOT/'data.npz') as f:d={k:f[k] for k in f.files}
    t,x,sigma,y,radio=[d[k] for k in ['times','design','sigma','residuals','radio']]
    q=basis(x/sigma[:,None]);y0=project(q,y/sigma);dof=len(t)-q.shape[1]
    local=np.arange(400,800.01,.5)
    with np.load(SOURCE/'run01/periodogram.npz') as g:periods=np.unique(np.r_[1/g['frequencies'][g['eligible']],local,scope['original_period_days']])
    raw=templates(t,periods);h=project(q,raw.reshape(len(t),-1)/sigma[:,None]);ht_h=np.einsum('nfi,nfj->fij',h.reshape(len(t),-1,2),h.reshape(len(t),-1,2))
    cross=h.T@y0;norm=y0@y0;sc,beta,inverse=score(ht_h,cross.reshape(-1,2))
    original=int(np.argmin(abs(periods-scope['original_period_days'])))
    np.testing.assert_allclose(sc[original],cal.read(SOURCE/'run01/result.json')['peak_statistic'],rtol=1e-8)
    localmask=np.isin(periods,local);peak=int(np.argmax(np.where(localmask,sc,-np.inf)));period=float(periods[peak])
    fit={'period_days':period,'statistic':float(sc[peak]),'amplitude_us':float(np.linalg.norm(beta[peak])*1e6),'coefficients_us':(beta[peak]*1e6).tolist()}
    if not (ROOT/'step1.json').exists():
        pulse('NOISE_FAMILY',models=len(scope['family']))
        verification=direct_check()
        base={name:noise_basis(t,radio,name,scope['fourier_modes']) for name in ['red2','red4','dm2','chrom4']}
        models=[];observed=[]
        for spec in scope['family']:
            m=Model(spec,base,q,sigma,h,ht_h,dof);null,scores,coeff=m.evaluate(y0,cross,norm);k=int(np.argmax(scores))
            observed.append({'model':spec['name'],'null_objective':float(null),'signal_objective':float(null-scores[k]),'peak_period_days':float(periods[k]),'peak_statistic':float(scores[k]),'candidate_statistic':float(scores[original]),'candidate_amplitude_us':float(np.linalg.norm(coeff[original])*1e6)})
            models.append(m);pulse('NOISE_MODEL_COMPLETE',model=spec['name'])
        ni=int(np.argmin([r['null_objective'] for r in observed]));si=int(np.argmin([r['signal_objective'] for r in observed]))
        statistic=observed[ni]['null_objective']-observed[si]['signal_objective']
        save('step1.json',{'method':scope['method'],'verification':verification,'refined':fit,'original_statistic_reproduced':float(sc[original]),'models':observed,'selected_null_index':ni,'selected_signal_index':si,'selected_null':observed[ni]['model'],'selected_signal':observed[si]['model'],'family_statistic':statistic,'relative_objective_scope':'Timing-marginalized Gaussian likelihood; shared white-covariance/timing determinant constant omitted; no signal-prior evidence claim'})
    else:
        base={name:noise_basis(t,radio,name,scope['fourier_modes']) for name in ['red2','red4','dm2','chrom4']}
        models=[Model(spec,base,q,sigma,h,ht_h,dof) for spec in scope['family']]
    step1=cal.read(ROOT/'step1.json')
    if not (ROOT/'step2.json').exists():
        pulse('OBSERVING_DAY_AND_BAND_REVIEW')
        # Exact white-noise leave-one-day-out via deleted-row sufficient statistics.
        hfix=templates(t,[period])[:,0]/sigma[:,None];v=y/sigma
        gh=hfix.T@hfix;hc=hfix.T@v;qx=q.T@hfix;qy=q.T@v;loo=[]
        for day in np.unique(np.floor(t)):
            ix=np.floor(t)==day;qr=q[ix];hr=hfix[ix];yr=v[ix]
            gq=np.eye(q.shape[1])-qr.T@qr;w,e=eigh(gq);positive=w>1e-10;gi=(e[:,positive]/w[positive])@e[:,positive].T
            qhx=qx-qr.T@hr;qyx=qy-qr.T@yr
            gram=gh-hr.T@hr-qhx.T@gi@qhx;cr=hc-hr.T@yr-qhx.T@gi@qyx
            b=np.linalg.pinv(gram,rcond=1e-12)@cr
            loo.append({'removed_day':int(day),'removed_toas':int(ix.sum()),'statistic':float(cr@b),'amplitude_us':float(np.linalg.norm(b)*1e6)})
        for index in [0,int(np.argmin([r['statistic'] for r in loo]))]:
            row=loo[index];keep=np.floor(t)!=row['removed_day'];direct=white_fit(t[keep],y[keep],sigma[keep],x[keep],period)
            np.testing.assert_allclose(row['statistic'],direct['statistic'],rtol=1e-6,atol=1e-5)
        splits={'time_halves':t<=np.median(np.unique(np.floor(t))),'receiver_bands':radio<scope['receiver_boundary_mhz']};groups={}
        z=project(q,hfix);common=float((z.T@y0)@np.linalg.pinv(z.T@z)@(z.T@y0))
        for name,mask in splits.items():
            subset=[white_fit(t[m],y[m],sigma[m],x[m],period) for m in [mask,~mask]]
            a=hfix.copy();b=hfix.copy();a[~mask]=0;b[mask]=0
            z=project(q,np.column_stack([a,b]));qb=basis(z);joint=float(np.sum((qb.T@y0)**2));extra_dof=qb.shape[1]-2
            groups[name]={'subsets':subset,'joint_extra_statistic':joint-common,'extra_dof':extra_dof,'consistency_p':float(chi2.sf(max(0,joint-common),extra_dof)) if extra_dof>0 else None}
        window=np.abs(np.mean(np.exp(2j*np.pi*(t[:,None]-REFERENCE)/local),axis=0))**2
        aliases={str(p):white_fit(t,y,sigma,x,p) for p in [365.25,730.5]}
        save('step2.json',{'refined_period_days':period,'leave_one_day_out':loo,'groups':groups,'annual_aliases':aliases,'limitation':'All subsets participated in discovery; subset statistics do not inherit the survey threshold. Fixed white noise influence checks; no phase-coherent planet claim.'})
        np.savez_compressed(ROOT/'refinement.npz',periods=periods,statistics=sc,local_periods=local,window=window)
    if not (ROOT/'step3.json').exists():
        pulse('SIMULATIONS',null_count=512,injection_count=256)
        ni=step1['selected_null_index'];rng=np.random.default_rng(scope['seed']);count=768
        generator=models[ni];samples=generator.s*rng.standard_normal((len(t),count))
        if generator.u.shape[1]:samples+=(generator.u/sigma[:,None])@rng.standard_normal((generator.u.shape[1],count))
        injected=templates(t,[period])[:,0]@beta[peak]
        samples[:,512:]+=injected[:,None]/sigma[:,None]
        yp=project(q,samples);hc=h.T@yp;yn=np.sum(yp*yp,axis=0)
        bestnull=np.full(count,np.inf);bestsignal=np.full(count,np.inf);recovered=np.zeros(count)
        for m in models:
            null,scores,_=m.evaluate(yp,hc,yn);k=np.argmax(scores,axis=0);signal=null-scores[k,np.arange(count)];changed=signal<bestsignal
            recovered[changed]=periods[k[changed]];bestnull=np.minimum(bestnull,null);bestsignal=np.minimum(bestsignal,signal)
            pulse('SIMULATION_MODEL_COMPLETE',model=m.spec['name'])
        stats=bestnull-bestsignal;observed=step1['family_statistic'];exceed=int(np.sum(stats[:512]>=observed))
        save('step3.json',{'seed':scope['seed'],'null_generator':generator.spec,'null_count':512,'injection_count':256,'observed_statistic':observed,'null_exceedances':exceed,'diagnostic_p_plus_one':(exceed+1)/513,'injected_period_days':period,'injected_amplitude_us':fit['amplitude_us'],'injection_exceeds_observed':int(np.sum(stats[512:]>=observed)),'injection_recovers_period_within_30_days':int(np.sum(abs(recovered[512:]-period)<=30)),'limitations':'Plug-in finite noise family and selected injection phase/amplitude; model and frequency selection repeated in every realization. Not a campaign p-value, posterior planet probability, or exhaustive noise model.'})
        np.savez_compressed(ROOT/'simulations.npz',statistic=stats,recovered_period_days=recovered)
    pulse('FIRST_THREE_STEPS_COMPLETE')


def cross_source():
    if (ROOT/'step4.json').exists():raise FileExistsError('Cross-source review already complete')
    from j1453_review import GLS
    # The shared helper's reference epoch must match this candidate's convention.
    import j1453_review as old
    old.REFERENCE=REFERENCE
    scope=cal.read(ROOT/'scope.json');period=cal.read(ROOT/'step1.json')['refined']['period_days']
    with np.load(ROOT/'data.npz') as a:d={k:a[k] for k in a.files}
    with np.load(PPTA/'profile/arrays.npz') as a:t,c,x=a['times'],a['covariance'],a['design']
    with np.load(PPTA/'prepared/observed.npz') as a:y=a['residuals']
    lo=max(t.min(),d['times'].min());hi=min(t.max(),d['times'].max());inside=(t>=lo)&(t<=hi);ii=(d['times']>=lo)&(d['times']<=hi)
    results={}
    for name,mask in [('ppta_full',np.ones(len(t),bool)),('ppta_overlap',inside)]:
        pulse('PPTA_FIXED_PERIOD_FIT',subset=name)
        g=GLS(c[np.ix_(mask,mask)],x[mask]);results[name]=g.fit(y[mask],t[mask],period)
    results['inpta_overlap']=white_fit(d['times'][ii],d['residuals'][ii],d['sigma'][ii],d['design'][ii],period)
    results['inpta_after_overlap']=white_fit(d['times'][~ii],d['residuals'][~ii],d['sigma'][~ii],d['design'][~ii],period)
    a=results['inpta_overlap'];b=results['ppta_overlap'];contrast=None
    if a['status']=='FIT':
        delta=np.array(a['coefficients_us'])-np.array(b['sin_cos_us']);cov=np.array(a['coefficient_covariance_us2'])+np.array(b['coefficient_covariance_us2']);stat=float(delta@np.linalg.pinv(cov)@delta)
        contrast={'statistic':stat,'dof':2,'conditional_consistency_p':float(chi2.sf(stat,2)),'limitation':'Conditional fixed-noise coefficient contrast assuming independent source errors; shared propagation noise can violate that assumption.'}
    save('step4.json',{'period_days':period,'overlap_mjd_tdb':[float(lo),float(hi)],'overlap_toas':{'ppta':int(inside.sum()),'inpta':int(ii.sum())},'fits':results,'coefficient_contrast':contrast,'ppta_result_unchanged':cal.digest(PPTA/'run01/result.json')==scope['ppta_result_sha256'],'limitations':'Descriptive fixed-period fits after candidate selection, not new calibrated searches. Overlap and post-overlap alone do not establish orbital coherence.'})
    pulse('ALL_FOUR_NUMERICAL_STEPS_COMPLETE')


def report():
    """Summarize saved simulations; no repeated scans or realizations."""
    scope=cal.read(ROOT/'scope.json');a,b,c,d=[cal.read(ROOT/f'step{i}.json') for i in range(1,5)]
    rows=a['models'];candidate=min(r['null_objective'] for r in rows)-min(r['null_objective']-r['candidate_statistic'] for r in rows)
    with np.load(ROOT/'simulations.npz') as f:stats=f['statistic'];recovered=f['recovered_period_days']
    exceed=int(np.sum(stats[:512]>=candidate));p=(exceed+1)/513
    selected=rows[a['selected_null_index']]
    assessment=save('candidate-assessment.json',{'original_period_days':scope['original_period_days'],'candidate_family_statistic':candidate,
        'null_global_max_exceedances':exceed,'null_count':512,'diagnostic_p_plus_one':p,
        'definition':'Compare the noise-family-profiled statistic at the original candidate period with each saved noise-only realization\'s maximum across the complete declared grid. This conservative candidate-specific comparison uses existing simulations and accounts for searching multiple periods within the finite family.',
        'different_global_peak_period_days':selected['peak_period_days'],'different_global_peak_statistic':a['family_statistic'],
        'different_global_peak_null_exceedances':c['null_exceedances'],
        'disposition':'INCONCLUSIVE_NOISE_SENSITIVE','reason':'Original candidate is weakened by noise alternatives, fails conditional receiver-band/source consistency checks, and lacks PPTA corroboration. A different 67-day residual peak exposes unresolved structure within the limited model family; it is not confirmation of the original candidate or a calibrated new survey discovery.'})
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=mpta.REPO/'outputs/j1939-deep-review-20260909';out.mkdir(exist_ok=True)
    with np.load(ROOT/'refinement.npz') as f:periods=f['periods'];scores=f['statistics'];local=f['local_periods'];window=f['window']
    fig,axs=plt.subplots(2,2,figsize=(11,7))
    mask=(periods>=400)&(periods<=800)
    axs[0,0].plot(periods[mask],scores[mask]);axs[0,0].axvline(scope['original_period_days'],color='grey',linestyle='--');axs[0,0].set(xlabel='Period (days)',ylabel='Released-noise statistic',title='Conditional local refinement')
    loo=b['leave_one_day_out'];axs[0,1].scatter([r['removed_day'] for r in loo],[r['statistic'] for r in loo],s=10);axs[0,1].set(xlabel='Removed observing day (TDB MJD)',ylabel='Remaining fixed-period statistic',title='All 157 observing days')
    axs[1,0].hist(stats[:512],bins=25,color='#456e89');axs[1,0].axvline(candidate,color='#b34d32',label=f'Original candidate: {candidate:.2f}');axs[1,0].set(xlabel='Noise-family selected grid maximum',ylabel='Noise-only realizations',title=f'{exceed}/512 exceed original-candidate statistic');axs[1,0].legend()
    models=['white1_white','white1_chrom4_1','white1_red_dm_chrom','white0.5_red_dm_chrom'];values=[next(r['candidate_statistic'] for r in rows if r['model']==name) for name in models]
    axs[1,1].barh(['Released','Chromatic','Joint noise','Joint + half white'],values,color='#456e89');axs[1,1].set(xlabel='Statistic at original 567.405-day period',title='Dependence on noise assumptions');axs[1,1].invert_yaxis()
    fig.suptitle('J1939+2134 deep review: inconclusive, noise-sensitive');fig.tight_layout();fig.savefig(out/'diagnostics.png',dpi=150);plt.close(fig)
    report_path=mpta.REPO/'docs/J1939_DEEP_REVIEW_REPORT_2026-09-09.md'
    low,high=b['groups']['receiver_bands']['subsets'];ov=d['fits'];mn=min(r['statistic'] for r in loo);mx=max(r['statistic'] for r in loo)
    lines=['# A bounded deep review of the J1939+2134 periodic timing candidate','',
      'Project Recherche · 9 September 2026 · Private research report','',
      '## Abstract','',
      f"We investigated the preserved InPTA J1939+2134 threshold crossing at 567.405 days using 18,191 arrival-time measurements over 157 observing days. A fixed 16-member white, achromatic and chromatic noise family reduces the original-period statistic from 149.353 to {candidate:.3f}. Of 512 noise-only realizations, {exceed} produced a grid maximum at least this large (plus-one diagnostic estimate {p:.4f}). The signal survives every individual observing-day removal under the original noise model, but receiver-band and overlapping-source checks do not support a stable common timing delay. The final disposition is **INCONCLUSIVE / NOISE-SENSITIVE**; no planet is confirmed.",'',
      '## 1. Data and fixed scope','',
      'The original source preparation, timing design, threshold (26.713) and consumed result remain unchanged. The InPTA data span approximately 2,156 days. Its released covariance is diagonal after the supplied EFAC scaling; the timing design includes projected DMX dispersion parameters. PPTA DR3 is retained with its own released correlated-noise covariance. All observations and original arrays remain outside Git.','',
      'The declared follow-up used the original eligible grid plus 400–800 days at 0.5-day spacing; 16 noise choices; 512 noise-only realizations and 256 injections with seed 2026092401; all observing-day deletions; two receiver bands divided at 1000 MHz; and a fixed-period cross-source comparison. Choices and source hashes were saved before the new calculations.','',
      '## 2. Likelihood and noise alternatives','',
      'We compared white-error scale 1 or 0.5, each with eight alternatives: white only; achromatic Fourier noise with gamma 2 and RMS 1 microsecond, or gamma 4 and RMS 1, 2 or 4 microseconds; dispersion-like or frequency^-4 noise with gamma 2 and RMS 1 microsecond at 400 MHz; and a joint model with gamma-4 achromatic RMS 2 microseconds plus both chromatic components. Each process uses 30 frequencies k/T with spectral weights normalized to its quoted RMS. These are explicitly chosen diagnostic covariances, not estimated physical noise parameters or an exhaustive model family.','',
      'The likelihood uses exact Woodbury covariance identities and projects/marginalizes the same linear timing parameters. Model comparison minimizes chi-square plus the covariance and timing-normal-matrix log determinants, with a common constant omitted. Noise selection is repeated separately under the null and sinusoid hypotheses. A small dense calculation verifies the low-rank likelihood, template Gram matrix and relative determinant; the original statistic is independently reproduced.','',
      '## 3. Original candidate and noise-only simulations','',
      f"The released-noise local refinement peaks at {a['refined']['period_days']:.1f} days, statistic {a['refined']['statistic']:.3f}, amplitude {a['refined']['amplitude_us']:.3f} microseconds. Under the preferred null model ({a['selected_null']}), the original 567.405-day statistic is {candidate:.3f} and its fitted amplitude is {selected['candidate_amplitude_us']:.3f} microseconds. The half-scale white-error choice is a diagnostic response to the initially low reduced chi-square; it is not independently calibrated uncertainty correction.",'',
      f"To assess the original candidate without confusing it with a different noise-model peak, we compared its profiled statistic with the saved global maximum from every noise-only simulation. {exceed}/512 exceeded it, giving (exceedances + 1)/(512 + 1) = {p:.4f}. This is a conservative search-adjusted diagnostic within the chosen plug-in family, not the original campaign false-alarm probability or a posterior probability that a planet exists. It does not establish an unusually small noise tail.",'',
      f"The same model family has a stronger residual maximum at {selected['peak_period_days']:.3f} days, statistic {a['family_statistic']:.3f}; 0/512 simulated maxima exceed that different peak (plus-one resolution 1/513). This result concerns the roughly 67-day feature, not the original 567-day candidate. It indicates that the bounded noise family leaves unexplained structure. This review does not establish the origin of that structure, promote it to a new calibrated survey detection, or silently expand the follow-up into another search campaign.",'',
      f"Injections at {c['injected_period_days']:.1f} days and {c['injected_amplitude_us']:.3f} microseconds recovered a period within 30 days in {c['injection_recovers_period_within_30_days']}/256 realizations. Only {c['injection_exceeds_observed']}/256 exceeded the much stronger observed *global* statistic, which belongs to the other period. The injections are sensitivity diagnostics under the selected null; they are not observed planet recoveries.",'',
      '## 4. Observing-day, time and receiver-band checks','',
      f"All 157 days were removed individually at the refined fixed period. The remaining statistic ranges from {mn:.3f} to {mx:.3f}; two direct nuisance-refitted calculations verify the sufficient-statistic method. The original-noise candidate is not driven by a single observing day. These subset statistics do not inherit the original search threshold.",'',
      '| Receiver subset | TOAs | Amplitude (microseconds) | Fixed-period statistic |','|---|---:|---:|---:|',
      f"| Below 1000 MHz | {low['toas']} | {low['amplitude_us']:.3f} | {low['statistic']:.3f} |",f"| At or above 1000 MHz | {high['toas']} | {high['amplitude_us']:.3f} | {high['statistic']:.3f} |",'',
      f"The high-frequency amplitude is poorly constrained. A joint fit with separate band coefficients improves chi-square by {b['groups']['receiver_bands']['joint_extra_statistic']:.3f} for two additional coefficients; its fixed-noise descriptive p-value is {b['groups']['receiver_bands']['consistency_p']:.3g}. The analogous time-split value is {b['groups']['time_halves']['consistency_p']:.4f}. These comparisons favor a more complex description than a common stationary sinusoid under the original covariance. They are post-selection, model-dependent diagnostics, not independent discovery probabilities or proof of a specific propagation process.",'',
      'Annual and two-year sinusoidal fits were retained as descriptive alias checks. The annual fit is poorly constrained by astrometric projection. No categorical exclusion of sampling or timing-model aliases is claimed.','',
      '## 5. Overlapping PPTA comparison','',
      f"At the refined {d['period_days']:.1f}-day period, full PPTA data give statistic {ov['ppta_full']['delta_chi2']:.3f} and amplitude {ov['ppta_full']['amplitude_us']:.4f} microseconds. In the common TDB MJD interval {d['overlap_mjd_tdb'][0]:.3f}–{d['overlap_mjd_tdb'][1]:.3f}, PPTA has {d['overlap_toas']['ppta']} TOAs and InPTA {d['overlap_toas']['inpta']}.",'',
      '| Overlap source | Amplitude (microseconds) | Fixed-period statistic |','|---|---:|---:|',
      f"| PPTA | {ov['ppta_overlap']['amplitude_us']:.3f} | {ov['ppta_overlap']['delta_chi2']:.3f} |",f"| InPTA | {ov['inpta_overlap']['amplitude_us']:.3f} | {ov['inpta_overlap']['statistic']:.3f} |",'',
      f"The conditional coefficient-contrast statistic is {d['coefficient_contrast']['statistic']:.3f} for two degrees of freedom, assuming independent source errors. Shared propagation noise and imperfect noise models limit that calculation; nevertheless, the overlapping observations provide no corroboration of a common planetary timing delay. The later InPTA subset gives only statistic {ov['inpta_after_overlap']['statistic']:.3f} with its own refitted nuisance terms.",'',
      '## 6. Disposition and limitations','',
      '**Park the original candidate as INCONCLUSIVE / NOISE-SENSITIVE.** Preserve its historical threshold crossing. This review supplies concrete reasons to weaken the planetary interpretation: sensitivity to chromatic/correlated-noise choices, receiver-band inconsistency, and lack of overlapping-source corroboration. It does not establish that no planet exists.','',
      'The finite Fourier basis, coarse noise amplitudes, selected noise-only generator, approximate timing conversion and fixed source noise assumptions limit the conclusions. The unexplained roughly 67-day residual feature further limits the adequacy of this noise family. More simulations of the same family alone would not resolve that model issue. Any future investigation of that different feature requires a separately recorded, bounded scope and source/systematics checks.','',
      '![Saved deep-review diagnostics](../outputs/j1939-deep-review-20260909/diagnostics.png)','',
      '## Reproducibility and references','',
      '- [Declared review scope](J1939_DEEP_REVIEW_2026-09-09.md) and [recurring review policy](CANDIDATE_DEEP_REVIEW.md).',
      '- [Original campaign report](PTA_CAMPAIGN_01_REPORT_2026-09-09.md), retained unchanged.',
      '- [InPTA DR2](https://github.com/inpta/InPTA.DR2), pinned source commit recorded in the original campaign.',
      '- [PPTA DR3](https://github.com/danielreardon/PPTA-DR3).',
      '- [NANOGrav ENTERPRISE](https://github.com/nanograv/enterprise) and [Fourier noise-model implementation](https://github.com/nanograv/enterprise_extensions/blob/master/enterprise_extensions/models.py).',
      '- Numerical receipts: `results/research/j1939-deep-review-20260909/`. Original inputs, saved simulation arrays and logs remain outside Git.','']
    report_path.write_text('\n'.join(lines))
    for path,sha in scope['historical_hashes'].items():assert cal.digest(path)==sha
    save('closeout.json',{'status':'COMPLETE','disposition':'INCONCLUSIVE_NOISE_SENSITIVE','target':'J1939+2134','report_path':str(report_path),'report_sha256':cal.digest(report_path),'candidate_diagnostic_p':p,'candidate_null_exceedances':exceed,'historical_json_records_preserved':len(scope['historical_hashes']),'confirmed_planets':0,'original_result_sha256':scope['original_result_sha256'],'source_result_unchanged':cal.digest(SOURCE/'run01/result.json')==scope['original_result_sha256'],'step_hashes':{f'step{i}.json':cal.digest(ROOT/f'step{i}.json') for i in range(1,5)},'simulation_arrays_sha256':cal.digest(ROOT/'simulations.npz')})
    pulse('REPORT_COMPLETE_WORKBOOK_PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run','cross-source','report']);args=parser.parse_args()
    try:
        if args.action=='prepare':prepare()
        elif args.action=='run':run()
        elif args.action=='cross-source':cross_source()
        else:report()
    except BaseException as error:
        if ROOT.exists():pulse('NEEDS_DIAGNOSIS',error=str(error))
        raise
