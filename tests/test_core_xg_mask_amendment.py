import json
from pathlib import Path

def test_frozen_r2_amendment():
    c=json.loads((Path(__file__).parents[1]/'docs/core_xg_mask_protocol_amendment_2026-11-03.json').read_text())
    assert c['revision']=='cxm-r2' and c['identity']['tolerance']==1e-12
    assert len(c['identity']['columns'])==8 and c['identity']['both_finite']
    assert c['amends']['lf_sha256']=='faf466b268217634b4afce93eca879ac1ea3227ed567507673694380ea245d65'
    assert c['budget']['new_admission_jobs']==1
    assert c['budget']['fit_jobs_B']==4 and c['budget']['fit_jobs_C']==2
    assert c['budget']['real_retries']==c['budget']['retrievals']==0
