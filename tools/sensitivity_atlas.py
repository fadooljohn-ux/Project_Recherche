"""Summarize saved search sensitivity; never fit, recalibrate, or search observations."""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
from astropy.constants import G, c, M_sun, M_earth
from recherche_common import require

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def workbook_rows(path, name):
    """Read existing OOXML cells without modifying their values or formatting."""
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        sheets = ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', ns)
        sheet = next(s for s in sheets if s.attrib['name'] == name)
        rid = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        target = next(r.attrib['Target'] for r in rels if r.attrib['Id'] == rid)
        member = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        rows = []
        for row in ET.fromstring(z.read(member)).find('m:sheetData', ns):
            values = {}
            for cell in row:
                col = 0
                for ch in re.match('[A-Z]+', cell.attrib['r'])[0]: col = col * 26 + ord(ch) - 64
                v = cell.find('m:v', ns)
                text = v.text if v is not None else None
                kind = cell.attrib.get('t')
                if kind == 's': value = strings[int(text)]
                elif kind == 'inlineStr': value = ''.join(cell.find('m:is', ns).itertext())
                elif text is None: value = None
                elif kind in ('str', 'e'): value = text
                else: value = float(text)
                values[col - 1] = value
            out = [None] * (max(values, default=-1) + 1)
            for i, value in values.items(): out[i] = value
            rows.append(out)
        return rows


def minimum_mass(amplitude_us, period_days, host_mass_solar=1.4):
    """Exact edge-on Kepler mass-function inversion, in Earth masses."""
    amplitude = np.asarray(amplitude_us, float)
    period = np.asarray(period_days, float)
    f = 4*np.pi**2*(c.value*amplitude*1e-6)**3/(G.value*(period*86400)**2)/M_sun.value
    lo = np.zeros_like(f)
    hi = f + 2*host_mass_solar
    for _ in range(64):
        mid = (lo+hi)/2
        small = mid**3/(host_mass_solar+mid)**2 < f
        lo = np.where(small, mid, lo)
        hi = np.where(small, hi, mid)
    return (lo+hi)/2 * M_sun.value/M_earth.value


def build(master, output):
    rows = workbook_rows(master, 'Searches')
    headers = rows.pop(0)
    records = [dict(zip(headers, row)) for row in rows]
    invalid = set()
    for row in workbook_rows(master, 'Work log')[1:]:
        if len(row)>5 and row[4]=='SUPERSEDED_INVALID_IMPORT':
            invalid.add(row[5].split(' is retained as an invalid import attempt')[0])
    curves, excluded = [], []
    for row in records:
        record_id = row['Record ID']
        if 'binary-pilot' in record_id:
            excluded.append({'record_id':record_id,'reason':'BINARY_SYSTEM; isolated-host mass conversion is not applicable'}); continue
        if record_id in invalid:
            excluded.append({'record_id':record_id,'reason':'SUPERSEDED_INVALID_IMPORT'}); continue
        path = Path(row['Evidence file'])
        if not path.is_absolute(): path = ROOT / path
        if digest(path) != row['Evidence SHA-256']:
            raise ValueError('Original evidence hash differs: '+record_id)
        result = json.loads(path.read_text())
        if not result.get('calibration_key'):
            excluded.append({'record_id':record_id,'reason':'NO_STANDARD_SAVED_CURVE; benchmark or legacy search'}); continue
        grid_path = path.parent/'periodogram.npz'
        if digest(grid_path) != result['periodogram_sha256']:
            raise ValueError('Saved curve hash differs: '+record_id)
        with np.load(grid_path,allow_pickle=False) as z:
            freq, eligible, best, worst = [z[k] for k in ['frequencies','eligible','best_phase_amplitude_us','worst_phase_amplitude_us']]
        require(len(freq)==result['grid_cells'] and int(eligible.sum())==result['eligible_cells'], "len(freq)==result['grid_cells'] and int(eligible.sum())==result['eligible_cells']")
        require(np.all(freq>0) and np.all(worst[eligible]>=best[eligible]), 'np.all(freq>0) and np.all(worst[eligible]>=best[eligible])')
        require(np.isclose(np.nanmedian(worst),result['sensitivity_median_worst_phase_us']), "np.isclose(np.nanmedian(worst),result['sensitivity_median_worst_phase_us'])")
        order=np.argsort(1/freq); period=(1/freq)[order]; eligible=eligible[order]
        best=best[order];worst=worst[order]
        def values(a):return [float(v) if np.isfinite(v) else None for v in a]
        curves.append({'record_id':record_id,'target':row['Target ID'],'dataset':row['Data / method'],
            'disposition':row['Result'],'threshold':result['threshold'],'threshold_scope':result['threshold_scope'],
            'observed_sha256':result['observed_sha256'],'original_result_sha256':row['Evidence SHA-256'],
            'periodogram_sha256':result['periodogram_sha256'],'calibration_key':result['calibration_key'],
            'noise_adequacy_flag':result['noise_adequacy_flag'],'period_days':period.tolist(),
            'eligible':eligible.tolist(),'best_amplitude_us':values(best),'worst_amplitude_us':values(worst),
            'best_minimum_mass_earth':values(minimum_mass(best,period)),
            'worst_minimum_mass_earth':values(minimum_mass(worst,period))})
    output.mkdir(parents=True,exist_ok=False)
    atlas={'schema':'recherche-sensitivity-atlas-v1','master_sha256':digest(master),'host_mass_solar':1.4,
        'definition':'95% detection probability at the injected grid frequency, circular orbit, phase extrema, fixed supplied noise and linear timing model',
        'limitations':['Not a posterior mass upper limit or occurrence-rate estimate.','Unknown inclination permits a larger true mass.',
        'Shared observations and repeated identities are not independent trials.','Masked cells have no sensitivity estimate; off-grid/eccentric sensitivity is not measured.'],
        'dataset_searches':len(curves),'unique_targets':len({r['target'] for r in curves}),
        'excluded_records':excluded,'curves':curves,'scientific_runs_executed':0}
    (output/'atlas.json').write_text(json.dumps(atlas,allow_nan=False,separators=(',',':'))+'\n')
    with gzip.open(output/'sensitivity-cells.csv.gz','wt',newline='') as f:
        w=csv.writer(f); w.writerow(['record_id','target','dataset','period_days','eligible','best_amplitude_us','worst_amplitude_us','best_minimum_mass_earth','worst_minimum_mass_earth'])
        for r in curves:
            for i,p in enumerate(r['period_days']):w.writerow([r['record_id'],r['target'],r['dataset'],p,r['eligible'][i],*[r[k][i] for k in ['best_amplitude_us','worst_amplitude_us','best_minimum_mass_earth','worst_minimum_mass_earth']]])
    # Standalone scientific figure; masked cells stay NaN, so lines do not bridge gaps.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,6),layout='constrained')
    sources=sorted({r['dataset'].split(';')[0].split(',')[0] for r in curves})
    colors=dict(zip(sources,plt.get_cmap('tab10').colors))
    seen=set()
    for r in curves:
        source=r['dataset'].split(';')[0].split(',')[0]
        ax.plot(r['period_days'],r['worst_minimum_mass_earth'],color=colors[source],alpha=.22,lw=.7,label=source if source not in seen else None);seen.add(source)
    ax.set(xscale='log',yscale='log',xlabel='Orbital period (days)',ylabel='Minimum companion mass (Earth masses)',
        title=f'{len(curves)} dataset searches: worst-phase conditional 95% sensitivity')
    ax.grid(alpha=.15);ax.legend(fontsize=8,loc='upper right');fig.savefig(output/'sensitivity-overview.png',dpi=160);plt.close(fig)
    template=(ROOT/'tools/sensitivity_atlas.html').read_text()
    (output/'index.html').write_text(template.replace('__ATLAS_JSON__',json.dumps(atlas,allow_nan=False).replace('</','<\\/')))
    summary={k:v for k,v in atlas.items() if k!='curves'}
    summary['artifact_sha256']={f.name:digest(f) for f in sorted(output.iterdir())}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['dataset_searches','unique_targets','excluded_records','scientific_runs_executed']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master',type=Path,required=True,help='Original evidence-bound master; preserve publication derivatives separately')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.master.resolve(),args.output.resolve())
