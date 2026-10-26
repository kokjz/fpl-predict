"""Check a transferred approved artifact against a synthetic origin-machine oracle.

No training/network/source changes. Executable pickle loading requires explicit
trust AND the separately verified artifact SHA256 from the supplied oracle.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path


def run(model_path,oracle_path,*,trust_local_model=False):
    if not trust_local_model:raise ValueError('Explicit trust required before model loading')
    oracle=json.loads(Path(oracle_path).read_text());p=Path(model_path)
    if oracle['schema_version']!=1 or hashlib.sha256(p.read_bytes()).hexdigest()!=oracle['artifact_sha256']:raise ValueError('Approved artifact checksum differs')
    os.environ.setdefault('LOKY_MAX_CPU_COUNT','2')
    import joblib
    import numpy as np
    import pandas as pd
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):
        model=joblib.load(p);out=model.predict(pd.DataFrame(oracle['features']),oracle['positions'])
    expected=pd.DataFrame(oracle['predictions'])
    if list(out)!=list(expected) or out.shape!=expected.shape or not np.isfinite(out.to_numpy()).all() or not np.allclose(out.to_numpy(),expected.to_numpy(),rtol=oracle['rtol'],atol=oracle['atol']):raise ValueError('Artifact prediction smoke mismatch; do not silently update oracle/tolerances')
    return dict(status='matched',rows=len(out),columns=list(out),artifact_sha256=oracle['artifact_sha256'],max_absolute_difference=float(np.max(np.abs(out.to_numpy()-expected.to_numpy()))),scope='Synthetic numerical/runtime compatibility only; not new forecast accuracy or promotion')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True);p.add_argument('--oracle',type=Path,required=True);p.add_argument('--trust-local-model',action='store_true');a=p.parse_args();print(json.dumps(run(a.model,a.oracle,trust_local_model=a.trust_local_model)))


if __name__=='__main__':main()
