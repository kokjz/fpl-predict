"""Synthetic chronology, aggregation, identity and gate regression tests."""
import numpy as np
import pandas as pd
import pytest
import fpl_team_xg as t
from fpl_model import CORE_FEATURES,FeatureStore,ew,sample_weights

def history():
    rows=[]
    for f in (1,2):
        for team in (1,2):
            for player in (1,2):
                rows.append(dict(season='2022-23',GW=f,fixture=f,team_id=team,opponent_team=3-team,element=team*10+player,was_home=team==1,minutes=90 if player==1 else 0,ts=pd.Timestamp('2022-08-01T15:00Z')+pd.Timedelta(days=7*(f-1)),expected_goals=float(team+player)/10,team_gf=team,team_ga=3-team))
    return pd.DataFrame(rows)

def bundle():
    s=np.repeat(t.SEASONS[:5],8);n=len(s)
    x=np.ones((n,len(CORE_FEATURES)));x[:,CORE_FEATURES.index('n_history')]=3;x[:,CORE_FEATURES.index('last5_minutes')]=60
    ts=pd.DatetimeIndex([pd.Timestamp(f'{int(season[:4])}-09-01T15:00Z')+pd.Timedelta(days=i%8) for i,season in enumerate(s)]).as_unit('ns').asi8
    a=dict(X_control=x,X_team_xg=np.column_stack([x.copy(),np.full((n,8),1.35)]),y=np.tile(np.arange(8,dtype=float),5),minutes=np.full(n,90.),season=s,gameweek=np.tile(np.repeat([1,2],4),5),fixture=np.tile([1,2,1,2,3,4,3,4],5),fpl_code=np.tile([1,1,2,2,1,1,2,2],5),element=np.tile([1,1,2,2,1,1,2,2],5),pos=np.full(n,2),n_history=np.full(n,3.),ts_ns=ts,cutoff_ns=np.repeat(ts.reshape(5,8)[:,::4],4,axis=1).ravel()-pd.Timedelta(days=1).value,candidate=np.ones(n,bool))
    for f in t.DEVELOPMENT:a['weights_'+f]=sample_weights(pd.DataFrame({'ts':pd.to_datetime(ts[s<f],utc=True)}))
    return a

def test_fixture_sum_zero_minute_and_reciprocal():
    f=t.fixture_statistics(history()).set_index(['fixture','team_id'])
    assert f.loc[(1,1),'xg']==pytest.approx(.5)
    assert f.loc[(1,1),'xga']==pytest.approx(.7)
    assert f.loc[(1,2),'xga']==f.loc[(1,1),'xg']

def test_missing_played_propagates_but_zero_minute_missing_does_not():
    d=history();d.loc[0,'expected_goals']=np.nan;f=t.fixture_statistics(d).set_index(['fixture','team_id'])
    assert np.isnan(f.loc[(1,1),'xg']) and np.isnan(f.loc[(1,2),'xga'])
    d=history();d.loc[1,'expected_goals']=np.nan;f=t.fixture_statistics(d)
    assert f.iloc[0].xg==pytest.approx(.2)
    d['expected_goals']=np.nan;assert t.fixture_statistics(d).xg.isna().all()

def test_integrity_refuses_multiple_opponents_and_duplicate_rows():
    d=history();d.loc[0,'opponent_team']=4
    with pytest.raises(ValueError):t.fixture_statistics(d)
    with pytest.raises(ValueError):t.fixture_statistics(pd.concat([history(),history().iloc[:1]]))

def test_cutoff_leakage_season_reset_and_prior():
    d=history();f=t.fixture_statistics(d);store=t.TeamXGStore(f);ts=d.ts.iloc[0]
    targets=pd.DataFrame(dict(season=['2022-23']*4+['2021-22'],team_id=[1]*5,opponent_team=[2]*5,cutoff=[ts,ts+pd.Timedelta(hours=3),ts+pd.Timedelta(hours=3,seconds=1),ts-pd.Timedelta(days=1),ts+pd.Timedelta(days=365)]))
    x=store.transform(targets)
    assert list(x)==t.NEW_FEATURES and x.shape==(5,8)
    assert x.iloc[[0,1,3,4]].eq(1.35).all().all()
    assert x.loc[2,'team_ew4_xg']==pytest.approx(ew([.5],4,1.35,4))
    changed=d.copy();changed.loc[changed.fixture.eq(1),'expected_goals']=999
    y=t.TeamXGStore(t.fixture_statistics(changed)).transform(targets.iloc[[0,1,3]])
    assert y.to_numpy().tobytes()==x.iloc[[0,1,3]].to_numpy().tobytes()
    # Same gf/ga store implementation mechanics after naming the two statistics.
    old=f.rename(columns={'xg':'team_xg','xga':'team_xga'}).copy()
    z=t.TeamXGStore(f).team('2022-23',1,ts+pd.Timedelta(days=20))
    for half in (4,12):
        for stat in ('xg','xga'):assert z[f'ew{half}_{stat}']==ew(old.loc[old.team_id.eq(1),'team_'+stat],half,1.35,4)

def test_identity_and_later_exclusion():
    a=bundle();assert t.shared_proof(a,t.DEVELOPMENT)['core_bytes_identical']
    a['X_team_xg'][0,0]=9
    with pytest.raises(ValueError,match='CORE'):t.shared_proof(a,t.DEVELOPMENT)
    for s in ('2026-27','2027-28'):
        with pytest.raises(ValueError):t.fold_masks([s],'2025-26')
    assert t.static_audit()['passed'] and t.static_audit()['i4_team_fields_read']==[]

def test_fit_feature_weights_and_control_parity(monkeypatch):
    a=bundle();calls=[]
    class Model:
        def fit(self,x,y,sample_weight):calls.append((x.copy(),y.copy(),sample_weight.copy()));return self
        def predict(self,x):return np.full(len(x),2.)
        def get_params(self):return {}
    monkeypatch.setattr(t,'estimator',lambda _:Model())
    c,_=t.fit_predict(a,'2023-24','control');p,_=t.fit_predict(a,'2023-24','team_xg')
    assert c.tobytes()==p.tobytes() and calls[0][0].to_numpy().tobytes()==calls[1][0][CORE_FEATURES].to_numpy().tobytes()
    assert calls[0][1].tobytes()==calls[1][1].tobytes() and calls[0][2].tobytes()==calls[1][2].tobytes()

def test_gate_formulas_at_boundary():
    control={k:dict(rmse=10.,mae=5.) for k in ('player_gw','fixture')};control['ndcg10']=.5
    candidate={k:dict(rmse=9.95,mae=5.025) for k in ('player_gw','fixture')};candidate['ndcg10']=.5
    fc={f:{k:dict(rmse=10.) for k in ('candidate_player_gw','candidate_fixture')} for f in t.DEVELOPMENT}
    fn={f:{k:dict(rmse=10.05) for k in ('candidate_player_gw','candidate_fixture')} for f in t.DEVELOPMENT}
    # Compute thresholds with the identical arithmetic to avoid decimal rounding.
    for f in t.DEVELOPMENT:
        for k in fn[f]:fn[f][k]['rmse']=1.005*10
    for k in ('player_gw','fixture'):candidate[k]['mae']=1.005*5
    assert t.gate_details(candidate,control,fn,fc,0)['passed']
    candidate['fixture']['rmse']=9.95001
    assert not t.gate_details(candidate,control,fn,fc,0)['passed']
