"""Pre-search red-noise frequency coverage for the bounded ELL1 adapter."""
import math
import numpy as np
import astropy.units as u

RULE='cover_search_band_v1'


def mode_plan(span_days, minimum_period_days, released_modes, maximum_modes=256):
    """Extend in powers of two; preserve an already sufficient released basis."""
    if not np.isfinite([span_days,minimum_period_days]).all() or min(span_days,minimum_period_days)<=0:
        raise ValueError('Positive finite span and search period required')
    if released_modes<1 or maximum_modes<released_modes:
        raise ValueError('Invalid or unsupported released mode count')
    required=int(math.ceil(span_days/minimum_period_days))
    selected=released_modes if released_modes>=required else 2**int(math.ceil(math.log2(required)))
    if selected>maximum_modes:
        raise ValueError(f'Red-noise coverage needs {selected} modes, above bounded limit {maximum_modes}')
    return {'required_modes':required,'released_modes':released_modes,'selected_modes':selected,
            'shortest_released_period_days':span_days/released_modes,
            'shortest_selected_period_days':span_days/selected,'extended':selected!=released_modes}


def configure(model,toas,minimum_period_days):
    """Keep released spectral parameters; never fit noise to an observed peak."""
    component=model.components.get('PLRedNoise')
    common={'rule':RULE,'minimum_search_period_days':float(minimum_period_days),
            'selection_uses_observed_periodogram':False,'maximum_modes':256}
    if component is None:
        return {**common,'status':'NO_RELEASED_RED_COMPONENT',
                'limitation':'Released white-noise model retained; absence of a fitted red component is not proof of absent correlated noise.'}
    amp,gamma,nlin,nlog,fmin=component.get_plc_vals()
    if nlog not in (None,0) or fmin!=1:
        raise ValueError('Logarithmic red-noise frequency layout needs separate coverage support')
    times=np.asarray(toas.table['tdbld'].data,float)
    span=float(np.ptp(times)) if component.TNREDTSPAN.quantity is None else float(component.TNREDTSPAN.quantity.to_value(u.day))
    plan=mode_plan(span,minimum_period_days,nlin)
    model.TNREDC.value=plan['selected_modes']
    _,frequencies=component.get_time_frequencies(toas)
    shortest=1/(float(np.max(frequencies))*86400)
    if shortest>minimum_period_days*(1+1e-10):raise ValueError('Configured red basis still misses search frequencies')
    return {**common,**plan,'status':'EXTENDED_BEFORE_CALIBRATION' if plan['extended'] else 'RELEASED_BAND_COVERS_SEARCH',
            'red_basis_span_days':span,'spectral_amplitude':float(amp),'spectral_gamma':float(gamma),
            'verified_shortest_period_days':shortest,
            'limitation':'Fixed released amplitude/slope extrapolated when extended; frequency coverage is not noise-posterior validation.'}
