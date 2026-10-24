from dataclasses import replace
import pytest
from decision_management import DecisionInner, DecisionManager
from decision_value import players, objective
from forecast import select_xi
from horizon_forecast import Horizon
from rolling_planner import Settings, _objective
from season_benchmark import Policy, managed_plan
from season_engine import State, Market, Action, prepare
from test_expected_selection import squad


def fixture(gameweek=1, grandfather=False):
    raw=squad()
    rows=[dict(id=r['id'],position=r['position'],team='shared' if grandfather and r['id']<=4 else str(r['id']//4),price_tenths=50,can_buy=True) for r in raw]
    # Ordinary fixture must itself respect the three-per-club purchase limit.
    if not grandfather:
        for r in rows:r['team']=str((r['id']-1)//3)
    m=Market.create('2025-26',gameweek,'2025-08-15T18:00Z','2025-08-15T17:00Z',rows)
    h=Horizon.create(m,[dict(gameweek=gameweek,id=r['id'],expected_points=r['expected_points']) for r in raw],trained_through='2025-05-25T18:00Z',feature_cutoff=m.as_of,source_as_of=m.as_of,model_id='invented')
    a=dict(gameweek=gameweek,as_of=m.as_of,trained_through='2025-05-25T18:00Z',model_sha256='invented',decision_sha256='invented',calendar_sha256='invented',rows=[dict(gameweek=gameweek,id=r['id'],p_play=(r['id']%4+1)/4) for r in raw])
    state=State('2025-26') if gameweek==1 else State('2025-26',gameweek,tuple((r['id'],50) for r in raw),250,1)
    cfg=Settings(seconds=.1,baseline_mode='feasibility',terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.)
    return state,m,h,a,cfg


def fake_inner(state,market,horizon,cfg,*,chip_schedule=None,opening_ids=None):
    xp=horizon.values();raw=[dict(r,expected_points=xp[state.gameweek,r['id']]) for r in market.players]
    choice=select_xi(raw)
    action=Action(tuple(r['id'] for r in market.players) if not state.holdings else (),(),tuple(choice['starters']),tuple(choice['bench']),choice['captain'],choice['vice'],(chip_schedule or {}).get(state.gameweek))
    value,parts=_objective(state,market,horizon,[action],cfg)
    return [action],dict(objective=value,components=parts,selected_plan_bound=dict(status='invented',feasible_objective=value,upper_objective=value,relative_gap=0),proven_optimal=True,mip_gap=0.,chip_schedule=chip_schedule or {},seconds=0.,fallback_retained=False,solver_diagnostics={})


def test_expected_rerank_changes_selection_not_finances_or_claimed_bound():
    state,m,h,a,cfg=fixture()
    original,report=fake_inner(state,m,h,cfg)
    actions,new=DecisionInner(a,fake_inner)(state,m,h,cfg)
    assert prepare(state,m,original[0]).state==prepare(state,m,actions[0]).state
    assert new['selected_plan_bound']['upper_objective'] is None and not new['proven_optimal']
    assert new['proposal_mean_bound']==report['selected_plan_bound']
    assert new['retained_mean_objective']==pytest.approx(_objective(state,m,h,actions,cfg)[0])


def test_manager_mechanical_admission_separates_mean_and_decision_objectives():
    state,m,h,a,cfg=fixture()
    actor=DecisionManager(a,fake_inner)
    actions,r=managed_plan(actor,state,m,h,cfg,Policy(1,True,2.,.1,1),(),None)
    assert r['objective']==pytest.approx(_objective(state,m,h,actions,cfg)[0])
    assert r['decision_objective']==pytest.approx(r['decision_trials'][0]['objective'])
    assert r['selected_schedule_bound']['upper_objective'] is None
    assert r['decision_selected_schedule_bound']['upper_objective'] is None
    assert 'trials' not in r and 'scenario_objectives' not in r


def test_appearance_origin_and_complete_coverage_required():
    state,m,h,a,cfg=fixture()
    with pytest.raises(ValueError,match='origin'):
        DecisionInner(dict(a,as_of='2025-08-14T17:00Z'),fake_inner)(state,m,h,cfg)
    with pytest.raises(ValueError,match='horizon'):
        DecisionInner(dict(a,rows=a['rows'][:-1]),fake_inner)(state,m,h,cfg)


def test_legitimate_unchanged_grandfathered_club_state_is_scored_after_engine_admission():
    state,m,h,a,cfg=fixture(2,True)
    actions,report=DecisionInner(a,fake_inner)(state,m,h,cfg)
    assert prepare(state,m,actions[0]).state.holdings==state.holdings
    raw=[dict(p,expected_points=h.values()[2,p['id']]) for p in m.players]
    with pytest.raises(ValueError):players(raw,{r['id']:.5 for r in raw})
    with pytest.raises(ValueError):players(raw[:-1],{r['id']:.5 for r in raw[:-1]},check_clubs=False)
