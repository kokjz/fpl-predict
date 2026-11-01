import json
from pathlib import Path
from fpl_model import estimator, CORE_FEATURES
from rich_market_combination import COMBINED
from market_stage_c import canonical_hash

def test_preregistered_design_and_budget():
    p=json.loads((Path(__file__).parents[1]/'docs/rmc_promotion_evidence_protocol_2026-11-02.json').read_text())
    assert p['features']==dict(control=CORE_FEATURES,combined=COMBINED)
    assert p['combined_features_canonical_sha256']==canonical_hash(COMBINED)
    assert p['hgb_parameters']==estimator('hgb7').get_params()
    assert [(x['stage'],x['method'],x['test']) for x in p['fit_order']]==[(s,m,t) for s,t in [('B','2025-26'),('C','2026-27')] for m in ['control','combined']]
    assert p['cutoff_2026_27']=='2026-11-02T00:00:00Z'
    assert p['gates']['full_scoring']['window']['gameweeks']==list(range(28,39))
    assert p['gates']['full_scoring']['rmse_ratio_max']==1.005
    assert p['snapshot_observation']['gating'] is False
    assert len(p['retrievals'])==4
