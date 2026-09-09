"""Isolated Intel libstempo worker; outputs timing arrays, never fits or searches."""
import argparse
import json
from pathlib import Path
import numpy as np
import libstempo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('par', type=Path)
    parser.add_argument('tim', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--target', default='J1721-2457')
    parser.add_argument('--ntoa', type=int, default=150)
    args = parser.parse_args()
    if np.finfo(np.longdouble).nmant < 63:
        raise RuntimeError('Intel extended precision is required')
    p = libstempo.tempopulsar(parfile=str(args.par), timfile=str(args.tim),
                            dofit=False, warnings=True, maxobs=max(256,args.ntoa+32))
    if p.name != args.target or p.nobs != args.ntoa:
        raise ValueError('Target or TOA count differs from the pinned inventory')
    residuals = p.residuals(removemean=True)
    design = p.designmatrix()
    names = ['Offset', *p.pars()]
    derivatives = {}
    # Representative spin, astrometric, dispersion and instrument derivatives.
    # Perturb only this in-memory model, then restore the released parameter.
    for name in ('F0', 'RAJ', 'DM2', 'JUMP2'):
        if name not in names:
            continue
        column = np.asarray(design[:,names.index(name)],dtype=np.longdouble)
        column -= column.mean()
        step = np.longdouble(5e-5) / np.max(np.abs(column))
        saved = p[name].val
        p[name].val = saved + step
        plus = p.residuals(removemean=True)
        p[name].val = saved - step
        minus = p.residuals(removemean=True)
        p[name].val = saved
        numerical = (plus-minus)/(2*step)
        # TEMPO2's columns describe the correction to the residual, hence -dr/dp.
        derivatives[name] = float(np.linalg.norm(numerical+column)/np.linalg.norm(column))
    p.formbats()
    noise = {k: {'value': float(v.val), 'flag': v.flag, 'flag_value': v.flagval}
             for k,v in p.noisemodel.items() if k.startswith(('efac_', 'equad_', 'ecorr_'))}
    np.savez_compressed(args.output, times=p.toas(), site_times=p.stoas.copy(),
                        residuals=residuals, design=design, names=np.array(names),
                        errors_us=p.toaerrs.copy(), frequency_hz=p.ssbfreqs(),
                        groups=p.flagvals('group').astype(str), deleted=p.deleted.copy())
    args.output.with_suffix('.json').write_text(json.dumps({
        'libstempo':libstempo.__version__, 'ephemeris':p.ephemeris, 'clock':p.clock,
        'noise':noise, 'longdouble_mantissa':int(np.finfo(np.longdouble).nmant),
        'f0':str(p['F0'].val), 'pepoch':str(p['PEPOCH'].val), 'timing_names':names,
        'derivative_relative_errors':derivatives,
        'fit_performed':False}, indent=2)+'\n')
    print('TIMING_EXPORT_COMPLETE',p.nobs,flush=True)


if __name__ == '__main__':
    main()
