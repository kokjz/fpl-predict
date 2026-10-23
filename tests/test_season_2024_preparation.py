import importlib.util
from pathlib import Path
import pandas as pd
import pytest


def module():
    s=importlib.util.spec_from_file_location('prepare2024',Path(__file__).parents[1]/'tools/prepare_season_2024.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def test_legacy_purchase_proxy_explicit_and_modern_missing_bool_rejected():
    m=module();assert m.eligibility(dict(status='a'))==(True,'legacy_status_proxy_excluding_u_n')
    assert not m.eligibility(dict(status='u'))[0] and not m.eligibility(dict(status='n'))[0]
    assert m.eligibility(dict(status='i',can_select=True))==(True,'archived_can_select')
    with pytest.raises(ValueError):m.eligibility(dict(status='a',can_select=None))
    with pytest.raises(ValueError):m.eligibility(dict(status='unknown'))


def test_transfer_outcomes_do_not_rewrite_origin_club_and_blank_is_explicit():
    elements=[dict(id=1,team=1),dict(id=2,team=3)]
    actual=pd.DataFrame([dict(element=1,fixture=2,team='B',total_points=6,minutes=90,yellow_cards=0,red_cards=0)])
    fixtures=pd.DataFrame([dict(fixture=1,team_h=1,team_a=4),dict(fixture=2,team_h=2,team_a=5)])
    values,changes=module().origin_outcomes(elements,actual,fixtures,dict(A=1,B=2,C=3))
    assert values[1]['actual']==6 and values[2]['minutes']==0 and changes[0]['origin_team']==1
    assert elements[0]['team']==1
    with pytest.raises(ValueError,match='coverage'):module().origin_outcomes(elements,actual.iloc[:0],fixtures,dict(A=1,B=2,C=3))


def test_preparation_requires_cache_trust_before_loading(tmp_path):
    with pytest.raises(ValueError,match='trust'):module().prepare({},tmp_path/'out')
    assert not (tmp_path/'out').exists()
