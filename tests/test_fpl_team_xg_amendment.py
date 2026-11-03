"""Write-once amendment contract; constants only."""
import hashlib
import json
from pathlib import Path

def test_amendment_protocol():
    root=Path(__file__).resolve().parents[1]/'docs'
    raw=(root/'fpl_team_xg_protocol_amendment_2026-11-03.json').read_bytes().replace(b'\r\n',b'\n')
    assert hashlib.sha256(raw).hexdigest()=='2c6d7ee6ae025142bc35e5f2276b8d3a7d642369c3be4174aa6c1ee39a70c4b2'
    p=json.loads(raw)
    assert p['brief_revision']=='txg-r2'
    assert p['rule']['expected_gameweeks']==[1,2,3,4,5,6,8,9,10,11,12,13,14,15]
    assert p['budget']==dict(new_admission_jobs=1,fit_jobs_B=4,fit_jobs_C=2,stage_C_requires_B_pass=True)
    assert hashlib.sha256((root/p['amends']['file']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==p['amends']['lf_sha256']
