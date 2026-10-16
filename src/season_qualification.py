"""Locked, bounded per-arm execution for the declared season-policy study."""
import argparse
import contextlib
import datetime as dt
import gzip
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path
from threadpoolctl import threadpool_limits
from adaptive_planner import Budget
from airsenal_planner import AIrsenalProcess,AIrsenalPlanner
from experiment_runner import file_hash
from management_policies import FixedCalendarPolicy,HoldPolicy
from native_planner import NativeProcess,NativePlanner,CanonicalPlanner
from native_solver_worker import read_json
from rolling_planner import Settings
from runtime import RESOURCES,workspace_root
from season_benchmark import run,Policy,read_bundle

PROTOCOL=RESOURCES/'season_policy_qualification_protocol.json'
POLICIES=('standingH1_adaptive','standingH6_adaptive','SolioAdaptedH6_sharedAdaptiveChips','AIrsenalAdaptedH6_sharedAdaptiveChips')
SOURCE_FILES=('season_qualification.py','season_benchmark.py','management_policies.py',
    'adaptive_planner.py','rolling_planner.py','horizon_forecast.py','season_engine.py',
    'points_replay.py','selection_benchmark.py','forecast.py','forecast_sensitivity.py',
    'fpl_model.py','model_registry.py','availability_evidence.py','native_planner.py',
    'airsenal_planner.py','native_solver_worker.py','airsenal_solver_worker.py',
    'native_transport.py','opening_baseline.py','experiment_runner.py','runtime.py','fpl_predict_cli.py')
RESOURCE_FILES=('season_policy_qualification_protocol.json','season_rules.json',
                'native_solver_recipe.json','airsenal_solver_recipe.json')


def protocol(path=PROTOCOL):
    p=read_json(Path(path).read_bytes())
    if p.get('schema_version')!=1 or tuple(p['policies'])!=POLICIES or p['openings']!=['own','common'] or p['replications']!=[1,2] or p['total_paths']!=20:raise ValueError('Unsupported qualification matrix')
    r=p['resources'];Budget(r['outer_seconds'],r['inner_seconds'],r['max_trials'])
    if r['threads']!=2:raise ValueError('Admitted native and standing workers require two threads')
    for key in ['forecast_bundle_sha256','outcome_bundle_sha256','common_opening_sha256']:
        if not isinstance(p[key],str) or len(p[key])!=64 or any(c not in '0123456789abcdef' for c in p[key]):raise ValueError('Require declared SHA256 inputs')
    Settings(**p['canonical_settings'])
    return p


def arms(p):
    result=[]
    for replication in p['replications']:
        for opening in p['openings']:
            for name in p['policies']:
                result.append(dict(name=f'r{replication}_{opening}_{name}',policy=name,
                    opening=opening,replication=replication,horizon=1 if name.startswith('standingH1_') else 6))
    for name in ['fixed_calendar','hold_no_chips']:
        for opening in p['openings']:
            result.append(dict(name=f'control_{opening}_{name}',policy=name,opening=opening,replication=None,horizon=6))
    return result


def output_path(path,home=None):
    root=Path(home or workspace_root()).resolve();path=Path(path).resolve()
    if not path.is_relative_to(root) or path==root:raise ValueError('Qualification output must be inside its private runtime home')
    if path.is_relative_to(Path(__file__).resolve().parent):raise ValueError('Never write qualification outputs into source')
    repo=Path(__file__).resolve().parent.parent
    if (repo/'.git').exists() and path.is_relative_to(repo) and path.relative_to(repo).parts[0] not in ('var','data','artifacts','forecasts','experiments','decision_trials'):
        raise ValueError('Use an ignored runtime directory or an external private home')
    return path


def fingerprint(decisions,outcomes,opening,protocol_path=PROTOCOL):
    p=protocol(protocol_path);paths=dict(decisions=Path(decisions),outcomes=Path(outcomes),opening=Path(opening))
    inputs={name:file_hash(path) for name,path in paths.items()}
    expected=dict(decisions=p['forecast_bundle_sha256'],outcomes=p['outcome_bundle_sha256'],opening=p['common_opening_sha256'])
    if inputs!=expected:raise ValueError('Qualification inputs differ from the predeclared protocol')
    source=Path(__file__).resolve().parent
    files={name:file_hash(source/name) for name in SOURCE_FILES}
    files.update({f'fpl_predict_resources/{name}':file_hash(RESOURCES/name) for name in RESOURCE_FILES})
    return dict(schema_version=1,protocol_sha256=file_hash(protocol_path),input_sha256=inputs,
        source_sha256=files,python=sys.version.split()[0],
        packages={name:importlib.metadata.version(name) for name in ['numpy','pandas','scipy','scikit-learn','joblib','threadpoolctl']},
        arms=arms(p),scope='Listed engine/control/protocol sources and runtime/input identities; historical freeze is retrospective, not proof forecasts existed before deadlines')


def create_lock(decisions,outcomes,opening,destination,*,protocol_path=PROTOCOL,home=None):
    value=fingerprint(decisions,outcomes,opening,protocol_path)
    path=output_path(destination,home);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as stream:json.dump(dict(value,created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat()),stream,indent=2,allow_nan=False)
    return value


class Trace:
    """Keep every RPC compressed; unexpected failures remain fatal."""
    def __init__(self,actor,directory,kind,stack):
        if kind not in ('solio','airsenal'):raise ValueError('Unsupported native trace kind')
        self.actor=actor;self.directory=directory;self.kind=kind;self.calls=0;self.failed=0;self.last=None
        self.stream=stack.enter_context(gzip.open(directory/'native_trace.jsonl.gz','xb',compresslevel=6))
    def request(self,value):
        self.calls+=1;reply=self.actor.request(value);self.last=(value,reply)
        self.stream.write((json.dumps(dict(index=self.calls,request=value,reply=reply),allow_nan=False)+'\n').encode());self.stream.flush()
        if reply.get('status')!='completed':
            self.failed+=1
            with (self.directory/f'native_failure_{self.calls:04d}.json').open('x') as stream:json.dump(dict(request=value,reply=reply),stream,indent=2,allow_nan=False)
            expected=(reply.get('message')=='No feasible native incumbent') if self.kind=='solio' else (
                reply.get('error_type')=='NativeBudgetExpired' or reply.get('message')=='No complete native plan within budget' or
                reply.get('error_type')=='ValueError' and reply.get('message','').startswith('The squad search found no legal squad'))
            if not expected:raise RuntimeError('Unexpected native failure; retain trace and stop the path')
        return reply


class Guarded:
    def __init__(self,inner,directory,trace=None):self.inner=inner;self.directory=directory;self.trace=trace
    def __call__(self,*args,**kwargs):
        actions,report=self.inner(*args,**kwargs)
        if report['selected_plan_bound']['status']=='inconsistent_dual':raise ValueError('Inconsistent selected-plan bound')
        if self.trace is not None and report['solver_diagnostics']['native_error_type'] is not None and self.trace.last[1].get('status')=='completed':
            with (self.directory/f'native_invalid_{self.trace.calls:04d}.json').open('x') as stream:json.dump(dict(request=self.trace.last[0],reply=self.trace.last[1],report=report),stream,indent=2,allow_nan=False)
            raise ValueError('Completed native proposal failed admission; stop the path')
        return actions,report


def run_arm(name,decisions,outcomes,opening,lock_path,lock_sha256,directory,*,protocol_path=PROTOCOL,
        home=None,native_python=None,solio_source=None,solio_site_packages=None,airsenal_site_packages=None):
    raw=Path(lock_path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=lock_sha256:raise ValueError('Qualification lock checksum mismatch')
    locked=read_json(raw);locked.pop('created_at_utc',None)
    if locked!=fingerprint(decisions,outcomes,opening,protocol_path):raise ValueError('Qualification source/runtime/input drift')
    p=protocol(protocol_path);arm=next((a for a in arms(p) if a['name']==name),None)
    if arm is None:raise ValueError('Undeclared qualification arm')
    directory=output_path(directory,home)
    if directory.exists():raise ValueError('Qualification output exists; preserve prior attempts')
    if arm['policy'].startswith('Solio') and not all([native_python,solio_source,solio_site_packages]):raise ValueError('Explicit optional Solio runtime required')
    if arm['policy'].startswith('AIrsenal') and not all([native_python,airsenal_site_packages]):raise ValueError('Explicit optional AIrsenal runtime required')
    bundle=read_bundle(decisions);hidden=read_bundle(outcomes)
    if bundle.get('schema_version')!=1 or hidden.get('schema_version')!=1:raise ValueError('Unsupported replay bundles')
    evaluator={int(g):{int(i):v for i,v in rows.items()} for g,rows in hidden['weeks'].items()}
    common=read_json(Path(opening).read_bytes()) if arm['opening']=='common' else None
    directory.mkdir(parents=True);trace=None;metadata=None;startup=None;manager=None;inner=None
    with contextlib.ExitStack() as stack:
        if arm['policy'].startswith('Solio'):
            actor=stack.enter_context(NativeProcess(native_python,solio_source,directory/'native_stderr.log',site_packages=solio_site_packages))
            metadata=actor.metadata;startup=actor.startup_seconds;trace=Trace(actor,directory,'solio',stack)
            inner=Guarded(CanonicalPlanner(NativePlanner(trace)),directory,trace)
        elif arm['policy'].startswith('AIrsenal'):
            actor=stack.enter_context(AIrsenalProcess(native_python,airsenal_site_packages,directory/'native_stderr.log',directory/'research-home'))
            metadata=actor.metadata;startup=actor.startup_seconds;trace=Trace(actor,directory,'airsenal',stack)
            inner=Guarded(CanonicalPlanner(AIrsenalPlanner(trace)),directory,trace)
        elif arm['policy']=='fixed_calendar':
            manager=FixedCalendarPolicy({int(g):c for g,c in p['controls']['fixed_calendar'].items()})
        elif arm['policy']=='hold_no_chips':manager=HoldPolicy()
        else:inner=Guarded(CanonicalPlanner(),directory)
        if manager is not None:
            delegate=manager
            def manager(*args,**kwargs):
                actions,report=delegate(*args,**kwargs)
                bounds=[report['selected_schedule_bound'],*[t['selected_plan_bound'] for t in report['trials']]]
                if any(b['status']=='inconsistent_dual' for b in bounds):raise ValueError('Inconsistent whole-policy bound')
                return actions,report
        r=p['resources'];settings=Settings(**p['canonical_settings'])
        with threadpool_limits(limits=r['threads']):
            summary=run(bundle['weeks'],evaluator,directory/'season',policy=Policy(arm['horizon'],True,r['outer_seconds'],r['inner_seconds'],r['max_trials']),
                opening_ids=common,settings=settings,inner_planner=inner,management_policy=manager,
                management_policy_id=arm['policy']+'-v1' if manager is not None else None)
    if locked!=fingerprint(decisions,outcomes,opening,protocol_path):raise ValueError('Qualification drift during execution; retain path but do not accept completion')
    summary.update(arm=arm,qualification_lock_sha256=lock_sha256,protocol_sha256=file_hash(protocol_path),
        input_sha256=locked['input_sha256'],native_runtime=metadata,native_startup_seconds=startup,
        native_calls=trace.calls if trace else 0,native_failed_attempts=trace.failed if trace else 0,
        model_promotion=False,policy_promotion=False)
    with (directory/'summary.json').open('x') as stream:json.dump(summary,stream,indent=2,allow_nan=False)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    listing=sub.add_parser('arms');listing.add_argument('--protocol',type=Path,default=PROTOCOL)
    for verb in ['lock','arm']:
        q=sub.add_parser(verb)
        for field in ['decisions','outcomes','opening','output']:q.add_argument('--'+field,type=Path,required=True)
        q.add_argument('--protocol',type=Path,default=PROTOCOL);q.add_argument('--home',type=Path)
        if verb=='arm':
            q.add_argument('--name',required=True);q.add_argument('--lock',type=Path,required=True);q.add_argument('--lock-sha256',required=True)
            for field in ['native-python','solio-source','solio-site-packages','airsenal-site-packages']:q.add_argument('--'+field,type=Path)
    a=parser.parse_args()
    if a.command=='arms':print(json.dumps(arms(protocol(a.protocol)),indent=2));return
    if a.command=='lock':create_lock(a.decisions,a.outcomes,a.opening,a.output,protocol_path=a.protocol,home=a.home)
    else:run_arm(a.name,a.decisions,a.outcomes,a.opening,a.lock,a.lock_sha256,a.output,protocol_path=a.protocol,home=a.home,
        native_python=a.native_python,solio_source=a.solio_source,solio_site_packages=a.solio_site_packages,airsenal_site_packages=a.airsenal_site_packages)


if __name__=='__main__':main()
