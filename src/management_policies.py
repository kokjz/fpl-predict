"""Explicit fixed-calendar and hold controls for whole-season research replay."""
import hashlib
import json
import time
from dataclasses import replace
from types import MappingProxyType
from adaptive_planner import Budget
from native_planner import CanonicalPlanner,canonical_actions,retained_bound
from opening_baseline import cheapest_opening
from rolling_planner import _fallback,_objective
from season_engine import rules_for

FIXED_CALENDAR=MappingProxyType({6:'wildcard',12:'bboost',15:'freehit',18:'3xc',
                               24:'wildcard',30:'bboost',33:'freehit',36:'3xc'})


class FixedCalendarPolicy:
    """Replan rosters, retaining predeclared chip dates and bounded attempts.

    Search allocation differs from the adaptive calendar: repeated inner solves
    use the one permitted schedule, rather than exploring alternative calendars.
    Select by expected objective only. This is not a causal chip-timing estimate
    independent of numerical search quality.
    """
    def __init__(self,calendar=None,*,inner_planner=None):
        chosen=dict(FIXED_CALENDAR if calendar is None else calendar)
        if any(type(g) is not int or not 1<=g<=38 or c not in ('wildcard','freehit','bboost','3xc') for g,c in chosen.items()):raise ValueError('Invalid fixed calendar')
        self.calendar=MappingProxyType(chosen)
        self.inner=CanonicalPlanner() if inner_planner is None else CanonicalPlanner(inner_planner)

    def __call__(self,state,market,horizon,*,settings,policy,blocked,opening_ids):
        start=time.monotonic();budget=Budget(policy.seconds,policy.solve_seconds,policy.max_trials)
        windows=rules_for(state.season)['chip_windows'];tokens=[]
        for g,name in sorted(self.calendar.items()):
            matches=[w for w in windows if w['name']==name and w['start']<=g<=w['stop']]
            if len(matches)!=1:raise ValueError('Fixed calendar outside chip windows')
            tokens.append((name,matches[0]['start']))
        if len(tokens)!=len(set(tokens)):raise ValueError('Fixed calendar reuses chip token')
        fh=sorted(g for g,c in self.calendar.items() if c=='freehit')
        if any(b==a+1 for a,b in zip(fh,fh[1:])):raise ValueError('Fixed calendar has consecutive Free Hits')
        unavailable=set(state.used_chips)|set(blocked);schedule={}
        if policy.chips:
            for (g,name),token in zip(sorted(self.calendar.items()),tokens):
                if g in horizon.gameweeks and token not in unavailable:
                    if g==state.gameweek and name=='freehit' and state.previous_chip=='freehit':continue
                    schedule[g]=name
        trials=[];best=None;chosen_index=None
        for _ in range(budget.max_trials):
            elapsed=time.monotonic()-start
            if trials and elapsed>=budget.seconds:break
            allowance=min(budget.solve_seconds,max(.01,budget.seconds-elapsed))
            actions,report=self.inner(state,market,horizon,replace(settings,seconds=allowance),
                chip_schedule=schedule,opening_ids=opening_ids)
            trials.append(dict(objective=report['objective'],schedule=dict(schedule),
                seconds=report['seconds'],fallback_retained=report['fallback_retained'],
                selected_plan_bound=report['selected_plan_bound']))
            if best is None or report['objective']>best[1]['objective']+1e-8:
                best=actions,report;chosen_index=len(trials)-1
        actions,report=best
        return actions,dict(report,seconds=time.monotonic()-start,trials=trials,
            selected_trial_index=chosen_index,chip_schedule=schedule,
            selected_schedule_bound=report['selected_plan_bound'],global_chip_search_bound=None,
            budget_exhausted=len(trials)==budget.max_trials or time.monotonic()-start>=budget.seconds,
            fixed_calendar=dict(self.calendar),calendar_sha256=hashlib.sha256(
                json.dumps(dict(self.calendar),sort_keys=True).encode()).hexdigest(),
            scope='Fixed predeclared calendar; same bounded roster solver and mean objective; no global season guarantee')


class HoldPolicy:
    """Descriptive no-transfer/no-chip floor; not the primary fair-resource anchor."""
    def __call__(self,state,market,horizon,*,settings,policy,blocked,opening_ids):
        start=time.monotonic()
        if state.holdings:ledger=dict(state.holdings)
        elif opening_ids is not None:ledger={i:market.indexed()[i]['price_tenths'] for i in opening_ids}
        else:ledger=cheapest_opening(market,state.bank)
        actions=canonical_actions(state,market,horizon,_fallback(state,market,horizon,{'ledger':ledger}))
        value,parts=_objective(state,market,horizon,actions,settings)
        bound=retained_bound(value,None)
        return actions,dict(objective=value,components=parts,seconds=time.monotonic()-start,
            budget_exhausted=False,chip_schedule={},selected_schedule_bound=bound,
            global_chip_search_bound=None,selected_trial_index=0,
            trials=[dict(objective=value,schedule={},seconds=time.monotonic()-start,
                         fallback_retained=False,selected_plan_bound=bound)],
            fallback_retained=False,solver_executed=False,proven_optimal=False,
            scope='Descriptive cheapest/common opening then hold15; reselect mean XI/captain/vice; intentionally leave transfers and chips unused')
