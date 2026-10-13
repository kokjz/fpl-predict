import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd,pytest
from candidate_models import enhance,BlendCore
from model_registry import approve,resolve_champion,REQUIRED_GATES,save_registry
from points_replay import realised_points

def test_new_features_only_use_old_feature_values():
    from test_model import tiny
    from fpl_model import normalise,FeatureStore
    raw=tiny();d=normalise(raw);x=FeatureStore(d).transform(d)
    raw.loc[raw.GW>=2,'minutes']=1;raw.loc[raw.GW>=2,'total_points']=50
    z=normalise(raw);xx=FeatureStore(z).transform(z)
    pd.testing.assert_frame_equal(enhance(x.loc[d.GW<=2]),enhance(xx.loc[z.GW<=2]))
    assert np.isfinite(enhance(x).to_numpy()).all()
    assert 'element' not in enhance(x).columns

def test_registry_rejects_any_failed_or_missing_gate():
    r={'champion':'1','versions':{'1':{'status':'approved'}}}
    for missing in REQUIRED_GATES:
        gates={k:True for k in REQUIRED_GATES if k!=missing}
        with pytest.raises(ValueError,match='Promotion rejected'):approve(r,'2','model','sha',{'gates':gates})
    assert r['champion']=='1'

def test_registry_uses_approved_version_and_checks_hash(tmp_path):
    (tmp_path/'good').write_bytes(b'good');(tmp_path/'newer').write_bytes(b'newer')
    r={'champion':'1','versions':{'1':{'status':'approved','artifact':'good','sha256':hashlib.sha256(b'good').hexdigest()},'2':{'status':'candidate','artifact':'newer'}}}
    save_registry(tmp_path,r);assert resolve_champion(tmp_path)[1]=='1'
    (tmp_path/'good').write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash mismatch'):resolve_champion(tmp_path)

def test_registry_rejects_unapproved_champion(tmp_path):
    save_registry(tmp_path,{'champion':'2','versions':{'2':{'status':'candidate'}}})
    with pytest.raises(ValueError,match='not approved'):resolve_champion(tmp_path)

def team():
    pos=[1,2,2,2,3,3,3,3,4,4,4,3,2,3,1]
    return {i+1:{'position':p} for i,p in enumerate(pos)}

def test_autosub_preserves_minimum_defenders_and_vice_captain():
    players=team();selection={'starters':list(range(1,12)),'bench':[12,13,14,15],'captain':2,'vice':5}
    played={i:True for i in players};played[2]=False
    actual={i:1. for i in players};actual[2]=0;actual[12]=20;actual[13]=4
    # MID first sub cannot replace a missing DEF in a three-defender formation.
    assert realised_points(selection,players,actual,played)==15

def test_goalkeeper_substitution_and_captain_no_fallback():
    players=team();selection={'starters':list(range(1,12)),'bench':[12,13,14,15],'captain':1,'vice':2}
    played={i:True for i in players};played[1]=False;played[2]=False
    actual={i:1. for i in players};actual[1]=0;actual[2]=0;actual[15]=5;actual[13]=4
    assert realised_points(selection,players,actual,played)==18
