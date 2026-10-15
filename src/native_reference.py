"""Frozen, bounded native-window feature pilot; no operational model promotion."""
import argparse
import datetime as dt
import json
from pathlib import Path
import platform
import time

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

from benchmark_evaluation import paired_block_errors
from benchmark_metrics import point_scores
from experiment_runner import file_hash
from external_benchmark import FIXTURE_KEYS, _identities, _json, _numeric, _timestamp
from native_history import NativeHistory, FEATURES

POSITION_FEATURES=[f"position_{i}" for i in range(1,5)]

POLICY = {
    "schema_version":1,"method":"native-window-cutoff-hgb7-gapmask-v1",
    "train_seasons":["2020-21","2021-22","2022-23","2023-24","2024-25"],
    "evaluation_season":"2025-26","train_last_gw":19,"validation_gws":[20,27],"test_gws":[28,38],
    "learner":"one pooled full-points HGB7; not original Dastan architecture",
    "parameters":dict(max_leaf_nodes=7,max_iter=200,learning_rate=.05,l2_regularization=20,
                       min_samples_leaf=60,early_stopping=False,random_state=20260921),
    "recency_half_life_days":730.5,"clip":[0,22],"refit_validation":False,
    "primary":"snapshot-known candidates; candidate season-history>=3 and last5minutes>=45",
    "secondary":["all candidates","all players"],"baseline":"last5 full-points history",
    "features":FEATURES+POSITION_FEATURES,"snapshot_missing":-1,"raw_numeric_missing":"NaN, never invented zero",
    "position_conditioning":"four fixed role indicators for the pooled learner; not four separately tuned models",
    "allowed_training_gap_keys":[["2025-26",9,83,155408],["2025-26",9,83,168636]],
    "gap_policy":"exact declared training rows only; preserve unknown statistics/rows; no validation/test mapped gaps",
    "snapshot_scope":"verified2025-26 only; all snapshot fields missing in earlier seasons",
    "identity":"stable FPL code across seasons; source-join mappings explicitly audited",
    "history_cutoff":"strictly deadline minus3hours; rest/congestion evaluated at deadline",
    "benchmark_eligible":False,"model_promotion":False,
    "limitations":["reused retrospective outcomes","provider-mutable historical statistics",
                   "older training deadlines reconstructed","not complete historic publication-time proof",
                   "manual target-window event reconstruction; not full kickoff history",
                   "not original-system reproduction or full-season points evidence"]}


def code_hashes():
    return {n:file_hash(Path(__file__).with_name(n)) for n in
            ("native_history.py","native_reference.py","benchmark_metrics.py","benchmark_evaluation.py")}


def environment():
    return dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,sklearn=sklearn.__version__)


def split_masks(rows):
    season=rows.season.eq("2025-26")
    return dict(train=rows.season.isin(POLICY["train_seasons"])|(season&rows.gameweek.le(19)),
                validation=season&rows.gameweek.between(20,27),test=season&rows.gameweek.between(28,38))


def load_inputs(entries):
    for entry in entries.values():
        if Path(entry["path"]).stat().st_size>200_000_000:raise ValueError("Input file size budget")
        if file_hash(entry["path"])!=entry["sha256"]: raise ValueError("Input checksum mismatch")
    proof=_json(Path(entries["provenance"]["path"]).read_bytes())
    if proof.get("native_inputs_ready") is not True: raise ValueError("Native input readiness failed")
    frames={k:pd.read_csv(entries[k]["path"]) for k in ("players","teams","snapshots","reference")}
    p=frames["players"]
    if not 0<len(p)<=200000 or set(FIXTURE_KEYS)-set(p):raise ValueError("Invalid native row universe")
    if not set(p.season)<=set([*POLICY["train_seasons"],"2025-26"]):raise ValueError("Unsupported training season")
    _numeric(p,["gameweek","fpl_code","fixture"],integer=True,minimum=1)
    if not p.gameweek.le(38).all() or p.duplicated(FIXTURE_KEYS).any():raise ValueError("Invalid/duplicate native keys")
    p["ts"]=pd.to_datetime(p.ts.map(_timestamp),utc=True)
    p["deadline"]=pd.to_datetime(p.deadline.map(_timestamp),utc=True)
    if p.deadline.ge(p.ts).any(): raise ValueError("Invalid target deadlines")
    # Validate all required raw schemas before a manifest can be frozen.
    NativeHistory(p,frames["teams"])
    # Independently enforce the pre-fit source-gap mask, not merely a producer's
    # readiness flag. Unmapped people remain explicit unknowns; no rows disappear.
    if "understat_id" not in p:raise ValueError("Missing source identity evidence")
    us=["us_shots","us_xG","us_xGChain","us_xGBuildup","us_key_passes","us_xA"]
    missing=p.minutes.gt(0)&p.understat_id.notna()&p[us].isna().any(axis=1)
    actual=sorted(p.loc[missing,["season","gameweek","fixture","fpl_code"]].values.tolist())
    if actual!=sorted(POLICY["allowed_training_gap_keys"]):raise ValueError("Unapproved native source-gap mask")
    if not p.loc[missing,us].isna().all().all():raise ValueError("Source-gap rows must retain all six statistics unknown")
    masks=split_masks(p)
    if not pd.DataFrame(masks).sum(axis=1).eq(1).all() or not all(m.any() for m in masks.values()):
        raise ValueError("Missing/out-of-scope split rows")
    if not set(POLICY["train_seasons"])<=set(p.season): raise ValueError("Missing training season")
    for name,weeks in (("validation",range(20,28)),("test",range(28,39))):
        if set(p.loc[masks[name],"gameweek"])!=set(weeks): raise ValueError("Incomplete evaluation window")
    for first,second in (("train","validation"),("validation","test")):
        if p.loc[masks[first],"ts"].max()+pd.Timedelta(hours=3)>=p.loc[masks[second],"deadline"].min():
            raise ValueError("Labels not complete before next split")
    ref=frames["reference"]
    _identities(ref,fixtures=True)
    keys=p.loc[masks["test"],FIXTURE_KEYS]
    joined=keys.merge(ref,on=FIXTURE_KEYS,how="outer",indicator=True,validate="one_to_one")
    if not joined._merge.eq("both").all(): raise ValueError("Frozen reference coverage differs")
    if not np.isfinite(ref[["actual","reference"]]).all().all(): raise ValueError("Invalid frozen reference")
    return frames,masks,proof


def prepare(paths,output):
    if Path(output).exists(): raise ValueError("Manifest exists")
    entries={k:dict(path=str(Path(p).resolve()),sha256=file_hash(p)) for k,p in paths.items()}
    frames,masks,_=load_inputs(entries)
    spec=dict(policy=POLICY,inputs=entries,code=code_hashes(),environment=environment(),
              splits={k:int(m.sum()) for k,m in masks.items()},
              created_at=dt.datetime.now(dt.timezone.utc).isoformat())
    with Path(output).open("x") as stream:json.dump(spec,stream,indent=2,allow_nan=False)
    return spec


def run(manifest,expected_sha256,directory):
    if file_hash(manifest)!=expected_sha256: raise ValueError("Manifest checksum mismatch")
    spec=_json(Path(manifest).read_bytes())
    if spec["policy"]!=POLICY or spec["code"]!=code_hashes() or spec["environment"]!=environment():
        raise ValueError("Frozen policy/code/environment changed")
    output=Path(directory);output.mkdir(parents=True,exist_ok=True)
    if any((output/n).exists() for n in ("predictions.csv","results.json")):raise ValueError("Output exists")
    times={};started=time.monotonic();frames,masks,proof=load_inputs(spec["inputs"])
    times["load_audit_seconds"]=time.monotonic()-started
    p=frames["players"];started=time.monotonic()
    x,evidence=NativeHistory(p,frames["teams"]).transform(p,frames["snapshots"])
    for position,name in enumerate(POSITION_FEATURES,1):x[name]=p.position.eq(position).astype(np.float32)
    times["feature_build_seconds"]=time.monotonic()-started
    if np.isinf(x.to_numpy()).any():raise ValueError("Infinite features")
    train=masks["train"];test=masks["test"]
    # Cohort and outcome/reference alignment are checked before fitting.
    out=p.loc[test,[*FIXTURE_KEYS,"total_points"]].rename(columns={"total_points":"actual"}).copy()
    out["candidate"]=evidence.loc[test,"candidate"];out["snapshot_known"]=evidence.loc[test,"snapshot_present"]
    out["last5"]=x.loc[test,"player_fpl_points_5"].fillna(0).to_numpy()
    ref=frames["reference"]
    out=out.merge(ref[[*FIXTURE_KEYS,"actual","reference","candidate"]],on=FIXTURE_KEYS,
                  suffixes=("","_frozen"),validate="one_to_one")
    if not np.allclose(out.actual,out.actual_frozen) or not out.candidate.eq(out.candidate_frozen).all():
        raise ValueError("Frozen outcomes/candidate definition differs")
    weights=np.power(.5,(p.loc[train,"ts"].max()-p.loc[train,"ts"]).dt.total_seconds().to_numpy()/86400/730.5)
    started=time.monotonic()
    with threadpool_limits(limits=2):
        model=HistGradientBoostingRegressor(**POLICY["parameters"])
        model.fit(x.loc[train],p.loc[train,"total_points"],sample_weight=weights)
        times["fit_seconds"]=time.monotonic()-started;started=time.monotonic()
        prediction=np.clip(model.predict(x.loc[test]),*POLICY["clip"])
        times["prediction_seconds"]=time.monotonic()-started
    # The explicit left key order is identical to the test feature order.
    if not out[FIXTURE_KEYS].equals(p.loc[test,FIXTURE_KEYS].reset_index(drop=True)):
        raise ValueError("Prediction output order differs")
    out["native_reference"]=prediction
    groups=out.groupby(["season","gameweek","fpl_code"])
    if groups.candidate.nunique().ne(1).any() or groups.snapshot_known.nunique().ne(1).any():
        raise ValueError("Double-GW cohort differs between fixtures")
    g=groups.agg(actual=("actual","sum"),native_reference=("native_reference","sum"),reference=("reference","sum"),
                 last5=("last5","sum"),candidate=("candidate","first"),snapshot_known=("snapshot_known","first")).reset_index()
    cohorts={"snapshot_known_candidates":g[g.candidate&g.snapshot_known],"all_candidates":g[g.candidate],"all_players":g}
    result=dict(policy=POLICY,manifest_sha256=expected_sha256,splits=spec["splits"],timings=times,
                snapshot_missing_fixture_rows=int((~evidence.snapshot_present).sum()),
                test_snapshot_missing_rows=int((~out.snapshot_known).sum()),metrics={},paired_primary_errors={})
    for name,d in cohorts.items():
        result["metrics"][name]={col:point_scores(d,col) for col in ("native_reference","reference","last5")}
    for col in ("reference","last5"):
        result["paired_primary_errors"][col]=paired_block_errors(cohorts["snapshot_known_candidates"],"native_reference",col)
    out.to_csv(output/"predictions.csv",mode="x",index=False)
    result["predictions_sha256"]=file_hash(output/"predictions.csv")
    with (output/"results.json").open("x") as stream:json.dump(result,stream,indent=2,allow_nan=False)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="action",required=True)
    p=sub.add_parser("prepare")
    for name in ("players","teams","snapshots","reference","provenance","output"):
        p.add_argument("--"+name,type=Path,required=True)
    p=sub.add_parser("run");p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--manifest-sha256",required=True);p.add_argument("--directory",type=Path,required=True)
    args=vars(parser.parse_args());action=args.pop("action")
    try:
        if action=="prepare":prepare({k:v for k,v in args.items() if k!="output"},args["output"])
        else:run(args["manifest"],args["manifest_sha256"],args["directory"])
    except (ValueError,KeyError,TypeError,OSError) as exc:parser.exit(2,f"Native reference rejected: {exc}\n")
    print("Retrospective native-reference artifact saved; no deployment/promotion.")


if __name__=="__main__":main()
