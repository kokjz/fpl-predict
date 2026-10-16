"""Bounded multi-GW mean-point MILP with exact constant-quote finance and FT state."""
from collections import Counter
from dataclasses import dataclass
import time
import warnings
import numpy as np
import pandas as pd
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
from forecast import select_xi
from season_engine import Action,Market,prepare,rules_for,available_transfers
from selection_benchmark import optimise,POSITIONS,sell_price


@dataclass(frozen=True)
class Settings:
    seconds:float=30.
    top_per_position:int=12
    cheap_per_position:int=6
    bench_weight:float=.1
    terminal_ft_value:float=1.
    terminal_squad_weight:float=.05
    churn_cost:float=.0001

    def __post_init__(self):
        if not np.isfinite([self.seconds,self.bench_weight,self.terminal_ft_value,self.terminal_squad_weight,self.churn_cost]).all() or not 0<self.seconds<=120:raise ValueError('Invalid bounded solver settings')
        if not 0<=self.bench_weight<=1 or min(self.terminal_ft_value,self.terminal_squad_weight,self.churn_cost)<0:raise ValueError('Invalid objective weights')
        if type(self.top_per_position) is not int or type(self.cheap_per_position) is not int or min(self.top_per_position,self.cheap_per_position)<1:raise ValueError('Invalid pool limits')


def _market(market,gw,xp):
    return Market.create(market.season,gw,market.deadline,market.as_of,[dict(p,expected_points=xp[(gw,p['id'])]) for p in market.players])


def _objective(state,market,horizon,actions,cfg):
    xp=horizon.values();value=0.;parts=[];last=None
    for gw,action in zip(horizon.gameweeks,actions):
        initial=not state.holdings;m=_market(market,gw,xp);p=prepare(state,m,action)
        roster={r['id'] for r in p.squad};xi=sum(xp[(gw,i)] for i in action.starters);capt=xp[(gw,action.captain)]
        reserve=cfg.bench_weight*sum(xp[(gw,i)] for i in roster-set(action.starters))
        churn=0. if initial else cfg.churn_cost*p.transfers
        week_value=xi+capt+reserve-p.hits-churn;value+=week_value
        parts.append(dict(gameweek=gw,xi_mean=xi,captain_mean=capt,reserve_proxy=reserve,hits=p.hits,churn_penalty=churn,bank=p.state.bank,next_ft=p.state.free_transfers))
        state=p.state;last=roster
    ft=cfg.terminal_ft_value*state.free_transfers if horizon.gameweeks[-1]<38 else 0.
    terminal=cfg.terminal_squad_weight*sum(np.mean([xp[(g,i)] for g in horizon.gameweeks[-2:]]) for i in last) if horizon.gameweeks[-1]<38 else 0.
    return float(value+ft+terminal),dict(weeks=parts,terminal_ft=ft,terminal_squad_proxy=float(terminal))


def _fallback(state,market,horizon,baseline):
    xp=horizon.values();actions=[]
    for k,gw in enumerate(horizon.gameweeks):
        ids=set(baseline['ledger']) if k==0 else set(dict(state.holdings));m=_market(market,gw,xp)
        squad=[p for p in m.players if p['id'] in ids];s=select_xi(squad)
        a=Action(tuple(sorted(ids-set(dict(state.holdings)))),tuple(sorted(set(dict(state.holdings))-ids)),tuple(s['starters']),tuple(s['bench']),s['captain'],s['vice'])
        state=prepare(state,m,a).state;actions.append(a)
    return actions


def plan(state,market,horizon,settings=None):
    cfg=settings or Settings();start=time.monotonic()
    if (state.season,state.gameweek,market.as_of)!=(horizon.season,horizon.origin,horizon.as_of) or market.gameweek!=state.gameweek:raise ValueError('Planner/forecast origin mismatch')
    if not horizon.gameweeks or len(horizon.gameweeks)>8:raise ValueError('Invalid horizon')
    from horizon_forecast import Horizon
    checked=Horizon.create(market,[dict(r) for r in horizon.forecasts],**dict(horizon.provenance))
    if checked.gameweeks!=horizon.gameweeks:raise ValueError('Unvalidated horizon')
    xp=horizon.values();allids={p['id'] for p in market.players}
    if set(xp)!={(g,i) for g in horizon.gameweeks for i in allids}:raise ValueError('Forecast coverage differs')
    rows=[dict(fpl_code=p['id'],position=p['position'],team=p['team'],price_tenths=p['price_tenths'],can_buy=int(p['can_buy']),prior_minutes=0.,ownership=0.,expected_points=xp[(state.gameweek,p['id'])]) for p in market.players]
    f=pd.DataFrame(rows);old=dict(state.holdings);rules=rules_for(state.season)
    baseline_status='full-market one-GW solution'
    try:
        baseline=optimise(f,'expected_points',owned=old or None,bank=state.bank,free_transfers=max(1,available_transfers(state,rules)),seconds=min(5.,cfg.seconds/4))
    except ValueError:
        if not old:raise ValueError('No validated opening-squad baseline') from None
        baseline={'ledger':old};baseline_status='held-squad fallback; one-GW solve unavailable'
    fallback=_fallback(state,market,horizon,baseline);fallback_value,_=_objective(state,market,horizon,fallback,cfg)
    # Preserve owned IDs and a full-market feasible baseline, then add form/budget candidates.
    pool=set(old)|set(baseline['ledger'])
    for pos in POSITIONS:
        eligible=f[f.position.eq(pos)&f.can_buy.eq(1)].copy()
        eligible['horizon_xp']=[sum(xp[(g,int(i))] for g in horizon.gameweeks) for i in eligible.fpl_code]
        pool.update(map(int,eligible.sort_values(['horizon_xp','fpl_code'],ascending=[False,True]).head(cfg.top_per_position).fpl_code))
        pool.update(map(int,eligible.sort_values(['price_tenths','fpl_code']).head(cfg.cheap_per_position).fpl_code))
    players=sorted([dict(p) for p in market.players if p['id'] in pool],key=lambda p:p['id']);n=len(players);H=len(horizon.gameweeks)
    c=[];lo=[];hi=[];groups=[]
    def var(cost=0.,upper=1,lower=0):
        i=len(c);c.append(cost);lo.append(lower);hi.append(upper);return i
    for t,gw in enumerate(horizon.gameweeks):
        cols={name:[] for name in ['old','new','buy','sell_old','sell_new','xi','captain']}
        for p in players:
            q=xp[(gw,p['id'])]
            terminal=cfg.terminal_squad_weight*np.mean([xp[(g,p['id'])] for g in horizon.gameweeks[-2:]]) if t==H-1 and gw<38 else 0.
            for name in cols:
                cost=-cfg.bench_weight*q-terminal if name in ('old','new') else -(1-cfg.bench_weight)*q if name=='xi' else -q if name=='captain' else cfg.churn_cost if name=='buy' and (old or t) else 0.
                upper=int(p['id'] in old) if name=='old' else int(p['can_buy']) if name=='buy' else 1
                cols[name].append(var(float(cost),upper))
        funds=state.bank+sum(sell_price(price,next(p['price_tenths'] for p in players if p['id']==i)) for i,price in old.items())
        cols.update(bank=var(upper=funds),ft=var(upper=5),used=var(upper=5),paid=var(4.,15),after=var(-cfg.terminal_ft_value if t==H-1 and gw<38 else 0.,5,1),excess=var(),cap=var(),repaired=var())
        groups.append(cols)
    rix=[];cix=[];vals=[];lower=[];upper=[]
    def add(row,l=-np.inf,u=np.inf):
        k=len(lower)
        for i,v in row.items():
            if v:rix.append(k);cix.append(i);vals.append(v)
        lower.append(l);upper.append(u)
    counts=Counter(p['team'] for p in players if p['id'] in old);needs_repair=any(v>3 for v in counts.values())
    for t,(gw,a) in enumerate(zip(horizon.gameweeks,groups)):
        prev=groups[t-1] if t else None
        for i,p in enumerate(players):
            initial=int(p['id'] in old)
            row={a['old'][i]:1,a['sell_old'][i]:1}
            if prev:row[prev['old'][i]]=-1
            add(row,initial if not prev else 0,initial if not prev else 0)
            row={a['new'][i]:1,a['buy'][i]:-1,a['sell_new'][i]:1}
            if prev:row[prev['new'][i]]=-1
            add(row,0,0)
            row={a['sell_new'][i]:1}
            if prev:row[prev['new'][i]]=-1
            add(row,u=0)
            row={a['buy'][i]:1}
            if prev:row.update({prev['old'][i]:1,prev['new'][i]:1})
            add(row,u=1 if prev else 1-initial)
            add({a['old'][i]:1,a['new'][i]:1},u=1)
            add({a['xi'][i]:1,a['old'][i]:-1,a['new'][i]:-1},u=0)
            add({a['captain'][i]:1,a['xi'][i]:-1},u=0)
        for pos,count in POSITIONS.items():
            ii=[i for i,p in enumerate(players) if p['position']==pos]
            add({a[k][i]:1 for k in ('old','new') for i in ii},count,count)
            add({a['xi'][i]:1 for i in ii},{1:1,2:3,3:2,4:1}[pos],{1:1,2:5,3:5,4:3}[pos])
        add({i:1 for i in a['xi']},11,11);add({i:1 for i in a['captain']},1,1)
        if needs_repair:
            row={a['repaired']:1,**{i:-1 for i in a['buy']}};add(row,u=0 if not prev else np.inf)
            if prev:
                add({a['repaired']:1,prev['repaired']:-1},l=0)
                row={a['repaired']:1,prev['repaired']:-1,**{i:-1 for i in a['buy']}};add(row,u=0)
            add({**{i:1 for i in a['buy']},a['repaired']:-15},u=0)
        else:add({a['repaired']:1},1,1)
        for team in sorted({p['team'] for p in players}):
            excess=max(0,counts[team]-3) if needs_repair else 0
            row={a[k][i]:1 for k in ('old','new') for i,p in enumerate(players) if p['team']==team};row[a['repaired']]=excess
            add(row,u=3+excess)
        row={a['bank']:1}
        if prev:row[prev['bank']]=-1
        for i,p in enumerate(players):
            row[a['buy'][i]]=p['price_tenths'];row[a['sell_new'][i]]=-p['price_tenths']
            row[a['sell_old'][i]]=-sell_price(old.get(p['id'],p['price_tenths']),p['price_tenths'])
        add(row,state.bank if not prev else 0,state.bank if not prev else 0)
        if gw==1:
            for key,v in [('ft',0),('used',0),('paid',0),('after',1)]:add({a[key]:1},v,v)
            continue
        row={a['ft']:1}
        topup=rules['ft_topups'].get(str(gw))
        if prev and topup is None:row[prev['after']]=-1
        value=topup if topup is not None else (available_transfers(state,rules) if not prev else 0)
        add(row,value,value)
        add({a['used']:1,a['ft']:-1},u=0)
        add({a['used']:1,**{i:-1 for i in a['buy']}},u=0)
        add({a['used']:1,a['ft']:-1,a['excess']:-15},l=-15)
        add({a['used']:1,a['excess']:15,**{i:-1 for i in a['buy']}},l=0)
        add({a['paid']:1,a['used']:1,**{i:-1 for i in a['buy']}},0,0)
        add({a['after']:1,a['ft']:-1,a['used']:1},u=1)
        add({a['after']:1,a['ft']:-1,a['used']:1,a['cap']:6},l=1)
        add({a['after']:1,a['cap']:-6},l=-1)
    matrix=coo_matrix((vals,(rix,cix)),shape=(len(lower),len(c))).tocsc()
    remaining=max(.01,cfg.seconds-(time.monotonic()-start))
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message='Unrecognized options detected:.*threads.*',category=RuntimeWarning)
        result=milp(np.array(c),integrality=np.ones(len(c)),bounds=Bounds(lo,hi),constraints=LinearConstraint(matrix,lower,upper),options=dict(time_limit=remaining,mip_rel_gap=1e-8,threads=2))
    if result.status==2:raise ValueError('MILP infeasible despite validated baseline')
    selected=fallback;reason='no valid incumbent';solution_value=None
    if result.x is not None and result.status in (0,1):
        rounded=np.rint(result.x);residual=matrix@rounded
        if np.max(np.abs(result.x-rounded))<=1e-5 and np.all(rounded>=np.array(lo)-1e-6) and np.all(rounded<=np.array(hi)+1e-6) and np.all(residual>=np.array(lower)-1e-6) and np.all(residual<=np.array(upper)+1e-6):
            actions=[];current=state
            for gw,a in zip(horizon.gameweeks,groups):
                ids={p['id'] for i,p in enumerate(players) if rounded[a['old'][i]]+rounded[a['new'][i]]>.5}
                xi=tuple(p['id'] for i,p in enumerate(players) if rounded[a['xi'][i]]>.5);capt=next(p['id'] for i,p in enumerate(players) if rounded[a['captain'][i]]>.5)
                bench=tuple(sorted(ids-set(xi),key=lambda i:(next(p['position'] for p in players if p['id']==i)==1,-xp[(gw,i)],i)))
                vice=next(i for i in sorted(xi,key=lambda i:(-xp[(gw,i)],i)) if i!=capt)
                action=Action(tuple(sorted(ids-set(dict(current.holdings)))),tuple(sorted(set(dict(current.holdings))-ids)),xi,bench,capt,vice)
                prepared=prepare(current,_market(market,gw,xp),action)
                if prepared.state.bank!=int(rounded[a['bank']]) or prepared.state.free_transfers!=int(rounded[a['after']]) or prepared.hits!=4*int(rounded[a['paid']]):raise ValueError('Solver/engine finance or FT mismatch')
                current=prepared.state;actions.append(action)
            solution_value,_=_objective(state,market,horizon,actions,cfg)
            if not np.isclose(solution_value,-np.dot(c,rounded),rtol=0,atol=1e-5):raise ValueError('Solver/objective reconciliation failed')
            if solution_value>=fallback_value-1e-7:selected=actions;reason='optimal restricted pool' if result.status==0 else 'validated time-limit incumbent'
    value,parts=_objective(state,market,horizon,selected,cfg)
    report=dict(objective=value,components=parts,fallback_objective=fallback_value,solver_objective=solution_value,
        status=int(result.status),selection=reason,baseline=baseline_status,proven_optimal=bool(result.status==0 and selected is not fallback),
        mip_gap=float(result.mip_gap) if getattr(result,'mip_gap',None) is not None else None,
        seconds=time.monotonic()-start,pool_players=n,full_market_players=len(market.players),variables=len(c),constraints=len(lower),
        scope='Deterministic origin-frozen1–8GWforecast, constant quotes/roster, restricted candidate pool, no chips or expected autosub objective; commit first action only')
    return selected,report


def main():
    import argparse,json
    from dataclasses import asdict
    from pathlib import Path
    from experiment_runner import file_hash
    from season_engine import State
    from horizon_forecast import Horizon
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Output exists; preserve prior evidence')
    if file_hash(a.input)!=a.sha256:p.error('Input checksum mismatch')
    spec=json.loads(a.input.read_text())
    if spec.get('schema_version')!=1:p.error('Unsupported planning input')
    m=Market.create(**spec['market']);v=dict(spec['state'])
    for k in ('holdings','used_chips'):v[k]=tuple(tuple(z) for z in v.get(k,[]))
    state=State(**v);h=Horizon.create(m,**spec['forecast']);cfg=Settings(**spec.get('settings',{}))
    actions,report=plan(state,m,h,cfg);a.output.mkdir(parents=True)
    result=dict(schema_version=1,scope='Experimental multiGW plan; only first action eligible for currentdeadline after review; no account writes',
        input_sha256=file_hash(a.input),engine_sha256=file_hash(Path(__file__)),forecast_adapter_sha256=file_hash(Path(__file__).with_name('horizon_forecast.py')),
        state_engine_sha256=file_hash(Path(__file__).with_name('season_engine.py')),settings=asdict(cfg),
        origin=state.gameweek,as_of=m.as_of,immediate_action=asdict(actions[0]),provisional_actions=[asdict(v) for v in actions],report=report)
    (a.output/'plan.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
