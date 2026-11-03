import json
from pathlib import Path

def test_frozen_protocol():
    p=json.loads((Path(__file__).parents[1]/'docs/fpl_crowd_signal_protocol_2026-11-03.json').read_text())
    assert p['revision']=='fcs-r1' and len(set(p['new_features']))==6
    assert p['gate']['pooled_rmse_ratio']==.995
    assert p['gate']['pooled_mae_ratio']==p['gate']['per_fold_rmse_ratio']==1.005
    assert p['resources']['retrievals']==p['resources']['retries']==0
    assert len(p['fit_order'])==6 and p['resources']['admission_jobs']==1
    assert p['seasons'][-1]=='2025-26'
