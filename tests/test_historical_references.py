import json

import numpy as np
import pandas as pd
import pytest

import historical_references as ref


def test_upstream_features_and_unknown_availability_have_explicit_encoding():
    x=pd.DataFrame({"player_fpl_points_1":[np.nan,3], "opp_xg_5":[2,1],
                    "sig_chance_playing":[-1,75]})
    result=ref.openfpl_matrix(x,["player fpl points 1", "opponent xg 5", "status player availability"])
    np.testing.assert_allclose(result,[[0,2,-1],[3,1,.75]])
    assert np.isnan(x.player_fpl_points_1.iloc[0])  # model transform preserves raw evidence
    with pytest.raises(ValueError,match="encoding"):
        ref.openfpl_matrix(x.assign(sig_chance_playing=88),["status player availability"])
    with pytest.raises(ValueError,match="mapping"):
        ref.openfpl_matrix(x,["a missing feature"])


def test_training_only_scalers_weights_and_published_member_budget():
    calls=[]
    class Head:
        def __init__(self,**parameters):
            assert parameters["n_jobs"]==2 and parameters["random_state"]==42
            self.best_iteration=1
        def fit(self,x,y,sample_weight,eval_set,sample_weight_eval_set,verbose):
            calls.append((x.copy(),y.copy(),sample_weight.copy(),eval_set[0][0].copy()))
            assert np.isclose(x.min(),0) and np.isclose(x.max(),1)
            assert np.isclose(sample_weight.mean(),1)
            self.mean=float(y.mean());return self
        def predict(self,x):
            assert x.min()>1  # query is transformed, never included in scaler fit
            return np.full(len(x),self.mean)
    t=pd.DataFrame({"total_points":np.arange(24)%12})
    v=pd.DataFrame({"total_points":np.arange(8)%8})
    events=[]
    prediction=ref.fit_openfpl(t,v,np.arange(24)[:,None],np.arange(30,38)[:,None],
                             np.arange(50,53)[:,None],1,events.append,Head)
    assert len(calls)==len(events)==10
    assert prediction.shape==(3,)
    assert all(np.array_equal(calls[0][0],c[0]) for c in calls)
    assert {e["member"] for e in events}=={m["candidate"] for m in ref.recipe()["members"]["1"]}


def toy():
    players=[];teams=[]
    for fixture,date in enumerate(["2025-08-01","2025-08-08","2025-08-15","2025-08-22"],1):
        ts=pd.Timestamp(date,tz="UTC")
        for club,opponent,home,gf,ga in [("A","B",True,2,1),("B","A",False,1,2)]:
            teams.append(dict(season="2025-26",fixture=fixture,team_name=club,opponent_name=opponent,
                              home=home,ts=ts,goals_scored=gf,goals_conceded=ga))
            for pos in range(1,5):
                players.append(dict(season="2025-26",gameweek=fixture,fixture=fixture,
                         fpl_code=pos+(10 if club=="B" else 0),position=pos,team_name=club,
                         opponent_name=opponent,home=home,ts=ts,deadline=ts-pd.Timedelta(hours=4),
                         minutes=90 if pos!=4 else 25,total_points=pos,team_goals=gf,
                         goals_scored=int(pos==4),assists=int(pos==3),goals_conceded=ga,saves=int(pos==1)))
    return pd.DataFrame(players),pd.DataFrame(teams)


def test_component_current_and_future_outcomes_do_not_change_prediction():
    p,t=toy();train=p.fixture.le(2);query=p.fixture.eq(3)
    baseline=ref.ConjugatePoisson().fit(p,t,train).predict(p[query],pd.Series(-1,index=p.index[query]))
    altered=p.copy();altered.loc[altered.fixture.ge(3),["total_points","goals_scored","assists","team_goals","saves","minutes"]]=0
    changed=t.copy();changed.loc[changed.fixture.ge(3),"goals_scored"]=9
    result=ref.ConjugatePoisson().fit(altered,changed,train).predict(altered[query],pd.Series(-1,index=p.index[query]))
    np.testing.assert_allclose(baseline,result)
    absent=ref.ConjugatePoisson().fit(p,t,train).predict(p[query],pd.Series(0,index=p.index[query]))
    np.testing.assert_array_equal(absent,0)


def test_component_missing_history_uses_declared_prior_without_row_drops():
    p,t=toy();query=p.fixture.eq(4)&p.fpl_code.eq(4)
    p.loc[query,"fpl_code"]=99
    model=ref.ConjugatePoisson().fit(p,t,p.fixture.le(2))
    result=model.predict(p[query],pd.Series(-1,index=p.index[query]))
    assert len(result)==1 and np.isfinite(result).all()
    with pytest.raises(ValueError,match="fit reaches"):
        model.predict(p[p.fixture.eq(1)],pd.Series(-1,index=p.index[p.fixture.eq(1)]))


def test_poisson_scoring_expectations_handle_no_show_and_negative_returns():
    scores=ref.minute_points([0,59,60,90],0,0,np.array([0,0,1]),0,0,2)
    np.testing.assert_allclose(scores,[0,1,6,6])
    assert ref.minute_points([90],0,10,np.array([0,0,1]),0,0,2)[0]<0
    counts=ref.involvement_counts(pd.DataFrame({"minutes":[0],"team_goals":[2]}),pd.Timestamp("2025-08-01",tz="UTC"))
    np.testing.assert_array_equal(counts,0)


def test_manifest_changes_rejected_before_any_fitting(tmp_path):
    path=tmp_path/"manifest.json";path.write_text(json.dumps({"policy":{}}))
    with pytest.raises(ValueError,match="checksum"):
        ref.run(path,"0"*64,tmp_path/"job")
    assert not (tmp_path/"job").exists()


def test_recipe_has_four_positions_and_fixed_member_definitions():
    recipe=ref.recipe()
    assert recipe["source_revision"]=="ad055ba7270145ce8ecc1f19581423493b1357e7"
    assert {k:len(v) for k,v in recipe["feature_schema"].items()}=={"1":196,"2":206,"3":206,"4":206}
    assert all(len(v)==10 for v in recipe["members"].values())
    assert ref.POLICY["promotion"] is False and ref.POLICY["original_system"] is False
