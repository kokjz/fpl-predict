"""Optional native inner planner with shared selection and canonical admission.

The subprocess is a trusted, hash-pinned research adapter, not a security
sandbox. No historical outcomes or account credentials are sent to it.
"""
import json
import math
import os
import queue
import subprocess
import threading
import time
from dataclasses import asdict,replace
from pathlib import Path
from forecast import select_xi
from horizon_forecast import Horizon
from native_solver_worker import MAX_MESSAGE,RESOURCES,read_json,verified_sources
from rolling_planner import Settings,plan,make_baseline,candidate_players,_fallback,_objective,_market
from season_engine import Action,prepare,available_transfers,rules_for

WORKER=Path(__file__).with_name('native_solver_worker.py')


class NativeTransportError(RuntimeError):pass


class NativeProcess:
    """One serial JSON worker; inherits the supervisor's process group."""
    def __init__(self,python,source_root,log_path,*,site_packages=None,startup_timeout=30.):
        self.process=None;self.stream=None;self.reader=None;self.lock=threading.Lock();self.messages=queue.Queue(maxsize=4);self.closed=False
        recipe=read_json((RESOURCES/'native_solver_recipe.json').read_bytes());source_root=Path(source_root).resolve()
        verified_sources(source_root,recipe['source_sha256'])
        path=Path(log_path);path.parent.mkdir(parents=True,exist_ok=True);self.stream=path.open('xb')
        env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','SYSTEMROOT','TMP','TEMP','TMPDIR')}
        env.update(OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',VECLIB_MAXIMUM_THREADS='2',PYTHONUNBUFFERED='1')
        if site_packages is not None:env['PYTHONPATH']=str(Path(site_packages).resolve())
        tick=time.monotonic()
        try:
            self.process=subprocess.Popen([str(python),str(WORKER.resolve()),'--source-root',str(source_root)],cwd=source_root,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stream)
            self.reader=threading.Thread(target=self._read,daemon=True);self.reader.start()
            self.metadata=self._receive(startup_timeout)
            if (self.metadata.get('status'),self.metadata.get('revision'),self.metadata.get('source_sha256'),self.metadata.get('highspy'),self.metadata.get('network_disabled'),self.metadata.get('threads'))!=('ready',recipe['revision'],recipe['source_sha256'],recipe['highspy_version'],True,2):raise NativeTransportError('Native startup metadata differs')
            self.startup_seconds=time.monotonic()-tick
        except Exception:
            self.close();raise

    def _read(self):
        try:
            while raw:=self.process.stdout.readline(MAX_MESSAGE+1):
                if len(raw)>MAX_MESSAGE or not raw.endswith(b'\n'):raise NativeTransportError('Oversized or incomplete native response')
                self.messages.put(raw,timeout=.2)
            self.messages.put(NativeTransportError('Native worker exited'),timeout=.2)
        except Exception as error:
            try:self.messages.put(error,timeout=.2)
            except queue.Full:pass

    def _receive(self,timeout):
        try:raw=self.messages.get(timeout=timeout)
        except queue.Empty:raise NativeTransportError('Native response timed out') from None
        if isinstance(raw,Exception):raise NativeTransportError('Native response stream failed') from raw
        try:value=read_json(raw)
        except (ValueError,UnicodeError):raise NativeTransportError('Invalid native JSON response') from None
        if not isinstance(value,dict):raise NativeTransportError('Native response must be an object')
        return value

    def request(self,value,*,timeout=None):
        raw=(json.dumps(value,allow_nan=False,separators=(',',':'))+'\n').encode()
        if len(raw)>MAX_MESSAGE:raise ValueError('Oversized native request')
        with self.lock:
            if self.closed or self.process.poll() is not None:raise NativeTransportError('Native worker is unavailable')
            try:
                self.process.stdin.write(raw);self.process.stdin.flush()
                return self._receive(timeout if timeout is not None else value['seconds']+5.)
            except Exception as error:
                self.close()
                if isinstance(error,NativeTransportError):raise
                raise NativeTransportError('Native request stream failed') from error

    def close(self):
        if self.closed:return
        self.closed=True
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:self.process.wait(timeout=2.)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=2.)
            if self.reader is not None:self.reader.join(timeout=.5)
            for stream in (self.process.stdin,self.process.stdout):
                if stream is not None:stream.close()
        if self.stream is not None:self.stream.close()

    def __enter__(self):return self
    def __exit__(self,*args):self.close()


def retained_bound(value,upper,status='solver_dual'):
    if upper is None or not math.isfinite(upper):upper=None;status='unavailable'
    elif upper<value-1e-5:upper=None;status='inconsistent_dual'
    else:upper=max(float(upper),value)
    gap=None if upper is None else upper-value
    return dict(status=status,feasible_objective=value,upper_objective=upper,absolute_gap=gap,relative_gap=None if gap is None else gap/max(abs(value),1e-9),scope='Fixed chip schedule, restricted pool and stated heuristic objective only; no outer-search/season/prediction confidence bound')


def canonical_actions(state,market,horizon,actions):
    if len(actions)!=len(horizon.gameweeks):raise ValueError('Incomplete provisional plan')
    result=[];xp=horizon.values()
    for g,action in zip(horizon.gameweeks,actions):
        m=_market(market,g,xp);original=prepare(state,m,action)
        choice=select_xi(sorted((dict(p) for p in original.squad),key=lambda p:p['id']))
        canonical=replace(action,starters=tuple(choice['starters']),bench=tuple(choice['bench']),captain=choice['captain'],vice=choice['vice'])
        checked=prepare(state,m,canonical)
        if checked.state!=original.state:raise ValueError('Selection changed financial state')
        state=checked.state;result.append(canonical)
    return result


class CanonicalPlanner:
    """Common deterministic mean XI/captain/vice/bench for roster comparisons."""
    def __init__(self,inner=plan):self.inner=inner
    def __call__(self,state,market,horizon,settings=None,**kwargs):
        tick=time.monotonic();cfg=settings or Settings();actions,report=self.inner(state,market,horizon,cfg,**kwargs)
        selected=canonical_actions(state,market,horizon,actions);value,parts=_objective(state,market,horizon,selected,cfg)
        if value<report['objective']-1e-5:raise ValueError('Canonical selection reduced stated objective')
        before=report['selected_plan_bound'];bound=retained_bound(value,before['upper_objective'],before['status'])
        return selected,dict(report,objective=value,components=parts,inner_objective=report['objective'],canonical_selection=True,selected_plan_bound=bound,proven_optimal=bool(report['proven_optimal'] and bound['relative_gap'] is not None and bound['relative_gap']<1e-7),seconds=time.monotonic()-tick)


def controlled_settings(seconds=30.):
    return Settings(seconds=seconds,baseline_mode='feasibility',terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.)


class NativePlanner:
    def __init__(self,transport):self.transport=transport
    def __call__(self,state,market,horizon,settings=None,*,chip_schedule=None,opening_ids=None):
        tick=time.monotonic();cfg=settings or controlled_settings();chips=dict(chip_schedule or {})
        if cfg.baseline_mode!='feasibility' or any(abs(v)>1e-12 for v in [cfg.terminal_ft_value,cfg.terminal_squad_weight,cfg.churn_cost]) or abs(cfg.bench_weight-.1)>1e-12:raise ValueError('Native comparison requires the declared common objective and feasible baseline')
        checked=Horizon.create(market,[dict(r) for r in horizon.forecasts],**dict(horizon.provenance))
        recipe=read_json((RESOURCES/'native_solver_recipe.json').read_bytes())
        if market.season!=recipe['season']:raise ValueError('Unaudited native season profile')
        if (state.season,state.gameweek)!=(checked.season,checked.origin) or market.gameweek!=state.gameweek:raise ValueError('Native forecast/state origin differs')
        baseline,baseline_status=make_baseline(state,market,horizon,cfg,opening_ids)
        fallback=_fallback(state,market,horizon,baseline,chips);fallback_value,_=_objective(state,market,horizon,fallback,cfg)
        players=candidate_players(state,market,horizon,cfg,baseline);xp=horizon.values();ids={p['id'] for p in players}
        qstate=asdict(state);qstate.pop('total_points')
        request=dict(schema_version=1,market=dict(season=market.season,gameweek=market.gameweek,deadline=market.deadline,as_of=market.as_of,rows=[{k:p[k] for k in ['id','position','team','price_tenths','can_buy']} for p in players]),state=qstate,xp=[[g,i,float(xp[g,i])] for g in horizon.gameweeks for i in sorted(ids)],through=horizon.gameweeks[-1],chip_schedule=chips,opening_ids=opening_ids,seconds=max(.001,cfg.seconds-(time.monotonic()-tick)))
        response=self.transport.request(request);selected=fallback;reason='validated fallback; native proposal unavailable';proposal_value=None;upper=None;native_status=None;gap=None;error_type=None
        if response.get('status')=='completed':
            try:
                native_status=response['native_status'];raw_value=float(response['objective'])
                if native_status not in ('HighsModelStatus.kOptimal','HighsModelStatus.kTimeLimit'):raise ValueError('Unexpected native solve status')
                if not math.isfinite(raw_value):raise ValueError('Invalid native objective')
                seen=set();rosters={g:set() for g in horizon.gameweeks}
                for p in response['picks']:
                    g=p['week'];i=p['id']
                    if type(g) is not int or type(i) is not int or g not in rosters or i not in ids or (g,i) in seen or type(p['squad']) is not int or p['squad'] not in (0,1):raise ValueError('Invalid native roster rows')
                    if {'actual','minutes','cards'}&set(p):raise ValueError('Outcome fields in proposal')
                    seen.add((g,i))
                    if p['squad']:rosters[g].add(i)
                actions=[];current=state
                for g in horizon.gameweeks:
                    roster=rosters[g];old=set(dict(current.holdings));m=_market(market,g,xp);by=m.indexed()
                    choice=select_xi([by[i] for i in sorted(roster)])
                    a=Action(tuple(sorted(roster-old)),tuple(sorted(old-roster)),tuple(choice['starters']),tuple(choice['bench']),choice['captain'],choice['vice'],chips.get(g))
                    p=prepare(current,m,a);stat=response['statistics'][str(g)]
                    if any(not math.isfinite(float(stat[k])) for k in ['ft','pt','itb']):raise ValueError('Nonfinite native financial values')
                    if abs(stat['ft']-available_transfers(current,rules_for(state.season)))>1e-5 or abs(stat['pt']*4-p.hits)>1e-5 or abs(stat['itb']*10-p.state.bank)>1e-5:raise ValueError('Native/engine financial mismatch')
                    current=p.state;actions.append(a)
                if opening_ids is not None and set(actions[0].buys)!=set(opening_ids):raise ValueError('Native common opening differs')
                proposal_value,_=_objective(state,market,horizon,actions,cfg)
                if proposal_value<raw_value-1e-5 or native_status=='HighsModelStatus.kOptimal' and abs(proposal_value-raw_value)>1e-5:raise ValueError('Native/canonical objective mismatch')
                upper=response.get('dual_bound');gap=response.get('mip_gap')
                if upper is not None and type(upper) not in (int,float):raise ValueError('Invalid native bound')
                if gap is not None and (type(gap) not in (int,float) or not math.isfinite(gap)):gap=None
                if proposal_value>=fallback_value-1e-7:selected=actions;reason='validated native proposal with common selection'
            except (ValueError,KeyError,TypeError,StopIteration) as error:
                upper=None;gap=None;error_type=type(error).__name__;reason='validated fallback; native proposal failed canonical admission'
        else:error_type=response.get('error_type','NativeSolverFailure')
        value,parts=_objective(state,market,horizon,selected,cfg);bound=retained_bound(value,upper)
        proven=bool(selected is not fallback and native_status=='HighsModelStatus.kOptimal' and bound['relative_gap'] is not None and bound['relative_gap']<1e-7)
        report=dict(objective=value,components=parts,fallback_objective=fallback_value,solver_objective=proposal_value,status=0 if proven else 1,selection=reason,baseline=baseline_status,proven_optimal=proven,mip_gap=gap,legacy_gap_scope='Raw native attempt; use selected_plan_bound for retained plan',selected_plan_bound=bound,fallback_retained=selected is fallback,solver_diagnostics=dict(native_status=native_status,native_maximisation_dual_bound=upper,reported_mip_gap=gap,baseline_objective_cut=False,native_error_type=error_type),seconds=time.monotonic()-tick,pool_players=len(players),full_market_players=len(market.players),chip_schedule=chips,canonical_selection=True,scope='Rule-adapted native core, shared candidate/selection/outer-chip policy; not untouched external manager or global optimum')
        return selected,report
