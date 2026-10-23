"""Compare two admitted fixed-schedule cores from identical frozen states.

No outcome/settlement arguments or reads. This is an outcome-informed numerical
diagnosis, not a season rebenchmark or automatic selection of a default policy.
Run serially after the historical batch under its resource/storage watchdog.
"""
import argparse,contextlib,gzip,hashlib,importlib.metadata,json,math,sys,time
from dataclasses import asdict
from pathlib import Path
from threadpoolctl import threadpool_limits
from native_planner import CanonicalPlanner,NativePlanner,NativeProcess
from season_qualification import Trace,Guarded
from season_benchmark import forecast,read_bundle
from season_engine import State,Market,Action
from rolling_planner import Settings,make_baseline,candidate_players
# Independent integer-ledger/mean-objective verifier from the source tools.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from probe_season_solver import verify_plan,failure_evidence


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def encode(value):return json.dumps(value,sort_keys=True,allow_nan=False).encode()


def run(decisions,reference,lock,lock_sha256,protocol,protocol_sha256,output,*,native_python=None,solio_source=None,solio_site_packages=None,solvers=None):
    repo=Path(__file__).resolve().parents[1];output=Path(output).resolve()
    if output.is_relative_to(repo) or output.exists():raise ValueError('Require a new private output directory')
    if digest(lock)!=lock_sha256 or digest(protocol)!=protocol_sha256:raise ValueError('Lock/protocol differs')
    p=json.loads(Path(protocol).read_text());locked=json.loads(Path(lock).read_text())
    if p['reference_seeds']!=[20261024,20261025] or p['origin_gameweeks']!=[1,6,16,30,38] or p['solvers']!=['standing','solio_adapted'] or p['inner_seconds']!=2. or p['horizon']!=6 or p['cases']!=20:raise ValueError('Undeclared fixed-state matrix')
    def verify():
        if digest(decisions)!=locked['inputs_sha256']['decisions']:raise ValueError('Decision input drift')
        if sys.version.split()[0]!=locked['python'] or any(importlib.metadata.version(n)!=v for n,v in locked['packages'].items()):raise ValueError('Runtime drift')
        for f,s in locked['source_sha256'].items():
            if (repo/f).resolve().is_relative_to(repo) is False or digest(repo/f)!=s:raise ValueError('Source drift')
    verify();weeks=read_bundle(decisions)['weeks'];output.mkdir(parents=True);cases=[];references={};tool_sha=digest(__file__)
    with contextlib.ExitStack() as stack:
        if solvers is None:
            if not all([native_python,solio_source,solio_site_packages]):raise ValueError('Explicit native runtime required')
            actor=stack.enter_context(NativeProcess(native_python,solio_source,output/'native_stderr.log',site_packages=solio_site_packages))
            traced=Trace(actor,output,'solio',stack)
            solvers={'standing':Guarded(CanonicalPlanner(),output),'solio_adapted':Guarded(CanonicalPlanner(NativePlanner(traced)),output,traced)}
            identity='Admitted standing and source-pinned native Solio cores';native_metadata=actor.metadata
        else:identity='Injected mechanical callbacks; not a numerical benchmark';native_metadata=None
        if set(solvers)!=set(p['solvers']):raise ValueError('Solver matrix differs')
        failed_attempt=None
        try:
            with threadpool_limits(limits=2):
                for seed in p['reference_seeds']:
                    for g in p['origin_gameweeks']:
                        path=Path(reference)/f'{seed}_standingH6_adaptive/result/season'/f'GW{g:02d}_decision.json'
                        raw=json.loads(path.read_text());references[str(path)]=digest(path);spec=weeks[g-1];market=Market.create(**spec['market']);h=forecast(market,spec['forecast'],6)
                        state=State(**dict(raw['state_before'],holdings=tuple(map(tuple,raw['state_before']['holdings'])),used_chips=tuple(map(tuple,raw['state_before']['used_chips']))))
                        if raw['gameweek']!=g or raw['inputs_as_of']!=market.as_of or dict(h.provenance)!=raw['forecast_provenance']:raise ValueError('Reference origin/provenance differs')
                        actions=[Action(**{k:tuple(v) if k in ['buys','sells','starters','bench'] else v for k,v in a.items()}) for a in raw['provisional_actions']]
                        ref,refids=verify_plan(state,spec['market'],h,actions,spec['blocked_tokens'])
                        if abs(ref-raw['report']['objective'])>1e-6:raise ValueError('Reference objective differs')
                        schedule={gw:a.chip for gw,a in zip(h.gameweeks,actions) if a.chip};opening=locked['openings'][str(seed)]['ids'] if g==1 else None
                        cfg=Settings(seconds=2.,baseline_mode='feasibility',terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.)
                        baseline,_=make_baseline(state,market,h,cfg,opening);pool={a['id'] for a in candidate_players(state,market,h,cfg,baseline)}
                        frozen=dict(state=raw['state_before'],market=spec['market'],forecast=spec['forecast'],chip_schedule=schedule,blocked_tokens=spec['blocked_tokens'],opening_ids=opening,reference_actions=raw['provisional_actions'],reference_objective=ref,candidate_ids=sorted(pool),reference_decision_sha256=digest(path))
                        name=f'{seed}_GW{g:02d}';payload=output/(name+'_input.json.gz')
                        with payload.open('xb') as f:f.write(gzip.compress(encode(frozen)))
                        for kind in p['solvers']:
                            failed_attempt=dict(seed=seed,origin=g,solver=kind,phase='solve')
                            tick=time.monotonic();chosen,report=solvers[kind](state,market,h,cfg,chip_schedule=schedule,opening_ids=opening)
                            failed_attempt.update(phase='admission',actions=chosen,report=report)
                            elapsed=time.monotonic()-tick;value,ids=verify_plan(state,spec['market'],h,chosen,spec['blocked_tokens'])
                            if type(report['objective']) not in (float,int) or not math.isfinite(report['objective']) or abs(value-report['objective'])>1e-6 or not all(x<=pool for x in ids):raise ValueError('Invalid returned objective or pool')
                            if opening is not None and ids[0]!=set(opening):raise ValueError('Opening changed')
                            comparable=all(x<=pool for x in refids);bound=report['selected_plan_bound'];upper=bound['upper_objective']
                            if bound['status']=='inconsistent_dual' or upper is not None and (type(upper) not in (float,int) or not math.isfinite(upper) or upper<value-1e-5 or comparable and upper<ref-1e-5):raise ValueError('Conditional bound excludes feasible plan')
                            row=dict(seed=seed,origin=g,solver=kind,objective=value,reference_objective=ref,difference_vs_reference=value-ref,seconds=elapsed,selected_conditional_bound=bound,reference_in_candidate_pool=comparable,pool_sha256=hashlib.sha256(encode(sorted(pool))).hexdigest(),input_sha256=digest(payload),fallback_retained=report['fallback_retained'])
                            with (output/(name+'_'+kind+'.json')).open('x') as f:json.dump(dict(metrics=row,actions=[asdict(a) for a in chosen],report=report),f,indent=2,allow_nan=False)
                            cases.append(row);failed_attempt=None
            verify()
            if digest(lock)!=lock_sha256 or digest(protocol)!=protocol_sha256 or digest(__file__)!=tool_sha:raise ValueError('Diagnostic drift')
            if any(digest(path)!=sha for path,sha in references.items()):raise ValueError('Frozen reference changed')
            result=dict(complete=len(cases)==20,cases=cases,identity=identity,source_tool_sha256=tool_sha,native_runtime=native_metadata,protocol_sha256=protocol_sha256,lock_sha256=lock_sha256,model_promotion=False,policy_promotion=False,scope=p['scope'])
            with (output/'summary.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
        except Exception as error:
            with (output/'failure.json').open('x') as f:json.dump(failure_evidence(dict(error_type=type(error).__name__,message=str(error),completed_cases=cases,failed_attempt=failed_attempt)),f,indent=2,allow_nan=False)
            raise
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['decisions','reference','lock','protocol','output','native-python','solio-source','solio-site-packages']:p.add_argument('--'+n,type=Path,required=True)
    for n in ['lock-sha256','protocol-sha256']:p.add_argument('--'+n,required=True)
    a=p.parse_args();run(a.decisions,a.reference,a.lock,a.lock_sha256,a.protocol,a.protocol_sha256,a.output,native_python=a.native_python,solio_source=a.solio_source,solio_site_packages=a.solio_site_packages)


if __name__=='__main__':main()
