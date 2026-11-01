"""Offline one-attempt confirmation admission, two exclusive fits and analysis."""
import argparse
import csv
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(Path(__file__).parent)]
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits,threadpool_info
import rmc_confirmation as study
import run_rich_market_combination as development
import run_market_stage_c as strict
import run_market_stage_c_amended as fixture


def build(manifest,output):
    development.protocol();runtime=fixture.legacy_runtime();tick=time.monotonic()
    for entry in manifest['inputs'].values():strict.verified(entry)
    for name in ['history','features','lambdas','development_summary','market']:
        strict.verified(manifest[name])
    for entry in manifest['bridges'].values():strict.verified(entry)
    with threadpool_limits(limits=2):
        p=study.read_scoped(manifest['inputs']['players']['path']);t=study.read_scoped(manifest['inputs']['teams']['path'])
        # Trusted local cache hashes are the exact original I4 export provenance.
        history=pd.read_pickle(manifest['history']['path']);features=pd.read_pickle(manifest['features']['path'])
        c=study.select_control(history,features,{season:pd.read_csv(entry['path']) for season,entry in manifest['bridges'].items()})
        del history,features
        preflight=study.base.schema_preflight(dict(players=p,teams=t,control=c))
        strict.write_json(output/'schema-preflight.json',preflight)
        if not preflight['passed']:raise ValueError('Confirmation schema gaps; no further attempt')
        p,t,c=study.validate_inputs(p,t,c)
        target=p.season.eq(study.FOLD)
        strict.write_json(output/'target-check.json',dict(season=study.FOLD,rows=int(target.sum()),points_core_equals_total_points=bool(p.loc[target,'total_points'].eq(c.loc[target,'points_core']).all()),mismatches=int(p.loc[target,'total_points'].ne(c.loc[target,'points_core']).sum())))
        with Path(manifest['market']['path']).open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
        new_lambdas,market_report=study.admit_market(rows,p)
        strict.write_json(output/'market-admission.json',market_report);strict.write_json(output/'new-lambdas.json',new_lambdas)
        lambdas=json.loads(strict.verified(manifest['lambdas']).read_text(encoding='utf-8'))+new_lambdas
        market,clocks,origins=study.market_rows(p,lambdas)
        snapshots=pd.DataFrame(columns=['season','gameweek','fpl_code','captured_at',*study.base.SNAPSHOT_FEATURES])
        rich,evidence=study.base.NativeHistory(p,t).transform(p,snapshots)
        for i,name in enumerate(study.base.i4.POSITION,1):rich[name]=p.position.eq(i).astype(np.float32)
        x=study.base.align_union(p,c,rich,evidence,market)
    train=p.season.lt(study.FOLD).to_numpy();test=p.season.eq(study.FOLD).to_numpy()
    a=dict(X_control=np.ascontiguousarray(c[study.CORE_FEATURES].to_numpy(np.float64)),X_combined=np.ascontiguousarray(x.to_numpy(np.float64)),y=p.total_points.to_numpy(float),minutes=p.minutes.to_numpy(float),season=p.season.to_numpy(str),gameweek=p.gameweek.to_numpy(np.int64),fixture=p.fixture.to_numpy(np.int64),fpl_code=p.fpl_code.to_numpy(np.int64),cutoff_ns=pd.DatetimeIndex(p.deadline-pd.Timedelta(hours=3)).as_unit('ns').asi8,ts_ns=pd.DatetimeIndex(p.ts).as_unit('ns').asi8,candidate=study.candidate_mask(c).to_numpy(bool),element=c.element.to_numpy(np.int64),pos=c.pos.to_numpy(np.int64),n_history=c.n_history.to_numpy(float),weights=study.sample_weights(pd.DataFrame({'ts':p.loc[train,'ts']})))
    previous=json.loads(strict.verified(manifest['development_summary']).read_text(encoding='utf-8'))
    verified=[]
    for key in ['X_control','y','minutes','season','gameweek','fixture','fpl_code','cutoff_ns','ts_ns','candidate','element','pos','n_history']:
        if study.array_hash(a[key][train])!=previous['proof']['hashes'][key]:raise ValueError('Original development bytes differ: '+key)
        verified.append(key)
    proof=study.shared_proof(a)
    # Original deterministic panel producer, run and hashed before any fit.
    squads,first=study.base.i4.make_squads(c.rename(columns={'gameweek':'GW'}),c,study.FOLD,count=20)
    panel=dict(first_gw=int(first),squads=squads);panel_sha=study.canonical_hash(panel)
    strict.write_json(output/'panels.json',dict(panel=panel,canonical_sha256=panel_sha,created_before_fits=True))
    unique={}
    for r in clocks:
        key=(r['season'],r['fixture'],r['team'])
        if key in unique and unique[key]!=r:raise ValueError('Market source clocks differ within fixture side')
        unique[key]=r
    if len(unique)!=3800 or any(pd.Timestamp(r['source_max'])>=pd.Timestamp(r['cutoff']) for r in unique.values()):raise ValueError('Incomplete/unsafe fixture-side market clocks')
    strict.write_json(output/'market-source-clocks.json',list(unique.values()))
    counts={m:dict(selected_features=study.base.selected_columns(c if m=='control' else x,train,m)) for m in study.base.METHODS}
    for m,v in counts.items():v.update(selected_feature_count=len(v['selected_features']),omitted_features=[n for n in study.base.FEATURES[m] if n not in v['selected_features']])
    strict.save_npz(output/'bundle.npz',**a)
    summary=dict(status='admitted',protocol_lf_sha256=development.PROTOCOL_SHA,receiving_runtime=runtime,proof=proof,bundle_sha256=strict.digest(output/'bundle.npz'),panel_sha256=panel_sha,panel_file_sha256=strict.digest(output/'panels.json'),features=counts,train_rows=int(train.sum()),test_rows=int(test.sum()),rows_per_season={s:int((p.season==s).sum()) for s in study.SEASONS},market_finite=bool(np.isfinite(market).all()),market_rows=len(market),rating_origins=origins,market_fixture_sides=len(unique),training_matches_original_development_keys=verified,confirmation_target_equal=True,confirmation_gameweeks=sorted(int(g) for g in set(p.loc[test,'gameweek'])),mapped_understat_gap_rows=0,clock_counts=preflight['control_clock_counts'],inputs=manifest,preparation_seconds=time.monotonic()-tick,fit_attempts=0)
    strict.write_json(output/'summary.json',summary);print(json.dumps(dict(status='admitted',panel_sha256=panel_sha,train_rows=int(train.sum()),test_rows=int(test.sum()))),flush=True)


def load_bundle(path):
    development.protocol();summary=json.loads((path.parent/'summary.json').read_text(encoding='utf-8'));panels=json.loads((path.parent/'panels.json').read_text(encoding='utf-8'))
    if strict.digest(path)!=summary['bundle_sha256'] or strict.digest(path.parent/'panels.json')!=summary['panel_file_sha256'] or study.canonical_hash(panels['panel'])!=summary['panel_sha256'] or not panels['created_before_fits']:raise ValueError('Frozen confirmation bundle/panels differ')
    with np.load(path,allow_pickle=False) as z:a={k:z[k] for k in z.files}
    if study.shared_proof(a)!=summary['proof']:raise ValueError('Shared confirmation proof differs')
    return a,summary,panels['panel']


def fit(bundle,method,ledger,output):
    if method not in study.base.METHODS:raise ValueError('Undeclared fit')
    a,s,_=load_bundle(bundle);ordinal=study.base.METHODS.index(method);ledger.mkdir(exist_ok=True)
    if len(list(ledger.glob('*.json')))!=ordinal or any(json.loads(p.read_text(encoding='utf-8'))['status']!='completed' for p in ledger.glob('*.json')):raise ValueError('Exclusive two-slot ledger/order; no retry')
    token=ledger/f'{ordinal:02d}_{method}.json';record=dict(status='attempted',method=method,ordinal=ordinal,bundle_sha256=s['bundle_sha256'],panel_sha256=s['panel_sha256']);strict.write_json(token,record);tick=time.monotonic()
    with threadpool_limits(limits=2):prediction,timing=study.fit_predict(a,method);pools=threadpool_info()
    if any(p['num_threads']!=2 for p in pools):raise ValueError('Thread limit differs')
    strict.save_npz(output/'predictions.npz',prediction=prediction)
    result=dict(status='completed',method=method,timing=timing,elapsed_seconds=time.monotonic()-tick,threadpools=pools,bundle_sha256=s['bundle_sha256'],panel_sha256=s['panel_sha256'],proof_sha256=s['proof']['proof_sha256'],predictions_sha256=strict.digest(output/'predictions.npz'))
    strict.write_json(output/'result.json',result);record.update(status='completed',result_sha256=strict.digest(output/'result.json'));token.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(status='completed',method=method)),flush=True)


def aggregate(build_dir,fits_dir,output):
    a,s,panel=load_bundle(build_dir/'bundle.npz');predictions={}
    for method in study.base.METHODS:
        directory=fits_dir/method;r=json.loads((directory/'result.json').read_text(encoding='utf-8'))
        if r['status']!='completed' or r['bundle_sha256']!=s['bundle_sha256'] or r['panel_sha256']!=s['panel_sha256'] or strict.digest(directory/'predictions.npz')!=r['predictions_sha256']:raise ValueError('Fit receipt differs')
        with np.load(directory/'predictions.npz',allow_pickle=False) as z:predictions[method]=z['prediction']
    with threadpool_limits(limits=2):report,z=study.analyse(a,predictions,panel)
    report.update(protocol_lf_sha256=development.PROTOCOL_SHA,panel_sha256=s['panel_sha256'],proof=s['proof'],method_fold_fits=2)
    strict.write_json(output/'report.json',report);z.to_csv(output/'predictions.csv.gz',index=False,mode='x');print(json.dumps(dict(gate_C_pass=report['gate']['passed'])),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['build','fit','aggregate'],required=True)
    for n in ['manifest','bundle','ledger','build-dir','fits-dir','output']:p.add_argument('--'+n,type=Path)
    p.add_argument('--method');a=p.parse_args();development.protocol();fixture.legacy_runtime();a.output.mkdir(parents=True,exist_ok=True)
    if a.phase=='build':build(json.loads(a.manifest.read_text(encoding='utf-8')),a.output)
    elif a.phase=='fit':fit(a.bundle,a.method,a.ledger,a.output)
    else:aggregate(a.build_dir,a.fits_dir,a.output)
if __name__=='__main__':main()
