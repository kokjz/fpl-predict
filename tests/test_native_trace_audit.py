import copy,importlib.util
from pathlib import Path
import sys
import pytest


def module():
    sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
    s=importlib.util.spec_from_file_location('trace_audit',Path(__file__).parents[1]/'tools/audit_native_trace.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def case(season='2024-25',g=16):
    players=[dict(id=i+1,position=p,team=str(i//3),price_tenths=50,can_buy=True) for i,p in enumerate([1]*2+[2]*5+[3]*5+[4]*3)]
    q=dict(schema_version=1,market=dict(season=season,gameweek=g,as_of='2024-10-01T00:00Z',deadline='2024-10-01T01:00Z',rows=players),state=dict(season=season,gameweek=g,holdings=[(i,50) for i in range(1,16)],bank=250,free_transfers=1,used_chips=[],previous_chip=None),xp=[[g,i,2.] for i in range(1,16)],through=g,chip_schedule={},opening_ids=None,seconds=2.)
    r=dict(status='completed',native_status='HighsModelStatus.kOptimal',objective=24.8,picks=[dict(week=g,id=i,squad=1) for i in range(1,16)],statistics={str(g):dict(ft=5 if season=='2025-26' else 1,pt=0,itb=25.)})
    return q,r


def test_independent_known_objective_and_season_specific_ft():
    m=module()
    for season in ['2024-25','2025-26']:
        q,r=case(season);assert m.validate(q,r)==1
        r['statistics']['16']['ft']=2
        with pytest.raises(AssertionError):m.validate(q,r)


@pytest.mark.parametrize('damage',['bank','objective','duplicate','roster','outcome','missing_forecast'])
def test_raw_reply_tamper_rejected(damage):
    q,r=case()
    if damage=='bank':r['statistics']['16']['itb']=24.
    elif damage=='objective':r['objective']+=1
    elif damage=='duplicate':r['picks'].append(r['picks'][0])
    elif damage=='roster':r['picks'].pop()
    elif damage=='outcome':q['market']['rows'][0]['actual']=10.
    else:q['xp'].pop()
    with pytest.raises(AssertionError):module().validate(q,r)


def test_only_expected_native_failure_is_accepted():
    q,r=case();m=module();assert m.validate(q,dict(status='failed',error_type='ValueError',message='No feasible native incumbent'))==0
    with pytest.raises(AssertionError):m.validate(q,dict(status='failed',error_type='RuntimeError',message='unexpected'))


def test_explicit_paid_slack_extension_and_strict_default():
    q,r=case();r['native_status']='HighsModelStatus.kTimeLimit';r['statistics']['16']['pt']=2;r['objective']-=8;m=module()
    with pytest.raises(AssertionError):m.validate(q,r)
    assert m.validate(q,r,allow_dominated_paid_slack=True)==1
    r['statistics']['16']['pt']=1.5
    with pytest.raises(AssertionError):m.validate(q,r,allow_dominated_paid_slack=True)
