import hashlib
import json
from pathlib import Path

def test_frozen_amendment():
    root=Path(__file__).parents[1]
    p=json.loads((root/'docs/fpl_crowd_signal_protocol_amendment_2026-11-03.json').read_text())
    assert p['revision']=='fcs-r2'
    assert p['amendment']['bound']['max_share_each_season']==.001
    assert p['amendment']['bound']['inclusive']
    original=(root/'docs'/p['original_protocol']['file']).read_bytes().replace(b'\r\n',b'\n')
    assert hashlib.sha256(original).hexdigest()==p['original_protocol']['lf_sha256']
    assert p['resources']['new_admission_jobs']==1
    assert p['resources']['real_retries']==p['resources']['retrievals']==0
