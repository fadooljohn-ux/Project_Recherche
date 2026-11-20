#!/usr/bin/env python3
"""Verify saved binary-hold inputs and inventory metadata; never fit or search."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
from statistics import median
from j1802_model_review import digest, toa_rows
from recherche_common import require

TARGETS = [('J1857+0943', '02'), ('J0740+6620', '02'),
           ('J0613-0200', '01'), ('J2043+1711', '02')]
KEYS = {'BINARY', 'PB', 'A1', 'TASC', 'EPS1', 'EPS2', 'PBDOT', 'M2', 'SINI',
        'RNAMP', 'RNIDX', 'TNREDAMP', 'TNREDGAM', 'TNREDC', 'TNREDTSPAN'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = Path(__file__).resolve().parent.parent
    rows = []
    for priority, (target, number) in enumerate(TARGETS, 1):
        batch = f'binary-pilot{number}-20260909'
        public = root / 'results/observed' / batch
        selection = public / 'selection.json'
        selected, = [r for r in json.loads(selection.read_text())['rows'] if r['target'] == target]
        par, tim = [args.data / batch / target / 'original' / (target + ext) for ext in ['.par', '.tim']]
        require(digest(par) == selected['par_sha256'], "digest(par) == selected['par_sha256']")
        require(digest(tim) == selected['tim_sha256'], "digest(tim) == selected['tim_sha256']")
        failure_path = public / target / 'prepared/failure.json'
        require(digest(failure_path) == digest(args.data / batch / target / 'prepared/failure.json'), "digest(failure_path) == digest(args.data / batch / target / 'prepared/failure.json')")
        failure = json.loads(failure_path.read_text())
        require(failure['target'] == target and failure['status'] == 'PREPARATION_FAILED', "failure['target'] == target and failure['status'] == 'PREPARATION_FAILED'")
        diagnostic = json.loads(failure['error'].split('SINI ', 1)[1])
        fields = {f[0]: f[1:] for line in par.read_text().splitlines()
                  if (f := line.split()) and f[0] in KEYS}
        toas = toa_rows(tim)
        require(toas and all('-cut' not in t for t in toas), "toas and all('-cut' not in t for t in toas)")
        times = [Decimal(t[2]) for t in toas]
        span = float(max(times) - min(times))
        pmin, pmax = max(30., 10 * float(fields['PB'][0])), min(2000., span / 2)
        rows.append({'priority': priority, 'target': target, 'release_name': selected.get('release_name', target),
            'batch': batch, 'status': 'NONLINEAR_SHAPIRO_HOLD_RETAINED',
            'bindings': {'par_sha256': digest(par), 'tim_sha256': digest(tim),
                         'selection_sha256': digest(selection), 'failure_sha256': digest(failure_path)},
            'toas': len(toas), 'paired_dm_toas': sum('-pp_dm' in t and '-pp_dme' in t for t in toas),
            'site_mjd_days': len({int(t) for t in times}), 'span_days': span, 'span_years': span / 365.25,
            'median_raw_toa_uncertainty_us': median(float(t[3]) for t in toas),
            'observatories': sorted({t[4] for t in toas}),
            'prospective_period_bounds_days': [pmin, pmax], 'released_parameters': fields,
            'relative_M2_uncertainty_percent': 100 * float(fields['M2'][2]) / float(fields['M2'][0]),
            'released_red_component': any(k in fields for k in ['RNAMP', 'TNREDAMP']),
            'historical_linearity_diagnostic': diagnostic, 'historical_adapter_sha256': failure['adapter_sha256'],
            'diagnostic_comparability': ('Earlier adapter and step convention; not a current derivative test'
                                        if number == '01' else 'Shared pilot02 adapter and step convention')})
    output = {'date': '2026-09-10', 'status': 'ASSESSMENT_COMPLETE_HOLDS_RETAINED',
        'scope': 'Saved input verification and raw timing-file metadata only',
        'priority_basis': 'Qualitative engineering judgment, not planet probability or calibrated sensitivity',
        'timing_fit_executed': False, 'calibration_executed': False, 'observed_search_executed': False,
        'period_bounds_note': 'Prospective existing rule on site times; not frozen barycentric bounds',
        'rows': rows, 'script_sha256': digest(Path(__file__)),
        'parser_sha256': digest(Path(__file__).with_name('j1802_model_review.py'))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'status': output['status'], 'targets': [r['target'] for r in rows],
                      'original_input_hashes_verified': 8, 'failure_records_verified': 4}))


if __name__ == '__main__':
    main()
