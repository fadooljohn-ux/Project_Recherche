"""Sequential, resumable IPTA campaign; each observed destination is consumed once."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np
import target_calibration as cal
from mpta_batch import now

REPO = Path(__file__).resolve().parents[1]
MASTER = REPO/'outputs/recherche-master-20260908/Project-Recherche-Master.xlsx'


def invoke(args, log):
    with log.open('w') as stream:
        result = subprocess.run([str(a) for a in args], cwd=REPO, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'Exit {result.returncode}: {log}')


def register_attempt(evidence, target, attempt, message):
    record = evidence / ('attempt-'+target+'-'+attempt)
    if (record/'master-workbook-update.json').exists():
        return
    record.mkdir(exist_ok=True)
    cal.write(record/'failure.json', {'target':target, 'attempt':attempt, 'error':message,
              'observed_search_executed':False, 'master_before_sha256':cal.digest(MASTER)})
    cal.write(record/'workbook-context.json', {'evidence':str(record/'failure.json'), 'entries':[
        [record.name, 'IPTA preparation attempt', target, 'PREPARATION_FAILED', message,
         'Attempt retained; diagnose adapter or input mismatch. Not an observed nondetection.']]})
    invoke([REPO/'tools/recherche', 'master-workbook',
            '--review',record/'workbook-context.json'],record/'workbook.log')


def profile(data, target, prepared):
    manifest=cal.read(data/'campaign.json')
    receipt=cal.read(prepared/'receipt.json')
    for name,digest in receipt['artifact_hashes'].items():
        if cal.digest(prepared/name)!=digest:
            raise ValueError('Prepared artifact changed: '+name)
    with np.load(prepared/'arrays.npz') as z:
        arrays={k:z[k] for k in z.files}
    policy={**cal.DEFAULT_POLICY, 'minimum_period_days':30.,
            'maximum_period_days':min(2000.,float(np.ptp(arrays['times']))/2),
            'search_count':len(manifest['selected']), 'seed':manifest['seeds'][target]}
    return cal.create_profile(data/target/'profile',target,arrays,{
        'timing_model':'IPTA DR2 Version B TDB; released legacy TEMPO conventions; DM_SERIES POLY',
        'noise_model':receipt['noise_model'],
        'preparation_receipt':str(prepared/'receipt.json'),
        'preparation_receipt_sha256':cal.digest(prepared/'receipt.json'),
        'context_sha256':cal.digest(prepared/'arrays.npz'),
        'campaign_manifest':str(data/'campaign.json'),
        'campaign_manifest_sha256':cal.digest(data/'campaign.json'),
    },policy,reference_epoch=float(cal.read(prepared/'timing.json')['pepoch']))


def run(data, targets=None):
    manifest=cal.read(data/'campaign.json')
    evidence=REPO/'results/observed'/data.name
    progress_path=data/'progress.json'
    state=cal.read(progress_path) if progress_path.exists() else {
        'selected':manifest['selected'], 'targets':{}, 'status':'RUNNING'}
    def save(target, **values):
        state['targets'].setdefault(target,{}).update(values)
        state['updated_utc']=now()
        cal.write(progress_path,state)
        cal.write(evidence/'progress.json',state)
        print(target,values.get('status','BOOKKEEPING_UPDATED'),flush=True)
    for target in targets or manifest['selected']:
        if target not in manifest['selected']:
            raise ValueError('Target outside campaign')
        if state['targets'].get(target,{}).get('status')=='COMPLETE':
            if not state['targets'][target].get('workbook_updated'):
                launch=Path(state['targets'][target]['result']).parents[2]
                invoke([REPO/'tools/recherche','master-workbook',launch,'--ipta-observed'],
                       data/target/'workbook-repair.log')
                save(target,workbook_updated=True)
            continue
        root=data/target
        # Register preserved failed preparations even when a later attempt passed.
        for failure in sorted(root.glob('attempt*/failure.json')):
            register_attempt(evidence,target,failure.parent.name,cal.read(failure)['error'])
        prepared=next((p.parent for p in sorted(root.glob('attempt*/receipt.json'),reverse=True)
                       if cal.read(p)['status']=='TIMING_NOISE_COMPATIBLE'),None)
        if prepared is None:
            save(target,status='PREPARING')
            try:
                invoke([REPO/'tools/recherche','ipta-prepare','--data',data,'--target',target],root/'preparation.log')
                prepared=sorted(root.glob('attempt*/receipt.json'))[-1].parent
            except Exception as error:
                for failure in sorted(root.glob('attempt*/failure.json')):
                    register_attempt(evidence,target,failure.parent.name,cal.read(failure)['error'])
                save(target,status='PREPARATION_GAP',error=str(error))
                continue
        save(target,status='PREPARED',prepared=str(prepared))
        profile_path=root/'profile/profile.json'
        if not profile_path.exists():
            # Separate process releases dense preparation matrices before calibration.
            invoke([REPO/'.pixi/envs/default/bin/python',Path(__file__),'profile','--data',data,
                    '--target',target,'--prepared',prepared],root/'profile.log')
        save(target,status='CALIBRATING')
        invoke([REPO/'tools/recherche','calibration','run','--profile',profile_path,
                '--cache',data/'calibration-cache'],root/'calibration.log')
        p=cal.read(profile_path)
        key=hashlib.sha256(cal.canonical({'profile':p,'implementation':cal.implementation()})).hexdigest()
        cache=data/'calibration-cache'/key
        cached=cal.verify_cache(cache,{'profile':p,'implementation':cal.implementation()})
        save(target,status='CALIBRATED',calibration=cached['summary'])
        launch=data/'executions'/f'{data.name}-{target}'
        if not (launch/'execution-freeze.json').exists():
            invoke([REPO/'tools/recherche','ipta-search','freeze','--data',launch,
                    '--profile',profile_path,'--cache',cache,'--preparation',prepared],root/'freeze.log')
        result_path=launch/target/'run01/result.json'
        if not result_path.exists():
            save(target,status='SEARCHING',execution=str(launch))
            # Use the scientific entry point directly, then register the terminal
            # result with the supported workbook-only command after status is saved.
            try:
                invoke([REPO/'.pixi/envs/default/bin/python',REPO/'tools/ipta_search.py',
                        'run','--data',launch],root/'observed.log')
            except Exception:
                save(target,status='OBSERVED_INCOMPLETE')
                invoke([REPO/'tools/recherche','master-workbook',launch,'--ipta-observed'],root/'workbook.log')
                raise
        result=cal.read(result_path)
        target_evidence=evidence/target
        target_evidence.mkdir(exist_ok=True)
        for origin in (result_path,result_path.parent/'periodogram.npz',launch/'execution-freeze.json',
                       launch/'selection.json',prepared/'receipt.json',prepared/'checks.json',
                       profile_path,cache/'calibration.json'):
            shutil.copy2(origin,target_evidence/origin.name)
        save(target,status='COMPLETE',result=str(result_path),result_sha256=cal.digest(result_path),
             disposition=result['status'],candidate=result['candidate'],noise_flag=result['noise_adequacy_flag'])
        invoke([REPO/'tools/recherche','master-workbook',launch,'--ipta-observed'],root/'workbook.log')
        shutil.copy2(launch/'master-workbook-update.json',target_evidence/'master-workbook-update.json')
        save(target,workbook_updated=True)
    state['status']='OBSERVED_PASS_COMPLETE' if all(state['targets'].get(t,{}).get('status')
                    in ('COMPLETE','PREPARATION_GAP') for t in manifest['selected']) else 'RUNNING'
    state['updated_utc']=now()
    cal.write(progress_path,state);cal.write(evidence/'progress.json',state)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('run','profile'))
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--target',action='append')
    parser.add_argument('--prepared',type=Path)
    args=parser.parse_args()
    if args.command=='profile':
        profile(args.data.resolve(),args.target[0],args.prepared.resolve())
    else:
        run(args.data.resolve(),args.target)
