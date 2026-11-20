"""Bounded native ELL1 nonlinear compatibility prototype, never a planet search."""
import argparse
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path

import astropy.units as u
import numpy as np
from scipy.linalg import cholesky, solve_triangular, eigh
from scipy.optimize import least_squares
from scipy.stats import chi2
import binary_wideband as binary
import binary_noise_coverage as coverage
import target_calibration as cal
from pulsar_pilot.spin_phase import bind_precise_spin_phase
from pulsar_pilot.pilot2_offline_resources import NetworkDeny


class NativeOrbit:
    """Exact native delay in physical mass/cos(i); no orbital derivative projection."""
    def __init__(self, model, toas, parameters, extent):
        self.model, self.toas, self.parameters = model, toas, parameters
        self.values = {p: np.longdouble(getattr(model, p).value) for p in parameters}
        self.scales = {p: np.longdouble(getattr(model, p).uncertainty_value) for p in parameters}
        if any(s <= 0 for s in self.scales.values()):
            raise ValueError('Missing orbital uncertainty')
        s = self.values['SINI']
        self.cos0 = np.sqrt(1-s*s)
        self.cos_scale = s/self.cos0*self.scales['SINI']
        self.lower, self.upper = np.full(len(parameters), -extent), np.full(len(parameters), extent)
        k = parameters.index('SINI')
        slo, shi = max(0., s-extent*self.scales['SINI']), min(1., s+extent*self.scales['SINI'])
        self.lower[k] = (np.sqrt(1-shi*shi)-self.cos0)/self.cos_scale
        self.upper[k] = (np.sqrt(1-slo*slo)-self.cos0)/self.cos_scale
        if self.values['M2']-extent*self.scales['M2'] <= 0:
            raise ValueError('Companion mass domain must remain positive')
        self.base_delay = np.asarray(model.delay(toas).to_value(u.s), np.longdouble)

    def set(self, x):
        if np.any(x < self.lower-1e-10) or np.any(x > self.upper+1e-10):
            raise ValueError('Outside declared orbital domain')
        for p, value in zip(self.parameters, x):
            if p == 'SINI':
                c = self.cos0+np.longdouble(value)*self.cos_scale
                if not 0 < c < 1:
                    raise ValueError('Unphysical inclination')
                getattr(self.model, p).value = np.sqrt(1-c*c)
            else:
                getattr(self.model, p).value = self.values[p]+np.longdouble(value)*self.scales[p]

    def delay(self, x):
        self.set(x)
        wave = np.zeros(2*self.toas.ntoas)
        wave[:self.toas.ntoas] = self.model.delay(self.toas).to_value(u.s)-self.base_delay
        return wave

    def jacobian(self, x):
        self.set(x)
        columns = []
        for p in self.parameters:
            scale = self.scales[p]
            if p == 'SINI':
                c = self.cos0+np.longdouble(x[self.parameters.index(p)])*self.cos_scale
                scale = -c/np.sqrt(1-c*c)*self.cos_scale
            v = np.zeros(2*self.toas.ntoas)
            v[:self.toas.ntoas] = self.model.d_delay_d_param(self.toas, p).to_value(u.s/getattr(self.model, p).units)*scale
            columns.append(v)
        return np.column_stack(columns)


class ProjectedFit:
    """Profile linear nuisance coefficients at every native orbital evaluation."""
    def __init__(self, covariance, design, data, orbit):
        self.L = cholesky(covariance, lower=True)
        self.D, self.y, self.orbit = design, data, orbit
        self.norms = np.linalg.norm(design, axis=0)
        self.W = self.white(design/self.norms)
        self.Q, self.R = np.linalg.qr(self.W, mode='reduced')
        if np.linalg.matrix_rank(self.W) != design.shape[1]:
            raise ValueError('Linear nuisance rank lost')
        self.log_measure = float(2*np.log(np.diag(self.L)).sum()+2*np.log(abs(np.diag(self.R))).sum())

    def white(self, v):
        return solve_triangular(self.L, v, lower=True)

    def project(self, v):
        w = self.white(v)
        return w-self.Q@(self.Q.T@w)

    def residual(self, x):
        return self.project(self.y-self.orbit.delay(x))

    def jacobian(self, x):
        return -self.project(self.orbit.jacobian(x))

    def coefficients(self, x):
        return np.linalg.lstsq(self.W, self.white(self.y-self.orbit.delay(x)), rcond=1e-12)[0]/self.norms


def execute(args, out, scope):
    import pint.logging
    from pint.models import get_model_and_toas
    from pint.fitter import WidebandTOAFitter
    from pint.residuals import WidebandTOAResiduals
    target = scope['target']
    if target != 'J1857+0943' or scope['orbital_parameters'] != ['PB','A1','TASC','EPS1','EPS2','M2','SINI']:
        raise ValueError('Prototype supports the declared J1857 seven-parameter case only')
    source = args.data/scope['source_batch']
    selection = cal.read(source/'selection.json')
    row, = [r for r in selection['rows'] if r['target'] == target]
    par, tim = [source/target/'original'/f'{target}.{s}' for s in ['par','tim']]
    for suffix, p in [('par',par), ('tim',tim)]:
        if cal.digest(p) != row[suffix+'_sha256']:
            raise ValueError('Original input binding differs')
    pint.logging.setup(level='WARNING', sink=out/'pint.log', removeprior=True)
    with ExitStack() as stack:
        deny = stack.enter_context(NetworkDeny())
        local = stack.enter_context(binary.BinaryResources(source)); local.bind_science_resources()
        model, toas = get_model_and_toas(par,tim,ephem='DE440',include_bipm=True,bipm_version='BIPM2019',planets=True,usepickle=False,limits='error')
        bind_precise_spin_phase(model); binary.bind_ell1_derivative(model)
        minimum = max(30., 10*float(model.PB.value))
        band = coverage.configure(model,toas,minimum)
        if model.BINARY.value != 'ELL1':
            raise ValueError('Native ELL1 model required')
        original = deepcopy(model)
        fitter = WidebandTOAFitter(toas,model)
        matrix = fitter.get_designmatrix(); names = matrix.get_label_names(axis=1); D = matrix.matrix
        if not set(scope['orbital_parameters']).issubset(names):
            raise ValueError('Orbital terms missing from native timing design')
        keep = [i for i,p in enumerate(names) if p not in scope['orbital_parameters']]
        nuisance_names = [names[i] for i in keep]; N = D[:,keep]
        y = np.asarray(WidebandTOAResiduals(toas,model).calc_wideband_resids(),float)
        if len(y) != 2*toas.ntoas or np.ptp(y[:toas.ntoas])*float(model.F0.value) >= .5:
            raise ValueError('Wideband layout or phase connection mismatch')
        orbit = NativeOrbit(model,toas,scope['orbital_parameters'],scope['parameter_domain_published_sigma'])
        times = np.asarray(toas.table['tdbld'].data,float)
        rows = []; numerical_holds = []
        rnamp, rnidx = model.RNAMP.value, model.RNIDX.value
        for scenario in scope['noise_scenarios']:
            model.RNAMP.value = rnamp*scenario['amplitude_factor']
            model.RNIDX.value = rnidx-scenario['gamma_offset']
            C = WidebandTOAFitter(toas,model).get_noise_covariancematrix().matrix
            fit = ProjectedFit(C,N,y,orbit)
            solutions = []
            for start in scope['optimizer_starts']:
                x = np.zeros(7); x[-1] = start
                sol = least_squares(fit.residual,x,jac=fit.jacobian,bounds=(orbit.lower,orbit.upper),
                                    max_nfev=scope['maximum_function_evaluations'],ftol=1e-10,xtol=1e-10,gtol=1e-8)
                solutions.append(sol)
            sol = min(solutions,key=lambda s: np.dot(s.fun,s.fun))
            wave = orbit.delay(sol.x); beta = fit.coefficients(sol.x)
            residual = fit.residual(sol.x); J = orbit.jacobian(sol.x)
            # Check analytic native derivatives at the fitted point against actual native delays.
            derivative_errors = {}
            for j,p in enumerate(orbit.parameters):
                h = min(.01, (sol.x[j]-orbit.lower[j])/2, (orbit.upper[j]-sol.x[j])/2)
                if h < 1e-5:
                    derivative_errors[p] = None
                    continue
                step = np.zeros(7); step[j] = h
                numeric = (orbit.delay(sol.x+step)-orbit.delay(sol.x-step))/(2*h)
                derivative_errors[p] = float(np.linalg.norm(numeric-J[:,j])/np.linalg.norm(J[:,j]))
            orbit.set(sol.x)
            full = deepcopy(model)
            for p,b in zip(nuisance_names,beta):
                if p in full.params:
                    getattr(full,p).value += np.longdouble(b)
            native = np.asarray(WidebandTOAResiduals(toas,full).calc_wideband_resids(),float)
            predicted = y-wave-N@beta
            # Free phase/DM offsets have no native model parameter; project them before comparison.
            error = fit.project(native-predicted)
            native_remainder = float(np.max(abs(error)))
            independent = fit.white(y-wave-N@beta)
            likelihood_error = float(abs(independent@independent-residual@residual))
            joint = np.column_stack([fit.W,fit.white(J)])
            norms = np.linalg.norm(joint,axis=0); normalized = joint/norms
            q,_ = np.linalg.qr(normalized,mode='reduced')
            rank = int(np.linalg.matrix_rank(normalized)); dof = len(y)-rank
            phase = np.asarray(model.components['BinaryELL1'].binary_instance.Phi().to_value(u.rad),float)
            H = np.zeros((len(y),14))
            for k in range(1,8):
                H[:toas.ntoas,2*k-2] = np.sin(k*phase); H[:toas.ntoas,2*k-1] = np.cos(k*phase)
            hh = fit.white(H); hh -= q@(q.T@hh)
            uh,sv,_ = np.linalg.svd(hh,full_matrices=False); hrank = int(sum(sv>sv[0]*1e-10))
            harmonic_stat = float(np.sum((uh[:,:hrank].T@residual)**2))
            information = []
            baseline = N[:,[j for j,p in enumerate(nuisance_names) if p.lower().startswith(('offset','dm','jump'))]]
            wb = fit.white(baseline); qb,_ = np.linalg.qr(wb,mode='reduced')
            for period in scope['synthetic_periods_days']:
                ph = 2*np.pi*(times-float(model.PEPOCH.value))/period
                T = np.zeros((len(y),2)); T[:toas.ntoas] = np.column_stack([np.sin(ph),np.cos(ph)])
                wt = fit.white(T); base = wt-qb@(qb.T@wt); projected = wt-q@(q.T@wt)
                fraction = float(min(eigh(projected.T@projected,base.T@base,eigvals_only=True)))
                information.append({'period_days':period,'worst_phase_information_retained':fraction})
            shifts = {p:float((getattr(model,p).value-orbit.values[p])/orbit.scales[p]) for p in orbit.parameters}
            stat = float(residual@residual)
            r = {**scenario,'chi2':stat,'dof':dof,'reduced_chi2':stat/dof,'conditional_chi2_tail':float(chi2.sf(stat,dof)),
                 'profile_objective_with_linear_nuisance_measure':stat+fit.log_measure,
                 'optimizer_success':all(s.success for s in solutions),'function_evaluations':[s.nfev for s in solutions],
                 'multistart_chi2_difference':float(abs(np.dot(solutions[0].fun,solutions[0].fun)-np.dot(solutions[1].fun,solutions[1].fun))),
                 'orbital_parameters':{p:float(getattr(model,p).value) for p in orbit.parameters},'orbital_shifts_published_sigma':shifts,
                 'on_declared_orbit_boundary':bool(np.any(np.minimum(sol.x-orbit.lower,orbit.upper-sol.x)<.01)),
                 'joint_rank':rank,'joint_columns':joint.shape[1],'normalized_joint_condition':float(np.linalg.cond(normalized)),
                 'native_derivative_relative_errors':derivative_errors,'native_nuisance_remainder_whitened':native_remainder,
                 'independent_chi2_absolute_error':likelihood_error,'orbital_harmonic_delta_chi2':harmonic_stat,
                 'orbital_harmonic_rank':hrank,'conditional_orbital_harmonic_tail':float(chi2.sf(harmonic_stat,hrank)),
                 'synthetic_template_information':information}
            rows.append(r)
            np.savez_compressed(out/(scenario['label']+'.npz'),times=times,covariance=C,nuisance_design=N,
                                residuals=y,orbital_solution=sol.x,nuisance_coefficients=beta,native_orbital_jacobian=J)
            for label,bad in [('OPTIMIZER',not r['optimizer_success']),('MULTISTART',r['multistart_chi2_difference']>scope['maximum_multistart_chi2_difference']),
                ('NATIVE_NUISANCE',native_remainder>scope['maximum_native_nuisance_remainder_sigma']),
                ('DERIVATIVE',any(v is not None and v>scope['maximum_derivative_relative_error'] for v in derivative_errors.values())),
                ('RANK',rank!=joint.shape[1]),('INDEPENDENT_LIKELIHOOD',likelihood_error>1e-6)]:
                if bad:numerical_holds.append(scenario['label'].upper()+'_'+label)
            print(json.dumps({'scenario':scenario['label'],'chi2':stat,'native_remainder':native_remainder,
                              'boundary':r['on_declared_orbit_boundary'],'numerical_holds':numerical_holds}),flush=True)
        if deny.attempts:raise RuntimeError('Scientific network access attempted')
        (out/'reference-model.par').write_text(original.as_parfile())
    ref = rows[0]; best = min(rows,key=lambda r:r['profile_objective_with_linear_nuisance_measure'])
    delta = ref['profile_objective_with_linear_nuisance_measure']-best['profile_objective_with_linear_nuisance_measure']
    holds = list(numerical_holds)
    if ref['on_declared_orbit_boundary']:holds.append('RELEASED_NOISE_ORBIT_BOUNDARY')
    if ref['conditional_chi2_tail']<scope['adequacy_tail_cutoff']:holds.append('RELEASED_NOISE_RESIDUAL_SCATTER')
    if ref['conditional_orbital_harmonic_tail']<scope['adequacy_tail_cutoff']:holds.append('RELEASED_NOISE_ORBITAL_STRUCTURE')
    if delta>scope['noise_objective_warning_delta']:holds.append('NOISE_ALTERNATIVE_REQUIRES_RESOLUTION')
    if min(v['worst_phase_information_retained'] for v in ref['synthetic_template_information'])<scope['minimum_template_information_fraction']:
        holds.append('TEMPLATE_INFORMATION_LOSS')
    result={'target':target,'status':'NONLINEAR_PROTOTYPE_COMPATIBILITY_HOLD' if holds else 'CONDITIONAL_NONLINEAR_PROTOTYPE_COMPATIBLE',
        'holds':holds,'toas':toas.ntoas,'paired_dm_toas':toas.ntoas,'linear_nuisance_columns':N.shape[1],
        'timing_names':names,'nonlinear_parameters':orbit.parameters,'inclination_coordinate':'cos(i)',
        'domain':'Released values plus/minus three published standard errors, with physical mass/inclination bounds; numerical domain, not an independent prior or posterior',
        'prospective_period_bounds_days':[minimum,min(2000.,float(np.ptp(times))/2)],'noise_coverage':band,'scenarios':rows,
        'best_diagnostic_noise':best['label'],'noise_objective_improvement':delta,'scope_sha256':cal.digest(args.scope),
        'inputs':{'par_sha256':cal.digest(par),'tim_sha256':cal.digest(tim),'selection_sha256':cal.digest(source/'selection.json'),
                  'prior_failure_sha256':cal.digest(source/target/'prepared/failure.json')},
        'code':{str(Path(p).resolve().relative_to(binary.ROOT)):cal.digest(p) for p in [__file__,binary.__file__,coverage.__file__]},
        'calibration_executed':False,'observed_outer_period_scan_executed':False,'operational_profile_created':False,
        'limits':'Finite-domain native orbit profiling with local linear nuisance treatment and five fixed-noise diagnostics. Conditional tails and local Fisher information are adequacy diagnostics, not global significance, posterior uncertainty, detection probability or general qualification. Any future calibration must use the same nonlinear/noise statistic in nulls, injections and observed execution.'}
    cal.write(out/'receipt.json',result)
    print(json.dumps({'status':result['status'],'holds':holds,'best_noise':best['label'],'noise_delta':delta}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--scope',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    scope=cal.read(args.scope);cal.write(args.output/'scope.json',scope)
    try:execute(args,args.output,scope)
    except Exception as error:
        cal.write(args.output/'failure.json',{'status':'PROTOTYPE_EXECUTION_FAILED','error':str(error),'script_sha256':cal.digest(__file__)})
        raise


if __name__=='__main__':main()
