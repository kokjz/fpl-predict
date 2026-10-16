from dataclasses import replace
import pytest
from adaptive_planner import Budget,calendar,plan_adaptive,scenario
from rolling_planner import _objective
from season_engine import prepare
from test_rolling_planner import setup,config


def test_calendar_assigns_each_chip_once_and_respects_expiry_consecutive_fh():
    s,_,_=setup(gw=18,H=1)
    gains={('3xc',1,18):10.,('bboost',1,18):9.,('3xc',1,19):8.,('bboost',1,19):2.,('freehit',20,20):30.}
    value,path=calendar(s,20,gains)
    assert value==47. and path[18]==('bboost',1) and path[19]==('3xc',1)
    _,path=calendar(s,20,{('freehit',2,20):30.},blocked=[('freehit',20)]) # token starts20
    assert not path


def test_calendar_correct_window_and_consecutive_boundary():
    s,_,_=setup(gw=19,H=1)
    gains={('freehit',2,19):10.,('freehit',20,20):11.}
    value,path=calendar(s,20,gains);assert value==11. and set(path)=={20}
    s=replace(s,gameweek=20,previous_chip='freehit',used_chips=(('freehit',2),))
    assert calendar(s,20,gains)==(0.,{})


def test_adaptive_uses_chip_at_season_end_and_reconciles_shared_scenarios():
    s,m,h=setup(gw=38,H=1)
    down,evidence=scenario(h,m,[dict(id=1,gameweeks=[38],multiplier=0.,reason='Synthetic ruled-out sensitivity',available_at=m.as_of,source_url='https://example.org/news')])
    actions,r=plan_adaptive(s,m,[('normal',.5,h),('down',.5,down)],settings=config(),budget=Budget(seconds=15.,solve_seconds=1.,max_trials=12))
    assert actions[0].chip in ('3xc','bboost','wildcard','freehit')
    assert r['objective']==pytest.approx(sum(.5*_objective(s,m,z,actions,config())[0] for z in [h,down]))
    assert r['coarse_reserve']==0 and not r['coarse_schedule']
    prepare(s,m,actions[0]);assert h.values()[38,1]>0 and down.values()[38,1]==0


def test_coarse_opportunity_cost_can_reserve_triple_captain_for_later():
    s,m,h=setup(gw=20,H=1)
    blocked=[('wildcard',20),('freehit',20),('bboost',20)]
    _,r=plan_adaptive(s,m,[('base',1.,h)],settings=config(),budget=Budget(seconds=10.,solve_seconds=1.,max_trials=6),blocked=blocked,
        coarse={'wildcard':0.,'freehit':0.,'bboost':0.,'3xc':1000.})
    assert not r['chip_schedule'] and '3xc' in r['coarse_schedule'].values()
    _,r2=plan_adaptive(s,m,[('base',1.,h)],settings=config(),budget=Budget(seconds=10.,solve_seconds=1.,max_trials=6),blocked=blocked,
        coarse={'wildcard':0.,'freehit':0.,'bboost':0.,'3xc':0.})
    assert r2['chip_schedule']=={20:'3xc'}


def test_scenario_rejects_late_evidence_and_duplicate_cells():
    _,m,h=setup();a=dict(id=1,gameweeks=[36],multiplier=0.,reason='sensitivity',available_at='2026-01-02T00:00Z',source_url='https://example.org/news')
    with pytest.raises(ValueError,match='Post-origin'):scenario(h,m,[a])
    a['available_at']=m.as_of
    with pytest.raises(ValueError,match='duplicate'):scenario(h,m,[a,a])
    with pytest.raises(ValueError,match='weights'):plan_adaptive(setup()[0],m,[('a',.9,h)])


def test_budget_retains_valid_no_chip_baseline():
    s,m,h=setup();actions,r=plan_adaptive(s,m,[('base',1.,h)],settings=config(),budget=Budget(seconds=5.,solve_seconds=1.,max_trials=1))
    assert r['budget_exhausted'] and len(r['trials'])==1 and not r['chip_schedule']
    prepare(s,m,actions[0])


def test_new_injury_evidence_changes_replanned_captain_without_future_knowledge():
    s,m,h=setup(gw=38,H=1);budget=Budget(seconds=5.,solve_seconds=1.,max_trials=1)
    normal,_=plan_adaptive(s,m,[('base',1.,h)],settings=config(),budget=budget)
    captain=normal[0].captain
    down,_=scenario(h,m,[dict(id=captain,gameweeks=[38],multiplier=0.,reason='Newly sourced injury downside sensitivity',available_at=m.as_of,source_url='https://example.org/news')])
    revised,_=plan_adaptive(s,m,[('down',1.,down)],settings=config(),budget=budget)
    assert revised[0].captain!=captain


def test_installed_command_contract_writes_once_without_runtime_initialisation(tmp_path,monkeypatch):
    import json,sys,hashlib
    from dataclasses import asdict
    from fpl_predict_cli import main
    s,m,h=setup(gw=38,H=1)
    forecast=dict(h.provenance);forecast['source_hashes']=dict(forecast['source_hashes']);forecast['rows']=[dict(v) for v in h.forecasts]
    spec=dict(schema_version=1,state=asdict(s),market=dict(season=m.season,gameweek=m.gameweek,deadline=m.deadline,as_of=m.as_of,rows=[dict(p) for p in m.players]),
        scenarios=[dict(name='base',weight=1.,forecast=forecast)],budget=dict(seconds=5.,solve_seconds=1.,max_trials=1))
    path=tmp_path/'input.json';path.write_text(json.dumps(spec));output=tmp_path/'result';runtime=tmp_path/'unused-runtime'
    monkeypatch.setenv('FPL_PREDICT_HOME',str(runtime));monkeypatch.setattr(sys,'argv',['fpl-predict','plan-adaptive','--input',str(path),'--sha256',hashlib.sha256(path.read_bytes()).hexdigest(),'--output',str(output)])
    main();report=json.loads((output/'plan.json').read_text());assert report['immediate_action'] and not runtime.exists()
    with pytest.raises(SystemExit):main()
