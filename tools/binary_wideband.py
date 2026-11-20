"""Bounded NG15 ELL1 / H3-only ELL1H white-dwarf binary pilot; additional circular outer companions."""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import json
import re
from pathlib import Path
import tarfile
from types import MethodType

import astropy.units as u
import numpy as np
from scipy.linalg import cholesky, solve_triangular
import mpta_batch as observed
import target_calibration as cal
import binary_noise_coverage as noise_coverage
from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner
from pulsar_pilot.pilot2_offline_resources import LocalPintRepository, NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase
from sensitivity_atlas import workbook_rows

ROOT=Path(__file__).resolve().parents[1]
POLICY={**cal.DEFAULT_POLICY,'minimum_period_days':30.,'maximum_period_days':2000.,'search_count':3,'seed':2026092900}
SHAPIRO_MODES={'fitted','omitted_in_release','fixed_from_literature','h3_only','ell1h_omitted_in_release'}


def check_shapiro_mode(fields, mode, model=None):
    """Omission is an explicit released-model choice, never deletion of a fit."""
    if mode not in SHAPIRO_MODES:raise ValueError('Unknown Shapiro mode: '+str(mode))
    if fields:
        expected='ELL1H' if mode in {'h3_only','ell1h_omitted_in_release'} else 'ELL1'
        if fields.get('BINARY')!=[expected]:raise ValueError('Shapiro mode requires released '+expected)
    if mode=='h3_only' and fields:
        if {'M2','SINI','H4','STIGMA','VARSIGMA'}.intersection(fields):
            raise ValueError('H3-only mode cannot discard other Shapiro terms')
        if fields.get('NHARMS')!=['3'] or 'H3' not in fields:
            raise ValueError('H3-only mode requires explicit H3 and NHARMS 3')
        if model is not None:
            component=model.components['BinaryELL1H']
            if (model.H3.value is None or not np.isfinite(model.H3.value)
                    or 'H3' not in model.free_params or model.NHARMS.value!=3
                    or model.H4.value is not None or model.STIGMA.value is not None
                    or component.binary_instance.fit_params!=['H3']):
                raise ValueError('Imported model is not a fitted H3-only three-harmonic model')
    if mode=='ell1h_omitted_in_release' and fields:
        if {'M2','SINI','H3','H4','STIGMA','VARSIGMA'}.intersection(fields):
            raise ValueError('ELL1H omitted mode cannot discard supplied Shapiro terms')
        if fields.get('NHARMS')!=['7']:
            raise ValueError('Bounded omitted ELL1H mode requires released NHARMS 7')
        if model is not None:
            component=model.components['BinaryELL1H']
            if (any(p in model.free_params for p in ['H3','H4','STIGMA'])
                    or model.H3.value not in (None,0) or model.H4.value is not None
                    or model.STIGMA.value is not None or model.NHARMS.value!=7
                    or component.binary_instance.H3.to_value(u.s)!=0):
                raise ValueError('Imported ELL1H does not preserve zero omitted Shapiro delay')
    if mode in {'omitted_in_release','fixed_from_literature'}:
        if {'M2','SINI','H3','H4','STIGMA','VARSIGMA'}.intersection(fields):
            raise ValueError('Omitted mode requires original PAR without Shapiro terms')
        if model is not None:
            if any(p in model.free_params for p in ['M2','SINI']):
                raise ValueError('Omitted Shapiro terms unexpectedly free')
            if any(getattr(model,p).value not in (None,0) for p in ['M2','SINI']):
                raise ValueError('Imported model has nonzero Shapiro terms')


def add_fixed_shapiro(model, specification):
    """Restore physical first/second orbital harmonics before adding fixed delay."""
    from pint import Tsun
    mass=float(specification['mass_solar']);inclination=float(specification['inclination_degrees'])
    if not (0<mass<1.5 and 0<inclination<90):raise ValueError('Invalid fixed Shapiro constraints')
    s=np.sin(np.deg2rad(inclination));zeta=s/(1+np.sqrt(1-s*s))
    r=Tsun.to_value(u.s)*mass
    old={p:float(getattr(model,p).value) for p in ['A1','EPS1','EPS2']}
    x=old['A1']-4*r*zeta
    model.A1.value=x
    model.EPS1.value=(old['A1']*old['EPS1']-4*r*zeta*zeta)/x
    model.EPS2.value=old['A1']*old['EPS2']/x
    model.M2.value=mass;model.M2.frozen=True
    model.SINI.value=s;model.SINI.frozen=True
    return {'mass_solar':mass,'inclination_degrees':inclination,'sini':float(s),
        'harmonic_recentring':{p:{'released':old[p],'physical_reference':float(getattr(model,p).value)} for p in old},
        'scope':'Fixed optical central values; first two Shapiro harmonics removed from released apparent orbit; original orbital uncertainties retained'}


def verify_preparation(data,target,require_adequacy=False):
    """Accept an unchanged, explicitly hash-adopted preparation without rerunning it."""
    root=data/target;selection=cal.read(data/'selection.json')
    receipt=cal.read(root/'prepared/receipt.json')
    if receipt['status']!='BINARY_TIMING_NOISE_COMPATIBLE':raise ValueError('Preparation is not compatible')
    profile,_=cal.load_profile(root/'profile/profile.json')
    if profile['provenance']['preparation_receipt_sha256']!=cal.digest(root/'prepared/receipt.json'):raise ValueError('Receipt differs')
    if receipt['adapter_sha256']!=cal.digest(__file__):
        reuse=selection.get('reused_preparations',{}).get(target,{})
        actual={'profile_sha256':cal.digest(root/'profile/profile.json'),'receipt_sha256':cal.digest(root/'prepared/receipt.json'),
                'adapter_sha256':receipt['adapter_sha256'],'selection_sha256':receipt['selection_sha256']}
        if reuse!=actual:raise ValueError('Unbound previous preparation')
    if receipt['observed_sha256']!=cal.digest(root/'prepared/observed.npz'):raise ValueError('Prepared observations differ')
    if profile['policy']['search_count']!=selection['policy']['search_count']:raise ValueError('Reused search allowance differs')
    if selection.get('noise_coverage_rule'):
        coverage=receipt.get('noise_coverage',{})
        if coverage.get('rule')!=selection['noise_coverage_rule']:raise ValueError('Noise coverage check missing')
        if receipt.get('noise_coverage_code_sha256')!=cal.digest(noise_coverage.__file__):raise ValueError('Noise coverage implementation differs')
    if require_adequacy and receipt.get('shapiro_mode')=='ell1h_omitted_in_release':
        report=cal.read(data/'preparation-diagnostics.json')
        expected={'selection':selection['requested_selection_sha256'],
                  'profile':cal.digest(root/'profile/profile.json'),
                  'receipt':cal.digest(root/'prepared/receipt.json'),
                  'observed':receipt['observed_sha256'],'phase':receipt['orbital_phase_sha256'],
                  'script':cal.digest(ROOT/'tools/j1802_preparation_diagnostics.py'),
                  'joint_noise':cal.digest(ROOT/'tools/joint_noise.py'),
                  'mpta_batch':cal.digest(observed.__file__)}
        check_ell1h_adequacy(report,target,expected)
    return receipt


def check_ell1h_adequacy(report,target,expected_bindings):
    """A valid timing interface does not override a recorded model-adequacy hold."""
    if (report.get('target')!=target or report.get('status')!='CONDITIONAL_PREPARATION_COMPATIBLE'
            or report.get('holds')):
        raise ValueError('Omitted ELL1H preparation adequacy remains held')
    if report.get('bindings')!=expected_bindings:
        raise ValueError('Omitted ELL1H adequacy evidence differs')


class BinaryResources(LocalPintRepository):
    """Use the release's UTC(VLA)-to-GPS clock in the existing GPS/BIPM chain."""
    def __init__(self, data):
        super().__init__(observed.RESOURCES,cal.read(observed.RESOURCES/'metadata/resources.json'))
        self.extra=data/'resources'
        self.binding=cal.read(self.extra/'binding.json')
        if self.binding['filename']!='vla2gps.clk' or cal.digest(self.extra/'vla2gps.clk')!=self.binding['sha256']:
            raise ValueError('Released VLA clock binding differs')

    def _bound_find_clock_file(self,name,format,bogus_last_correction=False,url_base=None,clock_dir=None,valid_beyond_ends=False):
        if name=='time_vla.dat' and url_base is None:
            return self._old_find_clock_file(name='vla2gps.clk',format='tempo2',
                bogus_last_correction=False,url_base=None,clock_dir=self.extra,
                valid_beyond_ends=False)
        return super()._bound_find_clock_file(name,format,bogus_last_correction,url_base,clock_dir,valid_beyond_ends)


def shapiro_derivative(binary, parameter):
    """Differentiate -2 r log(1 - s sin(phi)), including d sin(phi)/d phi."""
    phase=binary.Phi();s=binary.SINI;r=binary.TM2();denominator=1-s*np.sin(phase)
    with u.set_enabled_equivalencies(u.dimensionless_angles()):
        return (-2*np.log(denominator)*binary.prtl_der('TM2',parameter)
                +2*r*np.sin(phase)/denominator*binary.prtl_der('SINI',parameter)
                +2*r*s*np.cos(phase)/denominator*binary.prtl_der('Phi',parameter))


def bind_ell1_derivative(model, shapiro_mode='fitted'):
    """Local adapter repair: pinned PINT 1.1.5 omits cos(phi) in this derivative."""
    component,=[c for c in model.components.values() if c.category=='pulsar_system']
    if component.binary_model_name=='ELL1H' and shapiro_mode in {'h3_only','ell1h_omitted_in_release'}:
        # Retain PINT's orthometric derivative; the ELL1 M2/SINI repair is inapplicable.
        return
    if component.binary_model_name!='ELL1':raise ValueError('Unsupported binary derivative branch')
    component.binary_instance.d_delayS_d_par=MethodType(shapiro_derivative,component.binary_instance)


def select(data, archive, inventory, selection_path):
    requested=cal.read(selection_path)
    mode=requested.get('shapiro_mode','fitted')
    check_shapiro_mode({},mode)
    settings=requested.get('target_models',{})
    targets=requested['selected']
    if not targets or len(targets)!=len(set(targets)) or any(not re.fullmatch(r'J\d{4}[+-]\d{4}',t) for t in targets):
        raise ValueError('Selection needs unique canonical J-name targets')
    policy={**POLICY,'search_count':len(targets),'seed':int(requested['seed'])}
    master=ROOT/'outputs/recherche-master-20260908/Project-Recherche-Master.xlsx'
    searched={r[1] for r in workbook_rows(master,'Searches')[1:]}
    if searched.intersection(targets):raise ValueError('Selected target already has a registered search')
    if any(data.glob('*')):raise FileExistsError('Use a new pilot directory')
    data.mkdir(parents=True,exist_ok=True)
    admitted={observed.ALIASES.get(r['target'],r['target']):r for r in cal.read(inventory)}
    if not set(targets).issubset(admitted):raise ValueError('Pinned inventory missing pilot target')
    rows=[]
    with tarfile.open(archive) as t:
        member,=[n for n in t.getnames() if n.endswith('/clock/vla2gps.clk')]
        resources=data/'resources';resources.mkdir()
        (resources/'vla2gps.clk').write_bytes(t.extractfile(member).read())
        cal.write(resources/'binding.json',{'archive_member':member,'filename':'vla2gps.clk',
            'sha256':cal.digest(resources/'vla2gps.clk')})
        for i,target in enumerate(targets):
            row=admitted[target];folder=data/target/'original';folder.mkdir(parents=True)
            for suffix in ['par','tim']:
                content=t.extractfile(row[suffix+'_member']).read()
                p=folder/(target+'.'+suffix);p.write_bytes(content)
                if cal.digest(p)!=row[suffix+'_sha256']:raise ValueError('Pinned input hash mismatch')
            fields={v[0]:v[1:] for line in (folder/(target+'.par')).read_text().splitlines() if (v:=line.split())}
            model_settings=settings.get(target,{})
            target_mode=model_settings.get('shapiro_mode',mode)
            check_shapiro_mode(fields,target_mode)
            if target_mode=='fixed_from_literature' and 'fixed_shapiro' not in model_settings:
                raise ValueError('Fixed Shapiro mode needs target_models[target].fixed_shapiro')
            rows.append({**row,'target':target,'selected':True,'batch_index':i,'binary_period_days':float(fields['PB'][0]),
                         'shapiro_mode':target_mode,**({'fixed_shapiro':model_settings['fixed_shapiro']} if target_mode=='fixed_from_literature' else {}),
                         'binary_model':fields['BINARY'][0],
                         'selection_basis':'Published white-dwarf companion; supported released binary model; long coverage; no observed periodogram inspected'})
    cal.write(data/'selection.json',{'created_utc':observed.now(),'selected':targets,'rows':rows,
        'dataset':'NANOGrav15 v2.1.0 wideband; supported white-dwarf binaries','policy':policy,
        'shapiro_mode':mode,'noise_coverage_rule':noise_coverage.RULE,'requested_selection_sha256':cal.digest(selection_path),
        'archive_sha256':cal.digest(archive),'intake_inventory_sha256':cal.digest(inventory),
        'master_workbook_sha256':cal.digest(master),'observed_periodograms_inspected':False,
        'minimum_period_rule':'max(30 days, 10 inner binary periods)','maximum_period_rule':'min(2000 days, half observation span)',
        'references':requested['references']})
    print('SELECTED '+', '.join(targets),flush=True)


def binary_checks(model,toas,design,names,covariance,residuals,shapiro_mode='fitted'):
    component,=[c for c in model.components.values() if c.category=='pulsar_system']
    expected='ELL1H' if shapiro_mode in {'h3_only','ell1h_omitted_in_release'} else 'ELL1'
    if component.binary_model_name!=expected:raise ValueError('Unexpected binary component')
    params=[p for p in component.params if p in model.free_params]
    if shapiro_mode not in SHAPIRO_MODES:raise ValueError('Unknown Shapiro mode')
    required={'PB','A1','TASC','EPS1','EPS2'}
    if shapiro_mode=='fitted':required.update(['M2','SINI'])
    if shapiro_mode=='h3_only':required.add('H3')
    if not required.issubset(params):raise ValueError('Core orbital uncertainty columns are not all free')
    if not set(params).issubset(names):raise ValueError('Binary parameters missing from joint design')
    if len(residuals)!=2*toas.ntoas:raise ValueError('Unexpected TOA/DM layout')
    sigma=np.sqrt(np.diag(covariance)[:toas.ntoas])
    base=np.asarray(model.delay(toas).to_value(u.s),np.longdouble)
    checks={}
    for name in params:
        parameter=getattr(model,name);value=parameter.value
        uncertainty=parameter.uncertainty_value
        if uncertainty is None or uncertainty<=0:raise ValueError('Released binary uncertainty missing: '+name)
        step=np.longdouble(uncertainty)*3
        # Period/epoch uncertainties can be tiny: sub-sigma steps lose the delay
        # difference to floating-point cancellation. SINI needs a smaller step
        # because Shapiro delay is curved near edge-on inclination.
        derivative_step=np.longdouble(uncertainty)*(.03 if name=='SINI' else 1.)
        analytic=np.asarray(model.d_delay_d_param(toas,name).to_value(u.s/parameter.units),np.longdouble)
        try:
            parameter.value=value+derivative_step;dplus=np.asarray(model.delay(toas).to_value(u.s),np.longdouble)
            actual_plus=np.longdouble(parameter.value)
            parameter.value=value-derivative_step;dminus=np.asarray(model.delay(toas).to_value(u.s),np.longdouble)
            actual_minus=np.longdouble(parameter.value)
            parameter.value=value+step;plus=np.asarray(model.delay(toas).to_value(u.s),np.longdouble)
            parameter.value=value-step;minus=np.asarray(model.delay(toas).to_value(u.s),np.longdouble)
        finally:parameter.value=value
        numeric=(dplus-dminus)/(actual_plus-actual_minus)
        relative=float(np.linalg.norm(numeric-analytic)/np.linalg.norm(analytic))
        nonlinearity=float(max(np.max(abs(plus-base-analytic*step)/sigma),np.max(abs(minus-base+analytic*step)/sigma)))
        checks[name]={'step_in_parameter_units':float(step),'relative_derivative_error':relative,'maximum_nonlinearity_in_TOA_sigma':nonlinearity}
        if relative>1e-3 or nonlinearity>.1:raise ValueError('Binary derivative/local-linearity mismatch: '+name+' '+json.dumps(checks[name]))
    L=cholesky(covariance,lower=True);W=solve_triangular(L,design,lower=True);norm=np.linalg.norm(W,axis=0)
    normalized=W/norm;rank=int(np.linalg.matrix_rank(normalized))
    if rank!=design.shape[1]:raise ValueError('Joint timing/binary design is rank deficient')
    y=solve_triangular(L,residuals,lower=True);beta=np.linalg.lstsq(normalized,y,rcond=1e-12)[0]/norm
    scanner=prepare_covariance_gls_scanner(covariance,design,np.asarray(toas.table['tdbld'].data,float),np.array([1/100.]),float(model.PEPOCH.value))
    projected=scanner.whiten_and_project(residuals)
    independent=y-W@beta
    chi2_error=float(abs(projected@projected-independent@independent)/max(1.,independent@independent))
    if chi2_error>1e-8:raise ValueError('Independent null likelihood mismatch')
    shifts={p:float(abs(beta[names.index(p)])/getattr(model,p).uncertainty_value) for p in params}
    if max(shifts.values())>3:raise ValueError('Released orbit requires a shift outside checked 3-sigma neighborhood: '+json.dumps(shifts))
    if np.ptp(residuals[:toas.ntoas])*float(model.F0.value)>=.5:raise ValueError('Unresolved pulse-phase connection')
    return {'shapiro_mode':shapiro_mode,'binary_parameters':params,'derivatives':checks,'fitted_binary_shift_in_published_sigma':shifts,
            'independent_null_chi2_relative_error':chi2_error,'null_reduced_chi2':float(projected@projected/(len(residuals)-rank)),
            'design_rank':rank,'design_columns':design.shape[1],'normalized_design_condition':float(np.linalg.cond(normalized))}


def prepare(data,target):
    import pint.logging
    from pint.fitter import WidebandTOAFitter
    from pint.models import get_model_and_toas
    from pint.residuals import WidebandTOAResiduals
    selection=cal.read(data/'selection.json');row=next(r for r in selection['rows'] if r['target']==target)
    root=data/target;out=root/'prepared'
    if (out/'failure.json').exists() and not (root/'profile').exists():
        retained=root/f'attempt{len(list(root.glob("attempt*-failed")))+1:02d}-failed'
        out.rename(retained)
    out.mkdir(exist_ok=False)
    pint.logging.setup(level='INFO',sink=out/'pint.log',removeprior=True)
    par,tim=[root/'original'/(target+'.'+suffix) for suffix in ['par','tim']]
    for suffix,p in [('par',par),('tim',tim)]:
        if cal.digest(p)!=row[suffix+'_sha256']:raise ValueError('Released input changed')
    try:
        with ExitStack() as stack:
            deny=stack.enter_context(NetworkDeny());local=stack.enter_context(BinaryResources(data));local.bind_science_resources()
            model,toas=get_model_and_toas(par,tim,ephem='DE440',include_bipm=True,bipm_version='BIPM2019',planets=True,usepickle=False,limits='error')
            mode=row.get('shapiro_mode',selection.get('shapiro_mode','fitted'))
            fields={v[0]:v[1:] for line in par.read_text().splitlines() if (v:=line.split())}
            check_shapiro_mode(fields,mode,model)
            fixed=add_fixed_shapiro(model,row['fixed_shapiro']) if mode=='fixed_from_literature' else None
            bind_precise_spin_phase(model)
            bind_ell1_derivative(model,mode)
            coverage=noise_coverage.configure(model,toas,max(30.,10*row['binary_period_days']))
            fitter=WidebandTOAFitter(toas,model);matrix=fitter.get_designmatrix();names=matrix.get_label_names(axis=1)
            design=matrix.matrix;covariance=fitter.get_noise_covariancematrix().matrix
            residuals=np.asarray(WidebandTOAResiduals(toas,model).calc_wideband_resids(),float)
            checks=binary_checks(model,toas,design,names,covariance,residuals,mode)
            if mode in {'omitted_in_release','fixed_from_literature','ell1h_omitted_in_release'}:
                model.delay(toas)  # Refresh phase after finite-difference parameter restoration.
                component,=[c for c in model.components.values() if c.category=='pulsar_system']
                phase=np.asarray(component.binary_instance.Phi().to_value(u.rad),float)
                np.savez_compressed(out/'orbital-phase.npz',phase_radians=phase)
            times=np.asarray(toas.table['tdbld'].data,float);baseline=[i for i,n in enumerate(names) if n.lower().startswith(('offset','dm','jump'))]
            if deny.attempts:raise RuntimeError('Scientific network access attempted')
            (out/'timing-model.par').write_text(model.as_parfile())
            epoch=float(model.PEPOCH.value)
        policy={**selection['policy'],'minimum_period_days':max(30.,10*row['binary_period_days']),
                'maximum_period_days':min(2000.,float(np.ptp(times))/2),'seed':selection['policy']['seed']+row['batch_index']}
        arrays={'times':times,'covariance':covariance,'design':design,'baseline_design':design[:,baseline]}
        cal.validate_arrays(arrays)
        np.savez_compressed(out/'observed.npz',residuals=residuals)
        receipt={'status':'BINARY_TIMING_NOISE_COMPATIBLE','target':target,'toas':len(times),'epochs':len(set(np.floor(times).astype(int))),
                 'span_days':float(np.ptp(times)),'binary_period_days':row['binary_period_days'],'policy':policy,'checks':checks,'shapiro_mode':mode,'binary_model':fields['BINARY'][0],
                 'fixed_shapiro':fixed,
                 'noise_coverage':coverage,'noise_coverage_code_sha256':cal.digest(noise_coverage.__file__),
                 'orbital_phase_sha256':cal.digest(out/'orbital-phase.npz') if mode in {'omitted_in_release','fixed_from_literature','ell1h_omitted_in_release'} else None,
                 'timing_names':names,'noise_model':'Fixed NG15 wideband covariance with explicit red-frequency coverage: '+coverage['status']+'; all free binary, timing, DM and instrumental derivatives jointly projected',
                 'observed_sha256':cal.digest(out/'observed.npz'),'selection_sha256':cal.digest(data/'selection.json'),
                 'adapter_sha256':cal.digest(__file__),'resources_sha256':cal.digest(observed.RESOURCES/'metadata/resources.json'),
                 'additional_clock_binding':local.binding}
        cal.write(out/'receipt.json',receipt)
        cal.create_profile(root/'profile',target,arrays,{'timing_model':'Released '+fields['BINARY'][0]+' binary model; local linear marginalization of all free orbital parameters',
            'shapiro_mode':mode,'fixed_shapiro':fixed,'noise_model':receipt['noise_model'],'preparation_receipt_sha256':cal.digest(out/'receipt.json')},policy,reference_epoch=epoch)
        print(json.dumps({'target':target,'status':receipt['status'],'toas':len(times),'orbital_parameters':checks['binary_parameters']}),flush=True)
    except Exception as error:
        cal.write(out/'failure.json',{'target':target,'status':'PREPARATION_FAILED','error':str(error),'adapter_sha256':cal.digest(__file__)})
        raise


def calibrate(data):
    results=[];held=[]
    for target in cal.read(data/'selection.json')['selected']:
        root=data/target
        if (root/'prepared/failure.json').exists():
            held.append(cal.read(root/'prepared/failure.json'));continue
        profile,arrays=cal.load_profile(root/'profile/profile.json')
        receipt=verify_preparation(data,target,require_adequacy=True)
        result=cal.run(root/'profile/profile.json',data/'calibration-cache')
        with np.load(Path(result['path'])/'projection-and-sensitivity.npz') as z:
            indices=np.flatnonzero(z['eligible']);frequencies=z['frequencies'];amplitudes=z['worst_phase_amplitude_us']
        chosen=indices[np.linspace(0,len(indices)-1,3).astype(int)]
        scanner=prepare_covariance_gls_scanner(arrays['covariance'],arrays['design'],arrays['times'],frequencies[chosen],profile['reference_epoch_mjd_tdb'])
        generator=np.random.default_rng(profile['policy']['seed']+10000);recovered=0;trials=0;maximum_error=0.
        for i,grid_index in enumerate(chosen):
            template=observed.circular_template(arrays['times'],profile['reference_epoch_mjd_tdb'],frequencies[grid_index],len(arrays['covariance']))
            for phase in [0,np.pi/2]:
                coefficient=amplitudes[grid_index]*1e-6*np.array([np.cos(phase),np.sin(phase)])
                injected=template@coefficient
                fit=scanner.template_gram_pseudoinverse[i]@(scanner.projected_whitened_templates[:,i].T@scanner.whiten_and_project(injected))
                error=float(np.linalg.norm(fit-coefficient)/np.linalg.norm(coefficient));maximum_error=max(maximum_error,error)
                if error>1e-6:raise ValueError('Injected binary-projected amplitude recovery mismatch')
                for _ in range(16):
                    white=scanner.whiten_and_project(injected)+generator.standard_normal(len(injected))
                    rhs=scanner.projected_whitened_templates[:,i].T@white
                    statistic=rhs@scanner.template_gram_pseudoinverse[i]@rhs
                    recovered+=bool(statistic>result['threshold']);trials+=1
        results.append({'target':target,'calibration':result,'profile_sha256':cal.digest(root/'profile/profile.json'),
                        'noiseless_relative_amplitude_error':maximum_error,'conditional_injection_recovered':recovered,'conditional_injection_trials':trials,
                        'injection_scope':'Three eligible periods, two phases, 16 fixed-noise realizations each; diagnostic, not occurrence completeness'})
        print(json.dumps(results[-1]),flush=True)
    if not results:raise ValueError('No compatible binary preparation; inspect retained holds')
    cal.write(data/'preparation.json',{'status':'PREPARED','results':results,'held':held,'selection_sha256':cal.digest(data/'selection.json'),'observed_search_executed':False})


def freeze(data):
    prep=cal.read(data/'preparation.json')
    policy=cal.read(data/'selection.json')['policy']
    if prep['status']!='PREPARED' or prep['selection_sha256']!=cal.digest(data/'selection.json'):raise ValueError('Preparation differs')
    for row in prep['results']:
        root=data/row['target']
        if (root/'run01').exists():raise FileExistsError('Consumed observed destination')
        if cal.digest(root/'profile/profile.json')!=row['profile_sha256']:raise ValueError('Profile differs')
        receipt=verify_preparation(data,row['target'],require_adequacy=True)
    p=data/'execution-freeze.json'
    if p.exists():raise FileExistsError('Execution already frozen')
    targets={}
    for row in prep['results']:
        target=row['target'];root=data/target
        targets[target]={'profile_sha256':cal.digest(root/'profile/profile.json'),'observed_sha256':cal.digest(root/'prepared/observed.npz'),
                         'calibration':cal.run(root/'profile/profile.json',data/'calibration-cache')}
    f={'created_utc':observed.now(),'selection_sha256':cal.digest(data/'selection.json'),'code_sha256':cal.digest(observed.__file__),
       'implementation':cal.implementation(),'targets':targets,'batch_alpha_conditional':policy['false_alarm_probability'],'max_targets':policy['search_count'],
       'binary_adapter_sha256':cal.digest(__file__),'preparation_sha256':cal.digest(data/'preparation.json'),
       'noise_coverage_code_sha256':cal.digest(noise_coverage.__file__),
       'held_targets':[r['target'] for r in prep['held']],
       'search':'One hierarchical circular outer-companion grid per compatible binary; individual profile bounds; joint free binary/timing projection; fixed released noise; original selection count retained'}
    cal.write(p,f)


def run(data,target):
    f=cal.read(data/'execution-freeze.json')
    if f.get('noise_coverage_code_sha256')!=cal.digest(noise_coverage.__file__):raise ValueError('Frozen noise-coverage implementation changed')
    if f['binary_adapter_sha256']!=cal.digest(__file__) or f['preparation_sha256']!=cal.digest(data/'preparation.json'):raise ValueError('Frozen binary adapter or preparation changed')
    observed.run(data,target)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['select','prepare','calibrate','freeze','run']);p.add_argument('--data',type=Path,required=True)
    p.add_argument('--target');p.add_argument('--archive',type=Path);p.add_argument('--inventory',type=Path);p.add_argument('--selection',type=Path);a=p.parse_args()
    if a.command=='select':
        if not(a.archive and a.inventory and a.selection):p.error('select needs --archive, --inventory and --selection')
        select(a.data.resolve(),a.archive.resolve(),a.inventory.resolve(),a.selection.resolve())
    elif a.command in ['prepare','run']:
        if not a.target:p.error('--target required')
        globals()[a.command](a.data.resolve(),a.target)
    else:globals()[a.command](a.data.resolve())
