"""Retained feasible plans, not abandoned solver attempts, need the bound."""
from dataclasses import replace
import pytest
from scipy.optimize import OptimizeResult
import rolling_planner
from rolling_planner import plan,selected_bound
from test_rolling_planner import setup,config


def test_minimisation_dual_sign_and_objective_constant():
    b=selected_bound(OptimizeResult(status=1,mip_dual_bound=-117.,mip_gap=99.),100.,3.,False)
    assert b['upper_objective']==120. and b['absolute_gap']==20. and b['relative_gap']==.2


@pytest.mark.parametrize('dual',[None,float('nan'),float('inf'),-float('inf')])
def test_missing_or_nonfinite_dual_does_not_turn_attempt_gap_into_certificate(dual):
    b=selected_bound(OptimizeResult(status=1,mip_dual_bound=dual,mip_gap=0.),100.,0.,False)
    assert b['status']=='unavailable' and b['upper_objective'] is None and b['relative_gap'] is None


def test_inconsistent_dual_is_visible_and_never_clipped_to_false_zero_gap():
    b=selected_bound(OptimizeResult(status=0,mip_dual_bound=-80.),100.,0.,True)
    assert b['status']=='inconsistent_dual' and b['absolute_gap'] is None
    b=selected_bound(OptimizeResult(status=0),100.,0.,True)
    assert b['status']=='validated_optimal_status' and b['absolute_gap']==0.


def test_retained_baseline_uses_its_own_value_not_reported_attempt_ratio(monkeypatch):
    s,m,h=setup(gw=38,H=1);cfg=config();_,native=plan(s,m,h,cfg);f=native['fallback_objective']
    monkeypatch.setattr(rolling_planner,'milp',lambda *a,**k:OptimizeResult(status=1,x=None,mip_dual_bound=-(f+10),mip_gap=99.))
    _,r=plan(s,m,h,cfg)
    assert r['fallback_retained'] and r['mip_gap']==99. and not r['proven_optimal']
    assert r['selected_plan_bound']['absolute_gap']==pytest.approx(10.)
    assert r['selected_plan_bound']['relative_gap']==pytest.approx(10./f)


def test_baseline_cut_preserves_known_solution_including_fh_terminal_constant():
    s,m,h=setup(gw=20,H=1);cfg=replace(config(),terminal_squad_weight=.05,terminal_ft_value=1.)
    _,a=plan(s,m,h,replace(cfg,use_baseline_cut=False),chip_schedule={20:'freehit'})
    _,b=plan(s,m,h,replace(cfg,use_baseline_cut=True),chip_schedule={20:'freehit'})
    assert a['proven_optimal'] and b['proven_optimal'] and a['objective']==pytest.approx(b['objective'])
    assert b['selected_plan_bound']['absolute_gap']==pytest.approx(0.,abs=1e-5)


def test_nonfinite_attempt_gap_serialises_as_unknown(monkeypatch):
    s,m,h=setup()
    monkeypatch.setattr(rolling_planner,'milp',lambda *a,**k:OptimizeResult(status=1,x=None,mip_gap=float('inf')))
    _,r=plan(s,m,h,config());assert r['mip_gap'] is None and r['selected_plan_bound']['upper_objective'] is None


def test_outer_chip_search_has_no_global_certificate():
    from adaptive_planner import plan_adaptive,Budget
    s,m,h=setup(gw=38,H=1)
    _,r=plan_adaptive(s,m,[('base',1.,h)],settings=config(),budget=Budget(seconds=5.,solve_seconds=1.,max_trials=1))
    assert r['selected_schedule_bound']['upper_objective']>=r['objective']-1e-5
    assert r['global_chip_search_bound'] is None and r['trials'][0]['selected_plan_bound']==r['selected_schedule_bound']
