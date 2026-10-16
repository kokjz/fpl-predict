import json
from pathlib import Path
import numpy as np
import pytest
from conditional_integration import POLICY,fit_returns
from test_incumbent_availability import inputs


def frames():
    d,x,_,_=inputs()
    for col in ['dc_rate4','dc_rate12','dc_actions4','dc_records']:x[col]=1.
    d['points_core']=d.played*5.;d['dc_hit']=d.played;d['total_points']=d.played*7.
    head=d[d.season.eq('2025-26')&d.GW.ge(20)][['season','GW','element','fixture','played']].copy()
    head['control']=.8;head['structured']=.9
    return d,x,head


def test_shared_conditional_fit_is_outcome_safe_and_probabilities_drive_points():
    d,x,h=frames();a,r=fit_returns(d,x,h)
    assert np.allclose(a.old_xp,.8*(a.conditional_core+2*a.conditional_dc))
    assert np.allclose(a.new_xp,.9*(a.conditional_core+2*a.conditional_dc))
    assert r['appearing_training_rows']<r['training_rows']
    future=d.season.eq('2025-26')&d.GW.ge(20);d.loc[future&d.played.eq(1),'points_core']=100.
    d.loc[future&d.played.eq(1),'total_points']=102.
    b,_=fit_returns(d,x,h)
    assert np.array_equal(a[['old_xp','new_xp']].values,b[['old_xp','new_xp']].values)


def test_unknown_head_coverage_or_zero_minute_points_fail_closed():
    d,x,h=frames()
    with pytest.raises(ValueError,match='coverage'):fit_returns(d,x,h.iloc[1:])
    d.loc[d.season.eq('2025-26')&d.GW.ge(20)&d.played.eq(0),'total_points']=-1
    with pytest.raises(ValueError,match='Zero-minute'):fit_returns(d,x,h)


def test_protocol_is_bundled_and_fixed():
    p=Path(__file__).parents[1]/'src/fpl_predict_resources/conditional_selection_protocol.json'
    assert json.loads(p.read_text())==POLICY and not POLICY['promotion']
