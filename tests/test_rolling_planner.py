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


def test_fixed_chips_reconcile_freehit_reversion_wildcard_and_boost():
    s,m,h=setup();s=replace(s,holdings=tuple((i,40 if i==15 else 50) for i in range(1,16)),bank=230,free_transfers=4)
    chips={36:'freehit',37:'wildcard',38:'bboost'};actions,report=plan(s,m,h,config(),chip_schedule=chips)
    current=s
    for gw,a in zip(h.gameweeks,actions):
        p=prepare(current,Market.create(m.season,gw,m.deadline,m.as_of,[dict(z) for z in m.players]),a)
        if gw==36:
            assert p.state.holdings==s.holdings and p.state.bank==s.bank and p.state.free_transfers==4
        if gw==37:assert p.state.free_transfers==4 and dict(p.state.holdings)=={i:dict(current.holdings).get(i,50) for i in (*a.starters,*a.bench)}
        assert p.hits==0;current=p.state
    assert [a.chip for a in actions]==list(chips.values())
    assert report['objective']==pytest.approx(_objective(s,m,h,actions,config())[0])


def test_freehit_terminal_values_apply_to_restored_purchase_ledger():
    s,m,h=setup(gw=20,H=1);cfg=Settings(seconds=5.)
    a,r=plan(s,m,h,cfg,chip_schedule={20:'freehit'})
    assert r['objective']==pytest.approx(_objective(s,m,h,a,cfg)[0])
    assert r['components']['terminal_squad_proxy']==pytest.approx(cfg.terminal_squad_weight*sum(h.values()[20,i] for i,_ in s.holdings))


@pytest.mark.parametrize('schedule',[{36:'3xc',37:'3xc'},{36:'freehit',37:'freehit'},{35:'bboost'},{36:'unknown'}])
def test_chip_schedule_guards(schedule):
    s,m,h=setup()
    with pytest.raises(ValueError):plan(s,m,h,config(),chip_schedule=schedule)


@pytest.mark.parametrize('chips',[{37:'3xc',38:'bboost'},{37:'freehit',38:'3xc'},{37:'wildcard',38:'bboost'}])
def test_chip_milp_matches_exhaustive_two_week_state_search(chips):
    s,m,h=setup(gw=37,H=2);cfg=config();actions,r=plan(s,m,h,cfg,chip_schedule=chips);xp=h.values();by=m.indexed()
    squads=[tuple(sorted([1,2,3,4,5,6,7,*mid,*fwd])) for mid in combinations([8,9,10,11,12,18],5) for fwd in combinations([13,14,15,16,17],3)]
    values={}
    for g in h.gameweeks:
        for ids in squads:
            q=select_xi([dict(by[i],expected_points=xp[g,i]) for i in ids]);v=q['expected_points']
            if chips.get(g)=='3xc':v+=xp[g,q['captain']]
            if chips.get(g)=='bboost':v+=sum(xp[g,i] for i in q['bench'])
            values[g,ids]=v
    @lru_cache(None)
    def dp(t,owned,ft):
        if t==2:return 0.
        g=h.gameweeks[t];chip=chips.get(g);ans=-1e9
        for ids in squads:
            n=len(set(ids)-set(owned));free=chip in ('wildcard','freehit');hits=0 if free else 4*max(0,n-ft)
            ans=max(ans,values[g,ids]-hits-cfg.churn_cost*n+dp(t+1,owned if chip=='freehit' else ids,ft if free else min(5,max(0,ft-n)+1)))
        return ans
    assert r['objective']==pytest.approx(dp(0,tuple(range(1,16)),1),abs=1e-6)


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


def test_lost_selling_profit_changes_affordable_sell_and_rebuy_choice():
    s,m,h=setup();m=Market.create(m.season,m.gameweek,m.deadline,m.as_of,[dict(p,price_tenths=60 if p['id']==15 else 50) for p in m.players])
    rows=[]
    for r in h.forecasts:
        z=dict(r);i=z['id'];t=z['gameweek']-s.gameweek
        if i==15:z['expected_points']=5. if t==0 else 8.
        elif i==16:z['expected_points']=9. if t==0 else 0.
        elif i in (17,18):z['expected_points']=0.
        rows.append(z)
    h=Horizon.create(m,rows,**dict(h.provenance))
    discounted=replace(s,bank=0,holdings=tuple((i,40 if i==15 else 50) for i in range(1,16)))
    at_cost=replace(s,bank=0,holdings=tuple((i,60 if i==15 else 50) for i in range(1,16)))
    keep,_=plan(discounted,m,h,config(churn_cost=0.));trade,_=plan(at_cost,m,h,config(churn_cost=0.))
    assert 15 not in keep[0].sells and 15 in trade[0].sells and 15 in trade[1].buys
    assert 16 in keep[0].buys and 16 in trade[0].buys  # equity-preserving alternative sells a different forward


def test_valid_time_limit_incumbent_is_reconciled_and_not_called_optimal(monkeypatch):
    import rolling_planner
    native=rolling_planner.milp
    def bounded(*a,**k):
        r=native(*a,**k);r.status=1;return r
    monkeypatch.setattr(rolling_planner,'milp',bounded)
    s,m,h=setup();a,r=plan(s,m,h,config());assert r['selection']=='validated time-limit incumbent' and not r['proven_optimal']
    prepare(s,m,a[0])
