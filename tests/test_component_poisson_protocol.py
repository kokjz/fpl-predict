"""Constants-only preregistration contract; no real datasets."""
import hashlib
import json
from pathlib import Path
from fpl_model import CORE_FEATURES, estimator

def test_frozen_protocol():
    p=Path(__file__).resolve().parents[1]/'docs/component_poisson_protocol_2026-11-03.json'
    raw=p.read_bytes().replace(b'\r\n',b'\n')
    assert hashlib.sha256(raw).hexdigest()=='2916312d24f9fc5033edaca494adb1d4b069cbf55ca5fa154ef2420f1ff8346d'
    c=json.loads(raw)
    assert c['hgb_parameters']==estimator('hgb7').get_params()
    assert c['features']=={m:CORE_FEATURES for m in ('control','components')}
    assert [j['stage'] for j in c['fit_order']]==['B']*4+['C']*4
    assert [v['loss'] for v in c['head_specs'].values()]==['poisson']*4+['squared_error']
    assert c['stage_C']['retrievals']==0
    assert c['rule_table']['goal']=={'1':6,'2':6,'3':5,'4':4}
    assert c['sidecar']['cache_sha256']['history']=='543924f895bb82e78de64275208ad313239e105624eed91c7c00917d7255970b'
