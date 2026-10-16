import copy
import json
import sys
import pytest
from native_planner import NativeProcess,NativeTransportError,NativePlanner,CanonicalPlanner,canonical_actions,controlled_settings,retained_bound,RESOURCES
from rolling_planner import plan,Settings,_objective,_market
from season_engine import prepare,available_transfers,rules_for
from test_rolling_planner import setup


def response(s,m,h,cfg):
    actions,_=plan(s,m,h,cfg);current=s;rows=[];statistics={}
    for g,a in zip(h.gameweeks,actions):
        p=prepare(current,_market(m,g,h.values()),a);rows.extend(dict(id=i,week=g,squad=1) for i in sorted(v['id'] for v in p.squad))
        statistics[str(g)]=dict(ft=available_transfers(current,rules_for(s.season)),pt=p.hits/4,itb=p.state.bank/10.)
        current=p.state
    value,_=_objective(s,m,h,canonical_actions(s,m,h,actions),cfg)
    return dict(status='completed',native_status='HighsModelStatus.kOptimal',objective=value,dual_bound=value,mip_gap=0.,statistics=statistics,picks=rows)


class Fake:
    def __init__(self,value):self.value=value;self.requests=[]
    def request(self,q):self.requests.append(q);return copy.deepcopy(self.value)


def test_native_proposal_canonical_finance_objective_and_transport_whitelist():
    s,m,h=setup();cfg=controlled_settings(5.);backend=Fake(response(s,m,h,cfg));a,r=NativePlanner(backend)(s,m,h,cfg)
    assert r['proven_optimal'] and r['selected_plan_bound']['relative_gap']==0. and not r['fallback_retained']
    assert _objective(s,m,h,a,cfg)[0]==pytest.approx(r['objective'])
    q=backend.requests[0];assert 'total_points' not in q['state'] and all(not {'actual','minutes','cards'}&set(p) for p in q['market']['rows'])
    assert q['through']==38 and q['seconds']<=5.
    with pytest.raises(ValueError,match='declared'):NativePlanner(backend)(s,m,h,Settings())


@pytest.mark.parametrize('damage',['cash','roster','objective','status'])
def test_invalid_native_proposal_uses_valid_baseline_without_bound(damage):
    s,m,h=setup();cfg=controlled_settings(5.);r=response(s,m,h,cfg)
    if damage=='cash':r['statistics']['36']['itb']+=1.
    elif damage=='roster':r['picks'][0]['id']=999
    elif damage=='objective':r['objective']+=100.
    else:r['native_status']='HighsModelStatus.kInfeasible'
    actions,report=NativePlanner(Fake(r))(s,m,h,cfg);assert report['fallback_retained'] and not report['proven_optimal'] and report['selected_plan_bound']['upper_objective'] is None
    prepare(s,m,actions[0])


def test_failed_native_attempt_retains_baseline_and_unknown_bound():
    s,m,h=setup();a,r=NativePlanner(Fake(dict(status='failed',error_type='NoFeasibleIncumbent')))(s,m,h,controlled_settings())
    assert r['fallback_retained'] and r['selected_plan_bound']['relative_gap'] is None
    assert r['solver_diagnostics']['native_error_type']=='NoFeasibleIncumbent';prepare(s,m,a[0])


def test_canonical_policy_is_idempotent_preserves_finance_and_reports_selected_bound():
    s,m,h=setup();cfg=controlled_settings(5.);a,r=CanonicalPlanner()(s,m,h,cfg)
    assert canonical_actions(s,m,h,a)==a and r['canonical_selection']
    assert _objective(s,m,h,a,cfg)[0]==pytest.approx(r['objective'])
    assert retained_bound(10.,9.)['status']=='inconsistent_dual' and retained_bound(10.,None)['relative_gap'] is None
    with pytest.raises(ValueError,match='Incomplete'):canonical_actions(s,m,h,a[:-1])


def actor(tmp_path,monkeypatch,mode='echo'):
    import native_planner
    recipe=json.loads((RESOURCES/'native_solver_recipe.json').read_text());meta=dict(status='ready',revision=recipe['revision'],source_sha256=recipe['source_sha256'],highspy=recipe['highspy_version'],network_disabled=True,threads=2)
    script=tmp_path/'actor.py'
    script.write_text("import sys,json,time,os\nprint("+repr(json.dumps(meta))+",flush=True)\nfor line in sys.stdin:\n q=json.loads(line)\n"+(" time.sleep(5)\n" if mode=='timeout' else " print('malformed',flush=True)\n" if mode=='malformed' else " print(json.dumps({'status':'completed','echo':q,'private_env_present':'PRIVATE_AUTH_HINT' in os.environ}),flush=True)\n"))
    monkeypatch.setattr(native_planner,'WORKER',script);monkeypatch.setattr(native_planner,'verified_sources',lambda *a:{})
    return NativeProcess(sys.executable,tmp_path,tmp_path/'stderr.log')


def test_transport_serial_requests_no_secret_environment_and_clean_close(tmp_path,monkeypatch):
    monkeypatch.setenv('PRIVATE_AUTH_HINT','synthetic-should-not-forward')
    with actor(tmp_path,monkeypatch) as worker:
        for i in range(2):
            r=worker.request(dict(seconds=.1,index=i));assert r['echo']['index']==i and not r['private_env_present']
        process=worker.process
    assert process.poll() is not None and worker.closed


@pytest.mark.parametrize('mode',['timeout','malformed'])
def test_transport_failure_is_fatal_and_stops_worker(tmp_path,monkeypatch,mode):
    worker=actor(tmp_path,monkeypatch,mode)
    with pytest.raises(NativeTransportError):worker.request(dict(seconds=.1),timeout=.03 if mode=='timeout' else 1.)
    assert worker.closed and worker.process.poll() is not None
