"""Reconcile saved public portal metadata; never fit, calibrate or search TOAs."""
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools'))
from utmost_inventory import catalogue

DATA = REPO.parent / 'Project Recherche Data/utmost-ns-inventory-20260909'
OUT = REPO / 'results/research/utmost-ns-inventory-20260909'
read = lambda p: json.loads(p.read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if (OUT / 'inventory.json').exists():
        raise SystemExit('Inventory already saved; use a new dated intake for a fresh source snapshot.')
    master = read(DATA / 'master-before.json')
    known = {r[0] for r in master['Targets'][1:]}
    searched = {r[1] for r in master['Searches'][1:]}
    catpath = REPO.parent / 'Project Recherche Data/tpa-batch01-20260908/research/psrcat.db'
    cat, aliases = catalogue(catpath)
    old = read(REPO / 'results/research/utmost-inventory-20260909/inventory.json')
    ew = {r['target']: r for r in old['rows'] if r['preferred_inventory_variant']}
    api = read(DATA / 'access/portal-inventory.json')['data']
    rows = []
    for entry in api['pulsarFoldSummary']['edges']:
        n = entry['node']
        target = aliases.get(n['pulsar']['name'], n['pulsar']['name'])
        f = cat.get(target, {})
        binary = 'BINARY' in f or 'PB' in f or target == 'J1024-0719'
        first, last = map(datetime.fromisoformat, (n['firstObservation'], n['latestObservation']))
        span = (last - first).total_seconds() / 86400
        rows.append({
            'target': target, 'portal_name': n['pulsar']['name'],
            'aliases': [f['PSRB'][0]] if 'PSRB' in f else [],
            'catalogue_identity_resolved': bool(f), 'known_binary_or_wide_companion': binary,
            'already_in_master': target in known, 'previous_recherche_search': target in searched,
            'in_ew_dr1': target in ew,
            'ew_passed_original_coverage_screen': ew.get(target, {}).get('passes_target_and_coverage_screen', False),
            'first_observation_utc': n['firstObservation'], 'last_observation_utc': n['latestObservation'],
            'portal_span_integer_days': n['timespan'], 'span_days_from_utc': span,
            'portal_observation_count': n['numberOfObservations'],
            'verified_toa_count': None, 'verified_observing_days': None,
            'timing_package_verified': False,
            'standalone_disposition': ('IDENTITY_UNRESOLVED' if not f else
                'EXCLUDED_BINARY' if binary else 'EXCLUDED_SPAN_BELOW_1200_DAYS'),
            'acquisition_status': 'ARRIVAL_TIMES_REQUIRE_PORTAL_LOGIN',
            'combined_ew_ns_status': 'NOT_ASSESSED_WITH_COMPLETE_TIMING_INPUTS',
            'follow_up_deferred': target == 'J1752-2806',
        })
    rows.sort(key=lambda r: r['target'])
    assert len({r['target'] for r in rows}) == len(rows) == 174
    assert sum(r['portal_observation_count'] for r in rows) == 33361
    assert all(r['span_days_from_utc'] < 1200 for r in rows)
    summary = {
        'portal_targets': len(rows), 'portal_observations': 33361,
        'catalogue_identities_resolved': sum(r['catalogue_identity_resolved'] for r in rows),
        'known_binary_or_wide_companion': sum(r['known_binary_or_wide_companion'] for r in rows),
        'not_flagged_binary_but_short_span': sum(not r['known_binary_or_wide_companion'] for r in rows),
        'new_master_identities': sum(not r['already_in_master'] for r in rows),
        'new_resolved_master_identities': sum(not r['already_in_master'] and r['catalogue_identity_resolved'] for r in rows),
        'unresolved_identities': [r['target'] for r in rows if not r['catalogue_identity_resolved']],
        'previous_recherche_search': sum(r['previous_recherche_search'] for r in rows),
        'overlap_ew_dr1': sum(r['in_ew_dr1'] for r in rows),
        'overlap_ew_original_coverage_candidates': sum(r['ew_passed_original_coverage_screen'] for r in rows),
        'span_days_min': min(r['span_days_from_utc'] for r in rows),
        'span_days_max': max(r['span_days_from_utc'] for r in rows),
        'standalone_coverage_eligible': 0, 'combined_eligible': None,
        'calibrated': 0, 'observed_searches_launched': 0,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = [{
        'path': str(p.relative_to(DATA)), 'sha256': digest(p), 'bytes': p.stat().st_size,
    } for p in sorted((DATA / 'access').iterdir()) if p.is_file()]
    receipt = {
        'status': 'INVENTORY_COMPLETE_EXECUTION_BLOCKED', 'assessed_on': '2026-09-09',
        'source': 'https://pulsars.org.au/', 'project': 'MONSPSR',
        'paper': 'https://arxiv.org/html/2506.22697v1',
        'clock_commit': read(DATA / 'access/clock-tree.json')['sha'],
        'master_before_sha256': digest(REPO / 'outputs/recherche-master-20260908/Project-Recherche-Master.xlsx'),
        'catalogue_sha256': digest(catpath),
        'scope': '30-400 days; isolated targets; existing minimum 1200-day baseline; batches up to 25',
        'limits': [
            'Portal inventory differs from the paper sample and is not a frozen scientific release.',
            'Observation counts are not verified TOA or distinct observing-day counts.',
            'No standalone NS target meets the existing 1200-day baseline.',
            'Anonymous raw-TOA query was denied with a login requirement; no bypass attempted.',
            'No complete combined EW+NS PAR/TIM/noise package was obtained.',
            'J1752 follow-up is deferred until the first observed run completes.',
        ],
        'summary': summary, 'rows': rows, 'input_manifest': manifest,
    }
    (OUT / 'inventory.json').write_text(json.dumps(receipt, indent=2) + '\n')
    with (OUT / 'inventory.csv').open('w', newline='') as h:
        writer = csv.DictWriter(h, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
