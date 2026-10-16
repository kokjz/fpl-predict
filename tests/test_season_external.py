import pandas as pd
import numpy as np
import pytest
from native_history import NativeHistory,SNAPSHOT_FEATURES
from season_external import fixture_targets,aggregate,scoring_core,origin_features
from test_native_history import data
from season_engine import Market


def test_snapshot_at_observed_origin_is_not_a_snapshot_at_real_deadline():
    p,t,q,s=data();q['inputs_as_of']='2026-01-10T09:00Z'
    s=pd.DataFrame([dict(season='2025-26',gameweek=20,fpl_code=11,captured_at='2026-01-10T09:00Z',**{k:0. for k in SNAPSHOT_FEATURES})])
    x,e=NativeHistory(p,t).transform_at_origins(q,s);assert e.snapshot_present.all()
    q['inputs_as_of']=q.deadline
    with pytest.raises(ValueError,match='precede'):NativeHistory(p,t).transform_at_origins(q,s)
    s['captured_at']='2026-01-10T10:00Z'
    with pytest.raises(ValueError,match='Late'):NativeHistory(p,t).transform(q,s)


def test_origin_features_exclude_matches_between_origin_and_deadline_buffer():
    p,t,q,s=data();p.loc[p.fixture.eq(1),'ts']='2026-01-10T06:30Z';t.loc[t.fixture.eq(1),'ts']='2026-01-10T06:30Z'
    q['inputs_as_of']='2026-01-10T09:00Z'
    x,e=NativeHistory(p,t).transform_at_origins(q,s)
    assert e.player_source_count.eq(0).all() #06:30 is later than09:00-3h.
    _,later=NativeHistory(p,t).transform(q,s);assert later.player_source_count.eq(1).all()


def test_fixture_targets_keep_future_gws_at_one_origin_and_aggregate_doubles():
    m=Market.create('2025-26',1,'2025-08-15T17:30Z','2025-08-15T12:00Z',[dict(id=7,position=3,team='1',price_tenths=50,can_buy=True)])
    b=dict(elements=[dict(id=7,code=999,element_type=3,team=1,now_cost=50)],teams=[dict(id=1,name='A'),dict(id=2,name='B')])
    f=pd.DataFrame([dict(id=i,event=g,team_h=1,team_a=2,kickoff_time='2025-08-15T19:00Z') for i,g in [(1,1),(2,1),(3,3)]])
    q=fixture_targets(m,b,f,3);assert q.gameweek.eq(1).all() and q.target_gameweek.tolist()==[1,1,3]
    h=aggregate(m,q,np.array([1.,2.,3.]),np.array([.2,.2,.2]),through=3,trained_through='2025-05-01T00:00Z',model_id='test',source_hashes={})
    assert h.values()==pytest.approx({(1,7):3.4,(2,7):0.,(3,7):3.2})
    q.loc[0,'inputs_as_of']='2025-08-16T00:00Z'
    with pytest.raises(ValueError,match='origin'):aggregate(m,q,np.ones(3),np.zeros(3),through=3,trained_through='2025-05-01T00:00Z',model_id='test',source_hashes={})


def test_core_harmonisation_removes_dc_once_and_keeps_unknown_as_unknown_award():
    p=pd.DataFrame(dict(position=[1,2,3,4],total_points=[6.,6.,6.,6.],defensive_contribution=[20.,10.,11.,12.]))
    assert scoring_core(p).total_points.tolist()==[6.,4.,6.,4.]
    p['defensive_contribution']=np.nan;assert scoring_core(p).total_points.eq(6).all()


def test_next_gw_news_and_ep_do_not_become_known_future_target_values():
    p,t,q,s=data();q['inputs_as_of']='2026-01-10T09:00Z';q['target_gameweek']=[20,21]
    s=pd.DataFrame([dict(season='2025-26',gameweek=20,fpl_code=11,captured_at='2026-01-10T09:00Z',**{k:75. for k in SNAPSHOT_FEATURES})])
    x,_=origin_features(NativeHistory(p,t),q,s)
    assert x.ar_ep_next.tolist()==[75.,-1.] and x.sig_chance_playing.tolist()==[75.,-1.]
    assert x.value.tolist()==[75.,75.]


def test_future_training_labels_rejected_before_loading_optional_learner():
    from season_external import fit_reference
    bad=pd.DataFrame(dict(season=['2025-26']))
    with pytest.raises(ValueError,match='chronological'):
        fit_reference('dastan_adaptation',bad,bad,pd.DataFrame(),pd.DataFrame(),bad,pd.DataFrame(),lambda v:None)
