"""Offline build, one-fit worker, and aggregate for the frozen mits-r2 study.

Invoke each worker inside the qualified Windows guard. No network or registry
access. A new output and an exclusive six-slot ledger preserve every attempt.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import warnings

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import PoissonRegressor
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits, threadpool_info

from market_stage_b import SEASONS,FOLDS,ARMS,FEATURES,features,finite_shared,fold_masks,scores,paired_blocks
from market_strength import timestamp

PROTOCOL=Path(__file__).resolve().parents[1]/'docs/market_strength_stage_b_protocol_2026-10-28.json'
PROTOCOL_SHA='2bff608e5cf10aadbcbfc7f01e08110c3a917c8b7e3f2bf4445d831af2e8200d'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def protocol():
    raw=PROTOCOL.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(raw).hexdigest()!=PROTOCOL_SHA:raise ValueError('Frozen Stage-B protocol differs')
    d=json.loads(raw)
    if d['features']!=FEATURES:raise ValueError('Feature declaration differs')
    return d


def verified(entry):
    p=Path(entry['path'])
    if p.stat().st_size>200_000_000 or digest(p)!=entry['sha256']:raise ValueError('Input hash/size differs: '+str(p))
    return p


def read_csv(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as f:
        yield from csv.DictReader(f)


def write_json(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def save_npz(path,**values):
    with Path(path).open('xb') as f:np.savez_compressed(f,**values)


def load_inputs(manifest):
    # Verify original admitted inputs without using their results as targets.
    for entry in manifest['markets']:verified(entry)
    i4=json.loads(verified(manifest['i4_manifest']).read_text())
    if manifest['teams']['sha256']!=i4['inputs']['teams']['sha256'] or manifest['players']['sha256']!=i4['inputs']['players']['sha256']:
        raise ValueError('Not the frozen I4 sources')
    understat={}
    for row in read_csv(verified(manifest['teams'])):
        if row['season'] not in SEASONS:continue
        key=(row['season'],int(row['fixture']),row['team_name'])
        if key in understat:raise ValueError('Duplicate Understat team-match')
        pair=(float(row['xg']),float(row['xga']))
        if not np.isfinite(pair).all():raise ValueError('Non-finite admitted xG')
        understat[key]=pair
    contexts={}
    for row in read_csv(verified(manifest['players'])):
        if row['season'] not in SEASONS:continue
        key=(row['season'],int(row['fixture']));value=(int(row['gameweek']),row['deadline'])
        if key in contexts and contexts[key]!=value:raise ValueError('Inconsistent common target origin')
        contexts[key]=value
    fixtures={}
    if set(manifest['fpl'])!=set(SEASONS):raise ValueError('Wrong FPL target seasons')
    for season,entries in manifest['fpl'].items():
        clubs={int(r['id']):r['name'] for r in read_csv(verified(entries['teams']))}
        for row in read_csv(verified(entries['history'])):
            fixture=int(row['fixture']);key=(season,fixture);home=row['was_home'].lower()=='true'
            own=row['team'];opp=clubs[int(row['opponent_team'])]
            rec=dict(season=season,fixture=fixture,home=own if home else opp,away=opp if home else own,
                     fpl_kickoff=row['kickoff_time'],goals_home=float(row['team_h_score']),goals_away=float(row['team_a_score']))
            if key in fixtures and fixtures[key]!=rec:raise ValueError('FPL fixture score/context conflict')
            fixtures[key]=rec
    market=[];matched=set()
    lambdas=json.loads(verified(manifest['lambdas']).read_text())
    if Counter(r['season'] for r in lambdas)!=Counter({s:380 for s in ('2019-20',*SEASONS)}):raise ValueError('Market season coverage changed')
    for row in lambdas:
        rec=dict(season=row['season'],fixture=row['fixture'],date=row['csv_kickoff'][:10],home=row['home'],away=row['away'],
                 csv_kickoff=row['csv_kickoff'],lambda_home=row['lambda_home'],lambda_away=row['lambda_away'])
        if rec['season']!='2019-20':
            key=(rec['season'],int(rec['fixture']));f=fixtures[key]
            if (f['home'],f['away'])!=(rec['home'],rec['away']) or timestamp(f['fpl_kickoff'])!=timestamp(row['canonical_kickoff']):
                raise ValueError('Market/FPL target identity mismatch')
            rec['fpl_kickoff']=f['fpl_kickoff'];f['csv_kickoff']=rec['csv_kickoff'];matched.add(key)
        market.append(rec)
    if matched!=set(fixtures) or set(contexts)!=set(fixtures):raise ValueError('Incomplete shared fixture cohort')
    for key,f in fixtures.items():
        h=understat[(*key,f['home'])];a=understat[(*key,f['away'])]
        if not np.allclose([h[0],h[1]],[a[1],a[0]],atol=1e-8,rtol=0):raise ValueError('Understat side parity differs')
        f.update(xg_home=h[0],xg_away=a[0],gameweek=contexts[key][0],deadline=contexts[key][1])
    if Counter(f['season'] for f in fixtures.values())!=Counter({s:380 for s in SEASONS}):raise ValueError('Fixture count differs')
    return list(fixtures.values()),market


def build(manifest,output):
    cfg=protocol();tick=time.monotonic()
    if (output/'bundle.npz').exists():raise ValueError('Do not overwrite feature bundle')
    fixtures,market=load_inputs(manifest)
    with threadpool_limits(limits=2):x,y,keys,meta=features(fixtures,market)
    if Counter(r['season'] for r in meta)!=Counter({s:760 for s in SEASONS}):raise ValueError('Not all team-matches present')
    if len(set(keys))!=len(keys):raise ValueError('Duplicate team-match keys')
    values={**{'X_'+a:x[a] for a in ARMS},'y':y,'season':np.asarray([r['season'] for r in meta]),
            'gameweek':np.asarray([r['gameweek'] for r in meta],dtype=int),'fixture':np.asarray([r['fixture'] for r in meta],dtype=int),
            'team':np.asarray([r['team'] for r in meta]),'cutoff':np.asarray([r['cutoff'] for r in meta])}
    save_npz(output/'bundle.npz',**values)
    proof=canonical_hash([dict(key=list(k),target=float(v),cutoff=r['cutoff']) for k,v,r in zip(keys,y,meta)])
    cold={}
    for s in SEASONS:
        rows=[r for r in meta if r['season']==s]
        cold[s]={k:sum(bool(r[k]) for r in rows) for k in ['cold_start_C','cold_start_U','cold_start_M','cold_start_M_opponent','promoted_team']}
    summary=dict(status='built',rows=len(y),rows_per_season=dict(Counter(r['season'] for r in meta)),
        features=FEATURES,shared_keys_targets_origins_sha256=proof,bundle_sha256=digest(output/'bundle.npz'),
        protocol_lf_sha256=PROTOCOL_SHA,cold_start_and_promoted_counts=cold,
        rating_origins=len({r['cutoff'] for r in meta}),seconds=time.monotonic()-tick,
        inputs=manifest,stage_B_GLM_fits=0,stage_C_fits=0,
        scope='Identical keys/targets/cutoffs for C/U/M. Target/future outcomes excluded by chronological source clocks; already-played same-season history is allowed.')
    write_json(output/'metadata.json',meta);write_json(output/'summary.json',summary)
    print(json.dumps({k:summary[k] for k in ['status','rows','rows_per_season','seconds']}))


def fit(bundle,fold,arm,ledger,output):
    cfg=protocol();tick=time.monotonic()
    if fold not in FOLDS or arm not in ARMS:raise ValueError('Undeclared arm/fold')
    with np.load(bundle,allow_pickle=False) as source:d={k:source[k] for k in source.files}
    finite_shared({a:d['X_'+a] for a in ARMS},d['y'])
    if set(d['season'])!=set(SEASONS):raise ValueError('Wrong cohort seasons')
    train,test=fold_masks(d['season'],fold)
    if test.sum()!=760 or train.sum()!=760*(2 if fold=='2022-23' else 3):raise ValueError('Fold cohort differs')
    parent_summary=json.loads((bundle.parent/'summary.json').read_text())
    if digest(bundle)!=parent_summary['bundle_sha256']:raise ValueError('Feature artifact changed')
    proof=canonical_hash([dict(key=[str(s),int(f),str(t)],target=float(y),cutoff=str(c))
                          for s,f,t,y,c in zip(d['season'],d['fixture'],d['team'],d['y'],d['cutoff'])])
    if proof!=parent_summary['shared_keys_targets_origins_sha256']:raise ValueError('Pre-score key/target/origin parity differs')
    if any(d['X_'+a].shape[1]!=len(FEATURES[a]) for a in ARMS):raise ValueError('Feature schema differs')
    order=[(f,a) for f in FOLDS for a in ARMS];index=order.index((fold,arm));ledger.mkdir(parents=True,exist_ok=True)
    previous=sorted(ledger.glob('*.json'))
    if len(previous)!=index or any(json.loads(p.read_text())['status']!='completed' for p in previous):raise ValueError('Fit order/budget or prior failure; no silent retry')
    token=ledger/f'{index:02d}_{fold}_{arm}.json';attempt=dict(status='started',fold=fold,arm=arm,index=index,
        started_at=datetime.now(timezone.utc).isoformat(),protocol_lf_sha256=PROTOCOL_SHA,bundle_sha256=digest(bundle))
    write_json(token,attempt)
    try:
        scaler=StandardScaler();xx=scaler.fit_transform(d['X_'+arm][train]);xt=scaler.transform(d['X_'+arm][test])
        with warnings.catch_warnings():
            warnings.simplefilter('error',ConvergenceWarning)
            with threadpool_limits(limits=2):
                model=PoissonRegressor(alpha=0.,max_iter=1000,tol=.0001,solver='lbfgs',fit_intercept=True,warm_start=False)
                model.fit(xx,d['y'][train]);pred=model.predict(xt);pools=threadpool_info()
        result=scores(d['y'][test],pred)
        save_npz(output/'predictions.npz',pred=pred,y=d['y'][test],season=d['season'][test],fixture=d['fixture'][test],
                 team=d['team'][test],gameweek=d['gameweek'][test],cutoff=d['cutoff'][test])
        report=dict(status='completed',fold=fold,arm=arm,train_rows=int(train.sum()),test_rows=int(test.sum()),
                    train_seasons=sorted(set(d['season'][train])),test_seasons=sorted(set(d['season'][test])),
                    **result,n_iter=int(model.n_iter_),coefficients=model.coef_.tolist(),intercept=float(model.intercept_),
                    scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),threadpools=pools,
                    shared_keys_targets_origins_sha256=parent_summary['shared_keys_targets_origins_sha256'],
                    protocol_lf_sha256=PROTOCOL_SHA,bundle_sha256=digest(bundle),seconds=time.monotonic()-tick)
        write_json(output/'result.json',report)
        attempt.update(status='completed',result_sha256=digest(output/'result.json'))
    except BaseException as error:
        attempt.update(status='failed',error=repr(error));token.write_text(json.dumps(attempt,indent=2)+'\n');raise
    token.write_text(json.dumps(attempt,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:report[k] for k in ['fold','arm','mean_poisson_deviance','clean_sheet_Brier','calibration_rate_slope','seconds']}))


def aggregate(build_dir,fits_dir,output):
    protocol();summary=json.loads((build_dir/'summary.json').read_text());rows=[];comparisons={};passes=[]
    for fold in FOLDS:
        panels={};reports={}
        for arm in ARMS:
            directory=fits_dir/f'{fold}_{arm}';report=json.loads((directory/'result.json').read_text())
            run=json.loads((directory/'run.json').read_text())
            if report['status']!='completed' or run['status']!='completed' or report['shared_keys_targets_origins_sha256']!=summary['shared_keys_targets_origins_sha256']:
                raise ValueError('Incomplete/unqualified/mismatched fit')
            with np.load(directory/'predictions.npz',allow_pickle=False) as f:panels[arm]={k:f[k] for k in f.files}
            reports[arm]=report;rows.append(report)
        base=panels['C']
        for arm in ARMS:
            for k in ['y','season','fixture','team','gameweek','cutoff']:
                if not np.array_equal(base[k],panels[arm][k]):raise ValueError('Pre-score arm key/target/origin mismatch')
        comparisons[fold]={arm:paired_blocks(base['y'],panels['M']['pred'],panels[arm]['pred'],base['gameweek']) for arm in ['C','U']}
        passes.append(reports['M']['mean_poisson_deviance']<reports['C']['mean_poisson_deviance'] and reports['M']['mean_poisson_deviance']<reports['U']['mean_poisson_deviance'])
    report=dict(status='completed',protocol_lf_sha256=PROTOCOL_SHA,rows=rows,paired_intervals=comparisons,
                gate_B_per_fold=dict(zip(FOLDS,passes)),gate_B_pass=all(passes),GLM_attempts=6,stage_C_fits=0,
                cohort=summary,scope='Development team goals only; no model/policy/default promotion or season/player gain claim')
    write_json(output/'report.json',report);print(json.dumps(dict(gate_B_per_fold=report['gate_B_per_fold'],gate_B_pass=report['gate_B_pass'])))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['build','fit','aggregate'],required=True)
    p.add_argument('--manifest',type=Path);p.add_argument('--bundle',type=Path);p.add_argument('--fold');p.add_argument('--arm');p.add_argument('--ledger',type=Path)
    p.add_argument('--build-dir',type=Path);p.add_argument('--fits-dir',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    if a.phase=='build':build(json.loads(a.manifest.read_text(encoding='utf-8-sig')),a.output)
    elif a.phase=='fit':fit(a.bundle,a.fold,a.arm,a.ledger,a.output)
    else:aggregate(a.build_dir,a.fits_dir,a.output)
