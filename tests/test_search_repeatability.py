from dataclasses import replace
from types import SimpleNamespace
import copy
import pytest
import rolling_planner
from rolling_planner import Settings
from adaptive_planner import Budget, plan_adaptive
from search_repeatability import decision_fingerprint, FixedWorkManager
from test_decision_management import fixture, fake_inner


def test_fixed_limits_require_deterministic_baseline_and_explicit_nodes():
    for n in [0, True, -1, 1.2, 10001]:
        with pytest.raises(ValueError): Settings(node_limit=n, baseline_mode='feasibility')
    with pytest.raises(ValueError): Settings(node_limit=1)
    with pytest.raises(ValueError): Budget(fixed_work=1)
    state,m,h,a,cfg=fixture()
    with pytest.raises(ValueError,match='fixed-node'):
        plan_adaptive(state,m,[('same',1.,h)],settings=cfg,budget=Budget(1.,1.,3,True))


def test_fixed_outer_work_ignores_elapsed_selection_and_preserves_solve_guard(monkeypatch):
    state,m,h,a,cfg=fixture()
    cfg=replace(cfg,node_limit=1)
    clock=iter(range(0,10000,20))
    monkeypatch.setattr('adaptive_planner.time.monotonic',lambda:next(clock))
    calls=[]
    def inner(*args,**kwargs):
        calls.append(args[3].seconds)
        return fake_inner(*args,**kwargs)
    actions,report=plan_adaptive(state,m,[('same',1.,h)],settings=cfg,
        budget=Budget(1.,1.,5,True),inner_planner=inner)
    # Three unique legal schedules exist in this one-GW synthetic opening.
    assert len(calls)==3 and calls==[1.]*3
    assert report['search_control']['mode']=='fixed_work'


def test_fixed_inner_does_not_accept_time_guard_as_success(monkeypatch):
    state,m,h,a,cfg=fixture()
    monkeypatch.setattr(rolling_planner,'milp',lambda *a,**k:SimpleNamespace(status=1,message='Time limit reached'))
    with pytest.raises(RuntimeError,match='safety guard'):
        rolling_planner.plan(state,m,h,replace(cfg,node_limit=1))


def test_fixed_inner_forwards_node_seed_parallel_controls(monkeypatch):
    state,m,h,a,cfg=fixture();seen={}
    def solve(*args,**kwargs):
        seen.update(kwargs['options'])
        return SimpleNamespace(status=1,message='Iteration limit reached',x=None,mip_node_count=1)
    monkeypatch.setattr(rolling_planner,'milp',solve)
    actions,report=rolling_planner.plan(state,m,h,replace(cfg,node_limit=1))
    assert seen['node_limit']==1 and seen['random_seed']==0 and seen['parallel']=='off'
    assert report['fallback_retained'] and report['solver_diagnostics']['work_control']['mip_node_count']==1


def test_fingerprint_omits_elapsed_but_detects_provisional_financial_source_changes():
    raw=dict(gameweek=1,inputs_as_of='origin',state_before=dict(bank=100,total_points=0),
        action=dict(captain=1),provisional_actions=[dict(captain=1)],forecast_provenance=dict(model='fixed'),report=dict(seconds=1))
    base=decision_fingerprint(raw);same=copy.deepcopy(raw);same['report']['seconds']=99;same['state_before']['total_points']=55
    assert decision_fingerprint(same)==base
    for field,key in [('action','captain'),('provisional_actions',None),('state_before','bank'),('forecast_provenance','model')]:
        changed=copy.deepcopy(raw)
        if key is None:changed[field].append(dict(captain=2))
        else:changed[field][key]='different'
        assert decision_fingerprint(changed)!=base


@pytest.mark.parametrize('damage',[None,'missing','time','count','seed'])
def test_native_fixed_work_requires_valid_receipt_and_non_wall_status(damage):
    from test_native_planner import setup, response, Fake, controlled_settings, NativePlanner
    s,m,h=setup();ordinary=controlled_settings(2.)
    reply=response(s,m,h,ordinary)
    work=dict(node_limit=1,random_seed=0,parallel='off')
    reply.update(work_limit=work.copy(),mip_node_count=1,native_status='HighsModelStatus.kSolutionLimit')
    if damage=='missing':reply.pop('work_limit')
    if damage=='time':reply['native_status']='HighsModelStatus.kTimeLimit'
    if damage=='count':reply['mip_node_count']=2
    if damage=='seed':reply['work_limit']['random_seed']=1
    planner=NativePlanner(Fake(reply),canonicalise_dominated_paid=True)
    cfg=replace(ordinary,node_limit=1)
    if damage:
        with pytest.raises(RuntimeError):planner(s,m,h,cfg)
    else:
        actions,report=planner(s,m,h,cfg)
        assert report['solver_diagnostics']['native_error_type'] is None
        assert report['solver_diagnostics']['work_control']['node_limit']==1


def test_independent_native_auditor_checks_fixed_node_slack_and_failed_receipts():
    from test_native_trace_audit import module,case
    q,r=case();q['work_limit']=dict(node_limit=1,random_seed=0,parallel='off')
    r.update(work_limit=q['work_limit'].copy(),mip_node_count=1,native_status='HighsModelStatus.kSolutionLimit')
    r['statistics']['16']['pt']=2;r['objective']-=8
    auditor=module()
    with pytest.raises(AssertionError):auditor.validate(q,r)
    assert auditor.validate(q,r,allow_dominated_paid_slack=True)==1
    r['mip_node_count']=2
    with pytest.raises(AssertionError):auditor.validate(q,r,allow_dominated_paid_slack=True)
