import copy
import json
import sys
import pytest
from airsenal_planner import AIrsenalPlanner,AIrsenalProcess
from native_planner import canonical_actions,controlled_settings,NativeTransportError,RESOURCES
from rolling_planner import plan,_objective,_market
from season_engine import prepare
from test_rolling_planner import setup


class Fake:
    def __init__(self,result):self.result=result;self.requests=[]
    def request(self,q):self.requests.append(q);return copy.deepcopy(self.result)


def result(s,m,h,cfg):
    actions,_=plan(s,m,h,cfg);actions=canonical_actions(s,m,h,actions);current=s;outcomes=[]
    for g,a in zip(h.gameweeks,actions):
        p=prepare(current,_market(m,g,h.values()),a)
        points=sum(h.values()[g,i] for i in a.starters)+h.values()[g,a.captain]+.1*sum(h.values()[g,i] for i in a.bench)-p.hits
        outcomes.append(dict(gameweek=g,num_transfers=str(len(a.buys)),chip_played=None,points=points,discount_factor=1.,points_hit=p.hits,free_transfers=p.state.free_transfers,players_in=list(a.buys),players_out=list(a.sells),bank=p.state.bank))
        current=p.state
    return dict(status='completed',discount=1.,bound=None,horizon=len(outcomes),truncated=False,
        best=dict(root_gameweek=s.gameweek,outcomes=outcomes,total_score=sum(r['points'] for r in outcomes)))


def test_complete_native_plan_validates_but_never_claims_optimality():
    s,m,h=setup();cfg=controlled_settings(5.);backend=Fake(result(s,m,h,cfg))
    actions,report=AIrsenalPlanner(backend)(s,m,h,cfg)
    assert not report['fallback_retained'] and not report['proven_optimal']
    assert report['selected_plan_bound']['upper_objective'] is None
    assert _objective(s,m,h,actions,cfg)[0]==pytest.approx(report['objective'])
    assert 'total_points' not in backend.requests[0]['state']
    assert len(actions)==len(h.gameweeks)


@pytest.mark.parametrize('damage',['cash','ft','hits','incomplete','late','objective','id','outcome','move','bound'])
def test_corrupt_native_plan_cannot_change_the_validated_baseline(damage):
    s,m,h=setup();cfg=controlled_settings(5.);r=result(s,m,h,cfg);first=r['best']['outcomes'][0]
    if damage=='cash':first['bank']+=1
    elif damage=='ft':first['free_transfers']+=1
    elif damage=='hits':first['points_hit']+=4
    elif damage=='incomplete':r['best']['outcomes'].pop()
    elif damage=='late':first['gameweek']+=1
    elif damage=='objective':r['best']['total_score']+=100
    elif damage=='id':first['players_in'].append(99999)
    elif damage=='outcome':first['actual']=10
    elif damage=='move':first['num_transfers']='99'
    else:r['bound']=r['best']['total_score']
    actions,report=AIrsenalPlanner(Fake(r))(s,m,h,cfg)
    assert report['fallback_retained'] and report['solver_diagnostics']['native_error_type']
    assert report['selected_plan_bound']['relative_gap'] is None
    prepare(s,m,actions[0])


def test_worker_failure_is_explicit_not_a_successful_solve():
    s,m,h=setup();actions,report=AIrsenalPlanner(Fake(dict(status='failed',error_type='NativeBudgetExpired')))(s,m,h,controlled_settings())
    assert report['fallback_retained'] and report['solver_diagnostics']['native_error_type']=='NativeBudgetExpired'
    prepare(s,m,actions[0])


def test_actor_checks_runtime_and_closes_on_bad_startup(tmp_path,monkeypatch):
    import airsenal_planner as module
    recipe=json.loads((RESOURCES/'airsenal_solver_recipe.json').read_text())
    meta=dict(status='ready',revision=recipe['revision'],source_sha256=recipe['source_sha256'],versions={'airsenal':recipe['package_version'],**recipe['optional_planner_dependencies'],**recipe['other_observed_dependencies']},network_disabled=True,serial=True,discount=1.)
    script=tmp_path/'actor.py'
    script.write_text('import json,sys\nprint('+repr(json.dumps(meta))+',flush=True)\nfor line in sys.stdin:print(line.strip(),flush=True)\n')
    monkeypatch.setattr(module,'WORKER',script);monkeypatch.setattr(module,'verified_sources',lambda *a:{})
    with AIrsenalProcess(sys.executable,tmp_path,tmp_path/'first.log',tmp_path/'new-home') as actor:
        assert actor.request(dict(seconds=.1,value=3))['value']==3
        process=actor.process
    assert process.poll() is not None and actor.closed
    meta['discount']=.9
    script.write_text('import time\nprint('+repr(json.dumps(meta))+',flush=True)\ntime.sleep(5)\n')
    with pytest.raises(NativeTransportError,match='metadata'):AIrsenalProcess(sys.executable,tmp_path,tmp_path/'bad.log',tmp_path/'new-home')
