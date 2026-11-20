"""Pinned native TEMPO2 export and local binary checks for EPTA J1012."""
import argparse
import json
from pathlib import Path
import numpy as np
import libstempo


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('par',type=Path);parser.add_argument('tim',type=Path);parser.add_argument('output',type=Path)
    a=parser.parse_args()
    if np.finfo(np.longdouble).nmant<63:raise RuntimeError('Intel extended precision required')
    p=libstempo.tempopulsar(parfile=str(a.par),timfile=str(a.tim),dofit=False,warnings=True,maxobs=5400)
    if p.name!='J1012+5307' or p.nobs!=5324:raise ValueError('Target/count mismatch')
    y=p.residuals(removemean=True);x=p.designmatrix();names=['Offset',*p.pars()]
    required=['PB','A1','PBDOT','XDOT','TASC','EPS1','EPS2','H3','H4']
    checks={};errors=p.toaerrs*1e-6
    for name in required:
        if name not in names:raise ValueError('Missing free orbital column '+name)
        value=np.longdouble(p[name].val);unc=np.longdouble(p[name].err)
        if not np.isfinite(unc) or unc<=0:raise ValueError('Missing uncertainty '+name)
        column=np.asarray(x[:,names.index(name)],np.longdouble);column-=column.mean()
        try:
            p[name].val=value+unc;plus=p.residuals(removemean=True).copy()
            p[name].val=value-unc;minus=p.residuals(removemean=True).copy()
            numerical=(plus-minus)/(2*unc)
            p[name].val=value+3*unc;hi=p.residuals(removemean=True).copy()
            p[name].val=value-3*unc;lo=p.residuals(removemean=True).copy()
        finally:p[name].val=value
        derivative=float(np.linalg.norm(numerical+column)/np.linalg.norm(column))
        remainder=np.maximum(abs(hi-y+column*3*unc),abs(lo-y-column*3*unc))
        checks[name]={'value':str(value),'uncertainty':str(unc),'relative_derivative_error':derivative,
                      'max_3sigma_remainder_seconds':float(remainder.max()),
                      'max_3sigma_remainder_raw_TOA_sigma':float(np.max(remainder/errors))}
    p.formbats();restored=p.residuals(removemean=True)
    np.testing.assert_allclose(restored,y,rtol=0,atol=1e-12)
    noise={k:{'value':float(v.val),'flag':v.flag,'flag_value':v.flagval}
           for k,v in p.noisemodel.items() if k.startswith(('efac_','equad_','ecorr_'))}
    np.savez_compressed(a.output,times=p.toas(),site_times=p.stoas.copy(),residuals=y,design=x,names=np.array(names),
                        errors_us=p.toaerrs.copy(),frequency_hz=p.ssbfreqs(),groups=p.flagvals('group').astype(str),
                        systems=p.flagvals('sys').astype(str),deleted=p.deleted.copy())
    a.output.with_suffix('.json').write_text(json.dumps({'target':p.name,'libstempo':libstempo.__version__,
         'clock':p.clock,'ephemeris':p.ephemeris,'binary_parameters':checks,'noise':noise,'fit_performed':False,
         'longdouble_mantissa':int(np.finfo(np.longdouble).nmant)},indent=2)+'\n')
    print('NATIVE_BINARY_EXPORT_COMPLETE',p.nobs,json.dumps(checks),flush=True)


if __name__=='__main__':main()
