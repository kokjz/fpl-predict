"""Synthetic contract, keyed composition, omission and gate regressions."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import compliant_union as u
from test_fpl_native_combination import fixture

def test_frozen_contract():
    cfg=json.loads((Path(__file__).parents[1]/'docs/compliant_union_protocol_2026-11-04.json').read_text())
    assert cfg['features']==u.FEATURES and cfg['feature_sha256']==u.FEATURE_SHA256
    assert len(u.UNION)==204 and len(set(u.UNION))==204
    assert u.UNION[:49]==u.CORE_FEATURES
    assert u.static_audit()['passed']
    assert cfg['fit_order']==[dict(fold=f,method=m) for f in (*u.DEVELOPMENT,*u.AUDITS) for m in u.METHODS]

def frames():
    c=pd.DataFrame(dict(season=['2023-24']*2,fixture=[1,2],fpl_code=[10,20],cutoff=pd.to_datetime(['2023-08-01','2023-08-08'],utc=True)))
    for n in u.CORE_FEATURES:c[n]=np.array([.1,.2])
    blocks=[]
    for names in (u.native.NATIVE,u.MARKET_FEATURES,u.crowd.NEW_FEATURES):
        b=c[u.KEYS+['cutoff']].copy()
        b=pd.concat([b,pd.DataFrame({n:np.array([.3,.4]) for n in names})],axis=1)
        blocks.append(b)
    return c,blocks

def test_keyed_blocks_and_exact_prefix():
    c,bs=frames();x=u.union(c,*bs)
    assert x.columns.tolist()==u.UNION
    assert x[u.CORE_FEATURES].to_numpy().tobytes()==c[u.CORE_FEATURES].to_numpy().tobytes()
    for i in range(3):
        changed=list(bs);changed[i]=bs[i].iloc[::-1]
        with pytest.raises(ValueError,match='key order'):u.union(c,*changed)
        changed[i]=pd.concat([bs[i],bs[i].iloc[:1]])
        with pytest.raises(ValueError,match='Ambiguous'):u.union(c,*changed)
    bs[0].loc[0,'cutoff']+=pd.Timedelta(hours=1)
    with pytest.raises(ValueError,match='cutoff'):u.union(c,*bs)

def test_understat_ablation_full_union():
    p,t,_=fixture()
    c,bs=frames();c=c.iloc[np.arange(len(p))%2].reset_index(drop=True)
    c[u.KEYS]=p[u.KEYS].to_numpy();c['cutoff']=p.deadline.to_numpy()
    def builder(pp,tt):
        n,e=u.native.native_features(pp,tt)
        blocks=[]
        for values,names in [(n.to_numpy(float),u.native.NATIVE),(np.ones((len(p),3)),u.MARKET_FEATURES),(np.ones((len(p),6)),u.crowd.NEW_FEATURES)]:
            z=c[u.KEYS+['cutoff']].copy()
            z=pd.concat([z,pd.DataFrame(values,index=c.index,columns=names)],axis=1)
            blocks.append(z)
        return u.union(c,*blocks),e
    _,proof=u.native.ablation_invariance(p,t,builder)
    assert proof['feature_bytes_identical'] and proof['features']==204

def test_training_only_omission(monkeypatch):
    from test_fpl_team_xg import bundle
    a=bundle();a.pop('X_team_xg');a['X_union']=np.column_stack([a['X_control'],np.ones((len(a['y']),155))])
    train=a['season']<'2023-24';name=u.native.NATIVE[0];j=u.UNION.index(name)
    a['X_union'][train,j]=np.nan;a['X_union'][~train,j]=123.
    seen=[]
    class M:
        def fit(self,x,y,sample_weight):seen.extend(x.columns);return self
        def predict(self,x):return np.ones(len(x))
        def get_params(self):return {}
    monkeypatch.setattr(u,'estimator',lambda _:M())
    _,info=u.fit_predict(a,'2023-24','union')
    assert name not in seen and name in info['omitted_features']
    a['X_union'][0,0]=np.nextafter(a['X_union'][0,0],np.inf)
    with pytest.raises(ValueError,match='CORE bytes'):u.shared_proof(a,u.DEVELOPMENT)

def test_gates_bounds_and_exclusions():
    control={k:dict(rmse=10.,mae=5.) for k in ('player_gw','fixture')};control['ndcg10']=.5
    candidate={k:dict(rmse=.995*10,mae=1.005*5) for k in ('player_gw','fixture')};candidate['ndcg10']=.5
    fc={f:{k:dict(rmse=10.) for k in ('candidate_player_gw','candidate_fixture')} for f in u.DEVELOPMENT}
    fn={f:{k:dict(rmse=1.005*10) for k in ('candidate_player_gw','candidate_fixture')} for f in u.DEVELOPMENT}
    assert u.gate_details(candidate,control,fn,fc,0)['passed']
    candidate['fixture']['rmse']=np.nextafter(.995*10,np.inf)
    assert not u.gate_details(candidate,control,fn,fc,0)['passed']
    with pytest.raises(ValueError):u.retrieval_allowed(False,0)
    with pytest.raises(ValueError):u.retrieval_allowed(True,1)
    assert u.retrieval_allowed(True,0).endswith('/2526/E0.csv')
    with pytest.raises(ValueError):u.fold_masks(np.array(['2026-27']),'2025-26')
    with pytest.raises(ValueError):u.fold_masks(np.array(['2025-26']),'2026-27')

def test_crowd_recorded_balance_bound():
    from test_core_xg_mask import history
    h=history();h['selected']=1000.;h['transfers_in']=3.;h['transfers_out']=1.;h['transfers_balance']=2.
    assert u.crowd.field_checks(h)['passed']
    first=h[h.season=='2020-21'].index[:1];h.loc[first,'transfers_balance']=9.
    assert not u.crowd.field_checks(h)['passed']
