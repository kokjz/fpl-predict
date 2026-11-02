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
