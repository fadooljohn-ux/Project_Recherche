"""Project synthetic omitted Shapiro delays on prepared NG15 sampling; no data search."""
import argparse
import json
from itertools import product
from pathlib import Path

import numpy as np
from astropy.constants import GM_sun, c
from scipy.linalg import solve_triangular
import target_calibration as cal
import binary_wideband as binary
from pulsar_pilot.pilot1_runtime import build_search_frequency_grid, prepare_covariance_gls_scanner


def assess(data, constraints, output):
    if output.exists():raise FileExistsError('Consumed leakage assessment destination')
    requested=cal.read(constraints);selection=cal.read(data/'selection.json')
    if selection.get('shapiro_mode')!='omitted_in_release':raise ValueError('Requires explicit omitted mode')
    if cal.digest(constraints)!=selection['requested_selection_sha256']:raise ValueError('Selection constraints changed')
    results=[]
    for target in selection['selected']:
        root=data/target
        if (root/'prepared/failure.json').exists():
            results.append({'target':target,'status':'PREPARATION_HOLD'});continue
        profile,arrays=cal.load_profile(root/'profile/profile.json')
        receipt=binary.verify_preparation(data,target)
        if profile['provenance']['preparation_receipt_sha256']!=cal.digest(root/'prepared/receipt.json'):raise ValueError('Receipt binding differs')
        if receipt['orbital_phase_sha256']!=cal.digest(root/'prepared/orbital-phase.npz'):raise ValueError('Phase binding differs')
        with np.load(root/'prepared/orbital-phase.npz') as z:phase=z['phase_radians']
        if phase.shape!=arrays['times'].shape or not np.isfinite(phase).all():raise ValueError('Invalid orbital phases')
        policy=profile['policy']
        frequencies,grid=build_search_frequency_grid(arrays['times'],policy['minimum_period_days'],policy['maximum_period_days'],policy['oversampling'])
        scanner=prepare_covariance_gls_scanner(arrays['covariance'],arrays['design'],arrays['times'],frequencies,profile['reference_epoch_mjd_tdb'])
        W=solve_triangular(scanner.covariance_cholesky,arrays['design'],lower=True)
        norms=np.linalg.norm(W,axis=0);normalized=W/norms
        rows=[]
        fixed=receipt.get('fixed_shapiro')
        reference=np.zeros(len(phase))
        if fixed:
            reference=-2*(GM_sun/c**3).value*fixed['mass_solar']*np.log1p(-fixed['sini']*np.sin(phase))
        for mass,inc in product(requested['stress_grid'][target]['companion_mass_solar'],requested['stress_grid'][target]['inclination_degrees']):
            if not (0<mass<1.5 and 0<inc<90):raise ValueError('Invalid detached white-dwarf stress constraint')
            delay=-2*(GM_sun/c**3).value*mass*np.log1p(-np.sin(np.deg2rad(inc))*np.sin(phase))
            synthetic=np.zeros(len(arrays['covariance']));synthetic[:len(phase)]=delay-reference
            scan=scanner.scan(synthetic)  # Synthetic perturbation only; never loads observed.npz.
            white=solve_triangular(scanner.covariance_cholesky,synthetic,lower=True)
            fitted=np.linalg.lstsq(normalized,white,rcond=1e-12)[0]
            independent=white-normalized@fitted
            error=float(np.linalg.norm(independent-scanner.whiten_and_project(synthetic)))
            if error>1e-8:raise ValueError('Independent nuisance projection mismatch')
            bound=float(independent@independent)
            if scan['trigger_statistic']>bound+1e-8:raise ValueError('Synthetic power exceeds projection bound')
            rows.append({'mass_solar':mass,'inclination_degrees':inc,'raw_delay_peak_to_peak_us':float(np.ptp(delay)*1e6),
                'projected_whitened_norm_squared':bound,'maximum_synthetic_delta_chi2':scan['trigger_statistic'],
                'synthetic_peak_period_days':scan['peak_period_days'],'synthetic_peak_amplitude_us':scan['amplitude_us'],
                'independent_projection_l2_error':error})
        results.append({'target':target,'status':'LEAKAGE_ASSESSED','grid':grid,'scenarios':rows,'fixed_reference':fixed,
            'maximum_synthetic_delta_chi2':max(r['maximum_synthetic_delta_chi2'] for r in rows),
            'maximum_projected_whitened_norm_squared':max(r['projected_whitened_norm_squared'] for r in rows),
            'profile_sha256':cal.digest(root/'profile/profile.json'),'receipt_sha256':cal.digest(root/'prepared/receipt.json')})
    result={'status':'DEVELOPMENT_ASSESSMENT_COMPLETE','selection_sha256':cal.digest(data/'selection.json'),
        'constraints_sha256':cal.digest(constraints),'leakage_code_sha256':cal.digest(__file__),
        'scope':'Nine deterministic Shapiro scenarios per compatible target, relative to fixed Shapiro reference when supplied; actual sampling and fixed released covariance; all free timing/orbit/DM nuisance columns projected; full unmasked prospective grid.',
        'limitations':'Cartesian stress grid is not a posterior, continuous bound, calibration, significance estimate, or planet recovery. No observed periodogram computed. Phase and nuisance design fixed at released model.',
        'calibration_executed':False,'observed_search_executed':False,'results':results}
    cal.write(output,result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--constraints',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assess(a.data.resolve(),a.constraints.resolve(),a.output.resolve())
