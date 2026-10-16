"""Fixed-schedule numerical sensitivity; source-checkout research tool.

Reads forecast inputs and frozen decisions only, never evaluator/settlement
files. Run after the historical matrix is terminal, under its resource watchdog.
"""
import argparse
from dataclasses import asdict,is_dataclass
import gzip
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import time

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_season_path import read,digest,advance,expected
from native_planner import CanonicalPlanner
from rolling_planner import Settings,make_baseline,candidate_players
from season_benchmark import forecast
from season_engine import State,Market
from season_qualification import output_path
from threadpoolctl import threadpool_limits


def encode(value):return json.dumps(value,sort_keys=True,allow_nan=False).encode()


def failure_evidence(value):
    """Retain malformed replies without writing nonstandard JSON constants."""
    if is_dataclass(value):return failure_evidence(asdict(value))
    if isinstance(value,float) and not math.isfinite(value):return dict(nonfinite=repr(value))
    if isinstance(value,dict):return {str(k):failure_evidence(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [failure_evidence(v) for v in value]
    if value is None or type(value) in (str,int,float,bool):return value
    return dict(python_type=type(value).__name__,representation=repr(value))


def verify_sources(locked):
    for name,sha in locked['source_sha256'].items():
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Invalid locked source path')
        if digest(REPO/'src'/relative)!=sha:raise ValueError('Locked engine source/resource drift')
    if sys.version.split()[0]!=locked['python']:raise ValueError('Locked Python drift')
    if any(importlib.metadata.version(name)!=version for name,version in locked['packages'].items()):raise ValueError('Locked package drift')


def verify_plan(state,market,horizon,actions,blocked):
    assert len(actions)==len(horizon.gameweeks)
    current=asdict(state);xp=horizon.values();value=0.;rosters=[]
    for g,action in zip(horizon.gameweeks,actions):
        current,ids,hits,_=advance(current,dict(market,gameweek=g),asdict(action),blocked)
        value+=expected(asdict(action),xp,g,hits);rosters.append(ids)
    return value,rosters


def run(decisions,reference,opening,lock,lock_sha256,protocol,protocol_sha256,output,home,*,inner=None):
    if not __debug__:raise ValueError('Probe requires assertions enabled')
    if digest(protocol)!=protocol_sha256 or digest(lock)!=lock_sha256:raise ValueError('Protocol or source-lock checksum mismatch')
    p=read(protocol);locked=read(lock);verify_sources(locked)
    if p['schema_version']!=1 or p['horizon']!=6:raise ValueError('Unsupported probe protocol')
    if p['origin_gameweeks']!=[1,6,16,30,38] or p['inner_seconds']!=[.5,2.,5.]:raise ValueError('Require the declared fifteen-case matrix')
    if p['settings']!=dict(bench_weight=.1,terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.,baseline_mode='feasibility') or p['resources']['threads']!=2:raise ValueError('Unsupported diagnostic objective or threads')
    if digest(decisions)!=p['forecast_bundle_sha256'] or digest(decisions)!=locked['input_sha256']['decisions'] or digest(opening)!=locked['input_sha256']['opening']:raise ValueError('Frozen input checksum mismatch')
    weeks=read(decisions)['weeks'];common=read(opening);assert len(weeks)==38
    Settings(**p['settings'])
    references={g:digest(Path(reference)/f'GW{g:02d}_decision.json') for g in p['origin_gameweeks']}
    destination=output_path(output,home)
    if destination.exists():raise ValueError('Probe output exists; preserve prior attempts')
    destination.mkdir(parents=True)
    result=dict(schema_version=1,scope=p['scope'],reference_source_commit=p['reference_source_commit'],
        protocol_sha256=protocol_sha256,lock_sha256=lock_sha256,
        source_sha256=locked['source_sha256'],python=locked['python'],packages=locked['packages'],
        tool_sha256=digest(Path(__file__)),independent_auditor_sha256=digest(Path(__file__).with_name('audit_season_path.py')),
        input_sha256=dict(decisions=digest(decisions),opening=digest(opening)),cases=[],complete=False,
        model_promotion=False,policy_promotion=False,global_season_bound=None,
        solver_identity='standing CanonicalPlanner' if inner is None else 'Injected callback; mechanical/research check only')
    failed_attempt=None
    solve=CanonicalPlanner() if inner is None else inner
    from season_engine import Action
    try:
        with threadpool_limits(limits=p['resources']['threads']):
            for origin in p['origin_gameweeks']:
                spec=weeks[origin-1];market=Market.create(**spec['market']);raw=read(Path(reference)/f'GW{origin:02d}_decision.json')
                assert raw['gameweek']==market.gameweek==origin and raw['inputs_as_of']==market.as_of
                state=State(**dict(raw['state_before'],holdings=tuple(map(tuple,raw['state_before']['holdings'])),used_chips=tuple(map(tuple,raw['state_before']['used_chips']))))
                horizon=forecast(market,spec['forecast'],p['horizon'])
                assert dict(horizon.provenance)==raw['forecast_provenance']
                original=[Action(**{k:tuple(v) if k in ('buys','sells','starters','bench') else v for k,v in action.items()}) for action in raw['provisional_actions']]
                reference_value,reference_rosters=verify_plan(state,spec['market'],horizon,original,spec['blocked_tokens'])
                if origin==1:assert reference_rosters[0]==set(common)
                assert abs(reference_value-raw['report']['objective'])<1e-6
                schedule={g:a.chip for g,a in zip(horizon.gameweeks,original) if a.chip}
                expected_schedule={int(g):name for g,name in raw['report']['chip_schedule'].items()}
                assert schedule==expected_schedule
                frozen=dict(state=raw['state_before'],market=spec['market'],forecast=spec['forecast'],chip_schedule=schedule,
                    reference_actions=raw['provisional_actions'],reference_objective=reference_value,blocked_tokens=spec['blocked_tokens'],
                    reference_decision_sha256=digest(Path(reference)/f'GW{origin:02d}_decision.json'))
                payload=encode(frozen);request=destination/f'GW{origin:02d}_input.json.gz'
                with request.open('xb') as stream:stream.write(gzip.compress(payload))
                for seconds in p['inner_seconds']:
                    settings=Settings(**p['settings'],seconds=seconds)
                    baseline,_=make_baseline(state,market,horizon,settings,common if origin==1 else None)
                    pool={v['id'] for v in candidate_players(state,market,horizon,settings,baseline)}
                    comparable=all(ids<=pool for ids in reference_rosters)
                    failed_attempt=dict(origin=origin,inner_seconds=seconds,input_sha256=digest(request),phase='solver call')
                    started=time.monotonic()
                    actions,report=solve(state,market,horizon,settings,chip_schedule=schedule,opening_ids=common if origin==1 else None)
                    failed_attempt.update(phase='admission',actions=actions,report=report)
                    wall=time.monotonic()-started
                    value,rosters=verify_plan(state,spec['market'],horizon,actions,spec['blocked_tokens'])
                    assert all(ids<=pool for ids in rosters) and abs(value-report['objective'])<1e-6
                    if origin==1:assert rosters[0]==set(common)
                    bound=report['selected_plan_bound'];assert bound['status']!='inconsistent_dual'
                    upper=bound['upper_objective']
                    if upper is not None:
                        assert upper>=value-1e-5
                        if comparable:assert upper>=reference_value-1e-5,'Conditional bound excludes an admitted reference plan'
                    row=dict(origin=origin,inner_seconds=seconds,reference_objective=reference_value,objective=value,
                        difference_vs_reference=value-reference_value,selected_conditional_bound=bound,
                        comparable_reference_pool=comparable,pool_players=len(pool),
                        candidate_ids_sha256=hashlib.sha256(encode(sorted(pool))).hexdigest(),
                        fallback_retained=report['fallback_retained'],seconds=wall,solver_report_seconds=report['seconds'],
                        input_sha256=digest(request),reference_decision_sha256=frozen['reference_decision_sha256'])
                    output_case=destination/f'GW{origin:02d}_{str(seconds).replace(".","p")}s.json'
                    with output_case.open('x') as stream:json.dump(dict(metrics=row,actions=[asdict(a) for a in actions],report=report),stream,indent=2,allow_nan=False)
                    result['cases'].append(row)
                    failed_attempt=None
        verify_sources(locked)
        assert digest(protocol)==protocol_sha256 and digest(lock)==lock_sha256
        assert digest(decisions)==result['input_sha256']['decisions'] and digest(opening)==result['input_sha256']['opening']
        assert references=={g:digest(Path(reference)/f'GW{g:02d}_decision.json') for g in p['origin_gameweeks']}
        assert digest(Path(__file__))==result['tool_sha256'] and digest(Path(__file__).with_name('audit_season_path.py'))==result['independent_auditor_sha256']
        result['complete']=len(result['cases'])==15
        with (destination/'summary.json').open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    except Exception as error:
        with (destination/'failure.json').open('x') as stream:json.dump(failure_evidence(dict(error_type=type(error).__name__,message=str(error),partial=result,failed_attempt=failed_attempt)),stream,indent=2,allow_nan=False)
        raise
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['decisions','reference','opening','lock','protocol','output','home']:p.add_argument('--'+name,type=Path,required=True)
    for name in ['lock-sha256','protocol-sha256']:p.add_argument('--'+name,required=True)
    a=p.parse_args();value=run(a.decisions,a.reference,a.opening,a.lock,a.lock_sha256,a.protocol,a.protocol_sha256,a.output,a.home)
    print(json.dumps(dict(cases=len(value['cases']),complete=value['complete'],model_promotion=False,policy_promotion=False)))
if __name__=='__main__':main()
