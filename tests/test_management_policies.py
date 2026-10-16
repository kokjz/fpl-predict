"""Synthetic policy tests; no historical outcomes or timed MILP search."""
from dataclasses import replace
import pytest
from management_policies import FixedCalendarPolicy,HoldPolicy,FIXED_CALENDAR
from native_planner import retained_bound,controlled_settings
from rolling_planner import _fallback,_objective
from season_benchmark import run,Policy
from season_engine import Market,prepare
from test_season_benchmark import bundle
from test_rolling_planner import setup


def fake_inner(state,market,horizon,cfg,*,chip_schedule,opening_ids):
    ids=dict(state.holdings) or {i:50 for i in (opening_ids or range(1,16))}
    actions=_fallback(state,market,horizon,{'ledger':ids},chip_schedule)
    value,parts=_objective(state,market,horizon,actions,cfg)
    return actions,dict(objective=value,components=parts,seconds=0.,
        selected_plan_bound=retained_bound(value,None),proven_optimal=False,fallback_retained=True)


def test_fixed_calendar_full_season_uses_exact_dates_and_reconciles(tmp_path):
    d,o=bundle();summary=run(d,o,tmp_path/'fixed',settings=controlled_settings(),
        policy=Policy(max_trials=2),management_policy=FixedCalendarPolicy(inner_planner=fake_inner),
        management_policy_id='fixed-calendar-v1')
    assert {r['gameweek']:r['name'] for r in summary['chips']}==dict(FIXED_CALENDAR)
    assert summary['hits']==summary['transfers']==0
    assert summary['net_points']==456+2*4+2*1  # two BB bench fours and two extra captains


def test_hold_has_no_transfers_or_chips_and_carries_unused_resources(tmp_path):
    d,o=bundle();summary=run(d,o,tmp_path/'hold',settings=controlled_settings(),
        management_policy=HoldPolicy(),management_policy_id='hold-no-chips-v1')
    assert summary['net_points']==456 and summary['chips']==[]
    assert summary['transfers']==summary['hits']==0 and summary['final_state']['free_transfers']==5


def test_hold_retains_unbuyable_owned_and_ignores_attractive_transfer():
    s,m,h=setup();m=Market.create(m.season,m.gameweek,m.deadline,m.as_of,
        [dict(p,can_buy=False) if p['id']==15 else dict(p) for p in m.players])
    actions,report=HoldPolicy()(s,m,h,settings=controlled_settings(),policy=Policy(),blocked=(),opening_ids=None)
    assert not report['solver_executed'] and not report['fallback_retained']
    for a in actions:assert not a.buys and not a.sells and a.chip is None
    assert set(dict(prepare(s,m,actions[0]).state.holdings))==set(dict(s.holdings))


@pytest.mark.parametrize('calendar',[{1:'wildcard'},{6:'wildcard',7:'wildcard'},{19:'freehit',20:'freehit'}])
def test_fixed_calendar_rejects_illegal_windows_reuse_and_consecutive_freehit(calendar):
    s,m,h=setup()
    with pytest.raises(ValueError):FixedCalendarPolicy(calendar,inner_planner=fake_inner)(
        s,m,h,settings=controlled_settings(),policy=Policy(),blocked=(),opening_ids=None)


def test_fixed_calendar_omits_blocked_or_used_tokens_and_uses_declared_budget():
    s,m,h=setup(gw=18,H=3);s=replace(s,used_chips=(('3xc',1),));seen=[]
    def inner(*args,**kwargs):
        seen.append((args[3].seconds,dict(kwargs['chip_schedule'])))
        return fake_inner(*args,**kwargs)
    actions,report=FixedCalendarPolicy({18:'3xc',20:'bboost'},inner_planner=inner)(
        s,m,h,settings=controlled_settings(),policy=Policy(seconds=1.,solve_seconds=.2,max_trials=2),
        blocked=(('bboost',20),),opening_ids=None)
    assert len(seen)==2 and all(seconds<=.2 and schedule=={} for seconds,schedule in seen)
    assert report['selected_trial_index']==0 and report['selected_schedule_bound']['upper_objective'] is None
    assert all(a.chip is None for a in actions)
