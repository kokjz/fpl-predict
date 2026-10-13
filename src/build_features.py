"""Rebuild time-safe feature cache from immutable historical inputs."""
import json
from pathlib import Path
import time
from fpl_model import load_history,FeatureStore,CORE_FEATURES

from runtime import workspace_root
ROOT = workspace_root()

def main():
    t=time.time();d,a=load_history(ROOT/'data/historical');x=FeatureStore(d).transform(d)
    assert ((x.source_max_ts.isna())|(x.source_max_ts<d.cutoff)).all()
    out=ROOT/'artifacts';out.mkdir(exist_ok=True)
    d.to_pickle(out/'history.pkl');x.to_pickle(out/'features.pkl')
    (out/'data_audit.json').write_text(json.dumps({'seasons':a,'rows':len(d),'features':CORE_FEATURES,'seconds':time.time()-t},indent=2)+'\n')
    print('Features built',len(d),'rows',round(time.time()-t,1),'seconds')

if __name__=='__main__':main()
