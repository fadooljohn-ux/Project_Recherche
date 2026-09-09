"""Prepare and compare an inventory-bound isolated IPTA timing dataset; no search command."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np
from scipy import linalg
import target_calibration as cal
from ipta_likelihood_audit import audit as audit_likelihood

REPO = Path(__file__).resolve().parents[1]
DEFAULT = REPO.parent / 'Project Recherche Data/ipta-adapter01-20260909'
TARGET = 'J1721-2457'


def invoke(cmd, out, env):
    with out.open('w') as log:
        process = subprocess.run(cmd, env=env, cwd=out.parent, stdout=log,
                                 stderr=subprocess.STDOUT, timeout=1800)
    if process.returncode:
        raise RuntimeError(f'Command exited {process.returncode}; inspect {out}')


def noise_covariance(times, radio_hz, fields, prefix):
    """Released TEMPO2 power law, including its historical year normalization."""
    span = float(np.longdouble(fields['FINISH'][0])-np.longdouble(fields['START'][0]))
    offset = np.asarray(times-np.longdouble(fields['PEPOCH'][0]), float)
    count = int(fields[prefix+'C'][0])
    frequencies = np.arange(1,count+1)/span
    amplitude, gamma = float(fields[prefix+'Amp'][0]), float(fields[prefix+'Gam'][0])
    # TEMPO2 uses 3.16e7^3 for the PSD normalization, but 365.25 days
    # for its frequency pivot. Do not substitute the MPTA/PINT convention.
    weights = 10**(2*amplitude)*3.16e7**3*(frequencies*365.25)**(-gamma)/(span*86400)
    if prefix == 'TNRed':
        weights /= 12*np.pi**2
    phase = 2*np.pi*offset[:,None]*frequencies
    sine, cosine = np.sin(phase), np.cos(phase)
    if prefix == 'TNDM':
        scale = 1/(2.41e-16*radio_hz**2)
        sine *= scale[:,None]
        cosine *= scale[:,None]
    return (sine*weights)@sine.T + (cosine*weights)@cosine.T



def factor_covariance_error(covariance, path):
    factors = np.loadtxt(path, ndmin=2)
    error, norm = 0., 0.
    for start in range(0, len(covariance), 128):
        block = covariance[start:start+128]
        difference = block - factors[start:start+128] @ factors.T
        error += np.sum(difference**2)
        norm += np.sum(block**2)
    return float(np.sqrt(error / norm)) if norm else float(np.sqrt(error))


def ecorr_covariance(arrays, meta, reference, path):
    # Match TEMPO2 t2fit.C: input-order epoch anchors, +/- 1 second,
    # including singleton epochs and all arrivals in the anchor time window.
    n = len(arrays['times'])
    covariance = np.zeros((n,n))
    x = np.asarray(arrays['times']-np.longdouble(meta['pepoch']),float)
    bat = np.asarray(arrays['times'],float)
    flags = np.zeros(n,bool)
    values = {v['flag_value']:v['value']*1e-6 for k,v in meta['noise'].items() if k.startswith('ecorr_')}
    if any(v['flag'] != 'group' for k,v in meta['noise'].items() if k.startswith('ecorr_')):
        raise ValueError('Unexpected ECORR flag selector')
    for i in range(n):
        if flags[i] or arrays['groups'][i] not in values:
            continue
        flags[i:] |= (x[i:] > x[i]-1/86400) & (x[i:] < x[i]+1/86400)
        members = np.flatnonzero((bat > bat[i]-1/86400) & (bat < bat[i]+1/86400))
        covariance[np.ix_(members,members)] += values[arrays['groups'][i]]**2
    reference_cov = np.zeros_like(covariance)
    if path.stat().st_size:
        exported = np.loadtxt(path,ndmin=2)
        for anchor in np.unique(exported[:,0]):
            rows = exported[exported[:,0]==anchor]
            indices = rows[:,1].astype(int)
            reference_cov[np.ix_(indices,indices)] += np.outer(rows[:,2],rows[:,2])
    norm = np.linalg.norm(reference_cov)
    error = np.linalg.norm(covariance-reference_cov)
    return covariance, float(error/norm if norm else error)

def prepare(root, target_name=TARGET):
    target_id = target_name
    root = root.resolve()
    rt = root/'runtime/.pixi/envs/default'
    original = root/target_id/'original'
    if not (rt/'bin/tempo2').exists():
        raise FileNotFoundError('Install the isolated locked TEMPO2 runtime first; see the adapter report')
    release_inputs = cal.read(REPO/'results/research/ipta-dr2-review-20260909/input-manifest.json')
    # Verify the copied target files against the pinned intake before use.
    expected = {Path(p).relative_to(Path(p).parents[1] if Path(p).parent.name=='tims' else Path(p).parent).as_posix():v['sha256']
                for p,v in release_inputs.items() if f'/VersionB/{target_id}/' in p}
    for name,sha in expected.items():
        if cal.digest(original/name) != sha:
            raise ValueError(f'Released input changed: {name}')
    if not expected:
        raise ValueError('Target is absent from the pinned intake')
    inventory = cal.read(REPO/'results/research/ipta-dr2-review-20260909/inventory.json')
    row = next(r for r in inventory['rows'] if r['target'] == target_id)
    if row['selection_exclusions']:
        raise ValueError('Target is excluded from the isolated coverage inventory')
    ntoa = row['toa_count']
    text = (original/(target_id+'.IPTADR2.TDB.par')).read_text()
    fields = {v[0]:v[1:] for line in text.splitlines() if (v:=line.split())}
    if fields.get('BINARY') or fields['T2CMETHOD'] != ['TEMPO'] or fields['EPHEM'] != ['DE436']:
        raise ValueError('Input outside the bounded legacy single-pulsar model')
    if any(k.startswith(('TNSECORR','TNBand','TNGroup','TNChrom','GLEP')) for k in fields):
        raise ValueError('Additional noise/glitch components require a separate adapter extension')
    target = root/target_id
    out = target/f'attempt{len(list(target.glob("attempt[0-9]*")))+1:02d}'
    out.mkdir()
    try:
        # May 2019 model predates the June 2020 change to DM Taylor coefficients.
        # Adding POLY preserves the old coefficient meaning; original remains intact.
        (out/'model.par').write_text(text+'\nDM_SERIES POLY\n')
        data = root/'bound-tempo2-data'
        data.mkdir(exist_ok=True)
        clockdir = data/'clock'
        clockdir.mkdir(exist_ok=True)
        for p in (rt/'share/tempo2').iterdir():
            if p.name != 'clock' and not (data/p.name).exists():
                (data/p.name).symlink_to(p, target_is_directory=p.is_dir())
        # TEMPO2 routes through date-dependent alternate GPS chains and reads
        # legacy UT1 from this directory. Preserve the complete runtime set,
        # then apply the release's clock overrides without editing their bytes.
        shutil.copytree(rt/'share/tempo2/clock',clockdir,dirs_exist_ok=True)
        for p,v in release_inputs.items():
            if '/release/clock/' in p:
                release_root = os.environ.get('RECHERCHE_IPTA_RELEASE_ROOT')
                source = Path(release_root)/'clock'/Path(p).name if release_root else Path(p)
                if cal.digest(source)!=v['sha256']: raise ValueError('Released clock changed: '+str(source))
                shutil.copy2(source,clockdir/Path(p).name)
        alias = Path.home()/'.cache/recherche-tempo2'/(root.name+'-bound')
        alias.parent.mkdir(parents=True,exist_ok=True)
        if alias.is_symlink() and alias.resolve() != data:
            raise ValueError('Runtime alias points to another dataset')
        if not alias.exists(): alias.symlink_to(data,target_is_directory=True)
        if ' ' in str(alias): raise ValueError('TEMPO2 ephemeris reader needs a path without spaces')
        plugins=root/'plugins'
        plugins.mkdir(exist_ok=True)
        # This exact package's plugins use the darwin24 ABI suffix, including on
        # newer macOS hosts. The runtime lock pins that packaging convention.
        plugin=plugins/'recherche_ref_darwin24_plug.t2'
        env={**os.environ,'TEMPO2':str(alias),'TEMPO2_PLUG_PATH':str(plugins),
             'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
        invoke(['clang++','-arch','x86_64','-std=c++11','-dynamiclib','-undefined','dynamic_lookup',
                '-I'+str(rt/'include'),str(REPO/'tools/ipta_tempo2_reference.C'),
                '-L'+str(rt/'lib'),'-ltempo2','-Wl,-rpath,'+str(rt/'lib'),'-o',str(plugin)],out/'compile.log',env)
        tim=original/(target_id+'.IPTADR2.tim')
        invoke([str(rt/'bin/python'),'-u',str(REPO/'tools/ipta_tempo2_export.py'),
                str(out/'model.par'),str(tim),str(out/'timing.npz'),'--target',target_id,'--ntoa',str(ntoa)],out/'worker.log',env)
        invoke([str(rt/'bin/tempo2'),'-npsr','1','-nobs',str(max(256,ntoa+32)),'-gr','recherche_ref',
                '-f',str(out/'model.par'),str(tim),'-export',str(out/'reference.txt')],out/'reference.log',env)
        for log in (out/'worker.log',out/'reference.log'):
            if any(code in log.read_text() for code in ('[CLK4]','[CLK7]','[CLK9]','Could not open')):
                raise ValueError('Missing clock/resource or clock approximation: '+str(log))
        with np.load(out/'timing.npz',allow_pickle=False) as z:
            a={k:z[k] for k in z.files}
        meta=cal.read(out/'timing.json')
        reference=np.loadtxt(out/'reference.txt',dtype=np.longdouble)
        if len(reference)!=ntoa or np.any(a['deleted']) or np.any(reference[:,6]):
            raise ValueError('TOA count or inclusion changed')
        included=np.loadtxt(out/'reference.txt.included',dtype=int,ndmin=1)
        if not np.array_equal(included,np.arange(ntoa)):
            raise ValueError('TEMPO2 fit-window inclusion differs from prepared arrivals')
        white=a['errors_us']**2
        for key,p in meta['noise'].items():
            if key.startswith('efac_'): white[a['groups']==p['flag_value']] *= p['value']**2
        for key,p in meta['noise'].items():
            if key.startswith('equad_'): white[a['groups']==p['flag_value']] += p['value']**2
        white *= 1e-12
        red=noise_covariance(a['times'],a['frequency_hz'],fields,'TNRed')
        dm=noise_covariance(a['times'],a['frequency_hz'],fields,'TNDM')
        ecorr, ecorr_check = ecorr_covariance(a, meta, reference, out/'reference.txt.ecorr')
        covariance=red+dm
        covariance += ecorr
        covariance.flat[::len(white)+1] += white
        del ecorr
        design=a['design']
        names=list(a['names'])
        baseline=design[:,[i for i,n in enumerate(names) if n=='Offset' or n.startswith(('DM','JUMP','FD'))]]
        arrays=cal.validate_arrays({'times':a['times'],'covariance':covariance,'design':design,'baseline_design':baseline})
        L=linalg.cholesky(covariance,lower=True)
        W=linalg.solve_triangular(L,design,lower=True)
        W/=np.linalg.norm(W,axis=0)
        Q,_=linalg.qr(W,mode='economic')
        residuals=np.asarray(a['residuals'],float)
        whitened=linalg.solve_triangular(L,residuals,lower=True)
        post=whitened-Q@(Q.T@whitened)
        checks={'residual_max_difference_seconds':float(np.max(abs(a['residuals']-reference[:,3]))),
                'bat_max_difference_days':float(np.max(abs(a['times']-reference[:,1]))),
                'bat_bbat_max_difference_days':float(np.max(abs(reference[:,1]-reference[:,2]))),
                'white_relative_error':float(np.max(abs(np.sqrt(white)-reference[:,4]*1e-6)/(reference[:,4]*1e-6))),
                'red_covariance_relative_error':factor_covariance_error(red,out/'reference.txt.red'),
                'dm_covariance_relative_error':factor_covariance_error(dm,out/'reference.txt.dm'),
                'ecorr_covariance_relative_error':ecorr_check,
                'derivative_relative_errors':meta['derivative_relative_errors'],
                'phase_arc_cycles':float(np.ptp(residuals)*np.longdouble(meta['f0'])),
                'design_rank':int(np.linalg.matrix_rank(W)), 'design_columns':len(names),
                'normalized_design_condition':float(np.linalg.cond(W)),
                'weighted_rms_us':float(np.sqrt(np.average((residuals-np.average(residuals,weights=1/white))**2,weights=1/white))*1e6),
                'reduced_chi_square':float(post@post/(len(residuals)-len(names)))}
        failures=[]
        if checks['residual_max_difference_seconds']>1e-9: failures.append('timing export')
        if checks['bat_max_difference_days']>1e-12 or checks['bat_bbat_max_difference_days']>1e-12: failures.append('barycentric time convention')
        for key in ('white_relative_error','red_covariance_relative_error','dm_covariance_relative_error','ecorr_covariance_relative_error'):
            if checks[key]>1e-10: failures.append(key)
        if max(checks['derivative_relative_errors'].values())>1e-4: failures.append('finite-difference derivatives')
        if checks['phase_arc_cycles']>=0.5 or checks['design_rank']!=len(names): failures.append('phase/design')
        # Historical TRES/CHI2R depend on fit stage and noise subtraction.
        # They are descriptive comparisons, not an equivalent GLS likelihood.
        # Validate that likelihood directly through a penalized-noise fit.
        checks['published_rms_us'] = float(fields['TRES'][0])
        checks['published_reduced_chi_square'] = float(fields['CHI2R'][0])
        checks['published_summary_comparison'] = 'DESCRIPTIVE_ONLY; differing fit-stage/statistic definitions'
        checks['reference_fit_rows'] = len(included)
        for actual, published, rounding in (
            ('weighted_rms_us','published_rms_us',0.0005),
            ('reduced_chi_square','published_reduced_chi_square',0.00005),
        ):
            difference = abs(checks[actual]-checks[published])
            checks[actual+'_published_difference'] = difference
        checks['historical_summary_difference_flag'] = bool(
            checks['weighted_rms_us_published_difference'] > max(0.0005,0.001*checks['published_rms_us']) or
            checks['reduced_chi_square_published_difference'] > max(0.00005,0.001*checks['published_reduced_chi_square']))
        # Release large dense work arrays before the independent formulation.
        del red,dm,L,W,Q,whitened,post
        likelihood=audit_likelihood(out,out/'likelihood-audit.json')
        checks['independent_likelihood_absolute_difference'] = likelihood['absolute_difference']
        if not np.isclose(likelihood['marginal_reduced_chi2'],checks['reduced_chi_square'],rtol=1e-7,atol=1e-7):
            failures.append('Adapter covariance likelihood differs from reference factors')
        cal.write(out/'checks.json',checks)
        if failures: raise ValueError('Compatibility mismatch: '+', '.join(failures))
        np.savez_compressed(out/'arrays.npz',**arrays)
        np.savez_compressed(out/'observed.npz',residuals=residuals)
        resources=[*(clockdir.iterdir()),data/'ephemeris/DE436.1950.2050',data/'ephemeris/TDB.1950.2050',
                   data/'ephemeris/TIMEEPH_short.te405',*(data/'earth').rglob('*'),*(data/'observatory').rglob('*')]
        receipt={'status':'TIMING_NOISE_COMPATIBLE','target':target_id,'toas':ntoa,'observing_days':row['observing_days'],
                 'span_days':float(np.ptp(a['times'])),'checks':checks,
                 'scope':'Preparation only; no calibration, periodogram or observed search',
                 'model_adjustment':'DM_SERIES POLY preserves the May 2019 coefficient convention',
                 'noise_model':f"Fixed released EFAC/EQUAD/ECORR plus {fields['TNRedC'][0]} red and {fields['TNDMC'][0]} DM Fourier pairs; TEMPO2 epoch convention",
                 'noise_limit':'Conditional on released noise; no hyperparameter uncertainty or detection sensitivity measured',
                 'timing_names':names,'timing_design_sign':'TEMPO2 residual correction columns (-dr/dp)',
                 'clock_chains':[line for line in (out/'reference.log').read_text().splitlines() if line.startswith('CLOCK_CHAIN')],
                 'resource_hashes':{str(p.resolve()):cal.digest(p) for p in resources if p.is_file()},
                 'runtime_lock_sha256':cal.digest(root/'runtime/pixi.lock'),
                 'code_hashes':{str(p.relative_to(REPO)):cal.digest(p) for p in (Path(__file__),REPO/'tools/ipta_tempo2_export.py',REPO/'tools/ipta_tempo2_reference.C',REPO/'tools/ipta_likelihood_audit.py')},
                 'input_hashes':{str(p.relative_to(original)):cal.digest(p) for p in original.rglob('*') if p.is_file()},
                 'artifact_hashes':{p.name:cal.digest(p) for p in out.iterdir() if p.is_file()}}
        cal.write(out/'receipt.json',receipt)
        print(json.dumps({'receipt':str(out/'receipt.json'),'status':receipt['status'],'checks':checks},indent=2))
    except Exception as error:
        cal.write(out/'failure.json',{'status':'PREPARATION_FAILED','error':str(error),'search_launched':False})
        raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=DEFAULT)
    parser.add_argument('--target',default=TARGET)
    args=parser.parse_args()
    prepare(args.data,args.target)
