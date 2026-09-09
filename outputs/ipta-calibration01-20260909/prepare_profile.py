"""Bind the completed IPTA preparation to a one-target calibration policy."""
from pathlib import Path
import sys
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools'))
import target_calibration as cal

ROOT = REPO.parent / 'Project Recherche Data/ipta-calibration01-20260909'
source = cal.read(REPO / 'results/research/ipta-adapter01-20260909/closeout.json')
prepared = Path(source['final_attempt'])
receipt = cal.read(prepared / 'receipt.json')
if receipt['status'] != 'TIMING_NOISE_COMPATIBLE' or receipt['target'] != 'J1721-2457':
    raise ValueError('The reviewed target preparation is required')
for name, digest in receipt['artifact_hashes'].items():
    if cal.digest(prepared / name) != digest:
        raise ValueError('Prepared artifact changed: ' + name)
for name, digest in receipt['code_hashes'].items():
    if cal.digest(REPO / name) != digest:
        raise ValueError('Adapter code changed: ' + name)
with np.load(prepared / 'arrays.npz', allow_pickle=False) as z:
    arrays = {k: z[k] for k in z.files}
policy = {**cal.DEFAULT_POLICY, 'minimum_period_days': 30., 'maximum_period_days': 2000.,
          'search_count': 1, 'seed': 202609091721}
if policy['maximum_period_days'] > np.ptp(arrays['times']) / 2:
    raise ValueError('Period range exceeds half the prepared baseline')
timing = cal.read(prepared / 'timing.json')
profile = cal.create_profile(ROOT / 'profile', 'J1721-2457', arrays, {
    'timing_model': 'IPTA DR2 Version B TDB; TEMPO2 legacy convention; explicit historical DM_SERIES POLY',
    'noise_model': receipt['noise_model'],
    'preparation_receipt': str(prepared / 'receipt.json'),
    'preparation_receipt_sha256': cal.digest(prepared / 'receipt.json'),
    'context_sha256': cal.digest(prepared / 'arrays.npz'),
    'source_context': str(prepared / 'arrays.npz'),
    'scope': 'One fixed circular search, 30-2000 days; calibration only; no observed residuals ingested'
}, policy, reference_epoch=float(timing['pepoch']))
cal.write(ROOT / 'profile-preparation.json', {
    'profile': str(profile), 'profile_sha256': cal.digest(profile),
    'preparation_receipt_sha256': cal.digest(prepared / 'receipt.json'),
    'policy': policy, 'observed_search_launched': False})
print(profile)
