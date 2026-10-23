"""Source-only common-opening sensitivity; never selects a winning policy.

Run serially under experiment_runner's process-group/storage watchdog. Each arm
checks the same frozen lock before and after execution. Native traces remain
private and retain expected failures; invalid completed proposals are fatal.
"""
import argparse
import contextlib
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random
import sys
from threadpoolctl import threadpool_limits
from season_benchmark import read_bundle,run,Policy
from season_engine import Market
from rolling_planner import Settings
from season_qualification import Trace,Guarded
from native_planner import NativeProcess,NativePlanner,CanonicalPlanner
from selection_benchmark import legal

POLICIES=('standingH1_adaptive','standingH6_adaptive','SolioAdaptedH6_sharedAdaptiveChips')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protocol(path):
    p=json.loads(Path(path).read_text())
    if p['schema_version']!=1 or tuple(p['robustness']['policies'])!=POLICIES or p['robustness']['opening_seeds']!=[20261024,20261025] or p['robustness']['total_paths']!=6:
        raise ValueError('Undeclared robustness matrix')
    if p['resources']!={'threads':2,'per_path_seconds':900,'sampled_rss_mib':4096,'outer_seconds':15,'inner_seconds':2,'max_trials':12,'project_mib':2048,'growth_mib':256,'min_free_mib':5120}:
        raise ValueError('Resource contract differs')
    return p


def opening(market,seed):
    """Price/club/position/ID only; no forecast or result can enter sampling."""
    by=market.indexed();rng=random.Random(seed)
    pools={p:sorted(r['id'] for r in market.players if r['position']==p and r['can_buy']) for p in range(1,5)}
    for attempt in range(100000):
        ids=sorted(i for p,n in [(1,2),(2,5),(3,5),(4,3)] for i in rng.sample(pools[p],n))
        players=[dict(by[i]) for i in ids];cost=sum(p['price_tenths'] for p in players)
        if legal(players) and 900<=cost<=1000:return dict(ids=ids,cost_tenths=cost,attempts=attempt+1)
    raise ValueError('Declared source-only opening budget exhausted')


def fingerprint(decisions,outcomes,protocol_path):
    p=protocol(protocol_path);source=Path(__file__).resolve().parents[1]
    files=sorted((source/'src').glob('*.py'))+sorted((source/'src/fpl_predict_resources').glob('*.json'))+[Path(__file__)]
    return dict(schema_version=1,protocol_sha256=digest(protocol_path),
        inputs_sha256=dict(decisions=digest(decisions),outcomes=digest(outcomes)),
        source_sha256={str(f.relative_to(source)):digest(f) for f in files},
        python=sys.version.split()[0],packages={n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn','joblib','threadpoolctl']},
        policies=list(POLICIES),seeds=p['robustness']['opening_seeds'])


def destination(path):
    path=Path(path).resolve();repo=Path(__file__).resolve().parents[1]
    if path.is_relative_to(repo):raise ValueError('Keep robustness outputs outside the public source checkout')
    if path.exists():raise ValueError('Output exists; preserve all prior trials')
    return path


def create_lock(decisions,outcomes,protocol_path,output):
    value=fingerprint(decisions,outcomes,protocol_path)
    d=read_bundle(decisions);m=Market.create(**d['weeks'][0]['market'])
    if m.gameweek!=1 or m.season!='2025-26' or len(d['weeks'])!=38:raise ValueError('Require admitted2025/26fullseason')
    value['openings']={str(seed):opening(m,seed) for seed in value['seeds']}
    if len({tuple(v['ids']) for v in value['openings'].values()})!=2:raise ValueError('Openings must differ')
    path=destination(output);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(value,f,indent=2,allow_nan=False)
    return value


def run_arm(decisions,outcomes,protocol_path,lock_path,lock_sha256,seed,policy,output,*,native_python=None,solio_source=None,solio_site_packages=None):
    if digest(lock_path)!=lock_sha256:raise ValueError('Lock checksum mismatch')
    locked=json.loads(Path(lock_path).read_text());expected=dict(locked);openings=expected.pop('openings')
    if expected!=fingerprint(decisions,outcomes,protocol_path):raise ValueError('Source/input/runtime drift')
    if str(seed) not in openings or policy not in POLICIES:raise ValueError('Undeclared arm')
    bundle=read_bundle(decisions);m=Market.create(**bundle['weeks'][0]['market'])
    if openings[str(seed)]!=opening(m,seed):raise ValueError('Opening changed')
    directory=destination(output);hidden=read_bundle(outcomes)
    evaluator={int(g):{int(i):v for i,v in row.items()} for g,row in hidden['weeks'].items()}
    directory.mkdir(parents=True);trace=None;metadata=None
    with contextlib.ExitStack() as stack:
        if policy.startswith('Solio'):
            if not all([native_python,solio_source,solio_site_packages]):raise ValueError('Native runtime required')
            actor=stack.enter_context(NativeProcess(native_python,solio_source,directory/'native_stderr.log',site_packages=solio_site_packages))
            trace=Trace(actor,directory,'solio',stack);metadata=actor.metadata
            inner=Guarded(CanonicalPlanner(NativePlanner(trace)),directory,trace)
        else:inner=Guarded(CanonicalPlanner(),directory)
        with threadpool_limits(limits=2):
            summary=run(bundle['weeks'],evaluator,directory/'season',policy=Policy(1 if policy.startswith('standingH1') else 6,True,15,2,12),
                opening_ids=openings[str(seed)]['ids'],settings=Settings(baseline_mode='feasibility',terminal_ft_value=0.,terminal_squad_weight=0.,churn_cost=0.),inner_planner=inner)
    if expected!=fingerprint(decisions,outcomes,protocol_path):raise ValueError('Drift during replay')
    summary.update(seed=seed,policy_id=policy,lock_sha256=lock_sha256,native_runtime=metadata,native_calls=trace.calls if trace else 0,native_failed_attempts=trace.failed if trace else 0,model_promotion=False,policy_promotion=False)
    with (directory/'summary.json').open('x') as f:json.dump(summary,f,indent=2,allow_nan=False)
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['lock','arm'])
    for name in ['decisions','outcomes','protocol','output']:p.add_argument('--'+name,type=Path,required=True)
    for name in ['lock','native-python','solio-source','solio-site-packages']:p.add_argument('--'+name,type=Path)
    p.add_argument('--lock-sha256');p.add_argument('--seed',type=int);p.add_argument('--policy',choices=POLICIES)
    a=p.parse_args()
    if a.command=='lock':create_lock(a.decisions,a.outcomes,a.protocol,a.output)
    else:
        if not all([a.lock,a.lock_sha256,a.seed,a.policy]):p.error('Arm requires lock/hash/seed/policy')
        run_arm(a.decisions,a.outcomes,a.protocol,a.lock,a.lock_sha256,a.seed,a.policy,a.output,native_python=a.native_python,solio_source=a.solio_source,solio_site_packages=a.solio_site_packages)


if __name__=='__main__':main()
