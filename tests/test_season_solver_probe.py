"""Synthetic controller cases; these do not execute the historical quality study."""
import importlib.util
import json
from pathlib import Path
import pytest
from management_policies import HoldPolicy
from native_planner import retained_bound
from rolling_planner import Settings,make_baseline,_fallback,_objective
from season_benchmark import run,Policy
from test_season_qualification import inputs

spec=importlib.util.spec_from_file_location('season_quality_probe',Path(__file__).parents[1]/'tools/probe_season_solver.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def fixture(tmp_path):
    paths,home,lock=inputs(tmp_path);d=probe.read(paths['decisions']);o=probe.read(paths['outcomes'])
    hidden={int(g):{int(i):v for i,v in rows.items()} for g,rows in o['weeks'].items()}
    reference=home/'reference'
    run(d['weeks'],hidden,reference,policy=Policy(),settings=Settings(baseline_mode='feasibility',terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.),management_policy=HoldPolicy(),management_policy_id='invented')
    p=probe.read(Path(__file__).parents[1]/'docs/season_policy_quality_protocol.json');p['forecast_bundle_sha256']=probe.digest(paths['decisions']);p['reference_source_commit']='invented-controller-check'
    protocol=home/'protocol.json';protocol.write_text(json.dumps(p))
    return dict(decisions=paths['decisions'],reference=reference,opening=paths['opening'],lock=lock,
        lock_sha256=probe.digest(lock),protocol=protocol,protocol_sha256=probe.digest(protocol),output=home/'probe',home=home)


def fake(state,market,horizon,cfg,**kwargs):
    baseline,_=make_baseline(state,market,horizon,cfg,kwargs['opening_ids'])
    actions=_fallback(state,market,horizon,baseline,kwargs['chip_schedule']);value,_=_objective(state,market,horizon,actions,cfg)
    return actions,dict(objective=value,selected_plan_bound=retained_bound(value,value),fallback_retained=False,seconds=0.)


def test_fifteen_cases_keep_order_known_objective_and_do_not_read_evaluator(tmp_path,monkeypatch):
    args=fixture(tmp_path);calls=[];read=probe.read
    def guarded(path):
        assert not any(word in Path(path).name for word in ['settled','summary','outcomes'])
        return read(path)
    monkeypatch.setattr(probe,'read',guarded)
    def track(*pos,**kw):calls.append((pos[0].gameweek,pos[3].seconds));return fake(*pos,**kw)
    value=probe.run(**args,inner=track)
    assert calls==[(g,s) for g in [1,6,16,30,38] for s in [.5,2.,5.]]
    assert value['complete'] and len(value['cases'])==15 and not value['policy_promotion']
    assert value['solver_identity'].startswith('Injected')
    assert all(abs(r['objective']-(24.8 if r['origin']==38 else 148.8))<1e-6 and r['difference_vs_reference']==0 for r in value['cases'])
    assert len(list(args['output'].glob('*_input.json.gz')))==5
    assert len(list(args['output'].glob('*s.json')))==15
    with pytest.raises(ValueError,match='exists'):probe.run(**args,inner=fake)


@pytest.mark.parametrize('corruption',['lock_hash','protocol_hash','source','forecast','opening','matrix'])
def test_bad_identity_stops_before_output_or_solver(tmp_path,corruption):
    args=fixture(tmp_path)
    if corruption.endswith('_hash'):args[corruption.replace('_hash','_sha256')]='0'*64
    elif corruption=='source':
        value=probe.read(args['lock']);value['source_sha256']['rolling_planner.py']='0'*64;args['lock'].write_text(json.dumps(value));args['lock_sha256']=probe.digest(args['lock'])
    elif corruption=='matrix':
        value=probe.read(args['protocol']);value['inner_seconds']=[.5,2.,6.];args['protocol'].write_text(json.dumps(value));args['protocol_sha256']=probe.digest(args['protocol'])
    else:
        path=args['decisions'] if corruption=='forecast' else args['opening'];path.write_text(path.read_text()+'\n')
    with pytest.raises(ValueError):probe.run(**args,inner=lambda *a,**k:pytest.fail('Solver must not run'))
    assert not args['output'].exists()


@pytest.mark.parametrize('corruption',['objective','bound','objective_nan'])
def test_invalid_completed_case_is_preserved_and_fatal(tmp_path,corruption):
    args=fixture(tmp_path)
    def wrong(*a,**k):
        actions,report=fake(*a,**k)
        if corruption=='objective':report['objective']+=1
        elif corruption=='bound':report['selected_plan_bound']['upper_objective']-=1
        else:report['objective']=float('nan')
        return actions,report
    with pytest.raises(AssertionError):probe.run(**args,inner=wrong)
    failure=probe.read(args['output']/'failure.json')
    assert failure['partial']['complete'] is False and failure['failed_attempt']['actions']
    if corruption=='objective_nan':assert failure['failed_attempt']['report']['objective']=={'nonfinite':'nan'}
    assert not (args['output']/'summary.json').exists()


@pytest.mark.parametrize('target',['protocol','reference'])
def test_input_drift_after_calls_invalidates_completion(tmp_path,target):
    args=fixture(tmp_path);calls=[]
    def drift(*a,**k):
        calls.append(1)
        if len(calls)==1:
            path=args['protocol'] if target=='protocol' else args['reference']/'GW01_decision.json'
            path.write_text(path.read_text()+'\n')
        return fake(*a,**k)
    with pytest.raises(AssertionError):probe.run(**args,inner=drift)
    assert len(calls)==15 and not (args['output']/'summary.json').exists()
    assert len(probe.read(args['output']/'failure.json')['partial']['cases'])==15
