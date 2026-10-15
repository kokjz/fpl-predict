import json
import numpy as np
import pandas as pd
import pytest

import native_reference as pilot
from experiment_runner import file_hash
from native_history import PLAYER_STATS, TEAM_STATS, DEFENSIVE, SNAPSHOT_FEATURES


def inputs(tmp_path):
    players=[];teams=[];snapshots=[]
    for season in [*pilot.POLICY["train_seasons"],"2025-26"]:
        weeks=[1] if season!="2025-26" else [1,*range(20,39)]
        for gw in weeks:
            ts=pd.Timestamp(f"{int(season[:4])+1}-01-01T15:00:00Z")+pd.Timedelta(weeks=gw)
            deadline=ts-pd.Timedelta(minutes=90)
            for code,club,opponent,home,points in [(11,"A","B",True,2.),(22,"B","A",False,1.)]:
                row={name:1. for name in [*PLAYER_STATS,*DEFENSIVE]}
                row.update(season=season,gameweek=gw,fixture=gw,fpl_code=code,position=2,
                           team_name=club,opponent_name=opponent,home=home,ts=ts,deadline=deadline,
                           minutes=90.,total_points=points,starts=1.,understat_id=code)
                players.append(row)
                row={name:1. for name in TEAM_STATS if "league_rank" not in name}
                row.update(season=season,fixture=gw,team_name=club,opponent_name=opponent,ts=ts,
                           goals_scored=points,goals_conceded=3-points)
                teams.append(row)
                if season=="2025-26" and code==11:
                    snapshots.append(dict(season=season,gameweek=gw,fpl_code=code,captured_at=deadline-pd.Timedelta(hours=1),
                                          **{name:0. for name in SNAPSHOT_FEATURES}))
    players=pd.DataFrame(players)
    ref=players[players.season.eq("2025-26")&players.gameweek.ge(28)][["season","gameweek","fixture","fpl_code","total_points"]].copy()
    ref=ref.rename(columns={"total_points":"actual"}).assign(reference=1.3,candidate=True)
    paths={}
    for name,frame in (("players",players),("teams",pd.DataFrame(teams)),("snapshots",pd.DataFrame(snapshots)),("reference",ref)):
        path=tmp_path/f"{name}.csv";frame.to_csv(path,index=False);paths[name]=path
    paths["provenance"]=tmp_path/"provenance.json"
    paths["provenance"].write_text(json.dumps({"native_inputs_ready":True,"scope":"synthetic fixture"}))
    return paths,players


def test_fixed_reference_fit_never_trains_on_validation_or_test(tmp_path,monkeypatch):
    monkeypatch.setitem(pilot.POLICY,"allowed_training_gap_keys",[])
    paths,p=inputs(tmp_path);manifest=tmp_path/"manifest.json"
    pilot.prepare(paths,manifest)
    fits=[]
    class Constant:
        def __init__(self,**kwargs):assert kwargs["early_stopping"] is False
        def fit(self,x,y,sample_weight):
            fits.append(set(x.index));self.value=float(y.mean());return self
        def predict(self,x):return np.full(len(x),self.value)
    monkeypatch.setattr(pilot,"HistGradientBoostingRegressor",Constant)
    result=pilot.run(manifest,file_hash(manifest),tmp_path/"run")
    assert len(fits)==1 and fits[0]==set(p.index[pilot.split_masks(p)["train"]])
    primary=result["metrics"]["snapshot_known_candidates"]["native_reference"]
    assert primary["n"]==11
    assert result["metrics"]["all_candidates"]["native_reference"]["n"]==22
    assert not result["policy"]["model_promotion"] and not result["policy"]["benchmark_eligible"]
    with pytest.raises(ValueError,match="Output exists"):
        pilot.run(manifest,file_hash(manifest),tmp_path/"run")


@pytest.mark.parametrize("bad",["readiness","coverage","manifest","input"])
def test_failures_cannot_start_training(tmp_path,bad,monkeypatch):
    monkeypatch.setitem(pilot.POLICY,"allowed_training_gap_keys",[])
    paths,_=inputs(tmp_path);manifest=tmp_path/"manifest.json"
    if bad=="readiness":paths["provenance"].write_text('{"native_inputs_ready":false}')
    if bad=="coverage":
        d=pd.read_csv(paths["reference"]);d.iloc[1:].to_csv(paths["reference"],index=False)
    if bad in ("readiness","coverage"):
        with pytest.raises(ValueError):pilot.prepare(paths,manifest)
        assert not manifest.exists();return
    pilot.prepare(paths,manifest);expected=file_hash(manifest)
    if bad=="manifest":manifest.write_text(manifest.read_text()+" ")
    else:paths["players"].write_text("changed")
    monkeypatch.setattr(pilot,"HistGradientBoostingRegressor",lambda **_:pytest.fail("training must not begin"))
    with pytest.raises(ValueError,match="checksum"):pilot.run(manifest,expected,tmp_path/"run")


def test_a_new_validation_or_test_source_gap_is_rejected(tmp_path,monkeypatch):
    monkeypatch.setitem(pilot.POLICY,"allowed_training_gap_keys",[])
    paths,_=inputs(tmp_path);p=pd.read_csv(paths["players"])
    p.loc[p.season.eq("2025-26")&p.gameweek.eq(28),"us_xG"]=np.nan
    p.to_csv(paths["players"],index=False)
    with pytest.raises(ValueError,match="source-gap mask"):pilot.prepare(paths,tmp_path/"manifest.json")
