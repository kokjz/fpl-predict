"""Independent auditor known answers and deliberately corrupted frozen evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest
from management_policies import HoldPolicy
from season_benchmark import run,Policy
from rolling_planner import Settings
from test_season_benchmark import bundle

spec=importlib.util.spec_from_file_location('independent_season_audit',Path(__file__).parents[1]/'tools/audit_season_path.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def frozen(tmp_path):
    weeks,hidden=bundle();directory=tmp_path/'season'
    run(weeks,hidden,directory,policy=Policy(),settings=Settings(baseline_mode='feasibility',terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.),management_policy=HoldPolicy(),management_policy_id='audit-test-hold')
    return dict(schema_version=1,weeks=weeks),dict(schema_version=1,weeks={str(g):v for g,v in hidden.items()}),directory


def test_known_full_season_and_provisional_accounting(tmp_path):
    d,o,path=frozen(tmp_path);result=audit.audit(d,o,path,6)
    assert result['net_points']==456 and result['hits']==0 and result['deadlines']==38 and result['provisional_periods']==213
    with pytest.raises(AssertionError):audit.audit(d,o,path,1)


@pytest.mark.parametrize('corruption',['score','bank','cash_component','provisional','hash','source_clock','quote'])
def test_auditor_rejects_corrupted_evidence(tmp_path,corruption):
    d,o,path=frozen(tmp_path);decision=path/'GW01_decision.json';settled=path/'GW01_settled.json'
    if corruption=='source_clock':d['weeks'][0]['forecast']['trained_through']='2026-01-01T00:00Z'
    elif corruption=='quote':d['weeks'][0]['market']['rows'][0]['price_tenths']=2000
    elif corruption in ('score','bank','cash_component'):
        z=json.loads(settled.read_text())
        if corruption=='score':z['score']['net_points']+=1
        elif corruption=='bank':z['state_after']['bank']+=1
        else:z['score']['received']+=1
        settled.write_text(json.dumps(z))
    else:
        v=json.loads(decision.read_text())
        if corruption=='hash':v['report']['objective']+=1
        else:v['provisional_actions'][1]['buys']=[1]
        decision.write_text(json.dumps(v))
        if corruption=='provisional':
            z=json.loads(settled.read_text());z['score']['decision_sha256']=hashlib.sha256(decision.read_bytes()).hexdigest();settled.write_text(json.dumps(z))
    with pytest.raises(AssertionError):audit.audit(d,o,path,6)


def test_auditor_negative_captain_fallback_and_autosub_formation():
    players=[dict(id=i+1,position=pos,team='unused') for i,pos in enumerate([1]*2+[2]*5+[3]*5+[4]*3)]
    action=dict(starters=[1,3,4,5,8,9,10,11,13,14,15],bench=[6,12,7,2],captain=8,vice=9,chip=None)
    o={p['id']:dict(actual=1.,minutes=90.,cards=0.) for p in players}
    for i in [1,3,8]:o[i].update(actual=0.,minutes=0.)
    o[9]['actual']=-2.;o[6]['actual']=4.;o[12]['actual']=3.;o[2]['actual']=5.
    net,parts=audit.actual(action,dict(rows=players),o,4)
    assert parts['autosub_delta']==12. and parts['captain_bonus']==-2.
    assert net==11.
    action['chip']='3xc';net,parts=audit.actual(action,dict(rows=players),o,4)
    assert parts['extra_captain_bonus']==-2. and net==9.


def test_known_profit_basis_and_temporary_free_hit_resources():
    players=[dict(id=i+1,position=pos,team=f'C{i//3}',price_tenths=50,can_buy=True)
             for i,pos in enumerate([1]*2+[2]*5+[3]*5+[4]*3)]
    players.append(dict(id=16,position=2,team='C5',price_tenths=60,can_buy=True))
    state=dict(season='2025-26',gameweek=10,holdings=[(i,40 if i==3 else 50) for i in range(1,16)],bank=50,free_transfers=3,used_chips=[],previous_chip=None,total_points=0.)
    action=dict(buys=[16],sells=[3],starters=[1,16,4,5,8,9,10,11,13,14,15],bench=[6,12,7,2],captain=8,vice=9,chip=None)
    market=dict(season='2025-26',gameweek=10,rows=players)
    new,ids,hits,count=audit.advance(state,market,action)
    assert new['bank']==35 and dict(new['holdings'])[16]==60 and hits==0 and count==1 and new['free_transfers']==3
    action['chip']='freehit';new,ids,hits,count=audit.advance(state,market,action)
    assert new['bank']==50 and dict(new['holdings'])==dict(state['holdings']) and 16 in ids and new['free_transfers']==3
    assert set(new['used_chips'])=={('freehit',2)}
    with pytest.raises(AssertionError):audit.advance(state,market,action,blocked=[('freehit',2)])


def test_restricted_2024_full_season_has_no_2025_topup(tmp_path):
    d,o=bundle()
    for week in d:
        m=week['market'];m['season']='2024-25'
        for key in ('as_of','deadline'):m[key]=m[key].replace('2025','2024').replace('2026','2025')
        f=week['forecast'];f['trained_through']='2024-05-01T00:00Z'
        f['feature_cutoff']=f['source_as_of']=m['as_of']
    path=tmp_path/'season2024'
    run(d,o,path,policy=Policy(),settings=Settings(baseline_mode='feasibility',terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.),management_policy=HoldPolicy(),management_policy_id='restricted-hold-test')
    result=audit.audit(dict(schema_version=1,weeks=d),dict(schema_version=1,weeks={str(g):v for g,v in o.items()}),path,6)
    assert result['net_points']==456 and result['deadlines']==38
