import json
from pathlib import Path

import pandas as pd
import pytest

import archived_reference as ref
from experiment_runner import file_hash


def fixture(tmp_path):
    forecast=tmp_path/"saved";forecast.mkdir()
    outcome=tmp_path/"outcomes";(outcome/"players").mkdir(parents=True)
    bootstrap=dict(elements=[dict(id=1,code=101),dict(id=2,code=102)],
                   events=[dict(id=6,deadline_time="2026-10-10T10:00:00Z",finished=True,data_checked=True)])
    origin=tmp_path/"origin.json";origin.write_text(json.dumps(bootstrap))
    (outcome/"bootstrap.json").write_text(json.dumps(bootstrap))
    for i,points in [(1,5),(2,0)]:
        (outcome/"players"/f"{i}.json").write_text(json.dumps(dict(history=[dict(round=6,fixture=4,total_points=points)])))
    (forecast/"manifest.json").write_text(json.dumps(dict(as_of_utc="2026-10-09T10:00:00Z",created_at_utc="2026-10-09T10:01:00Z")))
    (forecast/"player_gameweek_predictions.json").write_text(json.dumps([
        dict(id=i,GW=6,position=3,candidate_pool=True,expected_points=2.) for i in [1,2]]))
    csv=tmp_path/"external.csv"
    pd.DataFrame([dict(stable_player_id="player_code_101",season="2026-27",gameweek=6,
                       position="MID",expected_points=4.,data_timestamp="2026-09-22T10:00:00Z")]).to_csv(csv,index=False)
    frozen=tmp_path/"frozen.json"
    frozen.write_text(json.dumps(dict(schema_version="frozen_official_forecast_v1",
        forecast_identity=dict(season="2026-27",gameweek=6,player_count=1,
                               generated_at="2026-09-22T11:00:00Z",published_at="2026-09-22T11:01:00Z"),
        files={"player_gameweek_projections.csv":dict(bytes=csv.stat().st_size,sha256=file_hash(csv))})))
    return csv,frozen,forecast,origin,outcome


def test_published_archive_matches_stable_codes_and_reports_missing_coverage(tmp_path):
    paths=fixture(tmp_path);before={str(p):file_hash(p) for p in tmp_path.rglob("*") if p.is_file()}
    report=ref.compare(*paths,6)
    assert report["coverage"]==dict(local=2,external=1,shared=1,local_candidates=2,shared_candidates=1)
    assert report["metrics"]["primary"]["external"]["rmse"]==1
    assert report["metrics"]["primary"]["reference"]["rmse"]==3
    assert report["paired"]["status"]=="insufficient_contiguous_weeks"
    assert report["external_generated"]!=report["local_generated"]
    assert str(tmp_path) not in json.dumps(report)
    assert before=={str(p):file_hash(p) for p in tmp_path.rglob("*") if p.is_file()}


def test_tampered_public_forecast_and_late_capture_are_rejected(tmp_path):
    paths=fixture(tmp_path);csv,frozen,*_=paths
    original=csv.read_bytes();csv.write_bytes(original+b"\n")
    with pytest.raises(ValueError,match="bytes differ"):
        ref.compare(*paths,6)
    csv.write_bytes(original)
    spec=json.loads(frozen.read_text());spec["forecast_identity"]["published_at"]="2026-10-11T10:00:00Z"
    frozen.write_text(json.dumps(spec))
    with pytest.raises(ValueError,match="late"):
        ref.compare(*paths,6)


def test_missing_histories_and_changed_identity_bridge_are_not_zero_filled(tmp_path):
    paths=fixture(tmp_path);_,_,_,_,outcome=paths
    file=outcome/"players/2.json";raw=file.read_bytes();file.unlink()
    with pytest.raises(FileNotFoundError):
        ref.compare(*paths,6)
    file.write_bytes(raw)
    bootstrap=json.loads((outcome/"bootstrap.json").read_text());bootstrap["elements"][1]["code"]=103
    (outcome/"bootstrap.json").write_text(json.dumps(bootstrap))
    with pytest.raises(ValueError,match="identity bridge"):
        ref.compare(*paths,6)


def test_unfinished_results_and_position_conflicts_rejected(tmp_path):
    paths=fixture(tmp_path);csv,frozen,_,_,outcome=paths
    frame=pd.read_csv(csv);frame["position"]="DEF";frame.to_csv(csv,index=False)
    spec=json.loads(frozen.read_text());spec["files"]["player_gameweek_projections.csv"]=dict(bytes=csv.stat().st_size,sha256=file_hash(csv))
    frozen.write_text(json.dumps(spec))
    with pytest.raises(ValueError,match="positional"):
        ref.compare(*paths,6)
    bootstrap=json.loads((outcome/"bootstrap.json").read_text());bootstrap["events"][0]["data_checked"]=False
    (outcome/"bootstrap.json").write_text(json.dumps(bootstrap))
    with pytest.raises(ValueError,match="finalised"):
        ref.compare(*paths,6)
