#!/usr/bin/env python3
"""Read-only J1802 release inventory; no model import, fit or search."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from recherche_common import require


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def toa_rows(path):
    rows = []
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0] in {'C', '#', 'FORMAT', 'MODE'}:
            continue
        try:
            float(fields[1]); Decimal(fields[2]); float(fields[3])
        except (ValueError, ArithmeticError):
            continue
        rows.append(fields)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    intake = json.loads((args.data / 'intake.json').read_text())
    files = intake['files'] + json.loads((args.data / 'config-intake.json').read_text())
    root = args.data / 'original' / 'NANOGrav15yr_PulsarTiming_v2.1.0'
    for row in files:
        path = args.data / 'original' / row['member']
        require(digest(path) == row['sha256'] and path.stat().st_size == row['bytes'], "digest(path) == row['sha256'] and path.stat().st_size == row['bytes']")
    keys = {'BINARY', 'H3', 'H4', 'STIGMA', 'VARSIGMA', 'M2', 'SINI', 'NHARMS',
            'PB', 'A1', 'TASC', 'EPS1', 'EPS2', 'START', 'FINISH', 'NTOA',
            'CHI2', 'RNAMP', 'RNIDX', 'TNREDAMP', 'TNREDGAM'}
    models = []
    for path in sorted(root.rglob('*.par')):
        fields = {v[0]: v[1:] for line in path.read_text().splitlines()
                  if (v := line.split()) and v[0] in keys}
        models.append({'member': str(path.relative_to(args.data / 'original')),
                       'sha256': digest(path), 'parameters': fields})
    reductions = {}
    for band in ['narrowband', 'wideband']:
        final, = (root / band / 'tim').glob('*.tim')
        excised, = (root / band / 'alternate/tim/excise').glob('*.tim')
        config, = (root / band / 'config').glob('*.yaml')
        rows = toa_rows(final)
        require(all('-cut' not in row for row in rows), "all('-cut' not in row for row in rows)")
        mjds = [Decimal(row[2]) for row in rows]
        cuts = Counter(row[row.index('-cut') + 1] for row in toa_rows(excised) if '-cut' in row)
        text = config.read_text()
        require('orb-phase-range: [0.15, 0.35]' in text, "'orb-phase-range: [0.15, 0.35]' in text")
        reductions[band] = {'final_toas': len(rows), 'site_mjd_days': len({int(v) for v in mjds}),
            'first_site_mjd': str(min(mjds)), 'last_site_mjd': str(max(mjds)),
            'span_days': float(max(mjds) - min(mjds)),
            'paired_dm_toas': sum('-pp_dm' in row and '-pp_dme' in row for row in rows),
            'retained_excision_file_cut_counts': dict(cuts), 'configured_phase_exclusion': [0.15, 0.35],
            'explicit_shapiro_removal': ('REMOVE: H3/H4 due to F-test' in text if band == 'wideband'
                                        else 'REMOVE: H3, H4' in text),
            'removal_reason': 'F-test' if band == 'wideband' else 'Explicit removal; target F-test value not supplied'}
    require(reductions['narrowband']['final_toas'] == 6796, "reductions['narrowband']['final_toas'] == 6796")
    require(reductions['wideband']['final_toas'] == 126, "reductions['wideband']['final_toas'] == 126")
    require(all(r['explicit_shapiro_removal'] for r in reductions.values()), "all(r['explicit_shapiro_removal'] for r in reductions.values())")
    result = {'target': 'J1802-2124', 'status': 'SOURCE_OMISSION_CLARIFIED_HOLD_RETAINED',
              'preserved_hold': 'MISSING_SHAPIRO_MODEL_HOLD',
              'scope': 'Released-file inspection only; no timing fit, calibration or observed search',
              'release_url': 'https://zenodo.org/records/16051178',
              'archive_sha256': intake['archive_sha256'], 'files': files,
              'models': models, 'reductions': reductions,
              'script_sha256': digest(Path(__file__)),
              'limitation': 'Excision labels are provenance, not an independent diagnosis of eclipses. Narrowband and wideband are overlapping reductions, not independent confirmation.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'files_verified': len(files), 'reductions': reductions}, indent=2))


if __name__ == '__main__':
    main()
