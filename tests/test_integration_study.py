import numpy as np
import pandas as pd
import pytest
from integration_study import aggregate,inputs_for,progression


def fixture():
    return pd.DataFrame([dict(season='2025-26',gameweek=26,fpl_code=1,fixture=i,position=3,candidate=True,
      actual=2.,minutes=30.,anchor=3.,old_xp=4.*p,new_xp=4.*q,old_p=p,new_p=q)
      for i,p,q in [(1,.5,.8),(2,.5,.8)]])


def test_dgw_joint_model_preserves_means_and_explicit_coupling():
    g=aggregate(fixture());r=g.iloc[0]
    assert r.old_xp==4. and r.old_p==.75 and r.old_persistent_p==.5
    assert r.new_xp==pytest.approx(6.4) and r.new_p==pytest.approx(.96)
    assert r.old_q*r.old_p==pytest.approx(r.old_xp)
    g['position']=3;g['team']='A';g['price_tenths']=60
    a=inputs_for(g,[1],'old_expected');b=inputs_for(g,[1],'old_expected',persistent=True)
    assert a[0]['expected_points']==b[0]['expected_points']==4.
    assert a[0]['p_play']==.75 and b[0]['p_play']==.5
    changed=g.assign(actual=999,minutes=999,cards=999)
    assert inputs_for(changed,[1],'old_expected')==a
    assert 'actual' not in a[0] and 'minutes' not in a[0]


def test_candidate_or_position_conflict_fails_before_aggregation():
    f=fixture();f.loc[0,'candidate']=False
    with pytest.raises(ValueError):aggregate(f)


def test_progression_uses_incumbent_anchor_and_fixed_combined_arm():
    def value(rmse,mae,rank):return {'candidates':dict(rmse=rmse,mae=mae,mean_within_gw_ndcg10=rank)}
    m={'validation':{'anchor':value(3,2,.4),'new_xp':value(2.9,2,.41)}}
    means=dict(anchor=40,old_mean=39,new_expected=41)
    assert progression(m,means)['passed']
    means['new_expected']=39.5
    assert not progression(m,means)['passed']
