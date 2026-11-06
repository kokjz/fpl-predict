"""Synthetic interface admission and P6; no fitted conditional artifact is loaded."""
import copy
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
from champion_availability import predict,prepare,POLICY_KEY
from conditional_forecaster import SIGNALS
from horizon_forecast import project
from approved_horizon import project_approved,observe_approved
from approved_decision import project_decision_approved
from fpl_model import CORE_FEATURES,DC_FEATURES
from promotion_groundwork_fixtures import ConstantModel,parity_case,forecast_case
from test_approved_horizon import setup


class ConditionalModel(ConstantModel):
    """Stand-in accepts the real predict(x,pos) interface and availability columns.

    The synthetic label-to-output relation tests plumbing, not calibration.
    """
    requires_availability=True
    seen=[]
    def predict(self,x,pos):
        assert set(CORE_FEATURES+DC_FEATURES+SIGNALS)<=set(x)
        a=x[SIGNALS].to_numpy(float)
        assert np.isfinite(a).all() and np.isin(a[:,1],[0.,1.]).all()
        assert ((a[:,1]!=1)|(a[:,0]==0)).all()
        type(self).seen.append(x.copy())
        p=np.where(x.availability_missing.eq(1),.8,.4+.4*x.availability_chance)
        return pd.DataFrame(dict(core_xp=5*p,dc_xp=.2*p,expected_points=5.2*p,
            expected_minutes=60*p,p_play=p,p60=.5*p),index=x.index)


def bootstrap(m):
    return dict(events=[dict(id=m.gameweek,is_next=True,deadline_time=m.deadline)],
        elements=[dict(id=p['id'],code=1000+p['id'],element_type=p['position'],
            chance_of_playing_next_round=75) for p in m.players])


def label_review(m,ident=1,**assumption):
    t=pd.Timestamp(m.as_of)
    return dict(schema_version=1,GW=m.gameweek,recorded_at_utc=(t-pd.Timedelta(minutes=10)).isoformat(),
        players=[dict(id=ident,reason='Synthetic pre-deadline label',source_url='https://example.org/news',
            published_at_utc=(t-pd.Timedelta(minutes=30)).isoformat(),
            checked_at_utc=(t-pd.Timedelta(minutes=20)).isoformat(),**assumption)])


def case(tmp_path,monkeypatch):
    root,h,m,f,k=setup(tmp_path,monkeypatch)
    b=bootstrap(m)
    return root,h,m,f,k,b


def conditional_project(h,m,f,b,**kw):
    return project(ConditionalModel(),h,m,f,through=32,trained_through='2026-01-01T00:00Z',
        source_as_of=m.as_of,model_id='synthetic-conditional',bootstrap=b,bootstrap_as_of=m.as_of,**kw)


def register_standin(root,k):
    artifact=root/'artifact.joblib';joblib.dump(ConditionalModel(),artifact)
    sha=hashlib.sha256(artifact.read_bytes()).hexdigest()
    p=root/'model_registry.json';r=json.loads(p.read_text());r['versions']['synthetic-v1']['sha256']=sha
    p.write_text(json.dumps(r))
    receipt=k['receipt_path'];doc=json.loads(receipt.read_text());doc['artifact_sha256']=sha
    receipt.write_text(json.dumps(doc));k['receipt_sha256']=hashlib.sha256(receipt.read_bytes()).hexdigest()
    return sha


def test_main_reference_bytes_unchanged(tmp_path):
    expected=Path(__file__).parent/'fixtures/promotion_groundwork_main_reference.json'
    raw=(json.dumps(parity_case(tmp_path),sort_keys=True,allow_nan=False,indent=2)+'\n').encode()
    assert raw==expected.read_bytes()


def test_next_labels_and_later_missing_and_both_label_provenance(tmp_path,monkeypatch):
    _,h,m,f,_,b=case(tmp_path,monkeypatch);ConditionalModel.seen=[]
    base,report=conditional_project(h,m,f,b)
    x=ConditionalModel.seen[-1]
    assert x[SIGNALS].to_numpy().tolist()==[[.75,0.],[0.,1.],[0.,1.]]*2
    assert report['learned_availability']['known_label_fixture_rows']==2
    assert report['learned_availability']['later_fixture_rows']==4
    revised,r=conditional_project(h,m,f,b,label_review=label_review(m,chance=25))
    changed=ConditionalModel.seen[-1]
    assert np.flatnonzero((x[SIGNALS]!=changed[SIGNALS]).any(axis=1)).tolist()==[0]
    assert changed.iloc[0].availability_chance==.25
    assert {k for k,v in base.values().items() if v!=revised.values()[k]}=={(30,1)}
    entry=r['learned_availability']['manual_labels'][0]
    assert entry['official_chance_label']==75 and entry['replacement_chance_label']==25
    assert entry['fixture_rows']==1 and entry['source_url']=='https://example.org/news'
    assert POLICY_KEY in revised.provenance['source_hashes']


@pytest.mark.parametrize('damage',['post_deadline','clock','position','unknown','duplicate','wrong_origin'])
def test_bad_snapshot_and_identity_are_refused(tmp_path,monkeypatch,damage):
    _,h,m,f,_,b=case(tmp_path,monkeypatch)
    if damage=='post_deadline':b['events'][0]['deadline_time']=m.as_of
    elif damage=='clock':
        with pytest.raises(ValueError,match='clocks'):
            project(ConditionalModel(),h,m,f,through=32,trained_through='2026-01-01T00:00Z',
                source_as_of=m.as_of,model_id='synthetic',bootstrap=b,bootstrap_as_of='2027-03-01T10:59Z')
        return
    elif damage=='position':b['elements'][0]['element_type']=4
    elif damage=='unknown':b['elements'].pop()
    elif damage=='duplicate':b['elements'].append(dict(b['elements'][0]))
    else:b['events'][0]['id']=31
    with pytest.raises(ValueError):conditional_project(h,m,f,b)


@pytest.mark.parametrize('assumption',[dict(availability=.5),dict(minutes=30),dict(availability=1.),dict(minutes=0)])
def test_next_gw_output_scaling_refused(tmp_path,monkeypatch,assumption):
    _,h,m,f,_,b=case(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match='P6'):
        conditional_project(h,m,f,b,availability_overrides={1:assumption},override_gameweek=30)
    with pytest.raises(ValueError,match='P6'):
        conditional_project(h,m,f,b,label_review=label_review(m,**assumption))


@pytest.mark.parametrize('assumption',[dict(chance=1),dict(chance=101),dict(chance=True),dict(chance=50,out=0),dict(out=1)])
def test_invalid_replacement_refused(tmp_path,monkeypatch,assumption):
    _,h,m,f,_,b=case(tmp_path,monkeypatch)
    with pytest.raises(ValueError):conditional_project(h,m,f,b,label_review=label_review(m,**assumption))


@pytest.mark.parametrize('damage',['no_source','post_record','post_deadline','unknown_id','duplicate_id','wrong_gw'])
def test_review_timing_and_source_rules_reused(tmp_path,monkeypatch,damage):
    _,h,m,f,_,b=case(tmp_path,monkeypatch);doc=label_review(m,chance=50)
    if damage=='no_source':doc['players'][0]['source_url']=''
    elif damage=='post_record':doc['players'][0]['published_at_utc']=m.as_of
    elif damage=='post_deadline':doc['recorded_at_utc']=m.deadline
    elif damage=='unknown_id':doc['players'][0]['id']=999
    elif damage=='duplicate_id':doc['players'].append(dict(doc['players'][0]))
    else:doc['GW']=32
    with pytest.raises((ValueError,StopIteration)):conditional_project(h,m,f,b,label_review=doc)


def test_later_gw_sensitivity_and_out_label_do_not_force_absence(tmp_path,monkeypatch):
    _,h,m,f,_,b=case(tmp_path,monkeypatch)
    base,_=conditional_project(h,m,f,b)
    later,_=conditional_project(h,m,f,b,availability_overrides={1:dict(availability=.5)},override_gameweek=32)
    assert later.values()[30,1]==base.values()[30,1]
    assert later.values()[32,1]==.5*base.values()[32,1]
    out,r=conditional_project(h,m,f,b,label_review=label_review(m,out=0))
    assert out.values()[30,1]>0
    assert r['learned_availability']['manual_labels'][0]['replacement_chance_label']==0


def test_approved_mean_and_appearance_use_identical_covariates(tmp_path,monkeypatch):
    root,h,m,f,k,b=case(tmp_path,monkeypatch);before=register_standin(root,k)
    extra=dict(bootstrap=b,bootstrap_as_of=m.as_of,label_review=label_review(m,chance=0))
    mean,r=project_approved(root,h,m,f,**k,**extra)
    decision,a,report=project_decision_approved(root,h,m,f,**k,**extra,allow_research_policy=True)
    assert decision.values()==mean.values()
    assert report['appearance']['mean_reproduction_max_abs_error']==0
    assert hashlib.sha256((root/'artifact.joblib').read_bytes()).hexdigest()==before
    assert len(a['rows'])==6 and all(np.isfinite(v['p_play']) for v in a['rows'])
    assert report['learned_availability']['manual_labels'][0]['official_chance_label']==75
    from test_approved_horizon import review
    sensitivity=review(m);sensitivity.update(bootstrap=b,bootstrap_as_of=m.as_of)
    with pytest.raises(ValueError,match='P6'):project_approved(root,h,m,f,**k,**sensitivity)


def test_forecast_runs_through_adapter_and_refuses_legacy_scaling(tmp_path,monkeypatch):
    ConditionalModel.seen=[]
    result=forecast_case(tmp_path/'base',monkeypatch,ConditionalModel())
    report=result['manifest']['learned_availability']
    assert report['known_label_fixture_rows']==15 and report['later_fixture_rows']==15
    m=__import__('types').SimpleNamespace(gameweek=20,as_of='2026-01-01T10:00Z')
    changed=forecast_case(tmp_path/'news',monkeypatch,ConditionalModel(),review=label_review(m,chance=25))
    old=result['fixture_predictions'];new=changed['fixture_predictions']
    assert [(a['id'],a['GW']) for a,b in zip(old,new) if a['expected_points']!=b['expected_points']]==[(1,20)]
    with pytest.raises(ValueError,match='P6'):
        forecast_case(tmp_path/'refused',monkeypatch,ConditionalModel(),overrides={'1':dict(minutes=30)})


def test_conditional_horizon_consumers_and_scenario_rule(tmp_path,monkeypatch):
    from test_rolling_planner import setup as roster
    from season_engine import Market,prepare as prepare_action
    from rolling_planner import plan,Settings
    from adaptive_planner import plan_adaptive,Budget,scenario
    from fpl_model import normalise
    from test_model import tiny
    state,m,_=roster(gw=20,H=2)
    m=Market.create(m.season,m.gameweek,m.deadline,m.as_of,[dict(p,team=str((p['id']-1)//3+1)) for p in m.players[:15]])
    b=bootstrap(m)
    f=pd.DataFrame([dict(id=g*10+t,event=g,team_h=t,team_a=t+1,kickoff_time='2026-01-02T13:00Z') for g in [20,21] for t in [1,3,5]])
    horizon,r=project(ConditionalModel(),normalise(tiny()),m,f,through=21,trained_through='2025-01-01T00:00Z',
        source_as_of=m.as_of,model_id='synthetic-conditional',bootstrap=b,bootstrap_as_of=m.as_of)
    cfg=Settings(seconds=3.,baseline_mode='feasibility')
    actions,report=plan(state,m,horizon,cfg)
    prepare_action(state,m,actions[0]);assert np.isfinite(report['objective'])
    actions,report=plan_adaptive(state,m,[('conditional',1.,horizon)],settings=cfg,
        budget=Budget(seconds=3.,solve_seconds=.5,max_trials=1))
    prepare_action(state,m,actions[0]);assert np.isfinite(report['objective'])
    adjustment=dict(id=1,gameweeks=[20],multiplier=.5,reason='Synthetic news',available_at=m.as_of,source_url='https://example.org/news')
    with pytest.raises(ValueError,match='P6'):scenario(horizon,m,[adjustment])
    adjustment['gameweeks']=[21];later,_=scenario(horizon,m,[adjustment])
    assert later.values()[21,1]==.5*horizon.values()[21,1]
    # The installed dispatcher consumes the same admitted Horizon, without
    # initialising a real workspace or resolving another champion.
    import sys
    from dataclasses import asdict
    from fpl_predict_cli import main
    provenance=dict(horizon.provenance)
    provenance['source_hashes']=dict(provenance['source_hashes'])
    spec=dict(schema_version=1,state=asdict(state),settings=asdict(cfg),
        market=dict(season=m.season,gameweek=m.gameweek,deadline=m.deadline,as_of=m.as_of,rows=[dict(p) for p in m.players]),
        forecast=dict(rows=[dict(r) for r in horizon.forecasts],**provenance))
    source=tmp_path/'conditional-plan.json';source.write_text(json.dumps(spec));output=tmp_path/'cli-plan'
    monkeypatch.setattr(sys,'argv',['fpl-predict','plan-horizon','--input',str(source),
        '--sha256',hashlib.sha256(source.read_bytes()).hexdigest(),'--output',str(output)])
    main();assert json.loads((output/'plan.json').read_text())['origin']==20


def test_empty_calendar_still_admits_labels_and_refuses_bad_context(tmp_path,monkeypatch):
    _,h,m,f,_,b=case(tmp_path,monkeypatch);f=f.iloc[:0]
    out,r=conditional_project(h,m,f,b)
    assert set(out.values().values())=={0.} and r['learned_availability']['next_fixture_rows']==0
    b['events'][0]['deadline_time']=m.as_of
    with pytest.raises(ValueError):conditional_project(h,m,f,b)


@pytest.mark.parametrize('chance',[0,25,50,75,100])
def test_all_registered_replacement_labels(tmp_path,monkeypatch,chance):
    _,h,m,f,_,b=case(tmp_path,monkeypatch)
    _,r=conditional_project(h,m,f,b,label_review=label_review(m,chance=chance))
    assert r['learned_availability']['manual_labels'][0]['replacement_chance_label']==chance


def test_conditional_double_labels_and_missing_bootstrap(tmp_path,monkeypatch):
    _,h,m,f,_,b=case(tmp_path,monkeypatch)
    f=pd.concat([f,pd.DataFrame([dict(id=99,event=30,team_h=1,team_a=2,kickoff_time='2027-03-01T14:00Z')])],ignore_index=True)
    _,r=conditional_project(h,m,f,b,label_review=label_review(m,chance=25))
    assert r['learned_availability']['manual_labels'][0]['fixture_rows']==2
    assert r['learned_availability']['next_fixture_rows']==4
    with pytest.raises(ValueError,match='bootstrap'):conditional_project(h,m,f,None)


def test_saved_conditional_forecast_is_accepted_by_decision_trial(tmp_path,monkeypatch):
    import datetime as dt
    from types import SimpleNamespace
    import forecast,decision_trial
    from promotion_groundwork_fixtures import forecast_output
    class Clock(dt.datetime):
        @classmethod
        def now(cls,tz=None):return cls(2026,1,1,11,tzinfo=dt.timezone.utc)
    clock=SimpleNamespace(datetime=Clock,timezone=dt.timezone)
    monkeypatch.setattr(forecast,'dt',clock);monkeypatch.setattr(decision_trial,'dt',clock)
    root=tmp_path/'synthetic-home';result=forecast_case(root,monkeypatch,ConditionalModel())
    dest=forecast_output(root/'forecasts');selection=result['planning']['lineups']['20']
    rows={p['id']:p for p in result['player_gameweek_predictions']}
    statepath=root/'state.json';state=json.loads(statepath.read_text())
    state.update(season='2026-27',screenshot_selection=dict(starters=selection['starters'],
        bench_outfield=[i for i in selection['bench'] if rows[i]['position']!=1],
        bench_goalkeeper=next(i for i in selection['bench'] if rows[i]['position']==1),
        captain=selection['captain'],vice_captain=selection['vice']))
    statepath.write_text(json.dumps(state))
    artifact=root/'synthetic.bin';digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
    monkeypatch.setattr(decision_trial,'resolve_champion',lambda _: (artifact,'synthetic-v1',dict(sha256=digest)))
    baseline=tmp_path/'synthetic-baseline.txt';baseline.write_text('Entirely generated selection; no private manager data')
    trial=decision_trial.freeze(root,dest,statepath,tmp_path/'frozen-trial',20,baseline)
    assert len(trial['players'])==15 and trial['model_sha256']==digest
