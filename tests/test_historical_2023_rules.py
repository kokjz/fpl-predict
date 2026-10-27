"""Historical rule differences must change finance, not future outcomes."""
import ast
import copy
from dataclasses import asdict,replace
from functools import lru_cache
from itertools import combinations
import pytest
from season_engine import State,Market,prepare
from horizon_forecast import Horizon
from rolling_planner import plan,_market,_objective
from native_solver_worker import patched_tree,validate_request,read_json,RESOURCES
from test_season_engine import state,market,action,roster
from test_rolling_planner import setup,config
from test_native_solver_worker import request
from forecast import select_xi


def test_two_transfer_cap_no_topup_and_chip_reset_with_fh_reversion():
    s=state(16,ft=2,season='2023-24');m=market(16,season=s.season)
    assert prepare(s,m,action()).state.free_transfers==2
    for chip in ('wildcard','freehit'):
        p=prepare(s,m,action(chip=chip))
        assert p.hits==0 and p.state.free_transfers==1
        assert p.state.holdings==s.holdings and p.state.bank==s.bank
    with pytest.raises(ValueError,match='season cap'):prepare(replace(s,free_transfers=3),m,action())


def test_wildcard_windows_are_20_then_21_and_other_chips_annual():
    s=state(20,ft=2,season='2023-24');p=prepare(s,market(20,season=s.season),action(chip='wildcard'))
    p=prepare(p.state,market(21,season=s.season),action(chip='wildcard'))
    assert p.state.used_chips==( ('wildcard',2),('wildcard',21) ) and p.state.free_transfers==1
    with pytest.raises(ValueError,match='already used'):prepare(replace(p.state,gameweek=22),market(22,season=s.season),action(chip='wildcard'))
    for chip in ('freehit','bboost','3xc'):
        p=prepare(s,market(20,season=s.season),action(chip=chip))
        with pytest.raises(ValueError,match='already used'):prepare(p.state,market(21,season=s.season),action(chip=chip))
    with pytest.raises(ValueError,match='history'):prepare(replace(s,used_chips=(('wildcard',20),)),market(20,season=s.season),action())


def test_independent_auditor_agrees_with_historical_finances():
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('historical_auditor',Path(__file__).parents[1]/'tools/audit_season_path.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    s=state(20,ft=2,season='2023-24')
    for g,chip in [(20,'wildcard'),(21,'wildcard'),(22,'freehit'),(23,None),(24,None)]:
        m=market(g,season=s.season);a=action(chip=chip);p=prepare(s,m,a)
        independent,_,hits,_=audit.advance(asdict(s),dict(season=m.season,gameweek=g,rows=[dict(p) for p in m.players]),asdict(a))
        assert independent['free_transfers']==p.state.free_transfers and independent['bank']==p.state.bank and hits==p.hits
        assert set(map(tuple,independent['used_chips']))==set(p.state.used_chips)
        s=p.state


@pytest.mark.parametrize('schedule',[{}, {36:'freehit'}, {36:'wildcard',37:'bboost'}])
def test_historical_milp_matches_independent_small_state_search(schedule):
    s,m,h=setup(gw=36,H=3);s=replace(s,season='2023-24',free_transfers=2)
    m=Market.create(s.season,m.gameweek,m.deadline,m.as_of,[dict(p) for p in m.players]);h=Horizon.create(m,[dict(v) for v in h.forecasts],**dict(h.provenance));cfg=config(churn_cost=0.)
    actions,report=plan(s,m,h,cfg,chip_schedule=schedule);xp=h.values();by=m.indexed()
    squads=[tuple(sorted([1,2,3,4,5,6,7,*mi,*fw])) for mi in combinations([8,9,10,11,12,18],5) for fw in combinations([13,14,15,16,17],3)]
    values={}
    for g in h.gameweeks:
        for ids in squads:
            q=select_xi([dict(by[i],expected_points=xp[g,i]) for i in ids]);v=q['expected_points']
            if schedule.get(g)=='bboost':v+=sum(xp[g,i] for i in q['bench'])
            values[g,ids]=v
    @lru_cache(None)
    def dp(t,ids,ft):
        if t==3:return 0.
        g=h.gameweeks[t];chip=schedule.get(g);free=chip in ('wildcard','freehit');answer=-1e9
        for nxt in squads:
            n=len(set(nxt)-set(ids));hits=0 if free else 4*max(0,n-ft)
            answer=max(answer,values[g,nxt]-hits+dp(t+1,ids if chip=='freehit' else nxt,1 if free else min(2,max(0,ft-n)+1)))
        return answer
    assert report['objective']==pytest.approx(dp(0,tuple(range(1,16)),2),abs=1e-6)
    current=s
    for g,a in zip(h.gameweeks,actions):current=prepare(current,_market(m,g,xp),a).state;assert current.free_transfers<=2


def test_native_request_uses_historical_cap_and_wildcard_boundary():
    recipe=read_json((RESOURCES/'native_solver_recipe.json').read_bytes());q=request(gw=20,H=2);q['market']['season']=q['state']['season']='2023-24';q['chip_schedule']={'20':'wildcard','21':'wildcard'}
    validate_request(q,recipe);bad=copy.deepcopy(q);bad['state']['free_transfers']=3
    with pytest.raises(ValueError,match='season cap'):validate_request(bad,recipe)
    bad=copy.deepcopy(q);bad['chip_schedule']={'20':'3xc','21':'3xc'}
    with pytest.raises(ValueError,match='Illegal'):validate_request(bad,recipe)


def test_native_old_transfer_ast_is_separate_and_exactly_admitted():
    source='''
def solve(data,fts,transfer_count,use_wc,use_fh,m):
    players=[];gws=[20,21];buy_price={};sell_price={};price_modified_players=[]
    squad={};squad_fh={};in_the_bank={};transfer_out_first={};fh_sell_price={}
    ft_states=[0,1,2,3,4,5]
    fts=int_vars(gws,name='ft',lb=0,ub=5)
    raw_gw_ft={w:fts[w]-transfer_count[w]+1-use_wc[w]-use_fh[w] for w in gws}
    m.addConstrs([raw_gw_ft[w]>=6-big_m*(1-ft_above_ub[w]) for w in gws])
    m.addConstrs([raw_gw_ft[w]<=5+big_m*ft_above_ub[w] for w in gws])
    m.addConstrs([fts[w+1]<=5+big_m*(1-ft_above_ub[w]) for w in gws])
    m.addConstrs([fts[w+1]>=5-big_m*(1-ft_above_ub[w]) for w in gws])
    m.addConstrs([fh_sell_price[p]*squad[p,w-1]+in_the_bank[w-1]>=fh_sell_price[p]*squad_fh[p,w] for p in players for w in gws])
'''
    default,default_hash=patched_tree(source);old,old_hash=patched_tree(source,legacy_transfer_rules=True)
    assert default_hash!=old_hash and default_hash==patched_tree(source)[1]
    assignments={n.targets[0].id:n.value for n in ast.walk(old) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
    assert ast.literal_eval(assignments['ft_states'])==[0,1,2]
    assert next(k.value.value for k in assignments['fts'].keywords if k.arg=='ub')==2
    expr=compile(ast.Expression(assignments['raw_gw_ft']),'test','eval')
    context=dict(data={'chip_transfer_weeks':[20]},gws=[20,21],fts={20:2,21:1},transfer_count={20:0,21:0})
    assert eval(expr,context)=={20:1,21:2}
    with pytest.raises(ValueError,match='historical FT'):patched_tree(source.replace('ub=5','ub=4'),legacy_transfer_rules=True)


@pytest.mark.parametrize('season,g,start',[('2023-24',21,21),('2023-24',20,21),('2024-25',19,20),('2025-26',20,20),('2025-26',19,20),('2025-26',2,2)])
def test_used_chip_history_cannot_include_this_or_a_future_window(season,g,start):
    s=replace(state(g,season=season),used_chips=(('wildcard',start),))
    with pytest.raises(ValueError,match='precede'):prepare(s,market(g,season=season),action())
    q=request(gw=g,H=1);q['market']['season']=q['state']['season']=season;q['state']['used_chips']=[['wildcard',start]]
    with pytest.raises(ValueError,match='used-chip'):validate_request(q,read_json((RESOURCES/'native_solver_recipe.json').read_bytes()))
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('historical_auditor',Path(__file__).parents[1]/'tools/audit_season_path.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    m=market(g,season=season)
    # The same action/context is valid when its history contains only an earlier
    # window (or no used window at GW2). This excludes unrelated audit failures.
    valid=replace(s,used_chips=(('wildcard',2),) if g>2 else ())
    result,_,_,_=audit.advance(asdict(valid),dict(season=season,gameweek=g,rows=[dict(p) for p in m.players]),asdict(action()))
    assert result['gameweek']==g+1
    with pytest.raises(AssertionError):
        audit.advance(asdict(s),dict(season=season,gameweek=g,rows=[dict(p) for p in m.players]),asdict(action()))


@pytest.mark.parametrize('season,extra',[('2023-24',1),('2024-25',4),('2025-26',4)])
def test_complete_historical_bootstrap_checks_its_own_transfer_cap(season,extra):
    from season_engine import rules_for,audit_bootstrap
    rules=rules_for(season);b=dict(game_settings=dict(squad_squadplay=11,squad_squadsize=15,squad_team_limit=3,squad_total_spend=1000,transfers_cap=20,transfers_sell_on_fee=.5,max_extra_free_transfers=extra),chips=[dict(name=w['name'],start_event=w['start'],stop_event=w['stop'],number=1,overrides={}) for w in rules['chip_windows']])
    assert audit_bootstrap(b,season,1)['active_rules_compatible']
    b['game_settings']['max_extra_free_transfers']=extra+1
    assert 'max_extra_free_transfers' in audit_bootstrap(b,season,1)['mismatches']
