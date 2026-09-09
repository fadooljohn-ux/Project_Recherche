"""Inventory saved UTMOST DR1 inputs without fitting or searching observations."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics
import warnings

REPO = Path(__file__).resolve().parents[1]
DATA = REPO.parent / 'Project Recherche Data'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fields(text):
    result = {}
    for line in text.splitlines():
        v = line.split()
        if v and not v[0].startswith(('#', '@')):
            result[v[0].upper()] = v[1:]
    return result


def catalogue(path):
    records, aliases = {}, {}
    for block in path.read_text().split('@'):
        f = fields(block)
        if 'PSRJ' not in f:
            continue
        target = f['PSRJ'][0]
        records[target] = f
        aliases[target] = target
        if 'PSRB' in f:
            aliases[f['PSRB'][0]] = target
    return records, aliases


def observations(path):
    rows, comments = [], 0
    for number, line in enumerate(path.read_text().splitlines(), 1):
        v = line.split()
        if not v:
            continue
        if v[0] == 'C' or v[0].startswith('#'):
            comments += 1
            continue
        if v[0] in ('FORMAT', 'MODE'):
            continue
        if len(v) < 5 or (len(v) - 5) % 2:
            raise ValueError(f'Unsupported TIM row {path}:{number}')
        freq, mjd, error = map(Decimal, v[1:4])
        if not all(x.is_finite() for x in (freq, mjd, error)) or freq <= 0 or error <= 0:
            raise ValueError(f'Invalid timing measurement {path}:{number}')
        rows.append({'name': v[0], 'frequency': float(freq), 'mjd': mjd,
                     'error_us': float(error), 'site': v[4],
                     'flags': dict(zip(v[5::2], v[6::2]))})
    return rows, comments


def inventory(root):
    tree = read(root / 'upstream-tree.json')
    original = root / ('TimingDataRelease1-' + tree['sha'])
    manifest = []
    for item in tree['tree']:
        if item['type'] != 'blob':
            continue
        p = original / item['path']
        data = p.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != item['sha']:
            raise ValueError(f'Upstream file changed: {p}')
        manifest.append({'path': item['path'], 'sha256': hashlib.sha256(data).hexdigest(),
                         'git_blob_sha': blob, 'bytes': len(data)})
    catpath = DATA / 'tpa-batch01-20260908/research/psrcat.db'
    cat, aliases = catalogue(catpath)
    canonical = lambda name: aliases.get(name, name)
    master = read(root / 'master-before.json')
    known = {canonical(r[0]): r for r in master['Targets'][1:]}
    searched = {canonical(r[1]) for r in master['Searches'][1:]}
    prior = DATA / 'mpta-batch01-20260908/research'
    priorpaths = [prior / 'jbo-archive-inventory.json', prior / 'nanograv-tables.json', prior / 'epta-sample.html']
    jbo = {canonical(p.split('/')[1]) for p in read(priorpaths[0]) if '/' in p}
    ng = {canonical(r[0]) for r in read(priorpaths[1]) if r and re.match(r'[JB]\d', r[0])}
    epta = {canonical(t) for t in re.findall(r'J\d{4}[+\-]\d{4}', priorpaths[2].read_text())}
    rows = []
    for par in sorted(original.glob('*pulsars/*/*.par')):
        f = fields(par.read_text())
        target = canonical(f['PSRJ'][0])
        tim = par.with_suffix('.tim')
        raw, comments = observations(tim)
        start = Decimal(f['START'][0]); finish = Decimal(f['FINISH'][0])
        obs = [o for o in raw if start <= o['mjd'] <= finish]
        dates = sorted({o['mjd'] for o in obs})
        days = {int(t) for t in dates}
        span = float(dates[-1] - dates[0]) if dates else 0
        cf = cat.get(target, {})
        reasons = []
        if not cf:
            reasons.append('catalogue_identity_unresolved')
        if 'BINARY' in f or 'BINARY' in cf or 'PB' in cf or target == 'J1024-0719':
            reasons.append('known_binary_or_wide_companion')
        if any(k.startswith('GL') for k in f):
            reasons.append('published_glitch_model')
        if 'IPERHARM' in f:
            reasons.append('harmonic_timing_convention')
        if span < 1200:
            reasons.append('span_below_1200_days')
        if len(days) < 40:
            reasons.append('fewer_than_40_observing_days')
        freqs = [o['frequency'] for o in obs]
        byday = defaultdict(list)
        for o in obs:
            byday[int(o['mjd'])].append(o['frequency'])
        # Conservative physical band separation; tiny effective-frequency shifts
        # within the same averaged 31-MHz band do not identify epoch DM.
        dual_days = sum(max(v) / min(v) >= 1.2 for v in byday.values())
        noise = {k: f[k][0] for k in ('TNGLOBALEF', 'TNGLOBALEQ', 'TNREDAMP', 'TNREDGAM', 'TNREDC') if k in f}
        posterior = par.with_name(par.stem + '_posteriors.csv')
        prerequisites = ['utmost_adapter_and_released_clock_binding',
                         'global_white_noise_translation',
                         'source_timing_and_phase_connection_verification',
                         'target_calibration_and_noise_adequacy']
        if dual_days < 40:
            prerequisites.append('single_band_dispersion_noise_policy')
        if not all(k in f for k in ('TNGLOBALEF', 'TNGLOBALEQ')):
            prerequisites.append('missing_released_white_noise_parameters')
        r = {'dataset_id': str(par.parent.relative_to(original)), 'target': target,
             'variant': par.parent.parent.name, 'aliases': cf.get('PSRB', [])[:1],
             'par_path': str(par.relative_to(original)), 'tim_path': str(tim.relative_to(original)),
             'par_sha256': digest(par), 'tim_sha256': digest(tim),
             'raw_toas': len(raw), 'toas_in_model_window': len(obs),
             'toas_outside_model_window': len(raw)-len(obs), 'commented_rows': comments,
             'declared_ntoa': int(f['NTOA'][0]), 'observing_days': len(days),
             'start_mjd': str(dates[0]) if dates else None, 'finish_mjd': str(dates[-1]) if dates else None,
             'span_days': span, 'sites': sorted({o['site'] for o in obs}),
             'frequency_min_mhz': min(freqs) if freqs else None,
             'frequency_max_mhz': max(freqs) if freqs else None,
             'well_separated_band_days': dual_days,
             'median_toa_uncertainty_us': statistics.median(o['error_us'] for o in obs) if obs else None,
             'pulse_number_toas': sum('-pn' in o['flags'] for o in obs),
             'units': f.get('UNITS', ['implicit; resolve EPHVER'])[0],
             'ephver': f.get('EPHVER', [None])[0], 'ephemeris': f['EPHEM'][0], 'clock': ' '.join(f['CLK']),
             'noise_parameters': noise, 'posterior_available': posterior.exists(),
             'posterior_columns': posterior.read_text().splitlines()[0].split(',') if posterior.exists() else [],
             'in_master': target in known, 'previously_searched_by_recherche': target in searched,
             'prior_search_membership': {'JBO800': target in jbo, 'NANOGrav11': target in ng, 'EPTA_DR2': target in epta},
             'screen_exclusion_reasons': reasons, 'passes_target_and_coverage_screen': not reasons,
             'preparation_prerequisites': prerequisites, 'ready_to_launch': False,
             'assessment': 'EXCLUDED_CURRENT_SCOPE' if reasons else 'CONDITIONAL_PREPARATION_CANDIDATE'}
        rows.append(r)
    # Extended sets are alternatives, never extra independent pulsars.
    groups = defaultdict(list)
    for r in rows:
        groups[r['target']].append(r)
    for group in groups.values():
        preferred = max(group, key=lambda r: (r['passes_target_and_coverage_screen'], r['span_days']))
        for r in group:
            r['preferred_inventory_variant'] = r is preferred
    candidates = [r for r in rows if r['passes_target_and_coverage_screen'] and r['preferred_inventory_variant']]
    summary = {'unique_pulsars': len(groups), 'dataset_variants': len(rows),
               'main_datasets': sum(r['variant']=='pulsars' for r in rows),
               'extended_alternatives': sum(r['variant']=='extended_pulsars' for r in rows),
               'target_coverage_candidates': len(candidates),
               'candidate_previously_searched_targets': sum(r['previously_searched_by_recherche'] for r in candidates),
               'candidate_not_previously_searched_targets': sum(not r['previously_searched_by_recherche'] for r in candidates),
               'candidate_new_to_master': sum(not r['in_master'] for r in candidates),
               'candidate_absent_from_three_named_prior_inventories': sum(not any(r['prior_search_membership'].values()) for r in candidates),
               'candidate_with_at_least_40_well_separated_band_days': sum(r['well_separated_band_days']>=40 for r in candidates),
               'ready_to_launch': 0, 'calibrations_executed': 0, 'observed_searches_executed': 0,
               'main_exclusions_nonexclusive': dict(Counter(reason for r in rows if r['variant']=='pulsars' for reason in r['screen_exclusion_reasons']))}
    result = {'schema_version': 1, 'status': 'INVENTORY_COMPLETE_COMPATIBILITY_CONDITIONAL',
              'upstream_url': 'https://github.com/Molonglo/TimingDataRelease1',
              'upstream_commit': tree['sha'], 'archive_sha256': digest(root/'upstream.tar.gz'),
              'policy': {'minimum_span_days': 1200, 'minimum_observing_days': 40,
                         'binary_support': 'DEFERRED', 'glitch_model_support': 'EXCLUDED_CURRENT_SCOPE',
                         'observing_day_definition': 'integer source-site MJD; screening only',
                         'coverage_window': 'released PAR START through FINISH, inclusive',
                         'well_separated_band_proxy': 'same-day max/min frequency >= 1.2; not a calibrated DM identifiability test',
                         'period_search': 'NONE', 'selection': 'NONE'},
              'summary': summary, 'inputs': {str(p):digest(p) for p in [catpath,*priorpaths,root/'master-before.json']},
              'rows': rows}
    (root/'file-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (root/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    columns = ['dataset_id','target','variant','preferred_inventory_variant','assessment','toas_in_model_window','observing_days','span_days','frequency_min_mhz','frequency_max_mhz','median_toa_uncertainty_us','in_master','previously_searched_by_recherche','screen_exclusion_reasons','preparation_prerequisites','par_sha256','tim_sha256']
    with (root/'inventory.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        writer.writerows({k:'; '.join(r[k]) if isinstance(r[k],list) else r[k] for k in columns} for r in rows)
    print(json.dumps(summary,indent=2))


def check_models(root):
    """Diagnose raw PAR compatibility only; do not load or fit observations."""
    from pint.models import get_model
    from pint.observatory import Observatory
    from loguru import logger
    logger.remove()
    record = read(root / 'inventory.json')
    original = root / ('TimingDataRelease1-' + record['upstream_commit'])
    rows = []
    for item in record['rows']:
        if not item['preferred_inventory_variant'] or not item['passes_target_and_coverage_screen']:
            continue
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            try:
                model = get_model(original/item['par_path'], allow_tcb=True, allow_T2=True)
                row = {'target': item['target'], 'parsed': True,
                       'components': list(model.components), 'free_params': model.free_params,
                       'has_scale_toa_error': 'ScaleToaError' in model.components,
                       'units': str(model.UNITS.value)}
            except Exception as error:
                row = {'target': item['target'], 'parsed': False, 'error': str(error)}
            row['warnings'] = sorted({str(w.message) for w in caught})
        rows.append(row)
    obs = Observatory.get('mo')
    result = {'scope': 'Model parsing only; no TOA processing, fitting, calibration or observed search',
              'models': rows, 'molonglo_observatory': {'name': obs.name,
                  'clock_files': obs.clock_files, 'clock_fmt': obs.clock_fmt}}
    (root/'model-parser-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'Model parsing: {sum(r["parsed"] for r in rows)}/{len(rows)}; '
          f'white noise loaded: {sum(r.get("has_scale_toa_error", False) for r in rows)}')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=DATA/'utmost-inventory-20260909')
    parser.add_argument('--check-models',action='store_true',help='Parse saved candidate PAR files; no fitting')
    args=parser.parse_args()
    if args.check_models:
        check_models(args.data)
    else:
        inventory(args.data)
