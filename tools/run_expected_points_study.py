"""Source-locked two-season/common-opening study; execute one bounded arm.

Run serially under experiment_runner's process-group/storage watchdog. Weights
and policy approval are never changed. All raw failures remain in the destination.
"""
import argparse
import contextlib
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
from threadpoolctl import threadpool_limits
from season_benchmark import read_bundle,run,Policy
from season_engine import Market
from season_qualification import Trace,Guarded
from rolling_planner import Settings
from native_planner import NativeProcess,NativePlanner,CanonicalPlanner

POLICIES=('standingH1_adaptive','standingH6_adaptive','SolioAdaptedH6_sharedAdaptiveChips')
ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sampler(market,seed):
    s=importlib.util.spec_from_file_location('original_source_only_sampler',ROOT/'tools/run_season_robustness.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    return m.opening(market,seed)


def protocol(path):
    p=json.loads(Path(path).read_text())
    if p['schema_version']!=1 or p['seasons']!=['2024-25','2025-26'] or p['opening_seeds']!=[20261070,20261071] or tuple(p['policies'])!=POLICIES or p['paths']!=12 or p['repetitions']!=1:raise ValueError('Undeclared study matrix')
    if p['resources']!=dict(threads=2,seconds_per_path=900,memory_mib=4096,outer_seconds=15,inner_seconds=2,max_trials=12,project_mib=2560,growth_mib=384,min_free_mib=5120):raise ValueError('Resource contract differs')
    return p


def private_destination(path):
    p=Path(path).resolve()
    if p.is_relative_to(ROOT) or p.exists():raise ValueError('Require new output outside public checkout')
    return p


def fingerprint(manifest,manifest_sha256,protocol_path):
    if digest(manifest)!=manifest_sha256:raise ValueError('Reference manifest checksum differs')
    p=protocol(protocol_path);references=json.loads(Path(manifest).read_text())
    if set(references)!=set(p['seasons']):raise ValueError('Reference seasons differ')
    for entries in references.values():
        if set(entries)!=set(('decisions','outcomes')):raise ValueError('Reference inputs differ')
        for e in entries.values():
            if digest(e['path'])!=e['sha256']:raise ValueError('Reference checksum differs')
    files=sorted((ROOT/'src').glob('*.py'))+sorted((ROOT/'src/fpl_predict_resources').glob('*.json'))+[Path(__file__),ROOT/'tools/run_season_robustness.py',ROOT/'tools/prepare_season_2024.py',ROOT/'tools/evaluate_season_policies.py']
    return dict(schema_version=1,manifest_sha256=manifest_sha256,protocol_sha256=digest(protocol_path),inputs=references,
        source_sha256={str(f.relative_to(ROOT)):digest(f) for f in files},python=sys.version.split()[0],packages={n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn','joblib','threadpoolctl']})


def create_lock(manifest,manifest_sha256,protocol_path,output):
    p=protocol(protocol_path);fp=fingerprint(manifest,manifest_sha256,protocol_path);openings={}
    for season,refs in fp['inputs'].items():
        d=read_bundle(refs['decisions']['path'])
        if d['schema_version']!=1 or len(d['weeks'])!=38 or [v['market']['gameweek'] for v in d['weeks']]!=list(range(1,39)) or any(v['market']['season']!=season for v in d['weeks']):raise ValueError('Incomplete or mismatched season')
        market=Market.create(**d['weeks'][0]['market']);openings[season]={str(n):sampler(market,n) for n in p['opening_seeds']}
        if len({tuple(x['ids']) for x in openings[season].values()})!=2:raise ValueError('Duplicate opening')
    result=dict(fingerprint=fp,openings=openings);path=private_destination(output);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    return result


def run_arm(manifest,manifest_sha256,protocol_path,lock,lock_sha256,season,seed,policy,output,*,native_python=None,solio_source=None,solio_site_packages=None):
    if digest(lock)!=lock_sha256:raise ValueError('Lock checksum differs')
    frozen=json.loads(Path(lock).read_text());p=protocol(protocol_path)
    if frozen['fingerprint']!=fingerprint(manifest,manifest_sha256,protocol_path):raise ValueError('Source/input/runtime drift')
    if season not in p['seasons'] or seed not in p['opening_seeds'] or policy not in POLICIES:raise ValueError('Undeclared arm')
    refs=frozen['fingerprint']['inputs'][season];d=read_bundle(refs['decisions']['path']);hidden=read_bundle(refs['outcomes']['path']);m=Market.create(**d['weeks'][0]['market'])
    opening=frozen['openings'][season][str(seed)]
    if sampler(m,seed)!=opening:raise ValueError('Opening drift')
    evaluator={int(g):{int(i):v for i,v in row.items()} for g,row in hidden['weeks'].items()};directory=private_destination(output);directory.mkdir(parents=True);trace=None;metadata=None
    with contextlib.ExitStack() as stack:
        if policy.startswith('Solio'):
            if not all([native_python,solio_source,solio_site_packages]):raise ValueError('Native runtime required')
            actor=stack.enter_context(NativeProcess(native_python,solio_source,directory/'native_stderr.log',site_packages=solio_site_packages));trace=Trace(actor,directory,'solio',stack);metadata=actor.metadata
            inner=Guarded(CanonicalPlanner(NativePlanner(trace)),directory,trace)
        else:inner=Guarded(CanonicalPlanner(),directory)
        with threadpool_limits(limits=2):
            result=run(d['weeks'],evaluator,directory/'season',policy=Policy(1 if policy.startswith('standingH1') else 6,True,15,2,12),opening_ids=opening['ids'],settings=Settings(baseline_mode='feasibility',terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.),inner_planner=inner)
    if frozen['fingerprint']!=fingerprint(manifest,manifest_sha256,protocol_path):raise ValueError('Drift during replay')
    result.update(season=season,seed=seed,policy_id=policy,lock_sha256=lock_sha256,native_runtime=metadata,native_calls=trace.calls if trace else 0,native_failed_attempts=trace.failed if trace else 0,model_promotion=False,policy_promotion=False)
    with (directory/'summary.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['lock','arm'])
    for name in ('manifest','protocol','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--manifest-sha256',required=True)
    for name in ('lock','native-python','solio-source','solio-site-packages'):p.add_argument('--'+name,type=Path)
    p.add_argument('--lock-sha256');p.add_argument('--season');p.add_argument('--seed',type=int);p.add_argument('--policy',choices=POLICIES);a=p.parse_args()
    if a.command=='lock':create_lock(a.manifest,a.manifest_sha256,a.protocol,a.output)
    else:
        if not all([a.lock,a.lock_sha256,a.season,a.seed,a.policy]):p.error('Arm requires lock/hash/season/seed/policy')
        run_arm(a.manifest,a.manifest_sha256,a.protocol,a.lock,a.lock_sha256,a.season,a.seed,a.policy,a.output,native_python=a.native_python,solio_source=a.solio_source,solio_site_packages=a.solio_site_packages)


if __name__=='__main__':main()
