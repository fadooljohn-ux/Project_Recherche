"""Bounded J1802 preparation diagnostics; no observed outer-period search."""
import argparse
from pathlib import Path

import numpy as np
from scipy.linalg import solve_triangular
from scipy.stats import chi2
import binary_wideband as binary
import joint_noise
import mpta_batch
import target_calibration as cal
from pulsar_pilot.pilot1_runtime import build_search_frequency_grid, prepare_covariance_gls_scanner
from recherche_common import require


def harmonic_fit(covariance, design, data, basis):
    L=np.linalg.cholesky(covariance)
    X=solve_triangular(L,design,lower=True);X/=np.linalg.norm(X,axis=0)
    q,_=np.linalg.qr(X,mode='reduced')
    y=solve_triangular(L,data,lower=True);y-=q@(q.T@y)
    h=solve_triangular(L,basis,lower=True);h-=q@(q.T@h)
    norms=np.linalg.norm(h,axis=0);h=h/norms
    beta,_,rank,_=np.linalg.lstsq(h,y,rcond=1e-12)
    fitted=h@beta
    improvement=float(fitted@fitted)
    errors=np.sqrt(np.diag(np.linalg.pinv(h.T@h)))/norms
    return {'rank':int(rank),'columns':basis.shape[1],'delta_chi2':improvement,
            'conditional_chi2_tail':float(chi2.sf(improvement,rank)),
            'coefficients_us':(beta/norms*1e6).tolist(),
            'conditional_errors_us':(errors*1e6).tolist(),
            'normalized_condition':float(np.linalg.cond(h))}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise FileExistsError('Diagnostic destination consumed')
    selection=cal.read(args.data/'selection.json');requested=cal.read(args.selection)
    require(selection['selected']==['J1802-2124'], "selection['selected']==['J1802-2124']")
    require(cal.digest(args.selection)==selection['requested_selection_sha256'], "cal.digest(args.selection)==selection['requested_selection_sha256']")
    settings=requested['diagnostics'];root=args.data/'J1802-2124'
    receipt=binary.verify_preparation(args.data,'J1802-2124')
    profile,a=cal.load_profile(root/'profile/profile.json')
    require(receipt['orbital_phase_sha256']==cal.digest(root/'prepared/orbital-phase.npz'), "receipt['orbital_phase_sha256']==cal.digest(root/'prepared/orbital-phase.npz')")
    with np.load(root/'prepared/orbital-phase.npz') as z:phase=z['phase_radians']
    with np.load(root/'prepared/observed.npz') as z:y=z['residuals']
    times=a['times'];n=len(times);C=a['covariance'];D=a['design']
    require(phase.shape==(n,) and len(y)==2*n, 'phase.shape==(n,) and len(y)==2*n')
    require(receipt['noise_coverage']['status']=='NO_RELEASED_RED_COMPONENT', "receipt['noise_coverage']['status']=='NO_RELEASED_RED_COMPONENT'")
    labels=[f'{kind}{k}' for k in settings['orbital_harmonics'] for kind in ['sin','cos']]
    basis=np.zeros((len(y),len(labels)))
    for i,k in enumerate(settings['orbital_harmonics']):
        basis[:n,2*i]=np.sin(k*phase);basis[:n,2*i+1]=np.cos(k*phase)
    baseline_harmonics=harmonic_fit(C,D,y,basis)
    contrast=joint_noise.Contrast(C,D,n);z=contrast.data(y)
    base_objective=float(z@z)
    noise=[{'rms_us':0.,'gamma':None,'objective':base_objective,'improvement':0.}]
    best_cov=C.copy();best=0
    for gamma in settings['red_gamma']:
        unit=mpta_batch.red_covariance(times,-14.,gamma,settings['red_modes'])
        unit/=np.mean(np.diag(unit))
        for rms in settings['red_rms_us']:
            red=unit*(rms*1e-6)**2
            projected=contrast.covariance(red);L=np.linalg.cholesky(projected)
            w=solve_triangular(L,z,lower=True)
            objective=float(w@w+2*np.log(np.diag(L)).sum())
            noise.append({'rms_us':rms,'gamma':gamma,'objective':objective,'improvement':base_objective-objective})
            if objective<noise[best]['objective']:
                best=len(noise)-1;best_cov=C.copy();best_cov[:n,:n]+=red
    noise_best=noise[best]
    alt_harmonics=harmonic_fit(best_cov,D,y,basis)
    # Only deterministic unit perturbations enter a prospective period grid.
    # Observed y is never passed to an outer-companion scanner.
    frequencies,grid=build_search_frequency_grid(times,profile['policy']['minimum_period_days'],
        profile['policy']['maximum_period_days'],profile['policy']['oversampling'])
    scanner=prepare_covariance_gls_scanner(C,D,times,frequencies,profile['reference_epoch_mjd_tdb'])
    leakage=[]
    for i,label in enumerate(labels):
        synthetic=basis[:,i]*settings['synthetic_harmonic_amplitude_us']*1e-6
        scan=scanner.scan(synthetic);w=scanner.whiten_and_project(synthetic)
        require(scan['trigger_statistic']<=float(w@w)+1e-8, "scan['trigger_statistic']<=float(w@w)+1e-8")
        leakage.append({'harmonic':label,'injected_amplitude_us':settings['synthetic_harmonic_amplitude_us'],
            'projected_norm_squared':float(w@w),'maximum_synthetic_delta_chi2':scan['trigger_statistic'],
            'synthetic_peak_period_days':scan['peak_period_days']})
    null_dof=len(y)-receipt['checks']['design_rank']
    null_chi2=receipt['checks']['null_reduced_chi2']*null_dof
    phase_fraction=(phase/(2*np.pi))%1
    phase_count=int(np.sum((phase_fraction>.15)&(phase_fraction<.35)))
    holds=[]
    if baseline_harmonics['rank']!=len(labels):holds.append('ORBITAL_DIAGNOSTIC_RANK_HOLD')
    if baseline_harmonics['conditional_chi2_tail']<.0027:holds.append('OMITTED_ORBITAL_STRUCTURE_HOLD')
    if noise_best['improvement']>10:holds.append('WIDEBAND_NOISE_MODEL_HOLD')
    if chi2.sf(null_chi2,null_dof)<.0027:holds.append('RESIDUAL_SCATTER_HOLD')
    if best and noise_best['rms_us']==max(settings['red_rms_us']):holds.append('NOISE_GRID_BOUNDARY_HOLD')
    result={'status':'PREPARATION_ADEQUACY_HOLD' if holds else 'CONDITIONAL_PREPARATION_COMPATIBLE',
        'target':'J1802-2124','holds':holds,'settings':settings,
        'null_chi2':null_chi2,'null_dof':null_dof,'conditional_null_tail':float(chi2.sf(null_chi2,null_dof)),
        'phase_cut':{'range':[.15,.35],'retained_TOAs_in_range':phase_count,'histogram_20_bins':np.histogram(phase_fraction,bins=np.linspace(0,1,21))[0].tolist()},
        'orbital_labels':labels,'released_noise_orbital_fit':baseline_harmonics,'best_grid_noise_orbital_fit':alt_harmonics,
        'noise_grid':noise,'best_noise_grid_member':noise_best,'noise_contrast_dimension':contrast.dimension,
        'discarded_fixed_noise_dimension':contrast.discarded_dimension,
        'shortest_red_period_days':float(np.ptp(times))/settings['red_modes'],
        'synthetic_grid':grid,'synthetic_leakage':leakage,
        'bindings':{'selection':cal.digest(args.selection),'profile':cal.digest(root/'profile/profile.json'),
                    'receipt':cal.digest(root/'prepared/receipt.json'),'observed':cal.digest(root/'prepared/observed.npz'),
                    'phase':cal.digest(root/'prepared/orbital-phase.npz'),'script':cal.digest(__file__),
                    'joint_noise':cal.digest(joint_noise.__file__),'mpta_batch':cal.digest(mpta_batch.__file__)},
        'calibration_executed':False,'observed_outer_periodogram_computed':False,
        'limitations':'Fixed white/DM noise and linear timing nuisance projection. Finite red grid is not a posterior or calibrated model-selection significance; phase harmonics are diagnostics, not physical Shapiro inference. Synthetic unit-amplitude leakage does not bound a physical omitted delay. No observed planet-period scan.'}
    cal.write(args.output,result)
    print(__import__('json').dumps({k:result[k] for k in ['status','holds','null_chi2','null_dof','conditional_null_tail','released_noise_orbital_fit','best_noise_grid_member','best_grid_noise_orbital_fit','phase_cut']},indent=2))


if __name__=='__main__':main()
