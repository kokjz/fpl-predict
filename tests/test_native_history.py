import numpy as np
import pandas as pd
import pytest

from native_history import NativeHistory, WindowIndex, PLAYER_STATS, TEAM_STATS, DEFENSIVE, FEATURES, SNAPSHOT_FEATURES


def data():
    players=[]; teams=[]
    for fixture,ts,gf,ga in [(1,"2026-01-01T15:00:00Z",2,1),(2,"2026-01-10T15:00:00Z",4,0),
                             (3,"2026-01-14T15:00:00Z",1,3)]:
        for player,club,opponent,home,scored,conceded in [(11,"A","B",True,gf,ga),(22,"B","A",False,ga,gf)]:
            p={name:1. for name in [*PLAYER_STATS,*DEFENSIVE]}
            p.update(season="2025-26",fixture=fixture,fpl_code=player,position=2,team_name=club,
                     opponent_name=opponent,home=home,ts=ts,minutes=90.,total_points=float(scored),starts=1.)
            players.append(p)
            t={name:1. for name in TEAM_STATS if "league_rank" not in name}
            t.update(season="2025-26",fixture=fixture,team_name=club,opponent_name=opponent,
                     ts=ts,goals_scored=float(scored),goals_conceded=float(conceded))
            teams.append(t)
    targets=pd.DataFrame([dict(season="2025-26",gameweek=20,fixture=2,fpl_code=11,position=2,
                               team_name="A",opponent_name="B",home=True,deadline="2026-01-10T10:00:00Z"),
                          dict(season="2025-26",gameweek=20,fixture=3,fpl_code=11,position=2,
                               team_name="A",opponent_name="B",home=True,deadline="2026-01-10T10:00:00Z")])
    snapshots=pd.DataFrame(columns=["season","gameweek","fpl_code","captured_at",*SNAPSHOT_FEATURES])
    return pd.DataFrame(players),pd.DataFrame(teams),targets,snapshots


def test_all_native_features_use_deadline_and_keep_double_histories_equal():
    p,t,targets,s=data(); x,e=NativeHistory(p,t).transform(targets,s)
    assert len(FEATURES)==286 and len(set(FEATURES))==286
    assert x.shape==(2,286)
    np.testing.assert_allclose(x.iloc[0],x.iloc[1],equal_nan=True)
    assert x.opp_goals_scored_1.tolist()==[1.,1.]
    assert not e.snapshot_present.any() and x.ar_ep_next.eq(-1).all()
    assert (e.opponent_source_max_ts<pd.Timestamp("2026-01-10T07:00:00Z")).all()


def test_mutating_future_player_team_and_opponent_results_changes_no_features():
    p,t,targets,s=data(); expected,_=NativeHistory(p,t).transform(targets,s)
    p.loc[p.fixture.ge(2),list(PLAYER_STATS)]=777
    p.loc[p.fixture.ge(2),"minutes"]=90
    t.loc[t.fixture.ge(2),[c for c in TEAM_STATS if "league_rank" not in c]]=888
    actual,_=NativeHistory(p,t).transform(targets,s)
    pd.testing.assert_frame_equal(expected,actual)


def test_global_league_context_includes_only_completed_past_matches():
    p,t,targets,s=data(); x,e=NativeHistory(p,t).transform(targets,s)
    assert x.status_league_rank.eq(1).all() and x.opp_status_league_rank.eq(2).all()
    assert e.league_source_count.eq(2).all()
    assert e.league_source_max_ts.eq(pd.Timestamp("2026-01-01T15:00:00Z")).all()


def test_boundary_and_nan_means_never_use_future_values():
    index=WindowIndex(pd.DataFrame({"ts":pd.to_datetime(["2026-01-01T15:00:00Z","2026-01-10T07:00:00Z"]),
                                    "value":[np.nan,100.]}),["value"])
    means,n,last=index.means(pd.Timestamp("2026-01-10T07:00:00Z"))
    assert n==1 and np.isnan(means[1][0])
    # Explicit microsecond inputs still compare against nanosecond Timestamp.value.
    frame=pd.DataFrame({"ts":pd.to_datetime(["2026-01-10T07:00:00Z"]).as_unit("us"),"value":[100.]})
    assert WindowIndex(frame,["value"]).means(pd.Timestamp("2026-01-10T07:00:00Z"))[1]==0


@pytest.mark.parametrize("problem",["late_snapshot","duplicate_snapshot","deadline","missing_raw","duplicate_raw"])
def test_missing_or_ambiguous_evidence_rejected(problem):
    p,t,targets,s=data()
    if problem in ("late_snapshot","duplicate_snapshot"):
        row=dict(season="2025-26",gameweek=20,fpl_code=11,captured_at="2026-01-10T10:00:00Z",**{k:0 for k in SNAPSHOT_FEATURES})
        s=pd.DataFrame([row] if problem=="late_snapshot" else [row,row])
    if problem=="deadline":targets.loc[1,"deadline"]="2026-01-11T10:00:00Z"
    if problem=="missing_raw":p=p.drop(columns="us_xG")
    if problem=="duplicate_raw":p=pd.concat([p,p.iloc[[0]]],ignore_index=True)
    with pytest.raises(ValueError):NativeHistory(p,t).transform(targets,s)


def test_known_snapshot_and_missing_snapshot_preserve_all_rows():
    p,t,targets,s=data()
    row=dict(season="2025-26",gameweek=20,fpl_code=11,captured_at="2026-01-10T09:00:00Z",**{k:0. for k in SNAPSHOT_FEATURES})
    x,e=NativeHistory(p,t).transform(targets,pd.DataFrame([row]))
    assert len(x)==len(targets) and e.snapshot_present.all()
    assert x.ar_ep_next.eq(0).all()  # genuine zero differs from absent=-1


def test_input_order_does_not_change_features():
    p,t,targets,s=data(); expected,_=NativeHistory(p,t).transform(targets,s)
    actual,_=NativeHistory(p.sample(frac=1,random_state=4),t.sample(frac=1,random_state=5)).transform(targets,s)
    pd.testing.assert_frame_equal(expected,actual)
