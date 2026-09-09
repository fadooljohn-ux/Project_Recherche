"""Compare official narrowband reduction with the selected wideband period."""
import json, sys, hashlib
from contextlib import ExitStack
from pathlib import Path
import numpy as np
from loguru import logger
logger.remove();logger.add(sys.stderr, level='WARNING')
import mpta_batch as m
from j1453_review import ROOT, REFERENCE, GLS, template, write
from pulsar_pilot.pilot2_offline_resources import NetworkDeny, LocalPintRepository
from pulsar_pilot.spin_phase import bind_precise_spin_phase
from pint.models import get_model_and_toas
from pint.residuals import Residuals

if (ROOT/'step4-narrowband.json').exists():
    raise FileExistsError('Narrowband closeout already exists')
par=next((ROOT/'narrowband-original').glob('*.par'));tim=next((ROOT/'narrowband-original').glob('*.tim'))
with ExitStack() as stack:
    deny=stack.enter_context(NetworkDeny())
    local=stack.enter_context(LocalPintRepository(m.RESOURCES,json.loads((m.RESOURCES/'metadata/resources.json').read_text())))
    local.bind_science_resources()
    model,toas=get_model_and_toas(par,tim,ephem='DE440',include_bipm=True,bipm_version='BIPM2019',planets=True,usepickle=False,limits='error')
    bind_precise_spin_phase(model)
    t=np.asarray(toas.table['tdbld'].data,float)
    y=Residuals(toas,model).time_resids.to_value('s')
    x,names,units=model.designmatrix(toas,incfrozen=False,incoffset=True)
    c=model.toa_covariance_matrix(toas)
    print('Prepared',len(t),'TOAs',x.shape,'components',list(model.components),flush=True)
    assert not deny.attempts
np.savez_compressed(ROOT/'narrowband-prepared.npz',times=t,residuals=y,design=x,covariance=c)
g=GLS(c,x)
period=json.loads((ROOT/'step1.json').read_text())['refined']['period_days']
local=np.linspace(100,140,801);scores,_=g.scan(y,g.bank(template(t,local,len(t))))
k=int(np.argmax(scores));fixed=g.fit(y,t,period)
wbt=np.load(ROOT/'metadata.npz')['times']
result={'status':'ALTERNATE_REDUCTION_DIAGNOSTIC','toas':len(t),'observing_days':len(np.unique(np.floor(t))),
 'mjd_start':float(t.min()),'mjd_end':float(t.max()),'span_days':float(np.ptp(t)),
 'days_outside_wideband_date_range':sorted(np.unique(np.floor(t[(t<wbt.min()-1)|(t>wbt.max()+1)])).tolist()),
 'fixed_wideband_period_fit':fixed,'local_peak':g.fit(y,t,local[k]),
 'model_components':list(model.components),'timing_design_names':names,
 'noise_model':'Full released narrowband TOA covariance including EFAC/EQUAD/ECORR; no noise waveform subtracted',
 'par_sha256':hashlib.sha256(par.read_bytes()).hexdigest(),'tim_sha256':hashlib.sha256(tim.read_bytes()).hexdigest(),
 'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'limitations':'Shared Arecibo observations, no independent confirmation. Local diagnostic only, no narrowband detection threshold calibrated.'}
write('step4-narrowband.json',result)
np.savez_compressed(ROOT/'narrowband-periodogram.npz',periods=local,delta_chi2=scores)
print(json.dumps(result),flush=True)
