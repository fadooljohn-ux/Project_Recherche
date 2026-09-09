"""Save calibration evidence and one noiseless integration check; no observed scan."""
from pathlib import Path
import sys
import csv
import json
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools'))
import target_calibration as cal
from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner

ROOT = REPO.parent / 'Project Recherche Data/ipta-calibration01-20260909'
OUT = REPO / 'results/research/ipta-calibration01-20260909'
log = (ROOT / 'calibration.log').read_text()
result = json.loads(log[log.index('{'):])
cache = Path(result['path'])
profile, arrays = cal.load_profile(ROOT / 'profile/profile.json')
receipt = cal.verify_cache(cache, {'profile': profile, 'implementation': cal.implementation()})
settings = cal.read(cache / 'calibration.json')
with np.load(cache / 'projection-and-sensitivity.npz', allow_pickle=False) as z:
    a = {k:z[k] for k in z.files}
periods = 1/a['frequencies']
eligible = a['eligible']
index = int(np.argmin(abs(periods-100)))
scanner = prepare_covariance_gls_scanner(arrays['covariance'], arrays['design'],
    arrays['times'], a['frequencies'][[index]], profile['reference_epoch_mjd_tdb'])
phase = 2*np.pi*(arrays['times']-profile['reference_epoch_mjd_tdb'])*a['frequencies'][index]
coefficients = np.array([80e-6, 60e-6])
nuisance = arrays['baseline_design'] @ (20e-6/np.max(abs(arrays['baseline_design']),axis=0))
synthetic = np.sin(phase)*coefficients[0]+np.cos(phase)*coefficients[1]+nuisance
projected = scanner.whiten_and_project(synthetic)
fitted = scanner.template_gram_pseudoinverse[0] @ (scanner.projected_whitened_templates[:,0].T @ projected)
np.testing.assert_allclose(fitted, coefficients, atol=1e-12, rtol=1e-8)
integration = {'type':'One noiseless synthetic circular signal plus baseline nuisance',
    'period_days':float(periods[index]), 'input_amplitude_us':100.,
    'recovered_amplitude_us':float(np.linalg.norm(fitted)*1e6),
    'maximum_coefficient_error_seconds':float(np.max(abs(fitted-coefficients))),
    'observed_residuals_used':False}
samples=[]
for requested in (30,60,100,180,365.25,730,1000,2000):
    i=int(np.argmin(abs(periods-requested)))
    samples.append({'requested_period_days':requested,'grid_period_days':float(periods[i]),
        'eligible':bool(eligible[i]),'retained_power':float(a['retained_power'][i]),
        'best_phase_95_amplitude_us':float(a['best_phase_amplitude_us'][i]) if eligible[i] else None,
        'worst_phase_95_amplitude_us':float(a['worst_phase_amplitude_us'][i]) if eligible[i] else None})
maxima=np.load(cache/'null-maxima.npy',allow_pickle=False)
summary={**result,'master_before_sha256':cal.read(ROOT/'baseline.json')['master_sha256'],
    'policy':profile['policy'],'span_days':float(np.ptp(arrays['times'])),
    'empirical_99th_percentile':settings['empirical_quantile'],
    'noise_only_nulls_above_adopted_threshold':int(np.sum(maxima>result['threshold'])),
    'masked_grid_periods_days':sorted(periods[~eligible].tolist()),
    'mask_rule':'Exclude cells retaining at most 20% power after full timing projection relative to baseline, or ill-conditioned templates',
    'sensitivity_definition':settings['sensitivity'], 'sampled_sensitivity':samples,
    'integration_check':integration,'profile_sha256':cal.digest(ROOT/'profile/profile.json'),
    'preparation_receipt_sha256':cal.read(ROOT/'profile-preparation.json')['preparation_receipt_sha256'],
    'cache_receipt_sha256':cal.digest(cache/'receipt.json'),
    'observed_search_launched':False,'execution_freeze_created':False,
    'noiseless_synthetic_checks':1,'sensitivity_monte_carlo_injections':0}
cal.write(OUT/'closeout.json',summary)
cal.write(OUT/'calibration.json',settings)
cal.write(OUT/'profile.json',profile)
cal.write(OUT/'integration-check.json',integration)
with (OUT/'sensitivity-and-mask.csv').open('w',newline='') as f:
    writer=csv.writer(f)
    writer.writerow(['period_days','frequency_per_day','eligible','retained_power','best_phase_95_amplitude_us','worst_phase_95_amplitude_us'])
    for i in np.argsort(periods):
        writer.writerow([periods[i],a['frequencies'][i],bool(eligible[i]),a['retained_power'][i],
            a['best_phase_amplitude_us'][i] if eligible[i] else '',a['worst_phase_amplitude_us'][i] if eligible[i] else ''])
cal.write(OUT/'artifact-manifest.json',{
    str(p):cal.digest(p) for p in [ROOT/'profile/profile.json', ROOT/'profile/arrays.npz',
        ROOT/'profile-preparation.json',ROOT/'calibration.log',*sorted(cache.iterdir())] if p.is_file()})
print(json.dumps({'summary':result,'masked_grid_periods_days':summary['masked_grid_periods_days'],
                  'nulls_above_threshold':summary['noise_only_nulls_above_adopted_threshold'],
                  'integration_check':integration},indent=2))
