"""Synthetic contracts for the single capacity arm."""
import hashlib
import json
from pathlib import Path


def test_frozen_capacity_protocol():
    p=Path(__file__).resolve().parents[1]/'docs/fpl_native_capacity_protocol_2026-11-02.json'
    raw=p.read_bytes().replace(b'\r\n',b'\n')
    assert hashlib.sha256(raw).hexdigest()=='408c348c3a3d67802521363ab2cef3afda5f08a8d1780d5cc69aea2de3f39877'
    cfg=json.loads(raw)
    from fpl_model import estimator
    import fpl_native_combination as previous
    assert cfg['features']==dict(control=previous.FEATURES['control'],capacity=previous.UNION)
    assert cfg['hgb_parameters']=={m:estimator(s).get_params() for m,s in [('control','hgb7'),('capacity','hgb15')]}
    assert len(cfg['fit_order'])==8
    assert cfg['stage_C']['retrieval']['attempts']==1


def capacity_bundle():
    from test_fpl_native_combination import native_bundle
    a=native_bundle();a['X_capacity']=a.pop('X_fpl_native')
    return a


def test_spec_and_unchanged_control(monkeypatch):
    import numpy as np
    import fpl_native_capacity as cap
    from fpl_model import estimator
    a=capacity_bundle();specs=[]
    class Model:
        def __init__(self,spec):self.spec=spec
        def fit(self,x,y,sample_weight):return self
        def predict(self,x):return np.ones(len(x))
        def get_params(self):return estimator(self.spec).get_params()
    def make(spec):specs.append(spec);return Model(spec)
    monkeypatch.setattr(cap,'estimator',make)
    control,ci=cap.fit_predict(a,'2022-23','control')
    candidate,ni=cap.fit_predict(a,'2022-23','capacity')
    assert specs==['hgb7','hgb15']
    assert ni['parameters']==estimator('hgb15').get_params()
    assert ci['parameters']==estimator('hgb7').get_params()
    assert cap.control_parity(control,candidate)['passed']
    assert cap.previous.estimator is estimator


def test_byte_identity_and_control_parity_negative_cases():
    import numpy as np
    import pytest
    import fpl_native_capacity as cap
    from market_stage_c import array_hash
    x=np.array([[1.,np.nan],[2.,3.]])
    assert cap.union_identity(x,array_hash(x))['passed']
    with pytest.raises(ValueError,match='union byte'):cap.union_identity(x,'bad')
    assert cap.control_parity(x,x.copy())['passed']
    other=x.copy();other[0,0]+=1
    with pytest.raises(ValueError,match='control prediction'):cap.control_parity(x,other)


def test_gate_reuse_and_hgb7_diagnostic(monkeypatch):
    import numpy as np
    import fpl_native_capacity as cap
    a=capacity_bundle()
    pred={(f,m):np.arange(8,dtype=float)+(.1 if m=='control' else 0) for f in cap.DEVELOPMENT for m in cap.METHODS}
    monkeypatch.setattr(cap.i4,'replay',lambda z,p,m:{name:dict(mean_total=100.+(name!='control')) for name in m})
    panels={f:dict(first_gw=4,squads=[[],[]]) for f in cap.DEVELOPMENT}
    report,_=cap.analyse(a,pred,panels,cap.DEVELOPMENT)
    expected,_=cap.previous.analyse(cap.original_arrays(a),{(f,'fpl_native' if m=='capacity' else m):v for (f,m),v in pred.items()},panels,cap.DEVELOPMENT)
    assert report['gate']==expected['gate'] and report['gate']['passed']
    assert report['metrics']['capacity']==expected['metrics']['fpl_native']
    diag=cap.hgb7_increment(a,pred,{f:pred[(f,'control')] for f in cap.DEVELOPMENT},panels)
    assert diag['descriptive'] and diag['new_fits']==0 and 'gate' not in diag


def test_later_seasons_excluded():
    import numpy as np
    import pytest
    import fpl_native_capacity as cap
    for season in ['2026-27','2027-28']:
        with pytest.raises(ValueError):cap.fold_masks(np.array([season]),'2025-26')
        with pytest.raises(ValueError):cap.scoped_confirmation(season)
