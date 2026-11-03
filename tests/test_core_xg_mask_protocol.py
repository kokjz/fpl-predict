import json
from pathlib import Path

def test_frozen_protocol():
    p=json.loads((Path(__file__).parents[1]/'docs/core_xg_mask_protocol_2026-11-03.json').read_text())
    assert p['revision']=='cxm-r1' and len(p['columns'])==6
    assert p['gate']['pooled_rmse_ratio']==1.0
    assert p['gate']['pooled_mae_ratio']==p['gate']['per_fold_rmse_ratio']==1.005
    assert p['resources']['retries']==p['resources']['retrievals']==0
    assert len(p['fit_order'])==6
    assert all(len(v)==14 and {r['season'] for r in v}=={'2022-23'} for v in p['masking']['expected'].values())
