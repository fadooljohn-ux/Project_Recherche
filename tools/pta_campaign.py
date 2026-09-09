"""Three-source, source-separated campaign using the existing calibrated GLS runtime."""
import argparse
from contextlib import ExitStack
import io
import inspect
import hashlib
import subprocess
import sys
from pathlib import Path
import shutil
import numpy as np
import mpta_batch as mpta
import target_calibration as cal
from pulsar_pilot.pilot2_offline_resources import LocalPintRepository, NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase

ROOT = mpta.REPO.parent / 'Project Recherche Data/pta-campaign01-20260908'
INTAKE = mpta.REPO.parent / 'Project Recherche Data/source-compatibility-20260908'
SOURCES = ('ppta', 'epta', 'inpta')
POLICY = {**cal.DEFAULT_POLICY, 'minimum_period_days': 30., 'maximum_period_days': 2000.,
          'search_count': 18, 'seed': 2026092300}


def preparation_implementation():
    return hashlib.sha256(''.join(inspect.getsource(f) for f in (prepare, normalized_tim, clock_binding, epta_noise_lines)).encode()).hexdigest()


def preparation_matches(root, receipt):
    current = preparation_implementation()
    # Parser extensions recognize C???? comments and scope END to its file.
    # Reuse an old profile only when its
    # normalized TIM is byte-identical under the repaired parser.
    equivalents = ('e4ae07246d8427f81501d0ffc4b734e1d555e831e128c3b12679b55ce5c2d0cc',
                   'fc77b01513a78d511eefd785d72286da380c77a28d9605410e197052ef491181')
    if receipt['preparation_implementation'] not in (current, *equivalents): return False
    text = '\n'.join(normalized_tim(root/'original'/(receipt['target']+'.tim'))) + '\n'
    return hashlib.sha256(text.encode()).hexdigest() == receipt['normalized_tim_sha256']


def inventory():
    ROOT.mkdir(exist_ok=True)
    screening = cal.read(INTAKE / 'screening-closeout.json')
    records = []
    for source in SOURCES:
        data = ROOT / source
        data.mkdir(exist_ok=True)
        if (data / 'selection.json').exists():
            continue
        rows = []
        for r in screening[source]['targets']:
            if not r['eligible_screen']:
                continue
            target = r['target']
            dest = data / target / 'original'
            dest.mkdir(parents=True, exist_ok=True)
            if source == 'ppta':
                original = INTAKE / 'ppta-v2'
                par, tim = original / (target + '_singlePsrNoise_fit.par'), original / (target + '.tim')
                for suffix in ('_singlePsrNoise_fit.par', '.tim'):
                    assert cal.digest(original / (target + suffix)) == cal.digest(INTAKE / 'ppta' / (target + suffix))
            elif source == 'epta':
                original = INTAKE / 'epta-noise/EPTA-DR2/DR2full' / target
                par, tim = original / (target + '.par'), original / (target + '_all.tim')
                shutil.copytree(original / 'tims', dest / 'tims', dirs_exist_ok=True)
                noise_root = INTAKE / 'epta-noise/EPTA-DR2/noisefiles/DR2full'
                for f in [target + '_noise.json', 'red_dict.json', 'dm_dict.json', 'chrom_dict.json']:
                    shutil.copy2(noise_root / f, dest / f)
            else:
                original = INTAKE / 'inpta' / target
                par, tim = original / (target + '.DMX.par'), original / (target + '_all.tim')
                shutil.copytree(original / 'tims', dest / 'tims', dirs_exist_ok=True)
            shutil.copy2(par, dest / (target + '.par'))
            shutil.copy2(tim, dest / (target + '.tim'))
            rows.append({**r, 'selected': True, 'aliases': [], 'exclusion_reasons': [],
                         'epochs': r['observing_days'], 'batch_index': len(rows) + len(records),
                         'par_sha256': cal.digest(par), 'tim_sha256': cal.digest(tim),
                         'prior_search_membership': dict.fromkeys(['JBO800', 'NANOGrav11', 'EPTA_DR2']),
                         'input_hashes': {str(p.relative_to(dest)): cal.digest(p) for p in dest.rglob('*') if p.is_file()}})
        selection = {'created_utc': mpta.now(), 'source': source.upper(), 'dataset': {'ppta': 'PPTA DR3 v2', 'epta': 'EPTA DR2full, Zenodo 8164425', 'inpta': 'InPTA DR2'}[source],
                     'selected': [r['target'] for r in rows], 'rows': rows, 'policy': POLICY,
                     'eligible_targets': len(rows), 'remaining_after_selection': 0,
                     'maximum_period_rule': 'min(2000 days, prepared TDB span / 2)',
                     'observed_periodograms_inspected': False}
        cal.write(data / 'selection.json', selection)
        records.extend({'source': source, 'target': r['target']} for r in rows)
    if not (ROOT / 'intake.json').exists():
        records = [{'source': s, 'target': t} for s in SOURCES for t in cal.read(ROOT / s / 'selection.json')['selected']]
        assert len(records) == POLICY['search_count']
        cal.write(ROOT / 'intake.json', {'created_utc': mpta.now(), 'datasets': records,
            'unique_targets': len({r['target'] for r in records}), 'policy': POLICY,
            'ppta_revision': '59423 / v2; seven selected PAR/TIM pairs identical to v1',
            'epta_release': '10.5281/zenodo.8164425; DR2full only, with matching noise and corrected Nancay clock',
            'inpta_commit': cal.read(INTAKE / 'inpta-tree.json')['sha'],
            'clock_commit': cal.read(INTAKE / 'clock-tree.json')['sha'],
            'support_hashes': {str(p): cal.digest(p) for p in [INTAKE / 'EPTA-DR2-noise.zip', *sorted((INTAKE / 'clocks').glob('*'))]},
            'historical_result_hashes': {str(p): cal.digest(p) for p in (mpta.REPO / 'results').rglob('*.json')},
            'master_sha256': cal.digest(mpta.REPO / 'outputs/recherche-master-20260908/Project-Recherche-Master.xlsx')})
    print('INTAKE COMPLETE: 18 datasets, 12 pulsars', flush=True)


def clock_binding(source):
    import pint.observatory as obs
    from pint.observatory.clock_file import ClockFile
    versions = {'ppta': '2020', 'epta': '2021', 'inpta': '2023'}
    version = versions[source]
    clocks = INTAKE / 'clocks'
    bipm = (INTAKE / 'epta-noise/EPTA-DR2/clockfiles' if source == 'epta' else clocks) / ('tai2tt_bipm' + version + '.clk')
    obs._bipm_clock_versions['bipm' + version] = ClockFile.read(bipm, format='tempo2')
    paths = [bipm]
    # PINT's declared clock chains are retained; only the file resolver is local.
    for name in ['parkes', 'gmrt', 'effelsberg', 'effelsberg_asterix', 'jodrell', 'jbdfb', 'jbroach', 'nancay', 'ncyobs', 'leap', 'wsrt']:
        o = obs.Observatory.get(name)
        chain = []
        for item in o.clock_files:
            filename = item['name'] if isinstance(item, dict) else item
            p = clocks / filename
            if source == 'ppta' and filename == 'pks2gps.clk': p = clocks / 'pks2gps-ppta-dr3.clk'
            if source == 'epta' and filename == 'ncyobs2obspm.clk': p = INTAKE / 'epta-noise/EPTA-DR2/clockfiles' / filename
            if source == 'epta' and filename == 'effix2gps.clk':
                # Daily final sample is at midday; release TOAs extend into
                # that same day. Permit only the remaining half-day, constant.
                derived = ROOT / 'effix2gps-final-day.clk'
                text = p.read_text()
                last = [l.split() for l in text.splitlines() if l.strip() and not l.lstrip().startswith('#')][-1]
                derived.write_text(text + f'\n{float(last[0])+.5:.6f} {last[1]} # Final observing-day endpoint\n')
                paths.append(p)
                p = derived
            if source == 'epta' and filename == 'leap2effix.clk':
                # Preserve the release's zero correction before the first
                # jump; PINT drops its MJD=0 sentinel when reading the file.
                derived = ROOT / 'leap2effix-zero-baseline.clk'
                derived.write_text('\n'.join('40000 0 # Original MJD=0 zero baseline' if l.split() == ['0','0'] else l for l in p.read_text().splitlines()) + '\n')
                paths.append(p); p = derived
            chain.append(ClockFile.read(p, format=o.clock_fmt, valid_beyond_ends=isinstance(item, dict) and item.get('valid_beyond_ends', False)))
            paths.append(p)
        o._clock = chain
    return 'BIPM' + version, {str(p): cal.digest(p) for p in paths}


def normalized_tim(path):
    """Expand released INCLUDEs and give valueless Tempo2 metadata flags value 1."""
    lines = []
    for raw in path.read_text().splitlines():
        fields = raw.split()
        if not fields: continue
        if fields[0].upper() == 'END': break
        if raw.startswith(('C', '#')) or fields[0] == 'c':
            lines.append('C ' + raw); continue
        if fields[0] == '-padd':
            if len(fields) != 2 or not lines: raise ValueError('Malformed phase-offset continuation')
            # Some EPTA files wrap a TOA's phase flag onto the next line.
            lines[-1] += ' ' + ' '.join(fields)
            continue
        if fields[0] == 'INCLUDE':
            lines.extend(normalized_tim(path.parent / fields[1])); continue
        try: float(fields[1]); float(fields[2]); float(fields[3])
        except (ValueError, IndexError):
            lines.append(raw.lstrip()); continue
        result = fields[:5]
        i = 5
        while i < len(fields):
            key = fields[i]
            if not key.startswith('-'): raise ValueError(f'Unexpected TIM flag token {key}')
            bare = i + 1 == len(fields)
            if not bare and fields[i+1].startswith('-'):
                try: float(fields[i+1])
                except ValueError: bare = True
            result.extend([key, '1' if bare else fields[i+1]])
            i += 1 if bare else 2
        if '-addsat' in result:
            # Tempo2 offsets site arrival time in seconds before barycentering.
            # PINT otherwise treats this as uninterpreted metadata.
            from decimal import Decimal, localcontext
            with localcontext() as context:
                context.prec = 35
                result[2] = str(Decimal(result[2]) + Decimal(result[result.index('-addsat')+1])/Decimal(86400))
        lines.append(' '.join(result))
    return lines


def epta_noise_lines(root, target):
    noise = cal.read(root / (target + '_noise.json'))
    lines = []
    for key, value in noise.items():
        name = key[len(target)+1:]
        if name.endswith('_efac'):
            lines.append(f'TNEF -group {name[:-5]} {value}')
        elif name.endswith('_log10_tnequad'):
            lines.append(f'TNEQ -group {name.removesuffix("_log10_tnequad")} {value}')
    # EPTA Table 1 uses TempoNest DM units. PINT uses equivalent timing
    # amplitude at 1400 MHz: A_PINT = A_TN sqrt(12 pi^2)/(k_DM * 1400^2).
    for kind, label, prefix in [('red','red_noise','TNRed'), ('dm','dm_gp','TNDM'), ('chrom','chrom_gp','TNChrom')]:
        key = target + '_' + label + '_log10_A'
        if key not in noise:
            continue
        amplitude = noise[key]
        if kind == 'dm': amplitude += np.log10(np.sqrt(12*np.pi**2)/(2.41e-4 * 1400**2))
        modes = cal.read(root / (kind + '_dict.json'))[target]
        if modes is None: raise ValueError('Noise amplitude lacks a published frequency count')
        lines.extend([f'{prefix}Amp {amplitude}', f'{prefix}Gam {noise[target + "_" + label + "_gamma"]}', f'{prefix}C {modes}'])
    return lines


def prepare(source, target):
    import pint.logging
    from pint.models import get_model
    from pint.toa import get_TOAs
    from astropy import units as u
    data = ROOT / source
    selection = cal.read(data / 'selection.json')
    row = next(r for r in selection['rows'] if r['target'] == target)
    root = data / target
    out = root / 'prepared'
    implementation = preparation_implementation()
    if (out / 'receipt.json').exists():
        if preparation_matches(root, cal.read(out / 'receipt.json')):
            print('ALREADY PREPARED', source, target, flush=True); return
        if (root / 'run01').exists() or (data / 'execution-freeze.json').exists():
            raise ValueError('Consumed or frozen preparation cannot be replaced')
        archive = root / ('preparation-attempt-' + str(len(list(root.glob('preparation-attempt-*')))+1))
        archive.mkdir()
        out.rename(archive / 'prepared')
        (root / 'profile').rename(archive / 'profile')
    out.mkdir(exist_ok=True)
    pint.logging.setup(level='WARNING', sink=out / 'pint.log', removeprior=True)
    original = root / 'original'
    for rel, sha in row['input_hashes'].items(): assert cal.digest(original / rel) == sha
    par = (original / (target + '.par')).read_text()
    omitted = {'EPHVER', 'NTOA', 'CHI2R', 'TRES', 'TNsubtractRed', 'TNsubtractDM', 'TNsubtractChrom', 'TNBandNoise'}
    lines = [line for line in par.splitlines() if line.split() and line.split()[0] not in omitted]
    # J1939's release repeats identical scalar chromatic settings.
    unique = []
    chromatic_values = {}
    for line in lines:
        fields = line.split()
        if fields[0].upper().startswith('TNCHROM'):
            key = fields[0].upper()
            if key in chromatic_values:
                if fields[1:] != chromatic_values[key]: raise ValueError('Conflicting repeated chromatic parameter')
                continue
            chromatic_values[key] = fields[1:]
        unique.append(line)
    lines = unique
    if source == 'epta': lines += epta_noise_lines(original, target)
    model = get_model(io.StringIO('\n'.join(lines)), allow_tcb=True)
    if any(c.category == 'pulsar_system' for c in model.components.values()): raise ValueError('Binary model outside campaign')
    # Project uncertainty in position/proper motion/parallax for a uniform annual mask.
    released_free = list(model.free_params)
    for name in model.params:
        if name in {'RAJ','DECJ','ELONG','ELAT','PMRA','PMDEC','PMELONG','PMELAT','PX'} or (source == 'inpta' and name.startswith('DMX_')):
            p = getattr(model, name)
            if p.value is not None: p.frozen = False
    bind_precise_spin_phase(model)
    with ExitStack() as stack:
        deny = stack.enter_context(NetworkDeny())
        local = stack.enter_context(LocalPintRepository(mpta.RESOURCES, cal.read(mpta.RESOURCES / 'metadata/resources.json')))
        local.bind_science_resources()
        bipm, clock_hashes = clock_binding(source)
        tim = out / 'format1.tim'
        tim.write_text('\n'.join(normalized_tim(original / (target + '.tim'))) + '\n')
        toas = get_TOAs(tim, model=model, ephem='DE440', planets=bool(model.PLANET_SHAPIRO.value), include_bipm=True, bipm_version=bipm, usepickle=False, limits='error')
        phase = model.phase(toas, abs_phase=False)
        if 'delta_pulse_number' in toas.table.colnames:
            from pint.phase import Phase
            phase += Phase(toas.table['delta_pulse_number'])
        relative, arc = mpta.unwrap_cluster(phase.frac.to_value(u.dimensionless_unscaled))
        if arc >= .5: raise ValueError(f'Ambiguous pulse connection: {arc}')
        residuals = np.asarray(relative / model.F0.value, float)
        times = np.asarray(toas.table['tdbld'].data, float)
        radio = toas.get_freqs().to_value(u.MHz)
        design, names, _ = model.designmatrix(toas)
        # Empty released JUMP / DMX ranges have no effect; do not send zero columns to GLS.
        keep = np.linalg.norm(design, axis=0) > 0
        dropped = [n for n, k in zip(names, keep) if not k]
        names = [n for n,k in zip(names,keep) if k]
        design = design[:, keep]
        baseline = design[:, [i for i,n in enumerate(names) if n == 'Offset' or n.startswith(('DM','JUMP','FD')) or n == 'NE_SW']]
        print('COVARIANCE', source, target, len(times), len(names), flush=True)
        # PINT's long-double Fourier basis sends the dense product through
        # a scalar fallback. The qualified scanner uses float64 covariance;
        # cast the basis before multiplication, preserving precise spin phase.
        covariance = np.diag(model.scaled_toa_uncertainty(toas).to_value(u.s)**2)
        basis = model.noise_model_designmatrix(toas)
        if basis is not None:
            # One small direct check of the extended-to-double product.
            weights = model.noise_model_basis_weight(toas)
            reference_covariance = (basis[:24] * weights) @ basis[:24].T
            basis = np.asarray(basis, dtype=float)
            weights = np.asarray(weights, dtype=float)
            np.testing.assert_allclose((basis[:24] * weights) @ basis[:24].T, reference_covariance, rtol=1e-12, atol=1e-24)
            covariance += (basis * weights) @ basis.T
            del basis, weights
        if source in ('ppta', 'epta'):
            # Released TNEQ is added AFTER EFAC scaling (EPTA Eq. 3).
            # PINT's ScaleToaError puts EQUAD inside EFAC, so correct only
            # that diagonal and retain its correlated-noise covariance.
            old_white = model.scaled_toa_uncertainty(toas).to_value(u.s)**2
            white = toas.get_errors().to_value(u.s)**2
            component = model.components['ScaleToaError']
            for name in component.EFACs:
                p = getattr(model, name); white[p.select_toa_mask(toas)] *= float(p.value)**2
            for name in component.EQUADs:
                p = getattr(model, name); white[p.select_toa_mask(toas)] += p.quantity.to_value(u.s)**2
            covariance[np.diag_indices_from(covariance)] += white - old_white
        bands = []
        for line in par.splitlines():
            fields = line.split()
            if fields and fields[0] == 'TNBandNoise':
                lo, hi, amp, gamma, modes = map(float, fields[1:])
                mask = (radio >= lo) & (radio < hi)
                covariance += mpta.red_covariance(times, amp, gamma, int(modes)) * mask[:,None] * mask[None,:]
                bands.append(fields[1:])
        if deny.attempts: raise RuntimeError('Scientific network request')
        (out / 'timing-model.par').write_text(model.as_parfile())
        np.savez_compressed(out / 'metadata.npz', radio=radio, errors=toas.get_errors().to_value(u.s), groups=np.array([f.get('group','') for f in toas.table['flags']]), mjd=toas.get_mjds().value)
    np.savez_compressed(out / 'observed.npz', residuals=residuals)
    policy = {**POLICY, 'maximum_period_days': min(2000., float(np.ptp(times))/2), 'seed': POLICY['seed'] + row['batch_index']}
    receipt = {'target': target, 'source': source.upper(), 'toas': len(times), 'epochs': len(np.unique(np.floor(times))), 'span_days': float(np.ptp(times)), 'phase_arc_cycles': arc,
               'timing_names': names, 'released_free_parameters': released_free, 'empty_columns_removed': dropped,
               'model_components': list(model.components), 'band_noise': bands, 'policy': policy,
               'noise_model': 'Fixed released white and available correlated noise; InPTA DMX release provides EFAC only',
               'dispersion': 'Released dispersion model projected; InPTA data-derived DMX values also projected as nuisance',
               'astrometry': 'Present position, proper motion and parallax columns projected',
               'noise_limit': 'Conditional on fixed source noise; missing hyperparameter uncertainty and absent terms are not calibrated by this search',
               'clock_hashes': clock_hashes, 'network_attempts': 0, 'selection_sha256': cal.digest(data / 'selection.json'),
               'preparation_implementation': implementation,
               'normalized_tim_sha256': cal.digest(tim),
               'code_sha256': cal.digest(__file__), 'shared_adapter_sha256': cal.digest(mpta.__file__), 'observed_sha256': cal.digest(out / 'observed.npz')}
    profile = cal.create_profile(root / 'profile', target, {'times':times,'covariance':covariance,'design':design,'baseline_design':baseline}, {'timing_model': 'Released single-pulsar model, projected timing and dispersion nuisance', 'noise_model': receipt['noise_model'], 'preparation': receipt}, policy, reference_epoch=float(model.PEPOCH.value))
    cal.write(out / 'receipt.json', receipt)
    print('PREPARED', source, target, str(profile), flush=True)


def calibrate(source, target):
    from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner
    root = ROOT / source / target
    receipt = cal.read(root / 'prepared/receipt.json')
    assert preparation_matches(root, receipt)
    result = cal.run(root / 'profile/profile.json', ROOT / source / 'calibration-cache')
    profile, arrays = cal.load_profile(root / 'profile/profile.json')
    scanner = prepare_covariance_gls_scanner(arrays['covariance'], arrays['design'], arrays['times'], np.array([.01]), profile['reference_epoch_mjd_tdb'])
    template = mpta.circular_template(arrays['times'], profile['reference_epoch_mjd_tdb'], .01, len(arrays['covariance']))
    injected = template[:,0]*.001 + arrays['baseline_design'] @ np.full(arrays['baseline_design'].shape[1], 1e-4)
    projected = scanner.whiten_and_project(injected)
    fitted = scanner.template_gram_pseudoinverse[0] @ (scanner.projected_whitened_templates[:,0].T @ projected)
    np.testing.assert_allclose(fitted, [.001,0], atol=1e-10, rtol=1e-7)
    cal.write(root / 'calibrated.json', {'target': target, 'calibration': result, 'profile_sha256': cal.digest(root / 'profile/profile.json'), 'preparation_sha256': cal.digest(root / 'prepared/receipt.json'), 'noiseless_injected_amplitude_us':1000, 'recovered_amplitude_us':float(np.linalg.norm(fitted)*1e6)})
    print('CALIBRATED', source, target, result['threshold'], flush=True)


def freeze():
    # Establish complete campaign readiness before writing any source freeze.
    for source in SOURCES:
        for target in cal.read(ROOT/source/'selection.json')['selected']:
            root = ROOT/source/target
            row = cal.read(root/'calibrated.json')
            assert preparation_matches(root, cal.read(root/'prepared/receipt.json'))
            assert row['profile_sha256'] == cal.digest(root/'profile/profile.json')
            assert row['preparation_sha256'] == cal.digest(root/'prepared/receipt.json')
            assert not (root/'run01').exists()
        if (ROOT/source/'execution-freeze.json').exists(): raise FileExistsError('Source already frozen')
    for source in SOURCES:
        data = ROOT / source
        selection = cal.read(data / 'selection.json')
        rows = [cal.read(data / t / 'calibrated.json') for t in selection['selected']]
        for r in rows:
            root = data / r['target']
            receipt = cal.read(root / 'prepared/receipt.json')
            assert preparation_matches(root, receipt)
            assert receipt['toas'] >= 40 and receipt['epochs'] >= 40 and receipt['span_days'] >= 1200
            assert receipt['policy']['search_count'] == 18
            assert receipt['policy']['false_alarm_probability'] == .01
            assert receipt['network_attempts'] == 0
            for path, sha in receipt['clock_hashes'].items(): assert cal.digest(path) == sha
            assert r['profile_sha256'] == cal.digest(root / 'profile/profile.json')
            assert r['preparation_sha256'] == cal.digest(root / 'prepared/receipt.json')
            assert not (root / 'run01').exists()
        prep = {'status':'PREPARED','created_utc':mpta.now(),'results':rows,'selection_sha256':cal.digest(data / 'selection.json'),'observed_search_executed':False}
        cal.write(data / 'preparation.json', prep)
        path = data / 'execution-freeze.json'
        if path.exists(): raise FileExistsError('Source already frozen')
        cal.write(path, {'created_utc':mpta.now(),'selection_sha256':prep['selection_sha256'], 'code_sha256':cal.digest(mpta.__file__),
            'campaign_adapter_sha256':cal.digest(__file__),'implementation':cal.implementation(),
            'preparation_sha256':cal.digest(data / 'preparation.json'),
            'targets':{r['target']:{'profile_sha256':r['profile_sha256'],'observed_sha256':cal.digest(data/r['target']/'prepared/observed.npz'),'calibration':r['calibration']} for r in rows},
            'search':'One 30 to min(2000, span/2) day circular grid per dataset; no seeds from observed peaks',
            'batch_alpha_conditional':.01,'max_targets':18,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()})
    cal.write(ROOT / 'campaign-freeze.json', {'created_utc':mpta.now(), 'datasets':cal.read(ROOT/'intake.json')['datasets'], 'intake_sha256':cal.digest(ROOT/'intake.json'), 'source_freezes':{s:cal.digest(ROOT/s/'execution-freeze.json') for s in SOURCES},'policy':POLICY})
    print('CAMPAIGN FROZEN:', len(cal.read(ROOT/'intake.json')['datasets']), 'datasets; allowance for 18', flush=True)


def run(source, target):
    data = ROOT / source
    campaign = cal.read(ROOT / 'campaign-freeze.json')
    frozen = cal.read(data / 'execution-freeze.json')
    assert campaign['source_freezes'][source] == cal.digest(data / 'execution-freeze.json')
    assert frozen['campaign_adapter_sha256'] == cal.digest(__file__)
    assert frozen['preparation_sha256'] == cal.digest(data / 'preparation.json')
    mpta.run(data, target)
    evidence = mpta.REPO / 'results/research' / ROOT.name
    evidence.mkdir(exist_ok=True, parents=True)
    shutil.copy2(data / target / 'run01/result.json', evidence / (source + '-' + target + '-result.json'))


def main():
    global ROOT
    p=argparse.ArgumentParser();p.add_argument('action',choices=['inventory','prepare','calibrate','freeze','run']);p.add_argument('--source',choices=SOURCES);p.add_argument('--target');p.add_argument('--data',type=Path);a=p.parse_args()
    if a.data is not None: ROOT = a.data.resolve()
    if a.action=='inventory': inventory()
    elif a.action=='freeze': freeze()
    else: globals()[a.action](a.source,a.target)
if __name__=='__main__': main()
