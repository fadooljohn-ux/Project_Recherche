"""Narrow orthometric admission and derivative routing; no observed search."""
import io
import sys
from pathlib import Path
import pytest
from pint.models import get_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import binary_wideband as binary

PAR='''PSR J0000+0000
F0 100
PEPOCH 55000
RAJ 00:00:00
DECJ 00:00:00
BINARY ELL1H
PB 6.8 1 1e-9
A1 10 1 1e-7
TASC 55000 1 1e-8
EPS1 1e-5 1 1e-8
EPS2 2e-5 1 1e-8
H3 {h3} 1 5e-8
NHARMS 3
'''

@pytest.mark.parametrize('h3', ['1.7e-7', '-5e-8', '0'])
def test_signed_h3_keeps_native_derivative(h3):
    par=PAR.format(h3=h3)
    fields={v[0]:v[1:] for line in par.splitlines() if (v:=line.split())}
    model=get_model(io.StringIO(par))
    native=model.components['BinaryELL1H'].binary_instance.d_delayS_d_par.__func__
    binary.check_shapiro_mode(fields,'h3_only',model)
    binary.bind_ell1_derivative(model,'h3_only')
    assert model.components['BinaryELL1H'].binary_instance.d_delayS_d_par.__func__ is native
    assert float(model.H3.value)==float(h3) and 'H3' in model.free_params

@pytest.mark.parametrize('change', [
    {'NHARMS':['7']}, {'NHARMS':None}, {'H3':None},
    {'H4':['0']}, {'STIGMA':['0.5']}, {'M2':['0.8']}, {'BINARY':['ELL1']},
])
def test_other_models_are_not_silently_reinterpreted(change):
    fields={'BINARY':['ELL1H'],'H3':['1.7e-7','1','5e-8'],'NHARMS':['3']}
    for key,value in change.items():
        if value is None:fields.pop(key)
        else:fields[key]=value
    with pytest.raises(ValueError):binary.check_shapiro_mode(fields,'h3_only')


def test_existing_ell1_derivative_repair_remains():
    par=PAR.format(h3='1.7e-7').replace('ELL1H','ELL1').replace('H3 1.7e-7 1 5e-8\nNHARMS 3','M2 0.3 1 0.01\nSINI 0.7 1 0.01')
    model=get_model(io.StringIO(par))
    binary.bind_ell1_derivative(model)
    assert model.components['BinaryELL1'].binary_instance.d_delayS_d_par.__func__ is binary.shapiro_derivative


def test_explicit_omitted_ell1h_preserves_native_zero_delay():
    par=PAR.format(h3='1.7e-7').replace('H3 1.7e-7 1 5e-8\n','').replace('NHARMS 3','NHARMS 7')
    fields={v[0]:v[1:] for line in par.splitlines() if (v:=line.split())}
    model=get_model(io.StringIO(par))
    native=model.components['BinaryELL1H'].binary_instance.d_delayS_d_par.__func__
    binary.check_shapiro_mode(fields,'ell1h_omitted_in_release',model)
    binary.bind_ell1_derivative(model,'ell1h_omitted_in_release')
    assert model.components['BinaryELL1H'].binary_instance.d_delayS_d_par.__func__ is native
    assert model.H3.value in (None,0) and 'H3' not in model.free_params
    model.H3.value=1e-6
    with pytest.raises(ValueError):
        binary.check_shapiro_mode(fields,'ell1h_omitted_in_release',model)


@pytest.mark.parametrize('change', [{'H3':['0']},{'H4':['0']},{'STIGMA':['0.5']},
                                  {'M2':['0.8']},{'NHARMS':['3']},{'BINARY':['ELL1']}])
def test_omitted_ell1h_rejects_supplied_terms_or_wrong_convention(change):
    fields={'BINARY':['ELL1H'],'NHARMS':['7'],**change}
    with pytest.raises(ValueError):binary.check_shapiro_mode(fields,'ell1h_omitted_in_release')


def test_omitted_ell1h_adequacy_hold_and_binding_enforced():
    good={'target':'J1802-2124','status':'CONDITIONAL_PREPARATION_COMPATIBLE','holds':[], 'bindings':{'profile':'bound'}}
    binary.check_ell1h_adequacy(good,'J1802-2124',{'profile':'bound'})
    for change in [{'status':'PREPARATION_ADEQUACY_HOLD'},{'holds':['WIDEBAND_NOISE_MODEL_HOLD']},
                   {'bindings':{'profile':'changed'}},{'target':'J0000+0000'}]:
        with pytest.raises(ValueError):binary.check_ell1h_adequacy({**good,**change},'J1802-2124',{'profile':'bound'})
