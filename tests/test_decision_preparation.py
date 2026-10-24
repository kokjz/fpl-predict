import importlib.util
from pathlib import Path
import pandas as pd
import pytest


def module():
    spec=importlib.util.spec_from_file_location('decision_prepare',Path(__file__).parents[1]/'tools/prepare_decision_availability.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def test_corrected_minutes_rebuild_appearance_features_and_preserve_original():
    original=pd.DataFrame([dict(element=99,fixture=11,minutes=0.,points_core=0.,played=0.,sixty=0.)])
    correction=pd.DataFrame([dict(element=99,fixture=11,minutes=17.,total_points=1.)])
    result=module().corrected_history(original,correction)
    assert result.loc[0,['minutes','points_core','played','sixty']].tolist()==[17.,1.,1.,0.]
    assert original.loc[0,['minutes','points_core','played','sixty']].tolist()==[0.,0.,0.,0.]
    with pytest.raises(ValueError):module().corrected_history(original.iloc[:0],correction)


def test_executable_cache_requires_explicit_trust_before_any_load(tmp_path):
    with pytest.raises(ValueError,match='trust'):
        module().prepare(tmp_path/'missing.json','bad',tmp_path/'out')
