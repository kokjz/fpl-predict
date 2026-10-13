"""Adversarial temporal tests and planning invariants, not mirrors of model code."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fpl_model import normalise,FeatureStore,CORE_FEATURES,DC_FEATURES,ew,sample_weights
from forecast import select_xi,legal_squad,aggregate_fixture_predictions

from runtime import workspace_root
ROOT = workspace_root()

def tiny():
    records=[]
    for fixture,gw,date in [(1,1,'2024-01-01'),(2,2,'2024-01-08'),(3,2,'2024-01-12'),(4,3,'2024-01-20')]:
        for element,pos,home in [(1,2,True),(2,4,False)]:
            records.append(dict(season='test',element=element,pos=pos,fixture=fixture,GW=gw,kickoff_time=date+'T12:00:00Z',minutes=90,total_points=6,goals_scored=1,assists=0,clean_sheets=1,bonus=0,bps=12,threat=20,creativity=4,saves=0,expected_goals=.3,expected_assists=.1,expected_goals_conceded=.7,defensive_contribution=11,was_home=home,team_id=element,opponent_team=3-element,team_h_score=1,team_a_score=0))
    return pd.DataFrame(records)

def test_current_and_future_results_cannot_change_earlier_features():
    raw=tiny();d=normalise(raw);x=FeatureStore(d).transform(d)
    changed=raw.copy();mask=changed.GW>=2
    for col in ['minutes','total_points','goals_scored','assists','bonus','bps','expected_goals','expected_assists','team_h_score','team_a_score','defensive_contribution']:
        changed.loc[mask,col]=37
    d2=normalise(changed);x2=FeatureStore(d2).transform(d2)
    pd.testing.assert_frame_equal(x.loc[d.GW<=2],x2.loc[d2.GW<=2])
    assert not np.allclose(x.loc[d.GW==3,CORE_FEATURES],x2.loc[d2.GW==3,CORE_FEATURES])

def test_second_double_fixture_cannot_see_first_fixture_result():
    d=normalise(tiny());x=FeatureStore(d).transform(d)
    a=d.index[(d.element==1)&(d.fixture==2)][0];b=d.index[(d.element==1)&(d.fixture==3)][0]
    assert d.loc[a,'cutoff']==d.loc[b,'cutoff']
    pd.testing.assert_series_equal(x.loc[a],x.loc[b],check_names=False)
    assert x.loc[a,'n_history']==1

def test_live_match_not_used_before_completion_buffer():
    d=normalise(tiny());target=d.iloc[[2]].copy();target['cutoff']=pd.Timestamp('2024-01-01T13:00:00Z')
    x=FeatureStore(d).transform(target);assert x.n_history.iloc[0]==0

def test_feature_whitelist_and_recency():
    prohibited={'element','name','value','xP','ep_this','total_points','minutes','selected','transfers_in','team_h_score','team_a_score'}
    assert prohibited.isdisjoint(CORE_FEATURES+DC_FEATURES)
    assert ew([0,0,10],4,0)>ew([10,0,0],4,0)
    d=normalise(tiny());w=sample_weights(d);assert w[0]<w[-1]

def test_shuffled_source_order_is_irrelevant():
    d=normalise(tiny());x=FeatureStore(d).transform(d)
    shuffled=normalise(tiny().sample(frac=1,random_state=1));z=FeatureStore(shuffled).transform(shuffled)
    pd.testing.assert_frame_equal(x,z)

def squad():
    pp=[]
    for pos,n in [(1,2),(2,5),(3,5),(4,3)]:
        for _ in range(n):
            ident=len(pp)+1;pp.append({'id':ident,'position':pos,'team':(ident-1)//3+1,'expected_points':float(ident%7+1)})
    return pp

def test_lineup_and_club_constraints():
    pp=squad();assert legal_squad(pp);r=select_xi(pp);selected=[p for p in pp if p['id'] in r['starters']]
    assert len(selected)==11 and len(r['bench'])==4
    assert sum(p['position']==1 for p in selected)==1
    assert sum(p['position']==2 for p in selected)>=3
    assert sum(p['position']==3 for p in selected)>=2
    assert sum(p['position']==4 for p in selected)>=1
    assert r['captain'] in r['starters'] and r['vice'] in r['starters'] and r['captain']!=r['vice']
    bad=[{**p,'team':1} for p in pp];assert not legal_squad(bad)
    dup=pp[:-1]+[pp[0]];assert not legal_squad(dup)

def test_blank_and_double_aggregation():
    base={'id':1,'GW':2,'expected_points':4.,'core_xp':3.,'dc_xp':1.,'expected_minutes':70.,'p_play':.8,'n_history':4,'opponent':'X'}
    rr=[{**base,'fixture':1},{**base,'fixture':2}]
    a=aggregate_fixture_predictions(rr,[{'id':1}], [1,2])
    assert a[0]['expected_points']==0 and a[0]['fixtures']==[] and a[0]['p_play']==0
    assert a[1]['expected_points']==8 and len(a[1]['fixtures'])==2

@pytest.mark.integration
def test_saved_dataset_has_disjoint_keys_and_safe_sources():
    if not __import__('os').environ.get('FPL_PREDICT_RUN_INTEGRATION'):
        pytest.skip('Optional local-data integration check; synthetic integrity tests always run')
    d=pd.read_pickle(ROOT/'artifacts/history.pkl');x=pd.read_pickle(ROOT/'artifacts/features.pkl')
    assert not d.duplicated(['season','element','fixture']).any()
    assert ((x.source_max_ts.isna())|(x.source_max_ts<d.cutoff-pd.Timedelta(hours=3))).all()
    for test in ['2024-25','2025-26']:
        assert d.loc[d.season<test,'ts'].max()<d.loc[d.season==test,'cutoff'].min()
    assert np.isfinite(x[CORE_FEATURES].to_numpy()).all()

def test_feature_names_independent_of_player_identity():
    raw=tiny();a=normalise(raw);x=FeatureStore(a).transform(a)
    raw['element']+=1000;b=normalise(raw);y=FeatureStore(b).transform(b)
    pd.testing.assert_frame_equal(x,y)

@pytest.mark.integration
def test_published_forecast_and_model_integrity():
    if not __import__('os').environ.get('FPL_PREDICT_RUN_INTEGRATION'):
        pytest.skip('Optional local-data integration check; synthetic integrity tests always run')
    import hashlib
    p=ROOT/'forecasts'/(ROOT/'forecasts/LATEST').read_text().strip()
    m=json.loads((p/'manifest.json').read_text())
    assert m['model_sha256']==hashlib.sha256((ROOT/'artifacts/model.joblib').read_bytes()).hexdigest()
    rr=json.loads((p/'fixture_predictions.json').read_text())
    assert len({(r['id'],r['fixture']) for r in rr})==len(rr)
    for r in rr:
        assert np.isfinite(r['expected_points'])
        assert r['expected_points']==pytest.approx(r['core_xp']+r['dc_xp'])
        assert 0<=r['p60']<=r['p_play']<=1
        assert 0<=r['expected_minutes']<=90
        assert 0<=r['dc_xp']<=2*r['p_play']+1e-9

@pytest.mark.integration
def test_future_outcomes_cannot_be_scored_early():
    if not __import__('os').environ.get('FPL_PREDICT_RUN_INTEGRATION'):
        pytest.skip('Optional local-data integration check; synthetic integrity tests always run')
    import argparse
    from score_forecast import run
    p=ROOT/'forecasts'/(ROOT/'forecasts/LATEST').read_text().strip()
    m=json.loads((p/'manifest.json').read_text())
    args=argparse.Namespace(forecast=str(p),gw=m['start_gw'],outcome_snapshot=m['snapshot'])
    with pytest.raises(ValueError,match='not yet finished and checked'):run(args)

@pytest.mark.integration
def test_raw_download_checksums():
    if not __import__('os').environ.get('FPL_PREDICT_RUN_INTEGRATION'):
        pytest.skip('Optional local-data integration check; synthetic integrity tests always run')
    import hashlib
    root=ROOT/'data/historical';m=json.loads((root/'manifest.json').read_text())
    for row in m['files']:
        assert hashlib.sha256((root/row['season']/row['file']).read_bytes()).hexdigest()==row['sha256']
