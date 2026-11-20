"""Fixed-period, source-separated EPTA comparison after native binary checks."""
import argparse
from pathlib import Path
import json
import numpy as np
from scipy import linalg
from scipy.stats import chi2,ncx2
from pint.models.tcb_conversion import IFTE_K,IFTE_MJD0
import target_calibration as cal
import mpta_batch as mpta


class LowRankGLS:
    def __init__(self,sigma,factors,design):
        self.sigma=sigma;self.u=factors/sigma[:,None]
        self.k=linalg.cho_factor(np.eye(factors.shape[1])+self.u.T@self.u,lower=True)
        norms=np.linalg.norm(design/sigma[:,None],axis=0)
        if np.any(norms==0):raise ValueError('Zero timing column')
        self.norms=norms;self.x=design/norms
        self.cx=self.precision(self.x)
        self.gram=self.x.T@self.cx
        self.condition=float(np.linalg.cond(self.gram))
        self.normal=linalg.cho_factor(self.gram,lower=True)
        self.design=design;self.factors=factors

    def precision(self,v):
        w=v/self.sigma[:,None] if v.ndim==2 else v/self.sigma
        result=w-self.u@linalg.cho_solve(self.k,self.u.T@w)
        return result/self.sigma[:,None] if v.ndim==2 else result/self.sigma

    def project_precision(self,v):
        cv=self.precision(v)
        return cv-self.cx@linalg.cho_solve(self.normal,self.x.T@cv)

    def fit(self,y,h=None):
        cy=self.precision(y);beta=linalg.cho_solve(self.normal,self.x.T@cy)/self.norms
        r=y-self.design@beta;null=float(r@self.precision(r))
        if h is None:return null,beta
        ph=self.project_precision(h);gram=h.T@ph
        cov=np.linalg.inv(gram);coeff=cov@(h.T@self.project_precision(y))
        return {'null_chi2':null,'delta_chi2':float(coeff@gram@coeff),'coefficients':coeff,
                'covariance':cov,'timing_coefficients':beta,'condition':self.condition}

    def independent_null(self,y):
        x=self.design/self.sigma[:,None];x/=np.linalg.norm(x,axis=0)
        z=np.column_stack([x,self.u]);prior=np.zeros((self.u.shape[1],z.shape[1]));prior[:,x.shape[1]:]=np.eye(self.u.shape[1])
        z=np.vstack([z,prior]);rhs=np.r_[y/self.sigma,np.zeros(self.u.shape[1])]
        solution,_,rank,_=linalg.lstsq(z,rhs,cond=1e-12,lapack_driver='gelsd')
        return float(np.sum((rhs-z@solution)**2)),int(rank),z.shape[1]


def factors(times,radio,fields,prefix,modes):
    span=float(np.longdouble(fields['FINISH'][0])-np.longdouble(fields['START'][0]))
    f=np.arange(1,modes+1)/span
    power=10**(2*float(fields[prefix+'Amp'][0]))*3.16e7**3*(f*365.25)**(-float(fields[prefix+'Gam'][0]))/(span*86400)
    if prefix=='TNRed':power/=12*np.pi**2
    phase=2*np.pi*np.asarray(times-np.longdouble(fields['PEPOCH'][0]),float)[:,None]*f
    b=np.empty((len(times),2*modes));b[:,0::2]=np.sin(phase);b[:,1::2]=np.cos(phase)
    b*=np.repeat(np.sqrt(power),2)
    if prefix=='TNDM':b/= (2.41e-16*radio**2)[:,None]
    return b


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--data',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();p=args.prepared.resolve();data=args.data.resolve();out=args.output.resolve()
    if out.exists():raise FileExistsError('Comparison destination consumed')
    receipt=cal.read(p/'compatibility.json');scope=cal.read(p/'scope.json')
    if receipt['status']!='NATIVE_TIMING_COMPATIBLE':raise ValueError('Timing compatibility has not passed')
    for name,digest in receipt['artifacts'].items():
        if cal.digest(p/name)!=digest:raise ValueError('Changed prepared artifact '+name)
    for name,digest in scope['code'].items():
        if cal.digest(mpta.REPO/name)!=digest:raise ValueError('Changed native adapter '+name)
    for name,digest in scope['inputs'].items():
        if cal.digest(p/name)!=digest:raise ValueError('Changed original input '+name)
    a=np.load(p/'timing.npz');meta=cal.read(p/'timing.json');ref=np.loadtxt(p/'reference.txt',dtype=np.longdouble)
    y=np.asarray(a['residuals'],float);x=np.asarray(a['design'],float);names=a['names'].tolist();n=len(y)
    fields={v[0]:v[1:] for line in (p/'model.par').read_text().splitlines() if (v:=line.split()) and not line.startswith('#')}
    sigma=np.asarray(ref[:,4]*1e-6,float)
    white=a['errors_us']**2
    for key,value in meta['noise'].items():
        if key.startswith('efac_'):white[a['groups']==value['flag_value']]*=value['value']**2
    for key,value in meta['noise'].items():
        if key.startswith('equad_'):white[a['groups']==value['flag_value']]+=value['value']**2
    white_error=float(np.max(abs(np.sqrt(white)*1e-6-sigma)/sigma))
    if white_error>1e-10:raise ValueError('White-noise convention mismatch')
    oldred=np.loadtxt(p/'reference.txt.red');olddm=np.loadtxt(p/'reference.txt.dm')
    red=factors(a['times'],a['frequency_hz'],fields,'TNRed',149)
    dm=factors(a['times'],a['frequency_hz'],fields,'TNDM',45)
    # Compare Gram products on all rows against 24 reference rows; Fourier
    # factors themselves can differ by irrelevant phase rotations.
    errors={}
    for label,ours,reference in [('red',red,oldred),('dm',dm,olddm)]:
        expected=reference@reference[:24].T
        error=float(np.linalg.norm(ours@ours[:24].T-expected)/np.linalg.norm(expected));errors[label]=error
        if error>1e-7:raise ValueError('Noise factor convention mismatch '+label)
    base=LowRankGLS(sigma,np.column_stack([red,dm]),x)
    null,beta=base.fit(y)
    shifts={name:float(abs(beta[names.index(name)])/np.longdouble(v['uncertainty'])) for name,v in meta['binary_parameters'].items()}
    independent,rank,columns=base.independent_null(y)
    if not np.isclose(null,independent,rtol=1e-7,atol=1e-5) or rank!=columns:raise ValueError('Independent null likelihood failed')
    out.mkdir(parents=True)
    null_receipt={'status':'TIMING_NOISE_COMPATIBLE' if max(shifts.values())<=3 else 'ORBITAL_SHIFT_HOLD',
                  'toas':n,'white_relative_error':white_error,'noise_factor_relative_errors':errors,
                  'marginal_null_chi2':null,'independent_augmented_chi2':independent,'joint_rank':rank,
                  'joint_columns':columns,'null_reduced_chi2':null/(n-x.shape[1]),
                  'orbital_shifts_in_published_sigma':shifts,'no_periodic_fit_executed_yet':True}
    cal.write(out/'null-compatibility.json',null_receipt)
    if max(shifts.values())>3:
        print(json.dumps(null_receipt),flush=True);return
    ngroot=data/'binary-pilot03-20260909/J1012+5307'
    ngprofile=cal.read(ngroot/'profile/profile.json');epoch=ngprofile['reference_epoch_mjd_tdb'];period=scope['fixed_period_days_tdb']
    times=np.asarray((np.asarray(a['times'],np.longdouble)-IFTE_MJD0)/IFTE_K+IFTE_MJD0,float)
    phase=2*np.pi*(times-epoch)/period
    # Fit in native TCB residual seconds, report coefficients/covariance in TDB.
    h=np.column_stack([np.sin(phase),np.cos(phase)])*float(IFTE_K)
    dev=data/'joint-noise-development-20260910/J1012+5307';devresult=cal.read(dev/'result.json');devscope=cal.read(dev/'scope.json')
    matrix=np.load(dev/'inputs.npz');candidate=int(np.argmin(abs(matrix['periods']/period-1)))
    model=devresult['original_candidate']['signal_model'];saved=np.load(dev/f'model-{model:02d}.npz')
    ngbeta=saved['observed_beta_grid'][candidate];ngcov=saved['inverse_gram'][candidate]
    newred=factors(a['times'],a['frequency_hz'],fields,'TNRed',256)
    newdm=factors(a['times'],a['frequency_hz'],fields,'TNDM',64)
    freeze={'period_days_tdb':period,'reference_epoch_mjd_tdb':epoch,'models':['published_red149_dm45','covered_red256_dm64','covered_double_red_power'],
            'conditional_fixed_period_alpha':.01,'TCB_to_TDB_K':str(IFTE_K),'TCB_to_TDB_epoch':str(IFTE_MJD0),
            'comparison':'Conditional fixed-period coefficients versus saved NG15 joint-noise model; no EPTA period selection',
            'overlap':'Separate observatories can share propagation noise. No independent-error assumption is claimed beyond this conditional coefficient diagnostic.',
            'native_preparation_scope_sha256':cal.digest(p/'scope.json'),'code_sha256':cal.digest(__file__),
            'NG15_reference':{name:cal.digest(dev/name) for name in ['result.json','scope.json','inputs.npz',f'model-{model:02d}.npz']}}
    cal.write(out/'comparison-freeze.json',freeze)
    records=[]
    for label,f in zip(freeze['models'],[np.column_stack([red,dm]),np.column_stack([newred,newdm]),np.column_stack([newred*np.sqrt(2),newdm])]):
        gls=LowRankGLS(sigma,f,x);fit=gls.fit(y,h)
        cov=fit['covariance'];coeff=fit['coefficients'];delta=coeff-ngbeta
        contrast=float(delta@np.linalg.solve(cov+ngcov,delta))
        power=float(ncx2.sf(chi2.isf(.01,2),2,ngbeta@np.linalg.solve(cov,ngbeta)))
        records.append({'model':label,'period_days':period,'delta_chi2':fit['delta_chi2'],
                        'fixed_period_conditional_p':float(chi2.sf(fit['delta_chi2'],2)),
                        'coefficients_us':(coeff*1e6).tolist(),'coefficient_covariance_us2':(cov*1e12).tolist(),
                        'amplitude_us':float(np.linalg.norm(coeff)*1e6),'NG15_waveform_detection_power_conditional':power,
                        'source_coefficient_contrast_chi2':contrast,'source_contrast_conditional_p':float(chi2.sf(contrast,2)),
                        'null_chi2':fit['null_chi2']})
        print('COMPARISON',label,fit['delta_chi2'],'power',power,flush=True)
    result={'status':'FIXED_PERIOD_COMPARISON_COMPLETE','target':'J1012+5307','completed_utc':mpta.now(),
            'toas':n,'epochs':len(np.unique(np.floor(times))),'span_days':float(np.ptp(times)),
            'mjd_tdb_range':[float(times.min()),float(times.max())],'records':records,
            'NG15_coefficients_us':(ngbeta*1e6).tolist(),'NG15_coefficient_covariance_us2':(ngcov*1e12).tolist(),
            'comparison_freeze_sha256':cal.digest(out/'comparison-freeze.json'),
            'interpretation':'Fixed-period conditional diagnostic only; no new survey detection or independent discovery significance.'}
    cal.write(out/'result.json',result)


if __name__=='__main__':main()
