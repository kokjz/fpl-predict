import numpy as np
import pandas as pd
import pytest
import availability_prospective as m

def example():
    d=pd.DataFrame(dict(season=['2025-26']*3,GW=[4]*3,element=[1,2,3],fixture=[1]*3,fpl_code=[101,102,103],pos=[2]*3,cutoff=pd.to_datetime(['2025-09-12T10:00Z']*3)))
    x=pd.DataFrame(1.,index=d.index,columns=m.CORE_FEATURES)
    bridge=pd.DataFrame(dict(id=[1,2,3],code=[101,102,103]))
    obs=pd.DataFrame(dict(gameweek=[4,4],fpl_code=[101,102],source_position=[2,2],published_at=['2025-09-12T09:59Z']*2,source_deadline=['2025-09-12T10:00Z']*2,chance_label=[0,75]))
    return d,x,bridge,obs

def test_features_and_unknowns():
    d,x,b,o=example();z,c=m.augment_control(d,x,b,o)
    assert list(z)==m.CORE_FEATURES+m.SIGNALS
    assert z[m.SIGNALS].to_numpy().tolist()==[[0,0],[.75,0],[0,1]]
    assert z[m.CORE_FEATURES].to_numpy().tobytes()==x.to_numpy().tobytes()
    assert m.FEATURE_HASHES=={'control':'3a81a8d37e56558d09297aaa562b1315d56d49f7813c69e81063f0d0b3f40453','availability':'f99485e88251dd6b0e2494befeb224387ef6747acc14c76c242b5c59b55cad92'}

@pytest.mark.parametrize('stamp',['2025-09-12T10:00Z','2025-09-12T10:00:01Z'])
def test_commit_boundary(stamp):
    d,x,b,o=example();o['published_at']=stamp
    with pytest.raises(ValueError,match='before both'):m.augment_control(d,x,b,o)

def test_key_join_and_shuffle():
    d,x,b,o=example();block=d[m.KEYS].assign(signal=[3,4,5])
    assert m.keyed_block(d,block,['signal']).signal.tolist()==[3,4,5]
    with pytest.raises(ValueError,match='order'):m.keyed_block(d,block.iloc[::-1],['signal'])

def test_census():
    z=m.census([dict(gameweek=g,chance_known=g) for g in range(4,39)])
    assert len(z)==38 and sum(r['status']=='admitted' for r in z)==35
    with pytest.raises(ValueError):m.census([dict(gameweek=4)]*35)

def test_sanity_gate_thresholds():
    control=dict(candidate_player_gw=dict(rmse=2,mae=1),mean_within_gw_ndcg10=.5)
    candidate=dict(candidate_player_gw=dict(rmse=2,mae=1.005),mean_within_gw_ndcg10=.495)
    assert m.gate_b(candidate,control)['passed']
    candidate['candidate_player_gw']['mae']=1.00501
    assert not m.gate_b(candidate,control)['passed']

def test_phase2_gate_formulas():
    control={u:dict(rmse=2.,mae=1.) for u in ('player_gw','fixture')}
    candidate={u:dict(rmse=1.99,mae=1.005) for u in control}
    assert m.phase2_gates(candidate,control,0,2.01,2,[-.1,.1])['passed']
    candidate['fixture']['rmse']=1.99001
    r=m.phase2_gates(candidate,control,0,2.01,2,[-.1,.1]);assert not r['passed'] and r['gate5']['descriptive']

def test_first_prospective_strict_boundary():
    events=[dict(id=i,deadline_time=f'2026-11-0{i}T10:00Z') for i in (4,5)]
    assert m.first_prospective_gameweek(events,'2026-11-04T10:00Z')['gameweek']==5
    with pytest.raises(ValueError):m.first_prospective_gameweek(events,'2026-11-06T10:00Z')

@pytest.mark.parametrize('operation',['fit','score','admission','freeze','predictions','availability','outcomes'])
def test_phase1_refuses_current_season(operation):
    with pytest.raises(ValueError):m.phase1_scope(['2026-27'],operation)

def test_fits_preserve_all_unknown_rows():
    rng=np.random.default_rng(12);n=180
    d=pd.DataFrame(dict(season=['2024-25']*120+['2025-26']*60,GW=[1]*120+[20]*60,fixture=range(n),fpl_code=range(n),ts=pd.to_datetime(['2025-01-01T12:00Z']*120+['2026-01-01T12:00Z']*60),cutoff=pd.to_datetime(['2025-01-01T10:00Z']*120+['2026-01-01T10:00Z']*60),points_core=rng.normal(3,1,n)))
    x=pd.DataFrame(rng.random((n,51)),columns=m.FEATURES['availability']);x['availability_missing']=1.;x['availability_chance']=0.
    fitted,p,r=m.fit(d,x,'availability','B');assert r['train_rows']==120 and len(p)==60
    fitted,p,r=m.fit(d,x,'availability','F');assert r['train_rows']==180 and p is None
