from dataclasses import replace
from functools import lru_cache
from itertools import combinations
import numpy as np
import pytest
from season_engine import State,Market,prepare
from horizon_forecast import Horizon
from rolling_planner import plan,Settings,_objective
from forecast import select_xi


def setup(gw=36,H=3):
    pos=[1]*2+[2]*5+[3]*5+[4]*3
    p=[dict(id=i+1,position=q,team=f'T{i//3}',price_tenths=50,can_buy=True) for i,q in enumerate(pos)]
    p.extend([dict(p[14],id=16,team='A'),dict(p[14],id=17,team='B'),dict(p[11],id=18,team='C')])
    m=Market.create('2025-26',gw,'2026-01-01T12:00Z','2026-01-01T11:00Z',p)
    state=State('2025-26',gw,tuple((i,50) for i in range(1,16)),250,1)
    rows=[]
    for t,g in enumerate(range(gw,gw+H)):
        for r in p:
            i=r['id'];v=30. if i==1 else 8. if i in [13,14] else 5. if i==15 else (9. if t==0 else 0.) if i==16 else 7. if i==17 else (0. if t==0 else 12.) if i==18 else 3.
            rows.append(dict(gameweek=g,id=i,expected_points=v))
    h=Horizon.create(m,rows,trained_through='2025-12-01T00:00Z',feature_cutoff=m.as_of,source_as_of=m.as_of,model_id='synthetic')
    return state,m,h


def config(**kwargs):return Settings(seconds=10.,bench_weight=0.,terminal_ft_value=0.,terminal_squad_weight=0.,**kwargs)


def test_multigw_rejects_flash_transfer_for_larger_later_gain():
    s,m,h=setup();actions,r=plan(s,m,h,config())
    one=Horizon.create(m,[dict(z) for z in h.forecasts if z['gameweek']==s.gameweek],trained_through='2025-12-01T00:00Z',feature_cutoff=m.as_of,source_as_of=m.as_of,model_id='synthetic')
    short,_=plan(s,m,one,config())
    assert 16 in short[0].buys and 17 in actions[0].buys and 16 not in actions[0].buys
    assert any(18 in a.buys for a in actions[1:]) and r['proven_optimal']
    assert r['objective']>=r['fallback_objective'] and all(v['bank']>=0 for v in r['components']['weeks'])


def test_exact_short_horizon_matches_independent_dynamic_program():
    s,m,h=setup(gw=37,H=2);cfg=config(churn_cost=0.);actions,r=plan(s,m,h,cfg);by=m.indexed();xp=h.values()
    squads=[]
    for mids in combinations([8,9,10,11,12,18],5):
        for forwards in combinations([13,14,15,16,17],3):squads.append(tuple(sorted([1,2,3,4,5,6,7,*mids,*forwards])))
    values={}
    for g in h.gameweeks:
        for ids in squads:
            pp=[dict(by[i],expected_points=xp[(g,i)]) for i in ids];values[g,ids]=select_xi(pp)['expected_points']
    @lru_cache(None)
    def dp(t,owned,ft):
        if t==len(h.gameweeks):return 0.
        ans=-1e9
        for ids in squads:
            n=len(set(ids)-set(owned));hit=4*max(0,n-ft);after=min(5,max(0,ft-n)+1)
            ans=max(ans,values[h.gameweeks[t],ids]-hit+dp(t+1,ids,after))
        return ans
    assert r['objective']==pytest.approx(dp(0,tuple(range(1,16)),1),abs=1e-6)


def test_financial_purchase_lot_reconciliation_and_topup():
    s,m,h=setup(gw=15,H=3);s=replace(s,holdings=tuple((i,40 if i==15 else 50) for i in range(1,16)),bank=0)
    rows=[dict(p,price_tenths=60 if p['id']==15 else 50) for p in m.players];m=Market.create(m.season,m.gameweek,m.deadline,m.as_of,rows)
    actions,r=plan(s,m,h,config());current=s
    for gw,a in zip(h.gameweeks,actions):
        week=Market.create(m.season,gw,m.deadline,m.as_of,rows);p=prepare(current,week,a);current=p.state
        assert current.bank>=0
    assert r['components']['weeks'][1]['next_ft']>=1 and len(actions)==3


def test_input_mutation_cannot_change_frozen_grid_or_market():
    s,m,h=setup();a,report=plan(s,m,h,config())
    value,parts=_objective(s,m,h,a,config())
    assert value==pytest.approx(report['objective'])
    with pytest.raises(TypeError):h.forecasts[0]['expected_points']=999
    with pytest.raises(ValueError,match='origin'):plan(replace(s,gameweek=35),m,h,config())


def test_timeout_incumbent_failure_uses_valid_fallback(monkeypatch):
    import rolling_planner
    from scipy.optimize import OptimizeResult
    s,m,h=setup();monkeypatch.setattr(rolling_planner,'milp',lambda *a,**k:OptimizeResult(status=1,x=None))
    actions,r=plan(s,m,h,config());assert r['selection']=='no valid incumbent' and not r['proven_optimal']
    assert len(actions)==3 and r['objective']==r['fallback_objective']
    prepare(s,m,actions[0])


def test_pruning_retains_owned_and_budget_feasible_baseline():
    s,m,h=setup();a,r=plan(s,m,h,Settings(seconds=10,top_per_position=1,cheap_per_position=1))
    assert r['pool_players']>=15 and len(a)==3
    assert r['objective']>=r['fallback_objective']-1e-6


def test_baseline_solver_timeout_can_keep_owned_squad(monkeypatch):
    import rolling_planner
    s,m,h=setup()
    monkeypatch.setattr(rolling_planner,'optimise',lambda *a,**k:(_ for _ in ()).throw(ValueError('timeout')))
    a,r=plan(s,m,h,config());assert 'held-squad fallback' in r['baseline'];prepare(s,m,a[0])


def test_plan_cli_write_once_and_source_checks(tmp_path,monkeypatch):
    import hashlib,json,sys
    from dataclasses import asdict
    from rolling_planner import main
    s,m,h=setup(gw=38,H=1)
    spec=dict(schema_version=1,market=dict(season=m.season,gameweek=m.gameweek,deadline=m.deadline,as_of=m.as_of,rows=[dict(p) for p in m.players]),state=asdict(s),
        forecast=dict(rows=[dict(r) for r in h.forecasts],**dict(h.provenance)),settings=asdict(config()))
    spec['forecast']['source_hashes']={}
    source=tmp_path/'input.json';source.write_text(json.dumps(spec));out=tmp_path/'output'
    monkeypatch.setattr(sys,'argv',['plan-horizon','--input',str(source),'--sha256',hashlib.sha256(source.read_bytes()).hexdigest(),'--output',str(out)])
    main();r=json.loads((out/'plan.json').read_text());assert r['origin']==38 and len(r['provisional_actions'])==1
    assert r['report']['components']['terminal_ft']==0 and r['report']['components']['terminal_squad_proxy']==0
    with pytest.raises(SystemExit):main()
