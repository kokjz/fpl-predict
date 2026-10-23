"""Same-state, same-origin calendar/inner-solver diagnosis; no outcome reads.

Only frozen provisional schedules are considered. Eventually realised chip dates
are not inputs. Incompatible chip inventories are reported, never repaired.
"""
import argparse,contextlib,gzip,hashlib,json,sys,time
from dataclasses import asdict,replace
from pathlib import Path
from threadpoolctl import threadpool_limits
from adaptive_planner import calendar
from native_planner import CanonicalPlanner,NativePlanner,NativeProcess
from season_qualification import Trace,Guarded
from season_benchmark import read_bundle,forecast
from season_engine import State,Market,prepare,rules_for
from rolling_planner import Settings,_market
sys.path.insert(0,str(Path(__file__).resolve().parent))
from probe_season_solver import verify_plan

ROOT=Path(__file__).resolve().parents[1]
COARSE={'wildcard':12.,'freehit':8.,'3xc':5.,'bboost':10.}


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compatible_schedule(state,through,schedule,blocked):
    windows=rules_for(state.season)['chip_windows'];used=set(state.used_chips);blocked=set(map(tuple,blocked));previous=state.previous_chip
    for g in range(state.gameweek,through+1):
        name=schedule.get(g)
        if name:
            candidates=[w for w in windows if w['name']==name and w['start']<=g<=w['stop']]
            if len(candidates)!=1:return 'no available chip window'
            token=(name,candidates[0]['start'])
            if token in used|blocked:return 'token already used or blocked in common state'
            if name==previous=='freehit':return 'consecutive Free Hits in common state'
            used.add(token)
        previous=name
    if any(type(g) is not int or not state.gameweek<=g<=through for g in schedule):return 'schedule outside horizon'
    return None


def remaining_reserve(state,market,horizon,actions,blocked):
    current=state;xp=horizon.values()
    for g,a in zip(horizon.gameweeks,actions):current=prepare(current,_market(market,g,xp),a).state
    windows=rules_for(state.season)['chip_windows'];gains={(w['name'],w['start'],g):COARSE[w['name']] for w in windows for g in range(max(current.gameweek,w['start']),w['stop']+1)}
    reserve,path=calendar(current,38,gains,blocked=blocked)
    return reserve,dict(remaining_tokens=[(w['name'],w['start']) for w in windows if (w['name'],w['start']) not in set(current.used_chips)|set(map(tuple,blocked)) and w['stop']>=current.gameweek],coarse_schedule={g:name for g,(name,start) in path.items()})


def run(decisions,reference,opening_lock,source_lock,protocol_path,output,*,native_python,solio_source,solio_site_packages):
    output=Path(output).resolve()
    if output.exists() or output.is_relative_to(ROOT):raise ValueError('Require a new private output directory')
    p=json.loads(Path(protocol_path).read_text());old=json.loads(Path(opening_lock).read_text());locked=json.loads(Path(source_lock).read_text())['fingerprint']
    if p['origin_gameweeks']!=[1,6,12,16,20,24,30,38] or p['reference_seed']!=20261025 or p['inner_seconds']!=2. or p['maximum_cases']!=32 or p['solvers']!=['standing','solio_adapted']:raise ValueError('Undeclared probe matrix')
    if digest(decisions)!=old['inputs_sha256']['decisions'] or digest(decisions)!=locked['inputs']['2025-26']['decisions']['sha256']:raise ValueError('Forecast bundle differs')
    sources={ROOT/f:sha for f,sha in locked['source_sha256'].items()};sources.update({Path(x):digest(x) for x in [decisions,opening_lock,source_lock,protocol_path,__file__]})
    def verify():
        if any(digest(f)!=sha for f,sha in sources.items()):raise ValueError('Source/input drift')
    verify();weeks=read_bundle(decisions)['weeks'];cases=[];skipped=[];references={};output.mkdir(parents=True);start=time.monotonic()
    with contextlib.ExitStack() as stack:
        actor=stack.enter_context(NativeProcess(native_python,solio_source,output/'native_stderr.log',site_packages=solio_site_packages));trace=Trace(actor,output,'solio',stack)
        solvers={'standing':Guarded(CanonicalPlanner(),output),'solio_adapted':Guarded(CanonicalPlanner(NativePlanner(trace)),output,trace)}
        with threadpool_limits(limits=2):
            for origin in p['origin_gameweeks']:
                records={}
                for name in p['schedule_sources']:
                    path=Path(reference)/f'{p["reference_seed"]}_{name}/result/season'/f'GW{origin:02d}_decision.json';records[name]=json.loads(path.read_text());references[str(path)]=digest(path)
                raw=records['standingH6_adaptive'];state=State(**dict(raw['state_before'],total_points=0.,holdings=tuple(map(tuple,raw['state_before']['holdings'])),used_chips=tuple(map(tuple,raw['state_before']['used_chips']))));spec=weeks[origin-1];market=Market.create(**spec['market']);h=forecast(market,spec['forecast'],6);opening=old['openings'][str(p['reference_seed'])]['ids'] if origin==1 else None
                if dict(h.provenance)!=raw['forecast_provenance'] or raw['inputs_as_of']!=market.as_of:raise ValueError('Reference origin differs')
                for name,record in records.items():
                    schedule={g:a['chip'] for g,a in zip(h.gameweeks,record['provisional_actions']) if a['chip']}
                    if record['inputs_as_of']!=market.as_of or dict(h.provenance)!=record['forecast_provenance'] or schedule!={int(g):c for g,c in record['report']['chip_schedule'].items()}:raise ValueError('Schedule provenance differs')
                    reason=compatible_schedule(state,h.gameweeks[-1],schedule,spec['blocked_tokens'])
                    if reason:skipped.append(dict(origin=origin,schedule_source=name,schedule=schedule,reason=reason));continue
                    payload=dict(state=asdict(state),market=spec['market'],forecast=spec['forecast'],schedule=schedule,opening=opening,blocked=spec['blocked_tokens'],reference_sha256={n:references[str(Path(reference)/f'{p["reference_seed"]}_{n}/result/season'/f'GW{origin:02d}_decision.json')] for n in records})
                    name_id=f'GW{origin:02d}_{name}';path=output/(name_id+'_input.json.gz');path.write_bytes(gzip.compress(json.dumps(payload,sort_keys=True).encode()))
                    for solver_name,solver in solvers.items():
                        cfg=Settings(seconds=2.,baseline_mode='feasibility',terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.);tick=time.monotonic();actions,report=solver(state,market,h,cfg,chip_schedule=schedule,opening_ids=opening)
                        value,ids=verify_plan(state,spec['market'],h,actions,spec['blocked_tokens'])
                        if abs(value-report['objective'])>1e-6 or opening is not None and ids[0]!=set(opening):raise ValueError('Independent proposal admission failed')
                        reserve,inventory=remaining_reserve(state,market,h,actions,spec['blocked_tokens']);row=dict(origin=origin,schedule_source=name,solver=solver_name,schedule=schedule,horizon_objective=value,coarse_reserve=reserve,total_proxy=value+reserve,seconds=time.monotonic()-tick,selected_plan_bound=report['selected_plan_bound'],input_sha256=digest(path),inventory=inventory)
                        (output/(name_id+'_'+solver_name+'.json')).write_text(json.dumps(dict(metrics=row,actions=[asdict(a) for a in actions],report=report),indent=2)+'\n');cases.append(row)
        verify()
        if any(digest(f)!=sha for f,sha in references.items()):raise ValueError('Frozen reference drift')
        result=dict(complete=len(cases)+2*len(skipped)==32,cases=cases,skipped=skipped,seconds=time.monotonic()-start,reference_hashes=references,source_sha256={str(f.relative_to(ROOT)):sha for f,sha in sources.items() if f.is_relative_to(ROOT)},protocol_sha256=digest(protocol_path),native_runtime=actor.metadata,native_calls=trace.calls,native_failed_attempts=trace.failed,model_promotion=False,policy_promotion=False,scope=p['scope'])
        (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['decisions','reference','opening-lock','source-lock','protocol','output','native-python','solio-source','solio-site-packages']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();run(a.decisions,a.reference,a.opening_lock,a.source_lock,a.protocol,a.output,native_python=a.native_python,solio_source=a.solio_source,solio_site_packages=a.solio_site_packages)


if __name__=='__main__':main()
