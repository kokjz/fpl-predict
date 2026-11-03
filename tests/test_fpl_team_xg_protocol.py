"""Constants-only preregistration contract, without real data."""
import hashlib
import json
from pathlib import Path
from fpl_model import CORE_FEATURES, estimator

def test_frozen_protocol():
    raw=(Path(__file__).resolve().parents[1]/'docs/fpl_team_xg_protocol_2026-11-03.json').read_bytes().replace(b'\r\n',b'\n')
    assert hashlib.sha256(raw).hexdigest()=='4a308b8666bd7e6992a856a0b0f91aba7c90eb4c4540bc3e44615f55150becb0'
    p=json.loads(raw)
    names=[f'{s}_ew{h}_{v}' for s in ('team','opp') for h in (4,12) for v in ('xg','xga')]
    assert p['new_features']==names
    assert p['features']=={'control':CORE_FEATURES,'team_xg':CORE_FEATURES+names}
    assert p['hgb_parameters']==estimator('hgb7').get_params()
    assert [(j['stage'],j['fold'],j['method']) for j in p['fit_order']]==[(s,f,m) for s,folds in [('B',['2023-24','2024-25']),('C',['2025-26'])] for f in folds for m in ['control','team_xg']]
    assert p['windows']['prior']==1.35 and p['windows']['prior_mass']==4
    assert p['stage_C']['retrievals']==0
