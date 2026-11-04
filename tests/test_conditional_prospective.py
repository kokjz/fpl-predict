import numpy as np
import pandas as pd
import pytest
import conditional_prospective as m
from test_availability_prospective import example

def test_order_hashes_unknown_and_zero():
    d,x,b,o=example()
    for n in m.EXTRA:x[n]=.1
    z,c=m.augment_control(d,x,b,o)
    assert list(z)==m.FEATURES['conditional']
    assert z[m.SIGNALS].to_numpy().tolist()==[[0,0],[.75,0],[0,1]]
    assert z[m.CORE_FEATURES].to_numpy().tobytes()==x[m.CORE_FEATURES].to_numpy().tobytes()
    assert m.FEATURE_HASHES=={'control':'3a81a8d37e56558d09297aaa562b1315d56d49f7813c69e81063f0d0b3f40453',
        'conditional_core':'3a81a8d37e56558d09297aaa562b1315d56d49f7813c69e81063f0d0b3f40453',
        'conditional_played':'f99485e88251dd6b0e2494befeb224387ef6747acc14c76c242b5c59b55cad92',
        'conditional_minutes':'3a81a8d37e56558d09297aaa562b1315d56d49f7813c69e81063f0d0b3f40453',
        'conditional_sixty':'3a81a8d37e56558d09297aaa562b1315d56d49f7813c69e81063f0d0b3f40453',
        'conditional_dc':'d325a5ee8ce793f92bd51815c7370c2726fdb000c1e068717f2a7f368ee3b0da'}

def test_keyed_loader_handles_shuffled_history_without_positional_join():
    d,x,b,o=example()
    for n in m.CORE_FEATURES:d[n]=x[n]
    for n in m.TRAINING:
        if n not in d:d[n]=np.arange(3,dtype=float)
    for n in m.EXTRA:x[n]=np.arange(3,dtype=float)
    original=d.copy();d=d.iloc[::-1];x=x.iloc[::-1]
    attached,z=m.attach_loader(original,d,x,{'2025-26':b})
    assert attached.played.tolist()==[0,1,2]
    assert z.dc_rate4.tolist()==[0,1,2]
    assert z[m.CORE_FEATURES].to_numpy().tobytes()==original[m.CORE_FEATURES].to_numpy().tobytes()
    block=original[m.KEYS].assign(signal=[1,2,3])
    with pytest.raises(ValueError,match='order'):m.keyed_block(original,block.iloc[::-1],['signal'])

@pytest.mark.parametrize('stamp',['2025-09-12T10:00Z','2025-09-12T10:00:01Z'])
def test_commit_time_boundary(stamp):
    d,x,b,o=example()
    for n in m.EXTRA:x[n]=.1
    o['published_at']=stamp
    with pytest.raises(ValueError,match='before both'):m.augment_control(d,x,b,o)

def test_gate_formulas_ranking_descriptive():
    old={'candidate_player_gw':dict(rmse=2,mae=1)}
    new={'candidate_player_gw':dict(rmse=2,mae=1.005)}
    assert m.gate_b(new,old)['passed']
    assert len(m.gate_b(new,old)['criteria'])==2
    new['candidate_player_gw']['rmse']=2.00001;assert not m.gate_b(new,old)['passed']
    c={u:dict(rmse=2,mae=1) for u in ('player_gw','fixture')};n={u:dict(rmse=1.99,mae=1.005) for u in c}
    assert m.phase2_gates(n,c,0,2.01,2,[-.1,.1])['passed']
    assert not m.phase2_gates(n,c,-.01,2.01,2,[-.1,.1])['passed']

def test_first_deadline_strict_after_push():
    e=[dict(id=10,deadline_time='2026-11-04T10:00Z'),dict(id=11,deadline_time='2026-11-05T10:00Z')]
    assert m.first_prospective_gameweek(e,'2026-11-04T10:00Z')['gameweek']==11

@pytest.mark.parametrize('operation',['fit','score','admission','freeze','predictions','outcomes','availability'])
def test_no_future_content(operation):
    with pytest.raises(ValueError):m.phase1_scope(['2026-27'],operation)

def test_core_bytes_pass_through_unchanged_fit(monkeypatch):
    d,x,b,o=example()
    for n in m.CORE_FEATURES:d[n]=x[n]
    d['ts']=pd.to_datetime(['2025-08-01T12:00Z']*3)
    for n in m.TRAINING:
        if n not in d:d[n]=0.
    for n in m.EXTRA:x[n]=.1
    xx,_=m.augment_control(d,x,b,o)
    def capture(rows,features,train,version):
        assert features[m.CORE_FEATURES].to_numpy(float).tobytes()==x[m.CORE_FEATURES].to_numpy(float).tobytes()
        return type('Frozen',(),{'metadata':{'captured':True}})()
    monkeypatch.setattr(m,'conditional_fit',capture)
    _,p,r=m.fit(d,xx,'conditional','F');assert p is None and r['metadata']['captured']
