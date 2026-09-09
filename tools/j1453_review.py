"""Bounded agent-assisted follow-up of the frozen J1453+1902 NG15 candidate.

This diagnostic does not change the qualified scanner or claim a new detection.
Scope and original evidence live alongside each review's external outputs.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import minimize_scalar
from scipy.stats import chi2

REPO = Path(__file__).resolve().parents[1]
DATA = REPO.parent / 'Project Recherche Data'
ROOT = DATA / 'j1453-human-review-20260908'
SOURCE = DATA / 'ng15-batch01-20260908/J1453+1902'
REFERENCE = 57777.0

def write(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def template(times, periods, dimension):
    phase = 2 * np.pi * (times[:, None] - REFERENCE) / np.atleast_1d(periods)
    out = np.zeros((dimension, phase.shape[1], 2))
    out[:len(times), :, 0], out[:len(times), :, 1] = np.sin(phase), np.cos(phase)
    return out

class GLS:
    def __init__(self, covariance, design):
        self.L = np.linalg.cholesky(covariance)
        norms = np.linalg.norm(design, axis=0)
        x = design[:, norms > 0] / norms[norms > 0]
        w = solve_triangular(self.L, x, lower=True)
        wn = np.linalg.norm(w, axis=0)
        u, s, _ = np.linalg.svd(w / wn, full_matrices=False)
        self.rank = int(np.sum(s > s[0] * 1e-12))
        self.Q = u[:, :self.rank]
        self.offset = float(2 * np.log(np.diag(self.L)).sum())
        if self.rank == len(wn):
            self.offset += float(2 * np.log(s).sum() + 2 * np.log(wn).sum())
        self.design = design

    def project(self, v):
        w = solve_triangular(self.L, v, lower=True)
        return w - self.Q @ (self.Q.T @ w)

    def bank(self, templates):
        z = self.project(templates.reshape(len(self.L), -1)).reshape(templates.shape)
        gram = np.einsum('dfi,dfj->fij', z, z)
        inverse = np.linalg.pinv(gram, rcond=1e-12)
        return z, inverse

    def scan(self, y, bank):
        z, inverse = bank
        cross = np.einsum('dfi,d->fi', z, self.project(y))
        beta = np.einsum('fij,fj->fi', inverse, cross)
        return np.einsum('fi,fi->f', cross, beta), beta

    def fit(self, y, times, period):
        bank = self.bank(template(times, [period], len(y)))
        score, beta = self.scan(y, bank)
        return {'period_days': float(period), 'delta_chi2': float(score[0]),
                'amplitude_us': float(np.linalg.norm(beta[0]) * 1e6),
                'sin_cos_us': (beta[0] * 1e6).tolist(),
                'coefficient_covariance_us2': (bank[1][0] * 1e12).tolist(),
                'null_chi2': float(np.sum(self.project(y)**2)), 'rank': self.rank,
                'dof_null': len(y) - self.rank}


def run():
    if (ROOT / 'step3.json').exists():
        raise FileExistsError('Completed review exists; read its evidence instead of repeating simulations')
    scope = json.loads((ROOT / 'scope.json').read_text())
    assert hashlib.sha256((SOURCE / 'run01/result.json').read_bytes()).hexdigest() == scope['original_result_sha256']
    a = np.load(SOURCE / 'profile/arrays.npz'); y = np.load(SOURCE / 'prepared/observed.npz')['residuals']
    t, c, x = a['times'], a['covariance'], a['design']; n = len(t)
    meta = np.load(ROOT / 'metadata.npz'); np.testing.assert_array_equal(t, meta['times'])
    days = np.floor(t).astype(int); local = np.linspace(100, 140, 801)
    gls = GLS(c, x); localbank = gls.bank(template(t, local, len(y)))
    scores, _ = gls.scan(y, localbank); j = int(np.argmax(scores))
    optimized = minimize_scalar(lambda p: -gls.fit(y,t,p)['delta_chi2'],
        bounds=(local[max(0,j-1)],local[min(len(local)-1,j+1)]), method='bounded',options={'xatol':1e-9})
    period = float(optimized.x); fit = gls.fit(y,t,period)
    original = gls.fit(y,t,118.42725685587168)
    np.testing.assert_allclose(original['delta_chi2'],34.91423261298593,rtol=1e-9)
    intervals = {}
    for delta, label in [(1,'conditional_68_percent'),(3.84145882,'conditional_95_percent')]:
        mask = scores >= fit['delta_chi2']-delta
        intervals[label] = {'envelope_days': [float(local[mask].min()),float(local[mask].max())],
                           'grid_resolution_days': .05, 'disjoint_components': int(np.sum(np.diff(np.r_[False,mask].astype(int))==1))}
    # Compare aliases and joint templates, not just the spectral-window amplitude.
    annual = gls.fit(y,t,365.25/3)
    both = np.concatenate([template(t,[period],len(y))[:,0],template(t,[365.25/3],len(y))[:,0]],axis=1)
    projected = gls.project(both); u,s,_=np.linalg.svd(projected,full_matrices=False)
    joint = float(np.sum((u[:,:4].T @ gls.project(y))**2))
    loo=[]
    for day in np.unique(days):
        keep = np.flatnonzero(days != day); ix=np.r_[keep,keep+n]
        g=GLS(c[np.ix_(ix,ix)],x[ix]); b=g.bank(template(t[keep],local,len(ix)))
        sc,_=g.scan(y[ix],b); k=int(np.argmax(sc)); f=g.fit(y[ix],t[keep],period)
        loo.append({'removed_mjd_day':int(day),'removed_toas':int(n-len(keep)),
                    'fixed_period':f,'local_peak_period_days':float(local[k]),'local_peak_statistic':float(sc[k])})
    window = np.abs(np.mean(np.exp(2j*np.pi*(t[:,None]-REFERENCE)/local),axis=0))**2
    step1={'original_grid_reproduced':original,'refined':fit,'profile_intervals':intervals,
           'uncertainty_scope':'Local fixed-noise profile likelihood; conditional on circular model and selected candidate, not global discovery confidence',
           'annual_third_harmonic':annual,'joint_two_period_delta_chi2':joint,
           'candidate_added_after_annual_delta_chi2':joint-annual['delta_chi2'],
           'annual_added_after_candidate_delta_chi2':joint-fit['delta_chi2'], 'leave_one_day_out':loo}
    write('step1.json',step1)
    print('STEP1',json.dumps({k:step1[k] for k in ('refined','profile_intervals','annual_third_harmonic','candidate_added_after_annual_delta_chi2')}),flush=True)
    # Disjoint subset coefficients for descriptive checks; joint split model provides a correct contrast.
    splits={'early_late':t <= np.median(np.unique(days)), 'radio_band':meta['freq_mhz']<800}
    groups={}
    for name, mask in splits.items():
        subsets=[]
        for selected in (mask,~mask):
            keep=np.flatnonzero(selected);ix=np.r_[keep,keep+n]
            g=GLS(c[np.ix_(ix,ix)],x[ix]); subsets.append({'toas':len(keep),'fit':g.fit(y[ix],t[keep],period)})
        h=template(t,[period],len(y))[:,0];ha=h.copy();hb=h.copy()
        ha[:n][~mask]=0;hb[:n][mask]=0
        split=np.column_stack([ha,hb]);z=gls.project(split);u,s,_=np.linalg.svd(z,full_matrices=False)
        rank=int(np.sum(s>s[0]*1e-12));sc=float(np.sum((u[:,:rank].T@gls.project(y))**2))
        extra=sc-fit['delta_chi2']; groups[name]={'subsets':subsets,'joint_split_delta_chi2':sc,
                 'extra_delta_chi2_over_common_signal':extra,'extra_dof':rank-2,
                 'fixed_period_consistency_p':float(chi2.sf(extra,rank-2))}
    step2={'groups':groups,'limitations':'Same discovery observations; descriptive fixed-period contrasts, not independent validation. Free subset nuisance parameters reduce sensitivity.'}
    write('step2.json',step2); print('STEP2',json.dumps(step2),flush=True)
    # Each covariance is a fixed member of one declared family. Marginalize linear timing
    # coefficients with the same flat-prior measure, profile sinusoid and discrete covariance.
    dt=np.abs(t[:,None]-t[None,:]); family=[('released',c.copy())]
    for amp in [.5,1,2,4]:
        cov=c.copy();cov[:n,:n]+=(amp*1e-6)**2*np.exp(-dt/365)
        family.append((f'red_exp365_{amp:g}us',cov))
    cov=c.copy();scale=np.ones(2*n);scale[n:]=2;cov*=scale[:,None]*scale[None,:]
    family.append(('double_dm_errors',cov))
    chrom=(1400/meta['freq_mhz'])**4
    for amp in [1,2]:
        cov=c.copy();cov[:n,:n]+=(amp*1e-6)**2*np.outer(chrom,chrom)*np.exp(-dt/90)
        family.append((f'chromatic_nu4_exp90_{amp}us',cov))
    original_grid=np.load(SOURCE/'run01/periodogram.npz')
    periods=np.unique(np.r_[1/original_grid['frequencies'][original_grid['eligible']],local,period])
    h=template(t,periods,len(y));models=[];observed=[]
    for name,cov in family:
        g=GLS(cov,x);b=g.bank(h);sc,beta=g.scan(y,b);null=float(g.project(y)@g.project(y)+g.offset); k=int(np.argmax(sc))
        observed.append({'model':name,'null_objective':null,'signal_objective':null-float(sc[k]),
            'peak':g.fit(y,t,periods[k]),'at_candidate':g.fit(y,t,period)})
        models.append((g,b))
    ni=int(np.argmin([r['null_objective'] for r in observed]));si=int(np.argmin([r['signal_objective'] for r in observed]))
    statistic=observed[ni]['null_objective']-observed[si]['signal_objective']
    rng=np.random.default_rng(scope['seed']);count=768
    samples=models[ni][0].L@rng.standard_normal((len(y),count))
    injection=template(t,[period],len(y))[:,0]@(np.array(fit['sin_cos_us'])*1e-6)
    samples[:,512:]+=injection[:,None]
    bestnull=np.full(count,np.inf);bestsignal=np.full(count,np.inf);recovered=np.zeros(count)
    for (name,_),(g,(z,inv)) in zip(family,models):
        yp=g.project(samples);q=np.sum(yp*yp,axis=0)+g.offset
        cross=(z.reshape(len(y),-1).T@yp).reshape(len(periods),2,count)
        score=np.einsum('fik,fij,fjk->fk',cross,inv,cross,optimize=True)
        ks=np.argmax(score,axis=0);candidate=q-score[ks,np.arange(count)]
        changed=candidate<bestsignal;recovered[changed]=periods[ks[changed]]
        bestnull=np.minimum(bestnull,q);bestsignal=np.minimum(bestsignal,candidate)
        print('SIMULATION model completed',name,flush=True)
    sim=bestnull-bestsignal; exceed=int(np.sum(sim[:512]>=statistic));krec=np.abs(recovered[512:]-period)<=2
    step3={'method':'Timing-marginalized Gaussian objective: chi-square + logdet(C) + logdet(Xscaled.T C^-1 Xscaled); same timing prior measure; discrete covariance selection repeated separately under null and sinusoid. No signal-prior evidence claim.',
       'covariance_models':observed,'selected_null':family[ni][0],'selected_signal':family[si][0],
       'selected_family_statistic':statistic,'seed':scope['seed'],'null_count':512,'injection_count':256,
       'null_generator':family[ni][0],'injected_amplitude_us':fit['amplitude_us'],'injected_period_days':period,
       'null_exceedances':exceed,'diagnostic_p_plus_one':(exceed+1)/513,
       'injection_exceeds_observed':int(np.sum(sim[512:]>=statistic)),
       'injection_recovers_period_within_2_days':int(np.sum(krec)),
       'limitations':'Plug-in noise family and modest simulation count; not a new campaign-calibrated discovery p-value. Injection at estimated signal is a sensitivity diagnostic. Full grid searched and covariance reselection repeated; does not model all possible propagation noise.'}
    write('step3.json',step3)
    np.savez_compressed(ROOT/'review-arrays.npz',local_periods=local,local_scores=scores,window=window,simulation_statistic=sim,recovered_periods=recovered)
    print('STEP3',json.dumps({k:v for k,v in step3.items() if k!='covariance_models'}),flush=True)
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(2,2,figsize=(11,7))
    axs[0,0].plot(local,scores);axs[0,0].axvline(365.25/3,color='orange',label='Annual third harmonic');axs[0,0].set(xlabel='Period (days)',ylabel='Delta chi-square');axs[0,0].legend()
    axs[0,1].plot(local,window);axs[0,1].set(xlabel='Period (days)',ylabel='Unweighted sampling-window power')
    axs[1,0].scatter([r['removed_mjd_day'] for r in loo],[r['fixed_period']['delta_chi2'] for r in loo],s=10);axs[1,0].set(xlabel='Removed observing day (MJD)',ylabel='Remaining fixed-period delta chi-square')
    axs[1,1].hist(sim[:512],bins=30,alpha=.7,label='Null');axs[1,1].hist(sim[512:],bins=30,alpha=.5,label='Injected');axs[1,1].axvline(statistic,color='black');axs[1,1].set(xlabel='Noise-family selected statistic',ylabel='Realizations');axs[1,1].legend()
    fig.suptitle('J1453+1902: candidate review diagnostics — not planet confirmation');fig.tight_layout();fig.savefig(ROOT/'review-diagnostics.png',dpi=150);plt.close(fig)
    # Save a nuisance-refitted timing curve. Points retain TOA units, not whitened units.
    h1=template(t,[period],len(y))[:,0];signal=h1@np.array(fit['sin_cos_us'])*1e-6
    wx=solve_triangular(gls.L,x,lower=True);norm=np.linalg.norm(wx,axis=0)
    coef=np.linalg.lstsq(wx/norm,solve_triangular(gls.L,y-signal,lower=True),rcond=1e-12)[0]/norm
    cleaned=y-x@coef;phase=((t-REFERENCE)/period)%1
    fig,ax=plt.subplots(figsize=(9,4));ax.errorbar(phase,cleaned[:n]*1e6,yerr=np.sqrt(np.diag(c)[:n])*1e6,fmt='.',alpha=.6)
    ph=np.linspace(0,1,300);bc=np.array(fit['sin_cos_us']);ax.plot(ph,np.sin(2*np.pi*ph)*bc[0]+np.cos(2*np.pi*ph)*bc[1]);ax.set(xlabel='Phase at refined period',ylabel='Timing residual (microseconds)',title='Joint nuisance-refitted wideband data; errors are marginal TOA errors');fig.tight_layout();fig.savefig(ROOT/'phase-fit.png',dpi=150)
    write('code-receipt.json',{'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope_sha256':hashlib.sha256((ROOT/'scope.json').read_bytes()).hexdigest(),'original_result_unchanged':hashlib.sha256((SOURCE/'run01/result.json').read_bytes()).hexdigest()==scope['original_result_sha256']})

if __name__ == '__main__':
    run()
