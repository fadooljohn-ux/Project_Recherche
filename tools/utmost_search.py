"""Freeze and execute a saved UTMOST batch without recalibration."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tarfile

import mpta_batch as mpta
import target_calibration as cal
import utmost_prepare as prep

DATA = prep.DATA
EVIDENCE = prep.REPO/'results/observed/utmost-batch01-20260909'


def configure(data):
    global DATA,EVIDENCE
    prep.configure(data)
    DATA=prep.DATA
    EVIDENCE=prep.REPO/'results/observed'/DATA.name


def freeze():
    output = DATA/'execution-freeze.json'
    if output.exists(): raise FileExistsError('UTMOST execution freeze already exists')
    selection = cal.read(DATA/'selection.json')
    if selection['selected'] != list(prep.TARGETS): raise ValueError('Selection changed')
    bindings = {}
    for path,sha in selection['resources'].items():
        if cal.digest(path) != sha: raise ValueError('Preparation resource changed')
    for row in selection['rows']:
        for kind in ('par','tim'):
            if cal.digest(prep.UPSTREAM/row[kind+'_path']) != row[kind+'_sha256']:
                raise ValueError('Original input changed')
    for target in selection['selected']:
        root = DATA/target
        receipt = cal.read(root/'prepared/receipt.json')
        calibrated = cal.read(root/'calibrated.json')
        if (root/'run01').exists(): raise FileExistsError('Target destination consumed')
        assert receipt['adapter_sha256'] == cal.digest(prep.__file__)
        assert receipt['shared_adapter_sha256'] == cal.digest(mpta.__file__)
        assert receipt['selection_sha256'] == cal.digest(DATA/'selection.json')
        assert calibrated['preparation_sha256'] == cal.digest(root/'prepared/receipt.json')
        assert calibrated['profile_sha256'] == cal.digest(root/'prepared/profile/profile.json')
        assert receipt['observed_sha256'] == cal.digest(root/'prepared/observed.npz')
        assert receipt['clock_replay_sha256'] == cal.digest(root/'prepared/mo2gps-sampled.clk')
        assert receipt['normalized_tim_sha256'] == cal.digest(root/'prepared/format1.tim')
        profile, arrays = cal.load_profile(root/'prepared/profile/profile.json')
        assert profile['policy'] == receipt['policy']
        assert profile['policy']['search_count'] == len(selection['selected'])
        cache = Path(calibrated['calibration']['path'])
        cal.verify_cache(cache, {'profile':profile,'implementation':cal.implementation()})
        # The existing observed runner expects a profile alongside prepared/.
        # An alias preserves the original profile bytes and calibration key.
        alias = root/'profile'
        if not alias.exists(): alias.symlink_to('prepared/profile',target_is_directory=True)
        assert alias.resolve() == (root/'prepared/profile').resolve()
        bindings[target] = {'profile_sha256':calibrated['profile_sha256'],
                            'observed_sha256':receipt['observed_sha256'],
                            'preparation_sha256':calibrated['preparation_sha256'],
                            'calibration':calibrated['calibration']}
    backup = DATA/'prelaunch-inputs.tar.gz'
    with tarfile.open(backup,'x:gz') as archive:
        for target in selection['selected']:
            archive.add(DATA/target/'prepared',arcname=target+'/prepared')
            archive.add(DATA/target/'calibrated.json',arcname=target+'/calibrated.json')
        for name in ('selection.json','calibration-cache'):
            archive.add(DATA/name,arcname=name)
    import hashlib
    with tarfile.open(backup) as archive:
        for member in archive.getmembers():
            if member.isfile():
                assert hashlib.sha256(archive.extractfile(member).read()).hexdigest()==cal.digest(DATA/member.name)
    record={'created_utc':mpta.now(),'selection_sha256':cal.digest(DATA/'selection.json'),
            'code_sha256':cal.digest(mpta.__file__),'implementation':cal.implementation(),
            'utmost_runner_sha256':cal.digest(__file__),'preparation_adapter_sha256':cal.digest(prep.__file__),
            'targets':bindings,'search':'One frozen 30-400 day circular grid per target; no period seeds',
            'batch_alpha_conditional':.01,'max_targets':len(selection['selected']),'authorization':'Owner authorized preparation and launch of saved batch, 2026-09-09',
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'verified_backup':str(backup),'backup_sha256':cal.digest(backup)}
    cal.write(output,record)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    shutil.copy2(output,EVIDENCE/'execution-freeze.json')
    print('FROZEN',len(bindings),'unchanged profiles, thresholds and masks',flush=True)


def run(target):
    frozen=cal.read(DATA/'execution-freeze.json')
    assert frozen['utmost_runner_sha256']==cal.digest(__file__)
    assert frozen['preparation_adapter_sha256']==cal.digest(prep.__file__)
    mpta.run(DATA,target)
    destination=EVIDENCE/target
    destination.mkdir(exist_ok=False)
    for name in ('result.json','periodogram.npz'):
        shutil.copy2(DATA/target/'run01'/name,destination/name)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['freeze','run'])
    parser.add_argument('--target')
    parser.add_argument('--data',type=Path)
    args=parser.parse_args()
    if args.data: configure(args.data)
    if args.target and args.target not in prep.TARGETS: parser.error('Target outside saved selection')
    if args.action=='run':
        if not args.target: parser.error('--target is required')
        run(args.target)
    else: freeze()
