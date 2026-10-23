import copy
import numpy as np
import pandas as pd
import pytest
from season_engine import prepare,settle
from season_sources import restricted_2024_bootstrap
from native_solver_worker import validate_request,RESOURCES,read_json
from test_season_engine import market,state,action,outcomes
from test_native_solver_worker import request
from fpl_model import ForecastModel,CORE_FEATURES


def bootstrap():
    from datetime import datetime,timedelta,timezone
    start=datetime(2024,8,16,17,30,tzinfo=timezone.utc)
    return dict(events=[dict(id=g,deadline_time=(start+timedelta(days=7*(g-1))).isoformat(),is_next=g==2,finished=g==1) for g in range(1,39)],elements=[dict(id=1,code=101,team=1,element_type=1),dict(id=2,code=102,team=1,element_type=5)],teams=[dict(id=1)],chips=[],game_settings=dict(squad_squadplay=11,squad_squadsize=15,squad_team_limit=3,squad_total_spend=1000,transfers_cap=20,transfers_sell_on_fee=.5,max_extra_free_transfers=4))


def test_manager_filter_explicit_preserves_source_and_missing_evidence():
    b=bootstrap();original=copy.deepcopy(b);view,info,bridge,r=restricted_2024_bootstrap(b,2,'2024-08-23T16:30Z')
    assert b==original and len(view['elements'])==len(bridge)==1 and r['excluded_managers']==1
    assert r['separate_dated_rule_evidence_required'] and not r['full_season_chip_capability_supported']
    b['elements'][1]['element_type']=6
    with pytest.raises(ValueError,match='Unknown'):restricted_2024_bootstrap(b,2,'2024-08-23T16:30Z')


def test_filter_cannot_hide_identity_or_financial_mismatch():
    b=bootstrap();b['elements'][1]['code']=101
    with pytest.raises(ValueError,match='identity'):restricted_2024_bootstrap(b,2,'2024-08-23T16:30Z')
    b=bootstrap();b['game_settings']['max_extra_free_transfers']=1
    with pytest.raises(ValueError,match='financial'):restricted_2024_bootstrap(b,2,'2024-08-23T16:30Z')


def test_annual_chips_and_no_afcon_topup():
    p=prepare(state(19,season='2024-25'),market(19,season='2024-25'),action(chip='3xc'));s,_=settle(p,outcomes())
    with pytest.raises(ValueError,match='already used'):prepare(s,market(20,season='2024-25'),action(chip='3xc'))
    assert prepare(state(16,season='2024-25'),market(16,season='2024-25'),action()).state.free_transfers==2
    a=prepare(state(19,season='2024-25'),market(19,season='2024-25'),action(chip='wildcard'))
    assert prepare(a.state,market(20,season='2024-25'),action(chip='wildcard')).state.used_chips==( ('wildcard',2),('wildcard',20) )
    with pytest.raises(ValueError,match='Unsupported chip'):prepare(state(24,season='2024-25'),market(24,season='2024-25'),action(chip='manager'))


def test_native_annual_tokens_and_unaudited_season_rejected():
    r=read_json((RESOURCES/'native_solver_recipe.json').read_bytes());q=request();q['market']['season']=q['state']['season']='2024-25';q['chip_schedule']={'19':'3xc','20':'3xc'}
    with pytest.raises(ValueError,match='Illegal'):validate_request(q,r)
    q['chip_schedule']={'19':'wildcard','20':'wildcard'};_,_,_,_,rules=validate_request(q,r)
    assert not rules['ft_topups'] and rules['excluded_chips']==['manager']
    q['market']['season']=q['state']['season']='2023-24'
    with pytest.raises(ValueError,match='Unaudited'):validate_request(q,r)


def test_no_dc_scoring_cannot_invent_contribution_points():
    class Constant:
        def predict(self,x):return np.repeat(2.,len(x))
    x=pd.DataFrame([{**{k:1. for k in CORE_FEATURES},'dc_rate4':1.}]);m=ForecastModel(Constant(),'hgb7',1.,Constant(),Constant(),Constant(),None,'none',{},dict())
    assert m.predict(x,[2]).expected_points.iloc[0]==2. and m.predict(x,[2]).dc_xp.iloc[0]==0.
