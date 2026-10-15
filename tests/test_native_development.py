import json
import numpy as np
import pandas as pd
import pytest

import native_development as study
from fpl_model import CORE_FEATURES
from native_history import PLAYER_STATS, TEAM_STATS, DEFENSIVE
from experiment_runner import file_hash


def source_inputs(tmp_path):
    players=[]; teams=[]; control=[]
    for year, season in enumerate(["2020-21", "2021-22", *study.FOLDS]):
        for gw in range(1,39):
            ts=pd.Timestamp(f"{2020+year}-08-01T15:00:00Z")+pd.Timedelta(weeks=gw)
            for code,club,opponent,home in [(11,"A","B",True),(22,"B","A",False)]:
                row={n:1. for n in [*PLAYER_STATS,*DEFENSIVE]}
                row.update(season=season,gameweek=gw,fixture=gw,fpl_code=code,position=2,
                           team_name=club,opponent_name=opponent,home=home,starts=1.,understat_id=code,
                           ts=ts,deadline=ts-pd.Timedelta(minutes=90),minutes=90.,total_points=2.)
                players.append(row)
                team={n:1. for n in TEAM_STATS if "league_rank" not in n}
                team.update(season=season,fixture=gw,team_name=club,opponent_name=opponent,ts=ts)
                teams.append(team)
                c={n:1. for n in CORE_FEATURES}
                c.update(season=season,GW=gw,fixture=gw,fpl_code=code,element=code,pos=2,team_id=code,
                         value=45.,ts=ts,cutoff=row["deadline"],source_max_ts=ts-pd.Timedelta(days=7),
                         points_core=2.,total_points=2.,minutes=90.)
                control.append(c)
    paths={}
    for name,rows in [("players",players),("teams",teams),("control",control)]:
        paths[name]=tmp_path/f"{name}.csv";pd.DataFrame(rows).to_csv(paths[name],index=False)
    paths["provenance"]=tmp_path/"proof.json";paths["provenance"].write_text('{"source":"synthetic"}')
    return paths


def entries(paths):return {k:{"path":str(v),"sha256":file_hash(v)} for k,v in paths.items()}


@pytest.mark.parametrize("problem",["coverage","target","future_source","naive_time","source_gap","later_control"])
def test_admission_failures_happen_before_fit(tmp_path,problem):
    paths=source_inputs(tmp_path)
    if problem=="source_gap":
        d=pd.read_csv(paths["players"]);d.loc[0,"us_xG"]=np.nan;d.to_csv(paths["players"],index=False)
    else:
        d=pd.read_csv(paths["control"])
        if problem=="coverage":d=d.iloc[1:]
        if problem=="target":d.loc[0,"points_core"]=99
        if problem=="future_source":d.loc[0,"source_max_ts"]=d.loc[0,"cutoff"]
        if problem=="naive_time":d.loc[0,"cutoff"]="2020-08-08T13:30:00"
        if problem=="later_control":d.loc[0,"season"]="2025-26"
        d.to_csv(paths["control"],index=False)
    with pytest.raises(ValueError):study.load(entries(paths))


def test_later_raw_rows_cannot_enter_development(tmp_path):
    paths=source_inputs(tmp_path)
    for name in ("players","teams"):
        d=pd.read_csv(paths[name]);later=d.iloc[[0]].copy();later["season"]="2025-26"
        if name=="players":later["total_points"]=9e9
        pd.concat([d,later]).to_csv(paths[name],index=False)
    p,t,c=study.load(entries(paths))
    assert set(p.season)==set(c.season)==set(t.season)=={"2020-21","2021-22",*study.FOLDS}
    assert len(p)==304


def test_only_declared_empty_calendar_week_is_permitted(tmp_path):
    paths=source_inputs(tmp_path)
    for name in ("players","control"):
        d=pd.read_csv(paths[name]);gw="GW" if name=="control" else "gameweek"
        d=d[~(d.season.eq("2022-23")&d[gw].eq(7))];d.to_csv(paths[name],index=False)
    study.load(entries(paths))
    for name in ("players","control"):
        d=pd.read_csv(paths[name]);gw="GW" if name=="control" else "gameweek"
        d=d[~(d.season.eq("2022-23")&d[gw].eq(6))];d.to_csv(paths[name],index=False)
    with pytest.raises(ValueError,match="Incomplete development fold"):study.load(entries(paths))


def test_only_training_labels_reach_all_participation_fits(monkeypatch):
    calls=[]
    class Regressor:
        def get_params(self):return {n:1 for n in ("max_leaf_nodes","max_iter","learning_rate","l2_regularization","min_samples_leaf","early_stopping","random_state")}
        def fit(self,x,y,sample_weight):calls.append(set(x.index));self.value=float(y.mean());return self
        def predict(self,x):return np.full(len(x),self.value)
    class Classifier:
        def __init__(self,**kwargs):self.classes_=[0,1,2]
        def fit(self,x,y,sample_weight):calls.append(set(x.index));return self
        def predict_proba(self,x):return np.tile([0.,.5,.5],(len(x),1))
    monkeypatch.setattr(study,"estimator",lambda _:Regressor())
    monkeypatch.setattr(study,"HistGradientBoostingClassifier",Classifier)
    x=pd.DataFrame(0.,index=range(12),columns=study.RICH)
    rows=pd.DataFrame({"ts":pd.date_range("2020-01-01",periods=12,tz="UTC"),
                       "minutes":[0,30,90]*4,"total_points":[0,-2,6]*3+[999,999,999]})
    train=rows.index<9;valid=~train
    pred=study.fit_predict("rich_participation",x,rows,train,valid)
    assert all(ids<=set(range(9)) for ids in calls) and len(calls)==3
    np.testing.assert_allclose(pred,2.)  # negative conditional mean retained


def test_feature_isolation_and_failed_point_rank_gates():
    assert set(study.FPL)<set(study.RICH)
    assert not any(n in study.RICH for n in study.SNAPSHOT_FEATURES)
    assert not any(n.startswith(study.OMIT_PREFIX) for n in study.RICH)
    control={k:{"rmse":3.,"mae":2.} for k in ("fixture","player_gw")};control["ndcg10"]=.5
    candidate={k:{"rmse":2.9,"mae":2.} for k in ("fixture","player_gw")};candidate["ndcg10"]=.51
    old={f:{k:{"rmse":3.} for k in ("candidate_fixture","candidate_player_gw")} for f in study.FOLDS}
    new={f:{k:{"rmse":2.9} for k in ("candidate_fixture","candidate_player_gw")} for f in study.FOLDS}
    assert study.gate(candidate,control,new,old,0.)
    assert not study.gate(candidate,control,new,old,-.01)
    candidate["ndcg10"]=.49
    assert not study.gate(candidate,control,new,old,10.)


def test_all_missing_column_selection_uses_training_only(monkeypatch):
    seen=[]
    class Regressor:
        def fit(self,x,y,sample_weight):seen.append(list(x));return self
        def predict(self,x):assert list(x)==seen[-1];return np.ones(len(x))
    monkeypatch.setattr(study,"estimator",lambda _:Regressor())
    x=pd.DataFrame(1.,index=range(6),columns=study.FPL)
    x.loc[:3,"ar_starts_3"]=np.nan
    x.loc[4:,"ar_starts_3"]=999.  # observed only in validation must not admit it
    rows=pd.DataFrame({"ts":pd.date_range("2020-01-01",periods=6,tz="UTC"),
                       "minutes":90.,"total_points":2.})
    study.fit_predict("fpl_windows",x,rows,rows.index<4,rows.index>=4)
    assert "ar_starts_3" not in seen[0] and "ar_starts_5" in seen[0]


def test_manifest_is_frozen_before_training(tmp_path,monkeypatch):
    paths=source_inputs(tmp_path);manifest=tmp_path/"manifest.json"
    monkeypatch.setattr(study,"panels",lambda c:{"synthetic":"frozen before fit"})
    monkeypatch.setattr(study,"fit_predict",lambda *a:pytest.fail("prepare must never fit"))
    study.prepare(paths,manifest);expected=file_hash(manifest)
    with pytest.raises(ValueError,match="Manifest exists"):study.prepare(paths,manifest)
    spec=json.loads(manifest.read_text());spec["policy"]["seed"]=7;manifest.write_text(json.dumps(spec))
    with pytest.raises(ValueError,match="checksum"):study.run(manifest,expected,tmp_path/"run")
