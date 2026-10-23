"""Frozen evidence corruption guards, hindsight bounds, and source-only openings."""
import importlib.util
import json
from pathlib import Path
import pytest
from management_policies import HoldPolicy
from rolling_planner import Settings
from season_benchmark import run,Policy
from season_engine import Market
from test_season_benchmark import bundle


def tool(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).parents[1]/'tools'/f'{name}.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def frozen(tmp_path):
    weeks,hidden=bundle();path=tmp_path/'season'
    run(weeks,hidden,path,policy=Policy(),settings=Settings(baseline_mode='feasibility',terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.),management_policy=HoldPolicy(),management_policy_id='diagnostic-test')
    return dict(schema_version=1,weeks=weeks),dict(schema_version=1,weeks={str(g):v for g,v in hidden.items()}),path


def test_known_hindsight_bounds_and_accounting(tmp_path):
    d,o,path=frozen(tmp_path);out=tool('diagnose_season_path').diagnose(d,o,path,6)
    assert out['deadlines']==38 and out['net_points']==456
    assert sum(x['n'] for k,x in out['owned_error_groups'].items() if k in ['zero','cameo','60plus'])==570
    assert all(r['owned_hindsight_base_headroom']>=0 and r['owned_hindsight_captain_headroom']>=0 for r in out['rows'])
    assert all(not r['changed_buys'] for r in out['provisional_revisions'])


@pytest.mark.parametrize('corruption',['hash','summary','outcome','clock','first_action','carry'])
def test_diagnostics_reject_corrupted_frozen_evidence(tmp_path,corruption):
    d,o,path=frozen(tmp_path)
    if corruption=='summary':
        p=path/'summary.json';x=json.loads(p.read_text());x['hits']+=4;p.write_text(json.dumps(x))
    elif corruption=='outcome':o['weeks']['1'][1]['actual']=999.
    elif corruption=='clock':d['weeks'][0]['forecast']['trained_through']='2027-01-01T00:00Z'
    else:
        p=path/('GW02_decision.json' if corruption=='carry' else 'GW01_decision.json');x=json.loads(p.read_text())
        if corruption=='hash':x['report']['objective']+=1
        if corruption=='first_action':x['provisional_actions'][0]['captain']=x['action']['vice']
        if corruption=='carry':x['state_before']['bank']+=1
        p.write_text(json.dumps(x))
        if corruption!='hash':
            z=path/p.name.replace('decision','settled');v=json.loads(z.read_text());v['score']['decision_sha256']=tool('diagnose_season_path').digest(p);z.write_text(json.dumps(v))
    with pytest.raises((ValueError,KeyError)):tool('diagnose_season_path').diagnose(d,o,path,6)


def test_openings_are_legal_deterministic_and_ignore_non_source_information():
    runner=tool('run_season_robustness');weeks,_=bundle();raw=weeks[0]['market'];raw=dict(raw,rows=[dict(p,price_tenths=60) for p in raw['rows']]);m=Market.create(**raw)
    a=runner.opening(m,20261024);assert a==runner.opening(m,20261024)
    assert len(a['ids'])==15 and 900<=a['cost_tenths']<=1000
    assert a==runner.opening(Market.create(**dict(raw,rows=list(reversed(raw['rows'])))),20261024)


def test_robustness_rejects_undeclared_protocol_and_output(tmp_path):
    runner=tool('run_season_robustness');p=Path(__file__).parents[1]/'docs/season_robustness_protocol_2026-10-24.json'
    assert runner.protocol(p)['robustness']['total_paths']==6
    v=json.loads(p.read_text());v['resources']['inner_seconds']=99;q=tmp_path/'bad.json';q.write_text(json.dumps(v))
    with pytest.raises(ValueError):runner.protocol(q)
    with pytest.raises(ValueError):runner.destination(p.parent/'private.json')
    with pytest.raises(ValueError):runner.destination(q)


def test_locked_standing_arm_runs_complete_season_and_refuses_input_drift(tmp_path):
    runner=tool('run_season_robustness');weeks,hidden=bundle()
    for week in weeks:
        original=week['market']['rows'];extra=[dict(p,id=p['id']+100,team='E'+str((p['id']-1)//3)) for p in original]
        week['market']['rows']=[dict(p,price_tenths=60) for p in [*original,*extra]]
        week['forecast']['rows'] += [dict(p,id=p['id']+100) for p in list(week['forecast']['rows'])]
    for row in hidden.values():row.update({i+100:dict(p) for i,p in list(row.items())})
    d=tmp_path/'d.json';d.write_text(json.dumps(dict(schema_version=1,weeks=weeks)))
    o=tmp_path/'o.json';o.write_text(json.dumps(dict(schema_version=1,weeks={str(g):v for g,v in hidden.items()})))
    p=Path(__file__).parents[1]/'docs/season_robustness_protocol_2026-10-24.json';lock=tmp_path/'lock.json'
    runner.create_lock(d,o,p,lock);sha=runner.digest(lock)
    result=runner.run_arm(d,o,p,lock,sha,20261024,'standingH1_adaptive',tmp_path/'result')
    assert result['final_state']['gameweek']==39 and result['native_calls']==0
    assert not result['model_promotion'] and not result['policy_promotion']
    d.write_text(d.read_text()+' ')
    with pytest.raises(ValueError,match='drift'):runner.run_arm(d,o,p,lock,sha,20261024,'standingH1_adaptive',tmp_path/'new')
