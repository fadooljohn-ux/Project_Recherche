"""Bounded UTMOST DR1 ingestion and fixed-noise calibration; no search action."""
import argparse
from contextlib import ExitStack
from decimal import Decimal
import io
from pathlib import Path
import shutil
import traceback

import numpy as np
from scipy.linalg import solve_triangular

import mpta_batch as mpta
import target_calibration as cal
import utmost_inventory as inventory
from pulsar_pilot.pilot2_offline_resources import LocalPintRepository, NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase

REPO = Path(__file__).resolve().parents[1]
DATA = REPO.parent / 'Project Recherche Data/utmost-preparation01-20260909'
UPSTREAM = REPO.parent / 'Project Recherche Data/utmost-inventory-20260909/TimingDataRelease1-e6c36c26b54749d89d29c148da98f0919b3ce5a8'
EVIDENCE = REPO / 'results/research/utmost-preparation01-20260909'
TARGETS = ('J1807-0847', 'J0134-2937', 'J1453-6413', 'J1224-6407')
POLICY = {**cal.DEFAULT_POLICY, 'minimum_period_days': 30., 'maximum_period_days': 400.,
          'search_count': 4, 'seed': 2026090901}


def configure(data):
    """Bind a saved batch without altering earlier selections or profiles."""
    global DATA, TARGETS, POLICY, EVIDENCE
    DATA = Path(data).resolve()
    selection = cal.read(DATA/'selection.json')
    TARGETS = tuple(selection['selected'])
    POLICY = selection['policy']
    EVIDENCE = REPO/'results/research'/DATA.name
    return selection


def inventory_next(data, batch_size):
    import math
    import hashlib
    import zipfile
    import xml.etree.ElementTree as ET
    data = Path(data).resolve()
    if data.exists(): raise FileExistsError('New batch directory already exists')
    if not 1 <= batch_size <= 25: raise ValueError('Batch size must be 1-25')
    master = REPO/'outputs/recherche-master-20260908/Project-Recherche-Master.xlsx'
    ns = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(master) as archive:
        strings = [''.join(t.itertext()) for t in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si',ns)] if 'xl/sharedStrings.xml' in archive.namelist() else []
        def cell(c):
            v=c.find('m:v',ns)
            if c.get('t')=='inlineStr': return ''.join(c.find('m:is',ns).itertext())
            return strings[int(v.text)] if c.get('t')=='s' and v is not None else v.text if v is not None else None
        searches = [[cell(c) for c in row] for row in ET.fromstring(archive.read('xl/worksheets/sheet3.xml')).findall('.//m:sheetData/m:row',ns)]
    # Search target and source are the second/third populated cells in this table.
    searched = {r[1] for r in searches[1:] if len(r)>2}
    consumed = {r[1] for r in searches[1:] if len(r)>2 and str(r[2]).startswith('UTMOST')}
    for p in (REPO.parent/'Project Recherche Data').glob('utmost-*/selection.json'):
        for target in cal.read(p)['selected']:
            if (p.parent/target/'run01').exists(): consumed.add(target)
    source = REPO/'results/research/utmost-inventory-20260909/inventory.json'
    rows = [r for r in cal.read(source)['rows'] if r['preferred_inventory_variant'] and r['passes_target_and_coverage_screen'] and r['target'] not in consumed]
    for r in rows:
        n=r['noise_parameters']
        proxy=math.hypot(float(n['TNGLOBALEF'])*r['median_toa_uncertainty_us'],10**(float(n['TNGLOBALEQ'])+6))/math.sqrt(r['toas_in_model_window'])
        r['rank_key']=[r['target'] in searched,sum(r['prior_search_membership'].values()),proxy,r['target']]
    rows.sort(key=lambda r:r['rank_key'])
    chosen=rows[:batch_size]
    if len(chosen)!=batch_size: raise ValueError('Insufficient remaining compatible targets')
    data.mkdir()
    seed=int.from_bytes(hashlib.sha256(data.name.encode()).digest()[:4],'big')
    policy={**POLICY,'search_count':len(chosen),'seed':seed}
    original=REPO.parent/'Project Recherche Data/utmost-preparation01-20260909'
    for name in ('de430.bsp','conventions'): (data/name).symlink_to(original/name,target_is_directory=name=='conventions')
    selection={'selected':[r['target'] for r in chosen],'rows':chosen,'policy':policy,
               'created_utc':mpta.now(),'source':'UTMOST','dataset':'UTMOST DR1',
               'selection_basis':'Unsearched by Recherche first, then fewer named prior-inventory memberships, then released white-error/sqrt(TOA count), then target ID; no residual peaks',
               'previously_consumed_targets':sorted(consumed),'eligible_before_selection':len(rows),
               'remaining_after_selection':len(rows)-len(chosen),'inventory_sha256':cal.digest(source),
               'master_sha256_at_selection':cal.digest(master),'observed_search_authorized':True,
               'resources':{str(p):cal.digest(p) for p in [data/'de430.bsp',UPSTREAM/'clock_file/mo2gps.clk',mpta.RESOURCES/'metadata/resources.json']}}
    cal.write(data/'selection.json',selection)
    cal.write(data/'remaining-ranked-inventory.json',rows[batch_size:])
    print('SELECTED',len(chosen),selection['selected'],flush=True)
    return selection


def sampled_clock(out, rows, tzrmjd):
    """Replay Tempo2's table lookup on the original unsorted clock at used MJDs.

    The release has overlapping entries near MJD 58106. Tempo2's
    TabulatedFunction_getValue uses this binary search without sorting.
    This derived clock is specific to these TOAs and the reference TOA.
    """
    source = UPSTREAM/'clock_file/mo2gps.clk'
    samples = np.array([list(map(float,l.split()[:2])) for l in source.read_text().splitlines()
                        if l.strip() and not l.startswith('#')])
    def value(x):
        if not samples[0,0] <= x <= samples[-1,0]: raise ValueError('Clock coverage gap')
        lo,hi=0,len(samples)-1
        while hi > lo+1:
            mid=(lo+hi)//2
            if samples[mid,0] > x: hi=mid
            else: lo=mid
        return (x-samples[hi-1,0])/(samples[hi,0]-samples[hi-1,0])*(samples[hi,1]-samples[hi-1,1])+samples[hi-1,1]
    dates = sorted({r['mjd'] for r in rows} | {Decimal(tzrmjd), Decimal(str(samples[0,0])), Decimal(str(samples[-1,0]))})
    path = out/'mo2gps-sampled.clk'
    path.write_text('# UTC(mo) UTC(GPS)\n# Tempo2 lookup replay ONLY at the bound TOAs and TZRMJD\n' +
                    '\n'.join(f'{x} {value(float(x)):.17g}' for x in dates)+'\n')
    from pint.observatory.clock_file import ClockFile
    from astropy.time import Time
    from astropy import units as u
    clock = ClockFile.read(path,format='tempo2',bogus_last_correction=False)
    np.testing.assert_allclose(clock.evaluate(Time([float(x) for x in dates],format='mjd',scale='utc')).to_value(u.s),
                               [value(float(x)) for x in dates],rtol=0,atol=1e-14)
    return clock


def select():
    path = DATA / 'selection.json'
    if path.exists():
        return cal.read(path)
    source = REPO / 'results/research/utmost-inventory-20260909/inventory.json'
    rows = [next(r for r in cal.read(source)['rows'] if r['target'] == t and r['preferred_inventory_variant']) for t in TARGETS]
    for r in rows:
        if not r['passes_target_and_coverage_screen'] or r['previously_searched_by_recherche']:
            raise ValueError('Selection is outside the bounded unsearched subset')
        for key in ('par', 'tim'):
            if cal.digest(UPSTREAM / r[key + '_path']) != r[key + '_sha256']:
                raise ValueError('Source input changed')
    result = {'selected': list(TARGETS), 'rows': rows, 'policy': POLICY,
              'selection_basis': 'Two released white and two red noise models; one fully pulse-numbered dataset; no observed peaks used',
              'inventory_sha256': cal.digest(source), 'observed_search_authorized': False,
              'resources': {str(p): cal.digest(p) for p in [DATA/'de430.bsp', UPSTREAM/'clock_file/mo2gps.clk', mpta.RESOURCES/'metadata/resources.json']},
              'conventions': {str(p): cal.digest(p) for p in sorted((DATA/'conventions').glob('*.C'))}}
    cal.write(path, result)
    return result


def prepare(target, selection):
    import pint.logging
    from astropy import units as u
    from pint.models import get_model
    from pint.toa import get_TOAs
    from pint.observatory import Observatory
    from pint.observatory.clock_file import ClockFile
    from pint.solar_system_ephemerides import load_kernel

    root = DATA / target
    root.mkdir(exist_ok=True)
    # Completed preparations are immutable. Failed attempts remain beside them.
    if (root/'prepared/receipt.json').exists():
        receipt = cal.read(root/'prepared/receipt.json')
        if receipt['adapter_sha256'] != cal.digest(__file__):
            raise ValueError('Completed preparation belongs to another adapter version')
        return receipt
    out = root / ('attempt%02d' % (len(list(root.glob('attempt*'))) + 1))
    out.mkdir()
    try:
        pint.logging.setup(level='WARNING', sink=out/'pint.log', removeprior=True)
        row = next(r for r in selection['rows'] if r['target'] == target)
        par = UPSTREAM / row['par_path']
        tim = UPSTREAM / row['tim_path']
        for p, sha in [(par,row['par_sha256']), (tim,row['tim_sha256'])]:
            if cal.digest(p) != sha: raise ValueError('Input changed')
        fields = inventory.fields(par.read_text())
        if fields.get('EPHEM') != ['DE430'] or fields.get('CLK') != ['TT(TAI)']:
            raise ValueError('Unimplemented clock or ephemeris convention')
        # Tempo2 defaults to SI/TCB when UNITS is absent and EPHVER >= 5.
        units = fields.get('UNITS', ['TCB'])[0]
        if 'UNITS' not in fields and fields.get('EPHVER') != ['5']:
            raise ValueError('Time-unit default is unresolved')
        omitted = {'EPHVER','NTOA','CHI2R','TRES','TRACK','MODE','NITS',
                   'TNGLOBALEF','TNGLOBALEQ','TNREDAMP','TNREDGAM','TNREDC'}
        lines = [l for l in par.read_text().splitlines() if l.split() and l.split()[0].upper() not in omitted]
        if 'UNITS' not in fields: lines.append('UNITS ' + units)
        model = get_model(io.StringIO('\n'.join(lines)), allow_tcb=True)
        if any(c.category == 'pulsar_system' for c in model.components.values()):
            raise ValueError('Binary support deferred')
        # Released spin and sky-position fit; fixed DM/solar wind retained.
        # Free DM per single-band epoch would absorb the prospective signal.
        bind_precise_spin_phase(model)
        rows, _ = inventory.observations(tim)
        rows = [r for r in rows if Decimal(fields['START'][0]) <= r['mjd'] <= Decimal(fields['FINISH'][0])]
        normalized = ['FORMAT 1']
        for r in rows:
            flags = ' '.join(k+' '+v for k,v in r['flags'].items())
            normalized.append(f"{r['name']} {r['frequency']:.17g} {r['mjd']} {r['error_us']:.17g} {r['site']} {flags}")
        (out/'format1.tim').write_text('\n'.join(normalized)+'\n')
        with ExitStack() as stack:
            deny = stack.enter_context(NetworkDeny())
            local = stack.enter_context(LocalPintRepository(mpta.RESOURCES, cal.read(mpta.RESOURCES/'metadata/resources.json')))
            local.bind_science_resources()
            load_kernel('DE430', path=str(DATA/'de430.bsp'))
            Observatory.get('mo')._clock = [sampled_clock(out, rows, fields['TZRMJD'][0])]
            toas = get_TOAs(out/'format1.tim', model=model, ephem='DE430', include_bipm=False,
                            planets=bool(model.PLANET_SHAPIRO.value), usepickle=False, limits='error')
            phase = model.phase(toas, abs_phase=False)
            if 'delta_pulse_number' in toas.table.colnames:
                from pint.phase import Phase
                phase += Phase(toas.table['delta_pulse_number'])
            relative, arc = mpta.unwrap_cluster(phase.frac.to_value(u.dimensionless_unscaled))
            phase_connection = 'COMPACT_PHASE_CLUSTER'
            pn_spread = None
            if 'pulse_number' in toas.table.colnames and np.all(np.isfinite(toas.table['pulse_number'])):
                pulse_numbers = np.asarray(toas.table['pulse_number'], np.longdouble)
                if not np.all(pulse_numbers == np.rint(pulse_numbers)):
                    raise ValueError('Released pulse numbers must be integers')
                delta = np.asarray(phase.int.value, np.longdouble) - pulse_numbers
                pn_spread = float(np.ptp(delta))
                # Supplied cycle counts define the residual even when timing
                # noise spans multiple rotations. A large integer spread is not
                # itself a count mismatch. Remove only an arbitrary constant;
                # do not wrap a supplied pulse-count residual to the nearest pulse.
                relative = delta - delta[0] + np.asarray(phase.frac.value, np.longdouble)
                relative -= relative[0]
                phase_connection = 'RELEASED_PULSE_NUMBERS'
            elif fields.get('TRACK') == ['-2']:
                raise ValueError('TRACK -2 requires complete released pulse numbers')
            if arc >= .5 and phase_connection != 'RELEASED_PULSE_NUMBERS':
                raise ValueError(f'Ambiguous pulse connection: {arc}')
            residuals = np.asarray(relative / model.F0.value, float)
            times = np.asarray(toas.table['tdbld'].data, float)
            errors = toas.get_errors().to_value(u.s)
            radio = toas.get_freqs().to_value(u.MHz)
            design, names, _ = model.designmatrix(toas)
            design = np.asarray(design, float)
            efac, logeq = float(fields['TNGLOBALEF'][0]), float(fields['TNGLOBALEQ'][0])
            # Tempo2 preProcess.C: multiply error by EFAC, then add EQUAD^2.
            white = (efac * errors)**2 + 10.**(2*logeq)
            covariance = np.diag(white)
            if 'TNREDAMP' in fields:
                covariance += mpta.red_covariance(times, float(fields['TNREDAMP'][0]), float(fields['TNREDGAM'][0]), int(fields['TNREDC'][0]))
            baseline = design[:, [names.index('Offset')]]
            # Null-model adequacy only: no periodic template is applied to data.
            chol = np.linalg.cholesky(covariance)
            wd = solve_triangular(chol, design, lower=True)
            wr = solve_triangular(chol, residuals, lower=True)
            wd /= np.linalg.norm(wd, axis=0)
            coefficients, _, rank, _ = np.linalg.lstsq(wd, wr, rcond=1e-12)
            projected = wr - wd @ coefficients
            reduced = float(projected @ projected / (len(times)-rank))
            if deny.attempts: raise RuntimeError('Unexpected scientific network access')
            (out/'timing-model.par').write_text(model.as_parfile())
        np.savez_compressed(out/'observed.npz', residuals=residuals)
        np.savez_compressed(out/'metadata.npz', white_variance=white, radio=radio, errors=errors)
        receipt = {'target':target, 'status':'PREPARED_CONDITIONAL', 'toas':len(times),
                   'observing_days':len({int(r['mjd']) for r in rows}), 'span_days':float(np.ptp(times)),
                   'source_units':units, 'runtime_units':str(model.UNITS.value),
                   'phase_arc_cycles':arc, 'pulse_number_integer_spread':pn_spread,
                   'phase_connection':phase_connection,
                   'timing_names':names, 'timing_rank':int(rank), 'null_reduced_chi2':reduced,
                   'noise_adequacy_flag':reduced > 2 or reduced < .5,
                   'noise_parameters':row['noise_parameters'], 'noise_model':'Released fixed total timing noise; EFAC outside EQUAD, optional Fourier red process',
                   'noise_limit':'Single band cannot separate dispersion/scattering from achromatic signals; fixed hyperparameters; no DM time-series inference',
                   'policy':{**POLICY,'seed':POLICY['seed']+TARGETS.index(target)},
                   'selection_sha256':cal.digest(DATA/'selection.json'), 'adapter_sha256':cal.digest(__file__),
                   'shared_adapter_sha256':cal.digest(mpta.__file__), 'observed_sha256':cal.digest(out/'observed.npz'),
                   'normalized_tim_sha256':cal.digest(out/'format1.tim'), 'network_attempts':0,
                   'clock_replay_sha256':cal.digest(out/'mo2gps-sampled.clk'),
                   'clock_policy':'Original Tempo2 binary-search interpolation replayed at bound TOAs and TZRMJD; unsorted source preserved',
                   'observed_search_executed':False}
        cal.create_profile(out/'profile', target, {'times':times,'covariance':covariance,'design':design,'baseline_design':baseline},
                           {'timing_model':'Released isolated-pulsar spin/position model with original time/clock conventions',
                            'noise_model':receipt['noise_model'], 'preparation':receipt}, receipt['policy'], float(model.PEPOCH.value))
        cal.write(out/'receipt.json',receipt)
        out.rename(root/'prepared')
        return receipt
    except Exception:
        cal.write(out/'failure.json', {'status':'PREPARATION_FAILED', 'target':target,
                  'adapter_sha256':cal.digest(__file__), 'traceback':traceback.format_exc(), 'observed_search_executed':False})
        raise


def calibrate(target):
    from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner
    root = DATA/target/'prepared'
    result = cal.run(root/'profile/profile.json', DATA/'calibration-cache')
    profile, arrays = cal.load_profile(root/'profile/profile.json')
    # Three deterministic injected templates check units/projection, not detection yield.
    frequencies = 1./np.array([60.,150.,250.])
    scanner = prepare_covariance_gls_scanner(arrays['covariance'],arrays['design'],arrays['times'],frequencies,profile['reference_epoch_mjd_tdb'])
    recovered = []
    for i,f in enumerate(frequencies):
        template = mpta.circular_template(arrays['times'],profile['reference_epoch_mjd_tdb'],f,len(arrays['times']))
        expected = np.array([.001,.0005])
        injected = template@expected + arrays['baseline_design']@np.array([.0002])
        projected = scanner.whiten_and_project(injected)
        fitted = scanner.template_gram_pseudoinverse[i] @ (scanner.projected_whitened_templates[:,i].T@projected)
        np.testing.assert_allclose(fitted,expected,rtol=1e-7,atol=1e-11)
        recovered.append({'period_days':float(1/f),'expected_coefficients_us':(expected*1e6).tolist(),'recovered_coefficients_us':(fitted*1e6).tolist()})
    result = {'target':target,'calibration':result,'template_checks':recovered,
              'profile_sha256':cal.digest(root/'profile/profile.json'), 'preparation_sha256':cal.digest(root/'receipt.json'),
              'observed_search_executed':False}
    cal.write(DATA/target/'calibrated.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['inventory','prepare','calibrate'])
    parser.add_argument('--target')
    parser.add_argument('--data',type=Path)
    parser.add_argument('--batch-size',type=int,default=25)
    args=parser.parse_args()
    if args.action=='inventory':
        if args.data is None: parser.error('inventory requires a new --data directory')
        inventory_next(args.data,args.batch_size)
    selection=configure(args.data) if args.data else select()
    if args.target and args.target not in selection['selected']: parser.error('Target outside saved selection')
    for path,sha in selection['resources'].items():
        if cal.digest(path)!=sha: raise ValueError('Bound resource changed')
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    shutil.copy2(DATA/'selection.json',EVIDENCE/'selection.json')
    if args.action=='inventory': return
    for target in ([args.target] if args.target else TARGETS):
        result=prepare(target,selection) if args.action=='prepare' else calibrate(target)
        cal.write(EVIDENCE/(target+'-'+args.action+'.json'),result)
        print(args.action.upper(),target,result.get('status',result.get('calibration',{}).get('status')),flush=True)


if __name__=='__main__':
    main()
