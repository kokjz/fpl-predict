"""Offline ert-r1 admission/build, exclusive single-fit worker, and reporting."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src')); sys.path.insert(0,str(Path(__file__).parent))
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits, threadpool_info
import expected_return_targets as ert
import run_market_stage_c as strict
import run_market_stage_c_amended as fixture
from fpl_model import CORE_FEATURES, candidate_mask, sample_weights
from market_stage_c import array_hash, canonical_hash

PROTOCOL=ROOT/'docs/expected_return_targets_protocol_2026-10-28.json'
PROTOCOL_SHA='a0d8a6b621684a2ec61da4840ee41a2d416fc120b91049fcb3ed9c17ac535f22'


def protocol():
    raw=PROTOCOL.read_bytes().replace(b'\r\n',b'\n')
    if strict.hashlib.sha256(raw).hexdigest()!=PROTOCOL_SHA: raise ValueError('Frozen ert protocol differs')
    return json.loads(raw)


def admission(manifest,output):
    protocol(); runtime=fixture.legacy_runtime(); start=time.monotonic()
    # This reuses only the existing input/source/fixture qualification path;
    # no lambdas, market features, prior fitted model or score is read.
    with threadpool_limits(limits=2):
        p,t,c,panels,logical,logical_bytes,source,receipt=fixture.guarded_load(manifest,output,strict.protocol(),fixture.amendment())
        result=ert.admission(p,t)
    result.update(protocol_lf_sha256=PROTOCOL_SHA,runtime=runtime,source_qualification=source,logical_control_sha256=logical,logical_control_bytes=logical_bytes,inputs=manifest,original_fixture_sha256=canonical_hash(panels),panel_guard=receipt,preparation_seconds=time.monotonic()-start)
    strict.write_json(output/'admission.json',result)
    if not result['gate_A_pass']:
        print(json.dumps({'gate_A_pass':False,'fits':0}),flush=True); return
    x=np.ascontiguousarray(c[CORE_FEATURES].to_numpy(np.float64))
    a=dict(X_control=x,X_expected_return=x.copy(),y=p.total_points.to_numpy(float),minutes=p.minutes.to_numpy(float),season=p.season.to_numpy(str),gameweek=p.gameweek.to_numpy(np.int64),fixture=p.fixture.to_numpy(np.int64),fpl_code=p.fpl_code.to_numpy(np.int64),cutoff_ns=pd.DatetimeIndex(p.deadline-pd.Timedelta(hours=3)).as_unit('ns').asi8,ts_ns=pd.DatetimeIndex(p.ts).as_unit('ns').asi8,candidate=candidate_mask(c).to_numpy(bool),element=c.element.to_numpy(np.int64),pos=c.pos.to_numpy(np.int64),n_history=c.n_history.to_numpy(float))
    recomputed={}
    for fold in ert.FOLDS:
        labels,info,train=ert.fold_labels(p,t,fold)
        a['label_'+fold]=labels
        a['weights_'+fold]=sample_weights(pd.DataFrame({'ts':p.loc[train,'ts']}))
        # Independently recompute each formula from the frozen raw components.
        q=p.loc[train]; xga=ert.opponent_xg(q,t[t.season.lt(fold)&t.season.isin(ert.SEASONS)])
        k=info['k']; gp=q.position.map({1:6,2:6,3:5,4:4}).to_numpy(float); cs=q.position.map({1:4,2:4,3:1,4:0}).to_numpy(float)
        keep=q.minutes.gt(0).to_numpy()&np.isfinite(q[['us_xG','us_xA']].to_numpy(float)).all(axis=1)
        expected=q.total_points.to_numpy(float).copy()
        i=keep
        expected[i]=expected[i]-gp[i]*q.goals_scored.to_numpy(float)[i]-3*q.assists.to_numpy(float)[i]-cs[i]*q.clean_sheets.to_numpy(float)[i]+gp[i]*k['k_G']*q.us_xG.to_numpy(float)[i]+3*k['k_A']*q.us_xA.to_numpy(float)[i]+cs[i]*k['k_CS']*np.exp(-xga[i])*q.minutes.ge(60).to_numpy()[i]
        if expected.tobytes()!=labels[train].tobytes(): raise ValueError('Training formula recomputation differs')
        recomputed[fold]=dict(training_formula_bytes_exact=True,evaluation_targets_actual=bool(np.array_equal(labels[~train],a['y'][~train])),labels_sha256=array_hash(labels),age_weights_sha256=array_hash(a['weights_'+fold]))
    proof=ert.shared_proof(a)
    strict.save_npz(output/'bundle.npz',**a)
    strict.write_json(output/'summary.json',dict(protocol_lf_sha256=PROTOCOL_SHA,bundle_sha256=strict.digest(output/'bundle.npz'),proof=proof,formula_recomputation=recomputed,panels=panels,inputs=manifest,admission_sha256=strict.digest(output/'admission.json'),panel_consistency_sha256=strict.digest(output/'panel-consistency.json')))
    print(json.dumps({'gate_A_pass':True,'fits':0,'shared_proof':proof['proof_sha256']}),flush=True)


def load_bundle(path):
    protocol(); summary=json.loads((path.parent/'summary.json').read_text(encoding='utf-8'))
    if summary['protocol_lf_sha256']!=PROTOCOL_SHA or strict.digest(path)!=summary['bundle_sha256']: raise ValueError('Frozen bundle differs')
    with np.load(path,allow_pickle=False) as z:a={k:z[k] for k in z.files}
    if ert.shared_proof(a)!=summary['proof']: raise ValueError('Shared proof changed')
    return a,summary


def fit(bundle,fold,method,ledger,output):
    cfg=protocol(); a,summary=load_bundle(bundle); job=dict(fold=fold,method=method)
    if job not in cfg['fit_order']: raise ValueError('Undeclared fit')
    ordinal=cfg['fit_order'].index(job); ledger.mkdir(exist_ok=True)
    if len(list(ledger.glob('*.json')))!=ordinal: raise ValueError('Exclusive fit ledger/order; no retry')
    for p in ledger.glob('*.json'):
        if json.loads(p.read_text(encoding='utf-8'))['status']!='completed': raise ValueError('Previous fit incomplete')
    token=ledger/f'{ordinal:02d}_{fold}_{method}.json'; record=dict(status='attempted',**job,ordinal=ordinal,bundle_sha256=summary['bundle_sha256'],protocol_lf_sha256=PROTOCOL_SHA)
    strict.write_json(token,record); start=time.monotonic()
    with threadpool_limits(limits=2): prediction,timing=ert.fit_predict(a,fold,method); pools=threadpool_info()
    if any(p['num_threads']!=2 for p in pools): raise ValueError('Thread limit differs')
    strict.save_npz(output/'predictions.npz',prediction=prediction)
    result=dict(status='completed',**job,timing=timing,elapsed_seconds=time.monotonic()-start,threadpools=pools,proof=summary['proof']['proof_sha256'],predictions_sha256=strict.digest(output/'predictions.npz'),bundle_sha256=summary['bundle_sha256'])
    strict.write_json(output/'result.json',result); record.update(status='completed',result_sha256=strict.digest(output/'result.json')); token.write_bytes((json.dumps(record,indent=2)+'\n').encode())
    print(json.dumps(result),flush=True)


def aggregate(build_dir,fits_dir,output):
    cfg=protocol(); a,s=load_bundle(build_dir/'bundle.npz'); predictions={}; timings={}
    for job in cfg['fit_order']:
        fold,method=job['fold'],job['method']; d=fits_dir/(fold+'_'+method); r=json.loads((d/'result.json').read_text(encoding='utf-8'))
        if r['status']!='completed' or r['bundle_sha256']!=s['bundle_sha256'] or r['proof']!=s['proof']['proof_sha256'] or r['predictions_sha256']!=strict.digest(d/'predictions.npz'): raise ValueError('Fit evidence differs')
        with np.load(d/'predictions.npz',allow_pickle=False) as z: predictions[(fold,method)]=z['prediction']
        timings[fold+'_'+method]=r['timing']
    with threadpool_limits(limits=2): report,frame=ert.analyse(a,predictions,s['panels'])
    report.update(protocol_lf_sha256=PROTOCOL_SHA,proof=s['proof'],timings=timings,method_fold_fits=4)
    report['pooled_fixed_squad_summaries']={}
    for method in ert.METHODS:
        totals=[z for fold in ert.FOLDS for z in report['points'][fold][method]['totals']]; deltas=[z for fold in ert.FOLDS for z in report['points'][fold][method]['deltas']]
        report['pooled_fixed_squad_summaries'][method]=dict(mean_total=float(np.mean(totals)),mean_delta=float(np.mean(deltas)),minimum_delta=min(deltas),maximum_delta=max(deltas),panels=len(deltas))
    strict.write_json(output/'report.json',report); frame.to_csv(output/'predictions.csv.gz',index=False,mode='x'); print(json.dumps({'gate_B_pass':report['gate']['passed']}),flush=True)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--phase',choices=['admission','fit','aggregate'],required=True)
    for name in ['manifest','bundle','ledger','build-dir','fits-dir']:p.add_argument('--'+name,type=Path)
    p.add_argument('--fold');p.add_argument('--method');p.add_argument('--output',type=Path,required=True);args=p.parse_args(); protocol();fixture.legacy_runtime(); args.output.mkdir(parents=True,exist_ok=True)
    if args.phase=='admission':admission(json.loads(args.manifest.read_text(encoding='utf-8')),args.output)
    elif args.phase=='fit':fit(args.bundle,args.fold,args.method,args.ledger,args.output)
    else:aggregate(args.build_dir,args.fits_dir,args.output)


if __name__=='__main__':main()
