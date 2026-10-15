"""Fixed Dastan-architecture adapted reference; see protocol and MIT notices.

No external weights/code execution, auto-download, registry change or promotion.
XGBoost is an optional explicit reference dependency, imported only on invocation.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from threadpoolctl import threadpool_limits

from benchmark_metrics import point_scores
from benchmark_evaluation import paired_block_errors
from experiment_runner import file_hash
from native_history import NativeHistory, FEATURES
from native_reference import load_inputs, environment as base_environment

CLF = dict(n_estimators=2000, learning_rate=.014251, max_depth=7, subsample=.6364,
           colsample_bytree=.6427, min_child_weight=17.89, reg_lambda=1.3015,
           early_stopping_rounds=30, tree_method="hist", max_bin=256, n_jobs=2, random_state=42)
REG = dict(n_estimators=6000, learning_rate=.035966, max_depth=6, subsample=.7366,
           colsample_bytree=.6553, min_child_weight=8.29, reg_lambda=.2567,
           early_stopping_rounds=90, tree_method="hist", max_bin=256, n_jobs=2, random_state=42)
POLICY = dict(method="dastan-architecture-cutoff-gapmask-xgb320-v1", classifier=CLF,
              regressor=REG, bands=[1,3,10], positions=[1,2,3,4], features=FEATURES,
              seed=42, train="through2025-26GW19", validation=[20,27], test=[28,38],
              refit_validation=False, age_weighting=False, per_position=True,
              model_nan_transform=0., benchmark_eligible=False, promotion=False,
              gamma=[.5,.75,1.], weight0=[1.,1.25,1.5,2.], weight1=[1.,1.25],
              direct_weights=[i/20 for i in range(11)], conditional_min_validation=50,
              conditional_min_training=10, xgboost="3.2.0")


def environment():
    import xgboost
    if xgboost.__version__ != POLICY["xgboost"]: raise ValueError("Reference requires pinned optional XGBoost3.2.0")
    return {**base_environment(), "xgboost": xgboost.__version__}


def code_hashes():
    return {n:file_hash(Path(__file__).with_name(n)) for n in
            ("conditional_reference.py","native_history.py","native_reference.py",
             "benchmark_metrics.py","benchmark_evaluation.py")}


def calibrate(probabilities, labels):
    best = dict(gamma=1., weights=[1.,1.,1.,1.]); score = -np.inf
    for gamma in POLICY["gamma"]:
        for w0 in POLICY["weight0"]:
            for w1 in POLICY["weight1"]:
                cal = dict(gamma=gamma, weights=[w0,w1,1.,1.])
                adjusted = apply_calibration(probabilities, cal)
                value = float(np.log(np.clip(adjusted[np.arange(len(labels)),labels],1e-12,1)).mean())
                if value > score: best,score = cal,value
    return best


def apply_calibration(probabilities, cal):
    if cal is None: return probabilities
    adjusted = np.clip(probabilities,1e-12,1)**cal["gamma"]*np.asarray(cal["weights"])
    return adjusted/adjusted.sum(axis=1,keepdims=True)


def validation_objective(frame, prediction):
    d = frame[["gameweek","fpl_code","total_points"]].copy();d["p"] = prediction
    grouped = d.groupby(["gameweek","fpl_code"]).agg(p=("p","sum"),actual=("total_points","sum"))
    scores = []
    for _,g in grouped.groupby(level=0):
        if len(g)<20 or g.actual.nunique()<2 or g.p.nunique()<2: continue
        y=g.actual.to_numpy();p=g.p.to_numpy();k=min(10,len(g));discount=1/np.log2(np.arange(2,k+2))
        ideal=float((np.sort(y)[::-1][:k]*discount).sum())
        if ideal<=0:continue
        ndcg=float((y[np.argsort(-p,kind="stable")][:k]*discount).sum())/ideal
        scores.append(.5*float(spearmanr(p,y).statistic)+.5*ndcg)
    return float(np.mean(scores)) if scores else -np.inf


def blend_weight(frame, mixture, direct):
    best = 0.;score = -np.inf
    for weight in POLICY["direct_weights"]:
        value = validation_objective(frame,(1-weight)*mixture+weight*direct)
        if value>score: best,score=weight,value
    return best


def check_populations(rows,masks):
    for pos in POLICY["positions"]:
        t=rows[masks["train"]&rows.position.eq(pos)];v=rows[masks["validation"]&rows.position.eq(pos)]
        if not len(t) or not len(v):raise ValueError("Missing positional split")
        if set(t.minutes.ge(60).astype(int))!={0,1}:raise ValueError("Missing p60 training class")
        for frame in (t,v):
            if not frame.minutes.ge(60).any() or not frame.minutes.lt(60).any():raise ValueError("Missing conditional population")
        if set(np.digitize(t.loc[t.minutes.ge(60),"total_points"],POLICY["bands"]))!={0,1,2,3}:
            raise ValueError("Missing training score band; no undeclared class fallback")


def fit_position(t,v,xt,xv,xq,progress,factory=None):
    if factory is None:
        import xgboost as factory
    yt=t.total_points.to_numpy();yv=v.total_points.to_numpy()
    low=t.minutes.lt(60).to_numpy();start=~low
    vl=v.minutes.lt(60).to_numpy();vs=~vl
    bt=np.digitize(yt,POLICY["bands"]);bv=np.digitize(yv,POLICY["bands"])
    models={}
    def head(name,classifier,a,y,b,z,multiclass=False):
        params=dict(CLF if classifier else REG)
        params["eval_metric"]="mlogloss" if multiclass else "logloss" if classifier else "rmse"
        if multiclass:params.update(objective="multi:softprob",num_class=4)
        model=(factory.XGBClassifier if classifier else factory.XGBRegressor)(**params)
        tick=time.monotonic();model.fit(a,y,eval_set=[(b,z)],verbose=False)
        progress(dict(head=name,train_rows=len(a),validation_rows=len(b),
                      seconds=time.monotonic()-tick,best_iteration=int(model.best_iteration)))
        return model
    models["p60"]=head("p60",True,xt,start.astype(int),xv,vs.astype(int))
    b,z=(xv[vl],yv[vl]) if vl.sum()>=50 else (xv,yv)
    models["under60"]=head("under60",False,xt[low],yt[low],b,z)
    b,z=(xv[vs],bv[vs]) if vs.sum()>=50 else (xv,bv)
    models["band"]=head("band",True,xt[start],bt[start],b,z,True)
    if list(models["band"].classes_)!=[0,1,2,3]:raise ValueError("Unexpected fitted band classes")
    cal=calibrate(models["band"].predict_proba(xv[vs]),bv[vs]) if vs.sum()>=50 else None
    bands=[]
    for k in range(4):
        in_k=start&(bt==k);val_k=vs&(bv==k)
        a,y=(xt[in_k],yt[in_k]) if in_k.sum()>10 else (xt[start],yt[start])
        b,z=(xv[val_k],yv[val_k]) if val_k.sum()>=50 else (xv[vs],yv[vs])
        bands.append(head(f"band{k}",False,a,y,b,z))
    models["direct"]=head("direct",False,xt,yt,xv,yv)
    def mixture(x):
        p=models["p60"].predict_proba(x)[:,1]
        under=np.maximum(models["under60"].predict(x),0)
        probabilities=apply_calibration(models["band"].predict_proba(x),cal)
        values=np.column_stack([np.maximum(m.predict(x),0) for m in bands])
        return p*(probabilities*values).sum(axis=1)+(1-p)*under
    weight=blend_weight(v,mixture(xv),np.maximum(models["direct"].predict(xv),0))
    tick=time.monotonic();prediction=np.maximum((1-weight)*mixture(xq)+weight*np.maximum(models["direct"].predict(xq),0),0)
    return prediction,dict(calibration=cal,direct_weight=weight,prediction_seconds=time.monotonic()-tick)


def prepare(paths,output):
    if Path(output).exists():raise ValueError("Manifest exists")
    entries={k:dict(path=str(Path(v).resolve()),sha256=file_hash(v)) for k,v in paths.items()}
    frames,masks,_=load_inputs(entries);check_populations(frames["players"],masks)
    # Additional frozen HGB prediction coverage/targets checked before fitting.
    native=pd.read_csv(entries["native_predictions"]["path"])
    keys=["season","gameweek","fixture","fpl_code"]
    ref=frames["reference"]
    join=ref.merge(native[keys+["actual","candidate","native_reference"]],on=keys,how="outer",validate="one_to_one",indicator=True,suffixes=("","_native"))
    if not join._merge.eq("both").all() or not join.actual.eq(join.actual_native).all() or not join.candidate.eq(join.candidate_native).all():raise ValueError("Frozen native comparison differs")
    if not np.isfinite(join.native_reference).all():raise ValueError("Invalid native predictions")
    spec=dict(policy=POLICY,inputs=entries,code=code_hashes(),environment=environment(),created_at=dt.datetime.now(dt.timezone.utc).isoformat())
    with Path(output).open("x") as f:json.dump(spec,f,indent=2,allow_nan=False)
    return spec


def run(manifest,expected,directory):
    if file_hash(manifest)!=expected:raise ValueError("Manifest checksum mismatch")
    spec=json.loads(Path(manifest).read_text())
    if spec["policy"]!=POLICY or spec["code"]!=code_hashes() or spec["environment"]!=environment():raise ValueError("Frozen policy/code/environment changed")
    out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    if any((out/n).exists() for n in ("predictions.csv","results.json","head_progress.jsonl")):raise ValueError("Output exists")
    frames,masks,_=load_inputs(spec["inputs"]);p=frames["players"];check_populations(p,masks)
    tick=time.monotonic();x,e=NativeHistory(p,frames["teams"]).transform(p,frames["snapshots"])
    x=x[FEATURES].fillna(POLICY["model_nan_transform"]).to_numpy(dtype=np.float32)
    result=dict(policy=POLICY,manifest_sha256=expected,feature_seconds=time.monotonic()-tick,positions={},metrics={},paired={})
    keys=["season","gameweek","fixture","fpl_code"];test=masks["test"]
    z=p.loc[test,keys+["total_points"]].rename(columns={"total_points":"actual"}).copy()
    z["candidate"]=e.loc[test,"candidate"];z["snapshot_known"]=e.loc[test,"snapshot_present"]
    ref=frames["reference"];native=pd.read_csv(spec["inputs"]["native_predictions"]["path"])
    z=z.merge(ref[keys+["actual","reference","candidate"]],on=keys,validate="one_to_one",suffixes=("","_ref"))
    if not z.actual.eq(z.actual_ref).all() or not z.candidate.eq(z.candidate_ref).all():raise ValueError("Frozen comparison targets/cohort differ")
    z=z.merge(native[keys+["native_reference"]],on=keys,validate="one_to_one")
    if not z[keys].equals(p.loc[test,keys].reset_index(drop=True)):raise ValueError("Prediction key order differs")
    prediction=pd.Series(np.nan,index=p.index[test])
    with (out/"head_progress.jsonl").open("x") as log,threadpool_limits(limits=2):
        for pos in POLICY["positions"]:
            train=masks["train"]&p.position.eq(pos);val=masks["validation"]&p.position.eq(pos);query=test&p.position.eq(pos)
            def progress(row):
                log.write(json.dumps(dict(position=pos,**row))+"\n");log.flush()
                print(f"Completed position{pos} {row['head']}",flush=True)
            values,meta=fit_position(p[train],p[val],x[train],x[val],x[query],progress)
            prediction.loc[query[query].index]=values;result["positions"][str(pos)]=meta
    if not np.isfinite(prediction).all():raise ValueError("Incomplete reference coverage")
    z["conditional_reference"]=prediction.to_numpy()
    g=z.groupby(["season","gameweek","fpl_code"]).agg({**{m:"sum" for m in ("actual","conditional_reference","reference","native_reference")},"candidate":"first","snapshot_known":"first"}).reset_index()
    for name,cohort in (("primary",g[g.candidate&g.snapshot_known]),("all_candidates",g[g.candidate]),("all_players",g)):
        result["metrics"][name]={m:point_scores(cohort,m) for m in ("conditional_reference","reference","native_reference")}
    for m in ("reference","native_reference"):result["paired"][m]=paired_block_errors(g[g.candidate&g.snapshot_known],"conditional_reference",m)
    z.to_csv(out/"predictions.csv",index=False,mode="x");result["predictions_sha256"]=file_hash(out/"predictions.csv")
    with (out/"results.json").open("x") as f:json.dump(result,f,indent=2,allow_nan=False)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="action",required=True)
    a=sub.add_parser("prepare")
    for n in ("players","teams","snapshots","reference","provenance","native-predictions","output"):a.add_argument("--"+n,required=True,type=Path)
    b=sub.add_parser("run")
    for n in ("manifest","manifest-sha256","directory"):b.add_argument("--"+n,required=True)
    args=vars(parser.parse_args());action=args.pop("action")
    try:
        if action=="prepare":prepare({k:v for k,v in args.items() if k!="output"},args["output"])
        else:run(args["manifest"],args["manifest_sha256"],args["directory"])
    except (ValueError,KeyError,TypeError,OSError,ImportError) as exc:parser.exit(2,f"Conditional reference rejected: {exc}\n")
    print("Named retrospective reference saved; no original-system or promotion claim.")


if __name__=="__main__":main()
