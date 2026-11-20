"""Bounded follow-up of the consumed NG15 J1012 binary candidate; saved checkpoints."""
import argparse
from contextlib import ExitStack
from pathlib import Path
import numpy as np
import astropy.units as u
from scipy.linalg import solve_triangular
import binary_wideband as binary
import target_calibration as cal
from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner as make


def save(root,name,value):
    cal.write(root/name,{**value,'review_code_sha256':cal.digest(__file__)})


def run(data,out):
    root=data/'J1012+5307';out.mkdir(parents=True,exist_ok=True)
    profile,a=cal.load_profile(root/'profile/profile.json')
    result=cal.read(root/'run01/result.json');n=len(a['times']);t=a['times'];epoch=profile['reference_epoch_mjd_tdb']
    y=np.load(root/'prepared/observed.npz')['residuals']
    grid=np.load(root/'run01/periodogram.npz');freq=grid['frequencies'];eligible=grid['eligible']
    k=int(np.argmin(abs(1/freq-result['peak_period_days'])))
    scope={'target':'J1012+5307','original_result_sha256':cal.digest(root/'run01/result.json'),
        'profile_sha256':cal.digest(root/'profile/profile.json'),'observed_sha256':cal.digest(root/'prepared/observed.npz'),
        'periodogram_sha256':cal.digest(root/'run01/periodogram.npz'),
        'family':['released30','red64','red128','red128_double_power','red128_chrom4'],
        'nulls_each':512,'injections_each':64,'seed':2026093300,'candidate_period_days':result['peak_period_days'],
        'noise_policy':'Keep released red amplitude/slope; extend 30 modes to 64/128, double red power at 128, or add 0.3 us RMS nu^-4 timing covariance at 1400 MHz with 100-day exponential correlation. No fitted noise selection.',
        'simulation_policy':'Each model analyzed separately; all original eligible periods scanned for every null/injection; original-period statistic compared with null maxima. Report largest per-model plus-one tail without pooling.',
        'subsets':'Full, first/second temporal halves, below/above 1000 MHz, GASP/GUPPI; joint TOA+DM rows retained; original and red128 covariances.',
        'influence':'Delete every observing-day TOA and corresponding DM rows; refit nuisance terms at the frozen candidate period; original and red128 covariance.',
        'limits':'Conditional finite noise family, not global significance. Cross-source raw EPTA T2 H3/H4 model needs unsupported orthometric Shapiro preparation; no independent fit claimed.'}
    if (out/'scope.json').exists():
        old=cal.read(out/'scope.json')
        if any(old.get(key)!=value for key,value in scope.items()) or old['review_code_sha256']!=cal.digest(__file__):raise ValueError('Review scope/code changed')
    else:save(out,'scope.json',scope)
    if not (out/'noise-inputs.npz').exists():
        import pint.logging
        from pint.models import get_model_and_toas
        from pint.fitter import WidebandTOAFitter
        pint.logging.setup(level='WARNING',sink=out/'metadata-pint.log',removeprior=True)
        with ExitStack() as stack:
            deny=stack.enter_context(binary.NetworkDeny());local=stack.enter_context(binary.BinaryResources(data));local.bind_science_resources()
            model,toas=get_model_and_toas(root/'prepared/timing-model.par',root/'original/J1012+5307.tim',ephem='DE440',include_bipm=True,bipm_version='BIPM2019',planets=True,usepickle=False,limits='error')
            np.testing.assert_allclose(toas.table['tdbld'].data,t,rtol=0,atol=1e-10)
            covariances={}
            for modes in [30,64,128]:
                model.TNREDC.value=modes
                covariances['red'+str(modes)]=WidebandTOAFitter(toas,model).get_noise_covariancematrix().matrix
            np.testing.assert_allclose(covariances['red30'],a['covariance'],rtol=1e-10,atol=1e-24)
            model.RNAMP.value=float(model.RNAMP.value)*np.sqrt(2)
            covariances['red128_double_power']=WidebandTOAFitter(toas,model).get_noise_covariancematrix().matrix
            if deny.attempts:raise ValueError('Network attempted')
            np.savez_compressed(out/'noise-inputs.npz',**covariances,radio=toas.get_freqs().to_value(u.MHz),backend=np.array([f.get('be','') for f in toas.table['flags']]))
        save(out,'noise-inputs.json',{'sha256':cal.digest(out/'noise-inputs.npz'),'released_covariance_reproduced':True})
    if cal.read(out/'noise-inputs.json')['sha256']!=cal.digest(out/'noise-inputs.npz'):raise ValueError('Noise inputs changed')
    meta=np.load(out/'noise-inputs.npz');families={'released30':meta['red30'],'red64':meta['red64'],'red128':meta['red128'],'red128_double_power':meta['red128_double_power']}
    extra=np.zeros_like(a['covariance']);scaling=(1400/meta['radio'])**4*.3e-6
    extra[:n,:n]=np.outer(scaling,scaling)*np.exp(-abs(t[:,None]-t[None,:])/100)
    families['red128_chrom4']=meta['red128']+extra
    base=make(a['covariance'],a['design'],t,np.array([freq[k]]),epoch)
    original=base.scan(y);coefficient=original['all_coefficients_seconds'][0]
    template=binary.observed.circular_template(t,epoch,freq[k],len(y));injected=template@coefficient
    for index,(name,C) in enumerate(families.items()):
        if (out/(name+'.json')).exists():continue
        scanner=make(C,a['design'],t,freq,epoch);observed=scanner.scan(y)
        candidate=float(observed['all_delta_chi2'][k]);peak=int(np.argmax(np.where(eligible,observed['all_delta_chi2'],-np.inf)))
        rng=np.random.default_rng(scope['seed']+index);maxima=[];recoveries=0
        for count,signal in [(512,None),(64,injected)]:
            for start in range(0,count,64):
                white=rng.standard_normal((len(y),min(64,count-start)))
                if signal is not None:white+=scanner.whiten_and_project(signal)[:,None]
                rhs=np.einsum('nfi,nb->fib',scanner.projected_whitened_templates,white)
                stats=np.einsum('fib,fij,fjb->fb',rhs,scanner.template_gram_pseudoinverse,rhs)
                peaks=np.argmax(np.where(eligible[:,None],stats,-np.inf),axis=0)
                values=stats[peaks,np.arange(len(peaks))]
                if signal is None:maxima.extend(values.tolist())
                else:recoveries+=int(np.sum((values>result['threshold'])&(abs(1/freq[peaks]/result['peak_period_days']-1)<.05)))
        exceed=int(np.sum(np.asarray(maxima)>=candidate))
        np.save(out/(name+'-null-maxima.npy'),np.asarray(maxima))
        save(out,name+'.json',{'model':name,'candidate_delta_chi2':candidate,'candidate_amplitude_us':float(np.linalg.norm(observed['all_coefficients_seconds'][k])*1e6),
            'strongest_eligible_period_days':float(1/freq[peak]),'maximum_delta_chi2':float(observed['all_delta_chi2'][peak]),
            'null_exceedances':exceed,'null_count':512,'diagnostic_p_plus_one':(exceed+1)/513,'injection_recovered':recoveries,'injection_count':64,
            'null_maxima_sha256':cal.digest(out/(name+'-null-maxima.npy'))})
        print(name,candidate,exceed,recoveries,flush=True)
    if not (out/'shapiro.json').exists():
        phase=np.load(root/'prepared/orbital-phase.npz')['phase_radians']
        from pint import Tsun
        delay=lambda m,i:-2*Tsun.to_value(u.s)*m*np.log1p(-np.sin(np.deg2rad(i))*np.sin(phase))
        ref=delay(.165,50);rows=[]
        for m in [.120,.165,.210]:
            for inc in [44.,50.,56.]:
                delta=np.zeros(len(y));delta[:n]=delay(m,inc)-ref
                fit=base.scan(y-delta)
                rows.append({'mass_solar':m,'inclination_degrees':inc,'candidate_delta_chi2':fit['trigger_statistic'],'amplitude_us':fit['amplitude_us']})
        save(out,'shapiro.json',{'scenarios':rows,'scope':'Fixed candidate period and final design; subtract alternative-minus-reference delay; linear nuisance refit, not full nonlinear Shapiro inference'})
    if not (out/'subsets.json').exists():
        records=[];days=np.floor(t).astype(int)
        for name in ['released30','red128']:
            C=families[name]
            for label,mask in [('first_half',t<=np.median(t)),('second_half',t>np.median(t)),('below1000MHz',meta['radio']<1000),('above1000MHz',meta['radio']>=1000),('GASP',meta['backend']=='GASP'),('GUPPI',meta['backend']=='GUPPI')]:
                keep=np.flatnonzero(mask);indices=np.r_[keep,keep+n]
                if len(keep)<20:records.append({'model':name,'subset':label,'status':'UNDERPOWERED','toas':len(keep)});continue
                scanner=make(C[np.ix_(indices,indices)],a['design'][indices],t[keep],np.array([freq[k]]),epoch)
                fit=scanner.scan(y[indices]);cov=scanner.template_gram_pseudoinverse[0]*1e12
                records.append({'model':name,'subset':label,'toas':len(keep),'timing_rank':scanner.timing_design_rank,'delta_chi2':fit['trigger_statistic'],'amplitude_us':fit['amplitude_us'],
                    'coefficients_us':(fit['all_coefficients_seconds'][0]*1e6).tolist(),'coefficient_covariance_us2':cov.tolist()})
        save(out,'subsets.json',{'fits':records,'scope':'Same fixed period and phase origin; subset nuisance refits. Correlated subsets are not independent confirmations.'})
    if not (out/'days.json').exists():
        records=[]
        for name in ['released30','red128']:
            C=families[name];scanner=make(C,a['design'],t,np.array([freq[k]]),epoch)
            Linv=solve_triangular(scanner.covariance_cholesky,np.eye(len(y)),lower=True)
            B=Linv-scanner.timing_projection_basis@(scanner.timing_projection_basis.T@Linv)
            P=B.T@B;Py=P@y;PT=P@template;gram=template.T@PT;rhs=template.T@Py
            for day in np.unique(days):
                removed=np.flatnonzero(days==day);indices=np.r_[removed,removed+n]
                block=P[np.ix_(indices,indices)];scale=np.sqrt(np.maximum(np.diag(block),np.finfo(float).tiny))
                inv=np.linalg.pinv(block/np.outer(scale,scale),rcond=1e-10)/np.outer(scale,scale)
                g=gram-PT[indices].T@inv@PT[indices];b=rhs-PT[indices].T@inv@Py[indices]
                statistic=float(b@np.linalg.pinv(g,rcond=1e-12)@b)
                records.append({'model':name,'day_mjd_tdb':int(day),'removed_toas':len(removed),'delta_chi2':statistic})
            # Verify the deletion identity once per covariance by a fresh reduced fit.
            keep=np.flatnonzero(days!=np.unique(days)[0]);indices=np.r_[keep,keep+n]
            direct=make(C[np.ix_(indices,indices)],a['design'][indices],t[keep],np.array([freq[k]]),epoch).scan(y[indices])['trigger_statistic']
            np.testing.assert_allclose(records[-len(np.unique(days))]['delta_chi2'],direct,rtol=1e-6,atol=1e-7)
        save(out,'days.json',{'fits':records,'scope':'All observing-day deletions with joint TOA/DM rows and nuisance refit at the fixed candidate period; generalized GLS deletion identity checked against direct fits.'})
    save(out,'closeout.json',{'status':'BOUNDED_REVIEW_COMPLETE','original_result_sha256':cal.digest(root/'run01/result.json'),
        'artifacts':{p.name:cal.digest(p) for p in out.glob('*.json') if p.name!='closeout.json'}})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();run(a.data.resolve(),a.output.resolve())
