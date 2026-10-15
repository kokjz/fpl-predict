"""Read-only scoring of a published frozen player-GW export against a saved forecast.

This adapter verifies supplied bytes and timing declarations, not publisher clocks,
training lineage or equal information cutoffs. No forecast or account action occurs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd

from benchmark_evaluation import paired_block_errors
from benchmark_metrics import point_scores
from experiment_runner import file_hash
from score_forecast import validate_forecast_timing


def admitted_export(csv, frozen, deadline, season, gameweek):
    spec=json.loads(Path(frozen).read_text())
    if spec.get("schema_version")!="frozen_official_forecast_v1":
        raise ValueError("Unsupported public frozen manifest")
    identity=spec["forecast_identity"]
    if identity["season"]!=season or identity["gameweek"]!=gameweek:
        raise ValueError("External season/gameweek mismatch")
    for key in ("generated_at", "published_at"):
        ts=pd.Timestamp(identity[key])
        if ts.tzinfo is None or ts>=deadline:
            raise ValueError("External forecast late or timezone unknown")
    if pd.Timestamp(identity["generated_at"])>pd.Timestamp(identity["published_at"]):
        raise ValueError("Publication precedes generation")
    entry=spec["files"]["player_gameweek_projections.csv"]
    if Path(csv).stat().st_size>2_000_000 or Path(csv).stat().st_size!=entry["bytes"] or file_hash(csv)!=entry["sha256"]:
        raise ValueError("External export bytes differ from frozen manifest")
    d=pd.read_csv(csv)
    if len(d)!=identity["player_count"] or not d.season.eq(season).all() or not d.gameweek.eq(gameweek).all():
        raise ValueError("External export scope/count differs")
    if not d.stable_player_id.map(lambda s:isinstance(s,str) and re.fullmatch(r"player_code_[1-9][0-9]*",s) is not None).all():
        raise ValueError("Unsupported stable player identifier")
    d["fpl_code"]=d.stable_player_id.str.removeprefix("player_code_").astype(int)
    if d.fpl_code.duplicated().any() or not np.isfinite(d.expected_points).all():
        raise ValueError("Duplicate identity/nonfinite public predictions")
    if not d.position.isin(["GKP","DEF","MID","FWD"]).all():
        raise ValueError("Unsupported external position")
    d["position"]=d.position.map({"GKP":1,"DEF":2,"MID":3,"FWD":4})
    if not d.data_timestamp.map(lambda s:pd.Timestamp(s).tzinfo is not None).all():
        raise ValueError("External source timezone unknown")
    times=pd.to_datetime(d.data_timestamp,utc=True,errors="raise")
    if times.isna().any() or times.max()>pd.Timestamp(identity["generated_at"]):
        raise ValueError("External source timestamp reaches generation")
    return d,identity


def compare(csv, frozen, forecast, forecast_bootstrap, outcome, gameweek):
    forecast=Path(forecast);outcome=Path(outcome)
    origin=json.loads(Path(forecast_bootstrap).read_text())
    final=json.loads((outcome/"bootstrap.json").read_text())
    event=next(e for e in final["events"] if e["id"]==gameweek)
    if not event.get("finished") or not event.get("data_checked"):
        raise ValueError("Outcomes not finalised")
    deadline=pd.Timestamp(event["deadline_time"])
    manifest=json.loads((forecast/"manifest.json").read_text())
    validate_forecast_timing(manifest,deadline)
    local=pd.DataFrame(json.loads((forecast/"player_gameweek_predictions.json").read_text()))
    local=local[local.GW.eq(gameweek)].copy()
    if local.empty or local.id.duplicated().any() or not local.candidate_pool.map(lambda v:type(v)is bool).all():
        raise ValueError("Invalid saved forecast scope/cohort")
    ids={r["id"]:r for r in origin["elements"]};final_ids={r["id"]:r for r in final["elements"]}
    if len(ids)!=len(origin["elements"]) or len(final_ids)!=len(final["elements"]):
        raise ValueError("Duplicate bootstrap identity")
    codes=[];actual=[];outcome_hashes={}
    for row in local.itertuples():
        if row.id not in ids or row.id not in final_ids or ids[row.id]["code"]!=final_ids[row.id]["code"]:
            raise ValueError("Stable identity bridge changed")
        codes.append(ids[row.id]["code"])
        path=outcome/"players"/f"{row.id}.json"
        history=json.loads(path.read_text())["history"]
        week=[r for r in history if r["round"]==gameweek]
        if len({r["fixture"] for r in week})!=len(week):
            raise ValueError("Duplicate outcome fixture")
        actual.append(sum(r["total_points"] for r in week));outcome_hashes[str(row.id)]=file_hash(path)
    local["fpl_code"]=codes;local["actual"]=actual
    if local.fpl_code.duplicated().any() or not np.isfinite(local.expected_points).all():
        raise ValueError("Invalid saved forecast identity/predictions")
    # Published schema declares season explicitly; match the finalised deadline's
    # football season, not the current wall-clock year or a caller's old assumption.
    year=deadline.year if deadline.month>=7 else deadline.year-1
    season=f"{year}-{str(year+1)[-2:]}"
    external,identity=admitted_export(csv,frozen,deadline,season,gameweek)
    pairs=local.merge(external[["fpl_code","position","expected_points"]],on="fpl_code",
                      how="inner",validate="one_to_one",suffixes=("","_external"))
    if pairs.empty or not pairs.position.eq(pairs.position_external).all():
        raise ValueError("No shared rows or positional identity conflict")
    pairs["season"]=season;pairs["gameweek"]=gameweek
    pairs["reference"]=pairs.expected_points;pairs["external"]=pairs.expected_points_external
    candidates=pairs[pairs.candidate_pool]
    return dict(scope="post-hoc single-GW archived comparison; different information cutoffs; not prospective pair or season ranking",
                season=season,gameweek=gameweek,deadline=deadline.isoformat(),
                external_generated=identity["generated_at"],external_published=identity["published_at"],
                local_generated=manifest["created_at_utc"],local_as_of=manifest["as_of_utc"],
                source_proof="supplied publisher manifest/hash/timing declarations; Git revision recorded separately, not independently certified clocks/training",
                coverage=dict(local=len(local),external=len(external),shared=len(pairs),
                              local_candidates=int(local.candidate_pool.sum()),shared_candidates=len(candidates)),
                metrics={name:{m:point_scores(frame,m) for m in ("reference","external")}
                         for name,frame in (("primary",candidates),("all_shared",pairs))},
                paired=paired_block_errors(candidates,"external","reference"),
                sha256=dict(external_csv=file_hash(csv),external_manifest=file_hash(frozen),
                            local_manifest=file_hash(forecast/"manifest.json"),
                            local_predictions=file_hash(forecast/"player_gameweek_predictions.json"),
                            origin_bootstrap=file_hash(forecast_bootstrap),
                            outcome_bootstrap=file_hash(outcome/"bootstrap.json"),
                            outcome_histories=hashlib.sha256(json.dumps(outcome_hashes,sort_keys=True).encode()).hexdigest()),
                model_promotion=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("csv","frozen","forecast","forecast-bootstrap","outcome","output"):
        parser.add_argument("--"+name,required=True,type=Path)
    parser.add_argument("--gameweek",required=True,type=int)
    a=parser.parse_args()
    try:
        if a.output.exists():
            raise ValueError("Output already exists")
        result=compare(a.csv,a.frozen,a.forecast,a.forecast_bootstrap,a.outcome,a.gameweek)
        with a.output.open("x") as f:
            json.dump(result,f,indent=2,allow_nan=False)
    except (ValueError,KeyError,TypeError,OSError,StopIteration) as exc:
        parser.exit(2,f"Archived comparison rejected: {exc}\n")
    print("Aggregate archived comparison saved; no forecast/team changes.")


if __name__=="__main__":
    main()
