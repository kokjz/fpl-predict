from dataclasses import replace
import copy
import pytest
from selection_control import FirstActionSelection
from season_engine import prepare
from season_benchmark import Policy, managed_plan
from horizon_forecast import Horizon
from rolling_planner import _fallback, _objective, Settings
from test_rolling_planner import setup


def inputs():
    s,m,h=setup()
    h=Horizon.create(m,[dict(r,expected_points=8. if r['id']==1 else r['expected_points']) for r in h.forecasts],**dict(h.provenance))
    cfg=Settings(seconds=120.,baseline_mode='feasibility',node_limit=1,
        terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.)
    a=dict(gameweek=m.gameweek,as_of=m.as_of,trained_through=h.provenance['trained_through'],
        model_sha256='invented',decision_sha256='invented',calendar_sha256='invented',
        rows=[dict(gameweek=g,id=p['id'],p_play=.3 if p['id']==14 else .9) for g in h.gameweeks for p in m.players])
    def manager(state,market,horizon,*,settings,policy,blocked,opening_ids):
        actions=_fallback(state,market,horizon,{'ledger':dict(state.holdings)}, {36:'freehit',37:'wildcard',38:'bboost'})
        v,parts=_objective(state,market,horizon,actions,settings)
        return actions,dict(objective=v,components=parts,selected_schedule_bound=dict(status='synthetic_source',feasible_objective=v,upper_objective=v+100,relative_gap=100/abs(v)),global_chip_search_bound=None,proven_optimal=True,mip_gap=0.,trials=[dict(objective=v)],scenario_objectives=[v],total_proxy=v)
    return s,m,h,a,cfg,manager


def test_only_first_selection_changes_and_source_plan_remains_unmodified():
    s,m,h,a,cfg,manager=inputs();policy=Policy(3,True,120.,120.,6)
    old,raw=manager(s,m,h,settings=cfg,policy=policy,blocked=(),opening_ids=None)
    frozen=copy.deepcopy(old)
    actions,r=managed_plan(FirstActionSelection(manager,a),s,m,h,cfg,policy,(),None)
    assert old==frozen and actions[1:]==old[1:]
    assert actions[0].captain==14 and old[0].captain!=14
    assert (actions[0].buys,actions[0].sells,actions[0].chip)==(old[0].buys,old[0].sells,old[0].chip)
    assert prepare(s,m,old[0]).state==prepare(s,m,actions[0]).state
    assert r['objective']==pytest.approx(_objective(s,m,h,actions,cfg)[0])
    assert r['selection_control']['expected_after_hits']>=r['selection_control']['expected_before_hits']-1e-9
    scores=r['selection_control']
    assert scores['transfer_hit_points']==0  # Free Hit carries no transfer charge.
    assert scores['expected_original_after_transfer_hits']==scores['expected_original_before_transfer_hits']==scores['expected_before_hits']
    assert scores['expected_selected_after_transfer_hits']==scores['expected_selected_before_transfer_hits']==scores['expected_after_hits']
    assert r['selected_schedule_bound']['upper_objective']==raw['selected_schedule_bound']['upper_objective']
    assert r['selected_schedule_bound']['feasible_objective']==pytest.approx(r['objective'])
    assert r['selection_control']['expected_objective_bound'] is None
    assert not r['proven_optimal'] and r['mip_gap'] is None
    assert 'trials' not in r and 'proposal_trials' in r and r['global_chip_search_bound'] is None
    # Future appearance cells are not read by a first-action-only control.
    changed=dict(a,rows=[dict(p,p_play=-99.) if p['gameweek']!=m.gameweek else p for p in a['rows']])
    other,_=FirstActionSelection(manager,changed)(s,m,h,settings=cfg,policy=policy,blocked=(),opening_ids=None)
    assert other==actions


@pytest.mark.parametrize('damage',['late','origin','missing','duplicate','probability','mean_bound'])
def test_invalid_sources_or_bounds_are_rejected(damage):
    s,m,h,a,cfg,base=inputs()
    if damage=='late':a['trained_through']=m.as_of
    if damage=='origin':a['gameweek']+=1
    if damage=='missing':a['rows'].pop(0)
    if damage=='duplicate':a['rows'].append(dict(a['rows'][0]))
    if damage=='probability':a['rows'][0]['p_play']=2.
    def manager(*args,**kwargs):
        actions,r=base(*args,**kwargs)
        if damage=='mean_bound':r['selected_schedule_bound']['upper_objective']=-1e6
        return actions,r
    with pytest.raises(ValueError):
        FirstActionSelection(manager,a)(s,m,h,settings=cfg,policy=Policy(3),blocked=(),opening_ids=None)



def test_explicit_selection_score_fields_distinguish_gross_from_transfer_hits():
    s,m,h,a,cfg,_=inputs();s=replace(s,free_transfers=0)
    def manager(state,market,horizon,*,settings,**kwargs):
        ledger=dict(state.holdings);ledger.pop(15);ledger[16]=50
        actions=_fallback(state,market,horizon,{'ledger':ledger},{})
        value,parts=_objective(state,market,horizon,actions,settings)
        return actions,dict(objective=value,components=parts,selected_schedule_bound=dict(status='synthetic_source',feasible_objective=value,upper_objective=value+100,relative_gap=100/abs(value)),proven_optimal=False)
    actions,report=FirstActionSelection(manager,a)(s,m,h,settings=cfg,policy=Policy(3),blocked=(),opening_ids=None)
    r=report['selection_control'];assert r['transfer_hit_points']==4
    assert r['expected_original_before_transfer_hits']==r['expected_before_hits']
    assert r['expected_selected_before_transfer_hits']==r['expected_after_hits']
    assert r['expected_selected_after_transfer_hits']==pytest.approx(r['expected_selected_before_transfer_hits']-4)
    assert r['expected_original_after_transfer_hits']==pytest.approx(r['expected_original_before_transfer_hits']-4)
    assert actions[0].buys==(16,) and actions[0].sells==(15,)
