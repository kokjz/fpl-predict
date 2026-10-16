import copy,json
from datetime import datetime,timedelta,timezone
import pytest
from season_benchmark import Policy,run


def bundle():
    p=[dict(id=i+1,position=pos,team=f'C{i//3}',price_tenths=50,can_buy=True) for i,pos in enumerate([1]*2+[2]*5+[3]*5+[4]*3)]
    weeks=[];outcomes={}
    for g in range(1,39):
        origin=datetime(2025,8,15,tzinfo=timezone.utc)+timedelta(days=7*(g-1))
        market=dict(season='2025-26',gameweek=g,as_of=origin.isoformat(),deadline=(origin+timedelta(hours=1)).isoformat(),rows=p)
        f=dict(rows=[dict(gameweek=t,id=q['id'],expected_points=2.) for t in range(g,min(38,g+5)+1) for q in p],
               trained_through='2025-05-01T00:00Z',feature_cutoff=market['as_of'],source_as_of=market['as_of'],model_id='synthetic',source_hashes={})
        weeks.append(dict(market=market,forecast=f,blocked_tokens=[]));outcomes[g]={q['id']:dict(actual=1.,minutes=90.,cards=0.) for q in p}
    return weeks,outcomes


def test_full_season_carries_state_and_freezes_decisions_before_settlement(tmp_path):
    d,o=bundle();s=run(d,o,tmp_path/'season',policy=Policy(chips=False));assert s['net_points']==456. and s['hits']==0 and len(s['final_state']['holdings'])==15
    assert s['final_state']['gameweek']==39 and len(list((tmp_path/'season').glob('*_decision.json')))==38
    assert json.loads((tmp_path/'season/GW02_decision.json').read_text())['state_before']['total_points']==12.
    with pytest.raises(ValueError,match='exists'):run(d,o,tmp_path/'season')


def test_season_inner_solver_uses_declared_settings_without_receiving_outcomes(tmp_path):
    from rolling_planner import plan,Settings
    calls=[];d,o=bundle()
    def inner(state,market,horizon,cfg,**kwargs):
        assert cfg.baseline_mode=='feasibility' and cfg.terminal_ft_value==0.
        assert all(not {'actual','minutes','cards'}&set(p) for p in market.players)
        calls.append(state.gameweek);return plan(state,market,horizon,cfg,**kwargs)
    cfg=Settings(baseline_mode='feasibility',terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.)
    result=run(d,o,tmp_path/'native-contract',policy=Policy(horizon=1,chips=True,max_trials=1),settings=cfg,inner_planner=inner)
    assert calls==list(range(1,39)) and result['planner_settings']['baseline_mode']=='feasibility'


def test_future_outcomes_do_not_change_earlier_actions(tmp_path):
    d,o=bundle();run(d,o,tmp_path/'a',policy=Policy(chips=False))
    changed=copy.deepcopy(o)
    for v in changed[38].values():v['actual']=3.
    s=run(d,changed,tmp_path/'b',policy=Policy(chips=False));assert s['net_points']==480.
    for g in range(1,39):
        a=json.loads((tmp_path/f'a/GW{g:02d}_decision.json').read_text());b=json.loads((tmp_path/f'b/GW{g:02d}_decision.json').read_text());assert a['action']==b['action']


def test_incomplete_horizon_or_origin_inventory_fails_before_output(tmp_path):
    d,o=bundle()
    with pytest.raises(ValueError,match='38complete'):run(d[:-1],o,tmp_path/'a')
    assert not (tmp_path/'a').exists()
    d[0]['forecast']['rows']=[r for r in d[0]['forecast']['rows'] if r['gameweek']==1]
    with pytest.raises(ValueError,match='horizon'):run(d,o,tmp_path/'b')
    assert not (tmp_path/'b').exists()


def test_common_opening_roster_is_explicit_and_does_not_allow_extra_players(tmp_path):
    d,o=bundle();s=run(d,o,tmp_path/'a',policy=Policy(chips=False),opening_ids=list(range(1,16)))
    assert s['initialisation']=='commonGW1roster'
    with pytest.raises(ValueError,match='opening'):run(d,o,tmp_path/'b',policy=Policy(chips=False),opening_ids=list(range(1,15)))


def test_lossless_compressed_bundle_input(tmp_path):
    import gzip
    from season_benchmark import read_bundle
    d,o=bundle();value=dict(schema_version=1,weeks=d);path=tmp_path/'decisions.json.gz'
    path.write_bytes(gzip.compress(json.dumps(value).encode()))
    assert read_bundle(path)==value
