"""Canonical admission for the optional, rule-adapted AIrsenal policy."""
import math
import time
from dataclasses import asdict
from pathlib import Path
from forecast import select_xi
from horizon_forecast import Horizon
from native_solver_worker import RESOURCES,read_json,verified_sources
from native_transport import JsonProcess,NativeTransportError
from native_planner import controlled_settings,retained_bound
from rolling_planner import make_baseline,candidate_players,_fallback,_objective,_market
from season_engine import Action,prepare

WORKER=Path(__file__).with_name('airsenal_solver_worker.py')


class AIrsenalProcess(JsonProcess):
    def __init__(self,python,source_root,log_path,home,*,startup_timeout=30.):
        recipe=read_json((RESOURCES/'airsenal_solver_recipe.json').read_bytes());root=Path(source_root).resolve()
        verified_sources(root,recipe['source_sha256'])
        if Path(home).exists():raise ValueError('Use a new AIrsenal research home')
        super().__init__([python,WORKER.resolve(),'--source-root',root,'--home',Path(home).resolve()],
            Path(log_path).resolve().parent,log_path,site_packages=root,startup_timeout=startup_timeout)
        try:
            m=self.metadata;versions={'airsenal':recipe['package_version'],**recipe['optional_planner_dependencies'],**recipe['other_observed_dependencies']}
            if (m.get('status'),m.get('revision'),m.get('source_sha256'),m.get('versions'),m.get('network_disabled'),m.get('serial'),m.get('discount'))!=('ready',recipe['revision'],recipe['source_sha256'],versions,True,True,1.):raise NativeTransportError('AIrsenal startup metadata differs')
        except Exception:
            self.close();raise


def number(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Nonfinite or untyped native value')
    return float(value)


class AIrsenalPlanner:
    def __init__(self,transport):self.transport=transport
    def __call__(self,state,market,horizon,settings=None,*,chip_schedule=None,opening_ids=None):
        tick=time.monotonic();cfg=settings or controlled_settings();chips=dict(chip_schedule or {})
        if cfg.baseline_mode!='feasibility' or any(abs(v)>1e-12 for v in [cfg.terminal_ft_value,cfg.terminal_squad_weight,cfg.churn_cost]) or abs(cfg.bench_weight-.1)>1e-12:raise ValueError('AIrsenal comparison requires the declared common objective')
        checked=Horizon.create(market,[dict(r) for r in horizon.forecasts],**dict(horizon.provenance))
        recipe=read_json((RESOURCES/'airsenal_solver_recipe.json').read_bytes())
        if market.season!=recipe['season'] or (state.season,state.gameweek)!=(checked.season,checked.origin) or market.gameweek!=state.gameweek:raise ValueError('Unaudited AIrsenal season/origin')
        baseline,status=make_baseline(state,market,horizon,cfg,opening_ids)
        fallback=_fallback(state,market,horizon,baseline,chips);floor,_=_objective(state,market,horizon,fallback,cfg)
        players=candidate_players(state,market,horizon,cfg,baseline);ids={p['id'] for p in players};xp=horizon.values()
        qstate=asdict(state);qstate.pop('total_points')
        request=dict(schema_version=1,market=dict(season=market.season,gameweek=market.gameweek,deadline=market.deadline,as_of=market.as_of,rows=[{k:p[k] for k in ['id','position','team','price_tenths','can_buy']} for p in players]),state=qstate,xp=[[g,i,float(xp[g,i])] for g in horizon.gameweeks for i in sorted(ids)],through=horizon.gameweeks[-1],chip_schedule=chips,opening_ids=opening_ids,seconds=max(.001,cfg.seconds-(time.monotonic()-tick)))
        answer=self.transport.request(request);selected=fallback;raw=None;error_type=None;native_status='failed';reason='validated fallback; native plan unavailable'
        if answer.get('status')=='completed':
            try:
                if answer.get('bound') is not None or answer.get('discount')!=1.:raise ValueError('Undeclared native objective/bound')
                best=answer['best'];outcomes=best['outcomes']
                if best['root_gameweek']!=state.gameweek or len(outcomes)!=len(horizon.gameweeks) or answer['horizon']!=len(horizon.gameweeks):raise ValueError('Incomplete or misdated native horizon')
                raw=number(best['total_score']);native_sum=0.;current=state;actions=[]
                names={None:None,'wildcard':'wildcard','free_hit':'freehit','bench_boost':'bboost','triple_captain':'3xc'}
                fields={'gameweek','num_transfers','chip_played','points','discount_factor','points_hit','free_transfers','players_in','players_out','bank'}
                for g,r in zip(horizon.gameweeks,outcomes):
                    if set(r)!=fields or type(r['gameweek']) is not int or r['gameweek']!=g:raise ValueError('Unknown/outcome fields or native period')
                    buys=r['players_in'];sells=r['players_out']
                    if any(type(i) is not int or i not in ids for i in [*buys,*sells]) or len(set(buys))!=len(buys) or len(set(sells))!=len(sells):raise ValueError('Invalid native transfer identities')
                    chip=names[r['chip_played']]
                    if chip!=chips.get(g):raise ValueError('Native chip schedule differs')
                    expected='W' if chip=='wildcard' else 'F' if chip=='freehit' else ('T' if chip=='3xc' else 'B' if chip=='bboost' else '')+str(0 if g==1 else len(buys))
                    if str(r['num_transfers'])!=expected:raise ValueError('Native move count differs')
                    roster=set(dict(current.holdings))-set(sells)|set(buys);m=_market(market,g,xp);by=m.indexed()
                    choice=select_xi([by[i] for i in sorted(roster)])
                    action=Action(tuple(buys),tuple(sells),tuple(choice['starters']),tuple(choice['bench']),choice['captain'],choice['vice'],chip)
                    p=prepare(current,m,action)
                    if any(type(r[k]) is not int for k in ['bank','free_transfers','points_hit']) or (r['bank'],r['free_transfers'],r['points_hit'])!=(p.state.bank,p.state.free_transfers,p.hits):raise ValueError('Native financial ledger differs')
                    value=sum(xp[g,i] for i in action.starters)+(2 if chip=='3xc' else 1)*xp[g,action.captain]+(1. if chip=='bboost' else .1)*sum(xp[g,i] for i in action.bench)-p.hits
                    points=number(r['points'])
                    if number(r['discount_factor'])!=1. or points>value+1e-5:raise ValueError('Native conditional objective differs')
                    native_sum+=points;current=p.state;actions.append(action)
                    if g==1 and (set(answer['opening_roster'])!=roster or opening_ids is not None and roster!=set(opening_ids)):raise ValueError('Native opening differs')
                if abs(native_sum-raw)>1e-5:raise ValueError('Native total objective differs')
                value,_=_objective(state,market,horizon,actions,cfg)
                if value<raw-1e-5:raise ValueError('Native canonical objective differs')
                native_status='truncated heuristic' if answer.get('truncated') else 'completed heuristic'
                if value>=floor-1e-7:selected=actions;reason='validated complete native plan'
            except (ValueError,KeyError,TypeError,StopIteration) as error:
                error_type=type(error).__name__;reason='validated fallback; native proposal failed canonical admission'
        else:error_type=answer.get('error_type','NativeSearchFailure')
        value,parts=_objective(state,market,horizon,selected,cfg)
        return selected,dict(objective=value,components=parts,fallback_objective=floor,solver_objective=raw,
            status=1,selection=reason,baseline=status,proven_optimal=False,mip_gap=None,
            selected_plan_bound=retained_bound(value,None),fallback_retained=selected is fallback,
            solver_diagnostics=dict(native_status=native_status,native_error_type=error_type,baseline_objective_cut=False),
            seconds=time.monotonic()-tick,pool_players=len(players),full_market_players=len(market.players),chip_schedule=chips,
            canonical_selection=True,scope='Adapted AIrsenal heuristic policy/common outer chips; no original manager or optimality claim')
