"""Bounded native-T2 compatibility and fixed-period EPTA J1012 follow-up."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import traceback
import numpy as np
import target_calibration as cal
import mpta_batch as mpta

REPO=Path(__file__).resolve().parents[1]
TARGET='J1012+5307'


def invoke(command,log,env):
    with log.open('w') as f:
        result=subprocess.run(command,env=env,cwd=log.parent,stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(f'Native command failed ({result.returncode}); see {log.name}')


def prepare(data,out):
    if out.exists():raise FileExistsError('Preparation destination exists; retain/read it')
    out.mkdir(parents=True)
    runtime=data/'ipta-adapter01-20260909/runtime'
    rt=runtime/'.pixi/envs/default'
    release=data/'source-compatibility-20260908/epta-noise/EPTA-DR2'
    source=release/'DR2full'/TARGET
    original=out/'original';shutil.copytree(source,original)
    noises=release/'noisefiles/DR2full'
    for name in [TARGET+'_noise.json','red_dict.json','dm_dict.json']:
        shutil.copy2(noises/name,original/name)
    noise=cal.read(original/(TARGET+'_noise.json'))
    lines=[]
    for key,value in noise.items():
        key=key[len(TARGET)+1:]
        if key.endswith('_efac'):lines.append(f'TNEF -group {key[:-5]} {value}')
        elif key.endswith('_log10_tnequad'):lines.append(f'TNEQ -group {key[:-14]} {value}')
    for kind,label,prefix in [('red','red_noise','TNRed'),('dm','dm_gp','TNDM')]:
        lines += [f'{prefix}Amp {noise[TARGET+"_"+label+"_log10_A"]}',
                  f'{prefix}Gam {noise[TARGET+"_"+label+"_gamma"]}',
                  f'{prefix}C {cal.read(original/(kind+"_dict.json"))[TARGET]}']
    (out/'model.par').write_text((original/(TARGET+'.par')).read_text()+'\n'+'\n'.join(lines)+'\n')
    bound=out/'bound-runtime';bound.mkdir();clock=bound/'clock'
    shutil.copytree(rt/'share/tempo2/clock',clock)
    for directory in [data/'source-compatibility-20260908/clocks',release/'clockfiles']:
        for p in directory.glob('*.clk'):shutil.copy2(p,clock/p.name)
    # Retain the original TIM tree. Exclude only the arrival outside measured
    # Effelsberg clock coverage, before any periodic fit; never extrapolate it.
    derived=out/'derived';shutil.copytree(original,derived)
    samples=[line.split() for line in (clock/'effix2gps.clk').read_text().splitlines()
             if line.strip() and not line.startswith('#')]
    first,last=float(samples[0][0]),float(samples[-1][0]);excluded=[]
    for tim in (derived/'tims').glob('*.tim'):
        lines_out=[]
        for line in tim.read_text().splitlines():
            v=line.split()
            if len(v)>=5 and v[4]=='effix' and not first<=float(v[2])<=last:
                excluded.append({'file':str(tim.relative_to(derived)),'toa':v[0],'mjd':v[2],
                                 'reason':'Outside measured effix2gps clock coverage'})
                line='C RECHERCHE_CLOCK_EXCLUSION '+line
            lines_out.append(line)
        tim.write_text('\n'.join(lines_out)+'\n')
    if len(excluded)!=1:raise ValueError('Clock exclusion differs from diagnosed single arrival')
    cal.write(out/'clock-exclusions.json',{'original_toas':5325,'retained_toas':5324,'excluded':excluded,
                                          'clock_span_mjd':[first,last]})
    for p in (rt/'share/tempo2').iterdir():
        if p.name!='clock':(bound/p.name).symlink_to(p,target_is_directory=p.is_dir())
    alias=Path.home()/'.cache/recherche-tempo2'/out.name
    if alias.exists() or alias.is_symlink():raise FileExistsError('Runtime alias exists')
    alias.parent.mkdir(parents=True,exist_ok=True);alias.symlink_to(bound,target_is_directory=True)
    plugins=out/'plugins';plugins.mkdir()
    env={**os.environ,'TEMPO2':str(alias),'TEMPO2_PLUG_PATH':str(plugins),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
    sources=[Path(__file__),REPO/'tools/epta_binary_export.py',REPO/'tools/epta_binary_reference.C']
    scope={'target':TARGET,'created_utc':mpta.now(),'fixed_period_days_tdb':138.9110415844769,
           'binary_model':'Native released T2 with H3/H4; retain default harmonic convention',
           'data_units':'TCB model, residuals and noise; transform time arguments and fitted amplitudes for TDB comparison',
           'compatibility_limits':{'relative_binary_derivative_error':.001,'maximum_3sigma_nonlinearity_TOA_sigma':.1,'maximum_fitted_orbital_shift_published_sigma':3},
           'followup':'Fixed NG15 candidate period only, published EPTA red149/DM45, extended red256 and double red256 power; conditional coefficient comparison and power, no period search',
           'inputs':{str(p.relative_to(out)):cal.digest(p) for p in original.rglob('*') if p.is_file()},
           'clock_hashes':{p.name:cal.digest(p) for p in clock.glob('*') if p.is_file()},
           'clock_exclusions_sha256':cal.digest(out/'clock-exclusions.json'),
           'derived_tim_hashes':{str(p.relative_to(derived)):cal.digest(p) for p in derived.rglob('*.tim')},
           'code':{str(p.relative_to(REPO)):cal.digest(p) for p in sources},'runtime_lock_sha256':cal.digest(runtime/'pixi.lock')}
    cal.write(out/'scope.json',scope)
    invoke(['clang++','-arch','x86_64','-std=c++11','-dynamiclib','-undefined','dynamic_lookup',
            '-I'+str(rt/'include'),str(REPO/'tools/epta_binary_reference.C'),'-L'+str(rt/'lib'),'-ltempo2',
            '-Wl,-rpath,'+str(rt/'lib'),'-o',str(plugins/'recherche_ref_darwin24_plug.t2')],out/'compile.log',env)
    invoke([str(rt/'bin/python'),'-u',str(REPO/'tools/epta_binary_export.py'),str(out/'model.par'),
            str(derived/(TARGET+'_all.tim')),str(out/'timing.npz')],out/'worker.log',env)
    invoke([str(rt/'bin/tempo2'),'-npsr','1','-nobs','5400','-gr','recherche_ref','-f',str(out/'model.par'),
            str(derived/(TARGET+'_all.tim')),'-export',str(out/'reference.txt')],out/'reference.log',env)
    inspect(out)


def inspect(out):
    meta=cal.read(out/'timing.json');a=np.load(out/'timing.npz');ref=np.loadtxt(out/'reference.txt',dtype=np.longdouble)
    failures=[]
    for name in ['worker.log','reference.log']:
        if any(code in (out/name).read_text() for code in ['[CLK4]','[CLK7]','[CLK9]','Could not open']):failures.append('Missing/approximated timing resource: '+name)
    checks={'toas':len(a['times']),'residual_difference_seconds':float(np.max(abs(a['residuals']-ref[:,3]))),
            'time_difference_days':float(np.max(abs(a['times']-ref[:,1]))),
            'fit_rows':len(np.loadtxt(out/'reference.txt.included',ndmin=1)),
            'binary':meta['binary_parameters']}
    if np.any(a['deleted']) or np.any(ref[:,6]) or checks['fit_rows']!=len(ref):failures.append('Inclusion/deletion mismatch')
    if checks['residual_difference_seconds']>1e-10 or checks['time_difference_days']>1e-10:failures.append('Native reference mismatch')
    for name,v in checks['binary'].items():
        if v['relative_derivative_error']>.001 or v['max_3sigma_remainder_raw_TOA_sigma']>.1:failures.append('Binary derivative/local-linearity: '+name)
    receipt={'status':'NATIVE_TIMING_COMPATIBLE' if not failures else 'TIMING_MODEL_HOLD','checks':checks,'failures':failures,
             'artifacts':{name:cal.digest(out/name) for name in ['scope.json','timing.npz','timing.json','reference.txt','reference.txt.red','reference.txt.dm']}}
    cal.write(out/'compatibility.json',receipt)
    print(json.dumps(receipt),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','inspect'])
    p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    # Reject reuse before the failure writer can touch a consumed preparation.
    if a.action=='prepare' and a.output.exists():p.error('Preparation destination exists; retain/read it')
    try:
        if a.action=='prepare':prepare(a.data.resolve(),a.output.resolve())
        else:inspect(a.output.resolve())
    except Exception:
        if a.output.exists():cal.write(a.output/'failure.json',{'action':a.action,'traceback':traceback.format_exc()})
        raise


if __name__=='__main__':main()
