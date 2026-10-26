import hashlib,importlib.util,json
from pathlib import Path
import joblib
import pandas as pd
import pytest
spec=importlib.util.spec_from_file_location('handover_smoke',Path(__file__).parents[1]/'tools/handover_smoke.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class InventedModel:
    def predict(self,x,pos):return pd.DataFrame(dict(expected_points=x.value.to_numpy()+pos))


def test_smoke_requires_trust_hash_and_exact_numerical_shape(tmp_path):
    p=tmp_path/'invented.joblib';joblib.dump(InventedModel(),p)
    # The test class is executable trusted test data, not a real user's model.
    o=dict(schema_version=1,artifact_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),features=[dict(value=1.)],positions=[2],predictions=[dict(expected_points=3.)],rtol=1e-7,atol=1e-8);q=tmp_path/'oracle.json';q.write_text(json.dumps(o))
    with pytest.raises(ValueError,match='trust'):m.run(p,q)
    assert m.run(p,q,trust_local_model=True)['status']=='matched'
    o['predictions'][0]['expected_points']=4.;q.write_text(json.dumps(o))
    with pytest.raises(ValueError,match='mismatch'):m.run(p,q,trust_local_model=True)
    p.write_bytes(b'not a pickle')
    with pytest.raises(ValueError,match='checksum'):m.run(p,q,trust_local_model=True)
