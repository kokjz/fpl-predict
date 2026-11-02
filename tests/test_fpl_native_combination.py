"""Synthetic checks for the frozen compliant combination."""
import hashlib
import json
from pathlib import Path

from fpl_model import CORE_FEATURES
from native_development import FPL
from market_stage_c import MARKET_FEATURES, canonical_hash


def test_protocol_contract():
    path=Path(__file__).resolve().parents[1]/'docs/fpl_native_combination_protocol_2026-11-02.json'
    raw=path.read_bytes().replace(b'\r\n',b'\n')
    assert hashlib.sha256(raw).hexdigest()=='a6760823ffd6b145fc7e332d21a83ffde8bf26eea6e0448fa987525987b1d188'
    cfg=json.loads(raw)
    union=list(dict.fromkeys([*CORE_FEATURES,*FPL,*MARKET_FEATURES]))
    assert cfg['features']==dict(control=CORE_FEATURES,fpl_native=union)
    assert cfg['feature_list_canonical_sha256']==canonical_hash(union)
    assert len(cfg['fit_order'])==8
    assert cfg['stage_C']['retrieval']['attempts']==1
    assert [j['stage'] for j in cfg['fit_order']]==['B']*4+['C']*4
