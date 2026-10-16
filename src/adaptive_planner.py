"""Bounded chip-calendar search and shared-plan sensitivity scenarios.

Chip timing is heuristic; each candidate schedule's squad/finance problem is
solved by the fixed-schedule MILP. Only the first action may be committed.
"""
from dataclasses import dataclass,replace
from functools import lru_cache
import math,time
from urllib.parse import urlsplit
import numpy as np
from availability_evidence import utc
from horizon_forecast import Horizon
from rolling_planner import plan,_objective,_market,Settings
from season_engine import rules_for,prepare


@dataclass(frozen=True)
class Budget:
    seconds:float=60.
    solve_seconds:float=2.
    max_trials:int=40

    def __post_init__(self):
        if not all(math.isfinite(v) for v in [self.seconds,self.solve_seconds]) or not 0<self.solve_seconds<=self.seconds<=120:raise ValueError('Invalid adaptive time budget')
        if type(self.max_trials) is not int or not 1<=self.max_trials<=80:raise ValueError('Invalid trial limit')


def scenario(base,market,adjustments):
    """Manual evidence-grounded XP sensitivities, never inferred probabilities.

    Adjustments: id, gameweeks, multiplier[0,2], reason, available_at, source_url.
    Returns a new grid; does not alter the base or assign a recovery date.
    """
    if (base.season,base.origin,base.as_of)!=(market.season,market.gameweek,market.as_of):raise ValueError('Scenario/market origin mismatch')
    xp=base.values();seen=set();evidence=[]
    for a in adjustments:
        if set(a)!={'id','gameweeks','multiplier','reason','available_at','source_url'}:raise ValueError('Invalid scenario fields')
        u=urlsplit(a['source_url'])
        if u.scheme!='https' or not u.hostname or u.username or u.password or not a['reason'].strip():raise ValueError('Require sourced scenario rationale')
        if utc(a['available_at'])>utc(market.as_of):raise ValueError('Post-origin evidence')
        scale=a['multiplier']
        if not math.isfinite(scale) or not 0<=scale<=2 or not a['gameweeks']:raise ValueError('Invalid sensitivity')
        for g in a['gameweeks']:
            key=(g,a['id'])
            if key not in xp or key in seen:raise ValueError('Unknown/duplicate scenario cell')
            seen.add(key);xp[key]*=scale
        evidence.append(dict(a))
    h=Horizon.create(market,[dict(gameweek=g,id=i,expected_points=v) for (g,i),v in xp.items()],
        **dict(base.provenance,model_id=str(base.provenance['model_id'])+'/manual-sensitivity'))
    return h,evidence


def calendar(state,through,gains,*,blocked=()):
    """Maximum additive opportunity assignment, not a full squad optimisation.

    gains maps (chip,start_window,GW) to an already declared expected opportunity.
    Missing entries forbid placement; one chip/GW, windows and consecutive FH
    restrictions are enforced, including the previous real gameweek.
    """
    rules=rules_for(state.season);blocked=set(blocked)
    tokens=[w for w in rules['chip_windows'] if (w['name'],w['start']) not in set(state.used_chips)|blocked and w['stop']>=state.gameweek]
    @lru_cache(None)
    def dp(g,mask,previous_fh):
        if g>through:return 0.,()
        best=dp(g+1,mask,False)
        for i,w in enumerate(tokens):
            key=(w['name'],w['start'],g)
            if mask&(1<<i) or not w['start']<=g<=w['stop'] or key not in gains or (w['name']=='freehit' and previous_fh):continue
            v=float(gains[key])
            if not math.isfinite(v):raise ValueError('Nonfinite chip opportunity')
            later,path=dp(g+1,mask|(1<<i),w['name']=='freehit');candidate=(v+later,((g,w['name'],w['start']),*path))
            if candidate[0]>best[0]+1e-10:best=candidate
        return best
    value,path=dp(state.gameweek,0,state.previous_chip=='freehit')
    return value,{g:(name,start) for g,name,start in path}


def plan_adaptive(state,market,scenarios,*,settings=None,budget=None,blocked=(),coarse=None,opening_ids=None):
    """scenarios: sequence(name, explicit_assumption_weight, Horizon), max3.

    All actions across the detailed horizon are shared between scenarios. There
    is no future-branch oracle; actual new evidence causes a new real-deadline
    invocation. Expected-value selection is followed by per-scenario diagnostics.
    Coarse gains are constant beyond the horizon, by chip name; supplied values
    are analyst assumptions, not calibrated projections or learned point gains.
    """
    cfg=settings or Settings();b=budget or Budget();start=time.monotonic()
    if not 1<=len(scenarios)<=3 or len({s[0] for s in scenarios})!=len(scenarios):raise ValueError('Require1–3 unique scenarios')
    if any(not str(n).strip() or not math.isfinite(w) or w<=0 for n,w,h in scenarios):raise ValueError('Invalid scenario weights')
    if not np.isclose(sum(w for _,w,_ in scenarios),1.):raise ValueError('Explicit weights must sum to1')
    base=scenarios[0][2];keys=set(base.values());mix={k:0. for k in keys}
    for _,weight,h in scenarios:
        checked=Horizon.create(market,[dict(r) for r in h.forecasts],**dict(h.provenance))
        if (checked.season,checked.origin,checked.as_of,checked.gameweeks)!=(base.season,base.origin,base.as_of,base.gameweeks) or set(h.values())!=keys:raise ValueError('Scenario origins/coverage differ')
        for k,v in h.values().items():mix[k]+=weight*v
    trained=max((h.provenance['trained_through'] for _,_,h in scenarios),key=utc)
    source=max((h.provenance['source_as_of'] for _,_,h in scenarios),key=utc)
    hashes={f'{name}:{k}':v for name,_,h in scenarios for k,v in h.provenance['source_hashes'].items()}
    mean=Horizon.create(market,[dict(gameweek=g,id=i,expected_points=v) for (g,i),v in mix.items()],trained_through=trained,
        feature_cutoff=market.as_of,source_as_of=source,model_id='explicit-shared-scenario-mean-v1',source_hashes=hashes)
    coarse=dict(coarse if coarse is not None else {'wildcard':12.,'freehit':8.,'3xc':5.,'bboost':10.})
    if set(coarse)!={'wildcard','freehit','3xc','bboost'} or any(not math.isfinite(v) or v<0 for v in coarse.values()):raise ValueError('Require four finite nonnegative coarse assumptions')
    rules=rules_for(state.season);used=set(state.used_chips);blocked=set(blocked);windows=[w for w in rules['chip_windows'] if (w['name'],w['start']) not in used|blocked and w['stop']>=state.gameweek]
    valid_tokens={(w['name'],w['start']) for w in rules['chip_windows']}
    if not blocked<=valid_tokens:raise ValueError('Unknown blocked chip token')
    end=mean.gameweeks[-1];future={(w['name'],w['start'],g):coarse[w['name']] for w in windows for g in range(max(end+1,w['start']),w['stop']+1)}
    trials=[];cache={}
    def solve(schedule):
        key=tuple(sorted(schedule.items()))
        if key in cache:return cache[key]
        elapsed=time.monotonic()-start
        if len(trials)>=b.max_trials or elapsed>=b.seconds:return None
        actions,report=plan(state,market,mean,replace(cfg,seconds=min(b.solve_seconds,max(.01,b.seconds-elapsed))),chip_schedule=schedule,opening_ids=opening_ids)
        after_used=set(used)
        for g,name in schedule.items():after_used.add((name,next(w['start'] for w in windows if w['name']==name and w['start']<=g<=w['stop'])))
        # Allocate remaining tokens to future slots jointly; no double-counted
        # reserve value or four chips promised on the same last deadline.
        remaining={k:v for k,v in future.items() if k[:2] not in after_used}
        future_state=state
        for g,action in zip(mean.gameweeks,actions):future_state=prepare(future_state,_market(market,g,mix),action).state
        if set(future_state.used_chips)!=after_used:raise ValueError('Chip inventory reconciliation failed')
        reserve,path=calendar(future_state,38,remaining,blocked=blocked) if future_state else (0.,{})
        result=(actions,report,report['objective']+reserve,path)
        trials.append(dict(schedule=dict(schedule),objective=report['objective'],coarse_reserve=reserve,total=result[2],seconds=report['seconds'],proven_optimal=report['proven_optimal'],gap=report['mip_gap'],
                           selected_plan_bound=report['selected_plan_bound'],fallback_retained=report['fallback_retained'],solver_diagnostics=report['solver_diagnostics']))
        cache[key]=result;return result
    best=solve({})
    if best is None:raise ValueError('No adaptive baseline')
    initial=best;near={};slots=[]
    # Earliest-expiring inventory first; no outcome-based choice of search order.
    for w in windows:
        for g in mean.gameweeks:
            if not w['start']<=g<=w['stop'] or (w['name']=='freehit' and g==state.gameweek and state.previous_chip=='freehit'):continue
            slots.append((g,w['name'],w['start']))
    # Within an expiry window, probe each chip family at the first date before
    # spending the remaining budget on that family's later dates.
    stops={(w['name'],w['start']):w['stop'] for w in windows}
    slots.sort(key=lambda s:(stops[s[1],s[2]],s[0],s[1]))
    for g,name,token_start in slots:
        # Retain capacity to validate the combined calendar, rather than spend
        # a small budget entirely on mutually exclusive single-chip probes.
        reserve=2 if b.max_trials>=10 else 0
        if len(trials)>=b.max_trials-reserve or time.monotonic()-start>=.8*b.seconds:break
        result=solve({g:name})
        if result is None:continue
        near[name,token_start,g]=result[1]['objective']-initial[1]['objective']
        if result[2]>best[2]+1e-8:best=result
    _,assignment=calendar(state,38,{**future,**near},blocked=blocked)
    combined={g:name for g,(name,_) in assignment.items() if g<=end}
    result=solve(combined)
    if result and result[2]>best[2]+1e-8:best=result
    # One bounded coordinate pass exposes some WC->BB interactions that the
    # additive scheduling proxy misses; it does not prove joint optimality.
    for g,name,token_start in slots:
        if len(trials)>=b.max_trials or time.monotonic()-start>=b.seconds:break
        schedule=dict(best[1]['chip_schedule'])
        schedule={t:n for t,n in schedule.items() if not (n==name and token_start<=t<=next(w['stop'] for w in windows if w['name']==name and w['start']==token_start))}
        if g in schedule:continue
        schedule[g]=name
        try:result=solve(schedule)
        except ValueError as e:
            if 'Consecutive Free Hits' in str(e):continue
            raise
        if result and result[2]>best[2]+1e-8:best=result
    actions,report,total,future_path=best
    sensitivity={name:_objective(state,market,h,actions,cfg)[0] for name,_,h in scenarios}
    return actions,dict(objective=report['objective'],coarse_reserve=total-report['objective'],total_proxy=total,
        selected_schedule_bound=report['selected_plan_bound'],global_chip_search_bound=None,
        scenario_objectives=sensitivity,scenario_weights={n:w for n,w,_ in scenarios},chip_schedule=report['chip_schedule'],
        coarse_schedule={g:name for g,(name,_) in future_path.items()},coarse_values=coarse,blocked_tokens=sorted(blocked),
        trials=trials,seconds=time.monotonic()-start,budget_exhausted=len(trials)>=b.max_trials or time.monotonic()-start>=b.seconds,
        scope='Heuristic chip search, fixed coarse proxies, shared full-horizon plan across scenarios; first action only, replan at next deadline; not global optimum or calibrated uncertainty')


def main():
    import argparse,json
    from dataclasses import asdict
    from pathlib import Path
    from experiment_runner import file_hash
    from season_engine import State,Market
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Output exists; preserve evidence')
    if file_hash(a.input)!=a.sha256:p.error('Input checksum mismatch')
    spec=json.loads(a.input.read_text())
    if spec.get('schema_version')!=1:p.error('Unsupported input schema')
    market=Market.create(**spec['market']);z=dict(spec['state'])
    for key in ('holdings','used_chips'):z[key]=tuple(tuple(v) for v in z.get(key,[]))
    state=State(**z);scenarios=[(v['name'],v['weight'],Horizon.create(market,**v['forecast'])) for v in spec['scenarios']]
    actions,report=plan_adaptive(state,market,scenarios,settings=Settings(**spec.get('settings',{})),budget=Budget(**spec.get('budget',{})),
        blocked=[tuple(v) for v in spec.get('blocked_tokens',[])],coarse=spec.get('coarse_values'))
    a.output.mkdir(parents=True)
    result=dict(schema_version=1,source_sha256=file_hash(__file__),planner_sha256=file_hash(Path(__file__).with_name('rolling_planner.py')),input_sha256=file_hash(a.input),
        immediate_action=asdict(actions[0]),provisional_actions=[asdict(v) for v in actions],report=report,
        scope='Experimental shared-scenario chip plan; no registry/account writes; later actions provisional')
    (a.output/'plan.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
