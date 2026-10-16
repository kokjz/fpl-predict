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


def test_dgw_card_and_minutes_moments_are_preserved_under_both_joint_models():
    f=fixture();f['old_p']=[.5,.8];f['new_p']=[.5,.8]
    f['old_p_card']=[.05,.02];f['new_p_card']=[.05,.02];f['conditional_card']=-1.
    f['old_xp']=f.old_p*4.-f.old_p_card;f['new_xp']=f.old_xp
    r=aggregate(f).iloc[0]
    assert r.old_p==pytest.approx(.9) and r.old_pc==pytest.approx(.019)
    assert r.old_q*r.old_p+r.old_qc*r.old_pc==pytest.approx(5.13)
    assert r.old_persistent_p==.8
    assert r.old_persistent_q*r.old_persistent_p+r.old_persistent_qc*r.old_persistent_pc==pytest.approx(5.13)


def test_audit_market_preserves_original_neutral_metadata_and_anchor(tmp_path,monkeypatch):
    import integration_study as study
    p=pd.DataFrame([dict(season='2025-26',gameweek=28,fixture=1,fpl_code=1,position=3,candidate=True,
        actual=2.,minutes=90.,old_p=.5,new_p=.8,old_xp=2.,new_xp=3.2)])
    a=p[['season','gameweek','fixture','fpl_code','position','candidate','actual','minutes']].assign(control=2.)
    raw=p[['season','gameweek','fpl_code']].assign(ts='2026-02-27T20:00Z',minutes=90.,yellow_cards=0.,red_cards=0.)
    previous=pd.DataFrame([dict(gameweek=28,fpl_code=1,reference=2.,actual=2.,minutes=90.,cards=0.,
        price_tenths=60,team='A',prior_minutes=22.5,blank_verified=0,fixture_count=1)])
    boot=dict(elements=[dict(code=1,element_type=3,team=1,now_cost=60,can_select=True,selected_by_percent='10')],teams=[dict(id=1,name='A')])
    monkeypatch.setattr(study,'read_snapshot',lambda *args:boot)
    monkeypatch.setattr(study,'extract_bootstrap',lambda *args:(dict(deadline='2026-02-27T18:30Z'),[]))
    snapshots={'snapshots':[dict(gameweek=28,file='one.json',sha256='a'*64,captured_at='2026-02-27T13:00Z')]}
    market,_=study.prepare_market(p,a,raw,snapshots,tmp_path,[dict(gameweek=28,published_at='2026-02-27T09:00Z')],previous)
    assert market.prior_minutes.iloc[0]==22.5  # never reconstruct as current-season zero
    assert market.anchor.iloc[0]==previous.reference.iloc[0]
