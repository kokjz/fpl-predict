"""On-demand public API snapshots, with retry, hashes and no account operations."""
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
import urllib.request
from availability_evidence import observations

from runtime import workspace_root
ROOT = workspace_root()

def fetch(url):
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"personal-fpl-research/1.0"})
            return urllib.request.urlopen(req,timeout=45).read()
        except Exception:
            if attempt==2: raise
            time.sleep(1+attempt)

def main():
    tag=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')
    root=ROOT/'data'/'current'/tag;root.mkdir(parents=True,exist_ok=False)
    log=[]
    def save(endpoint,name):
        url='https://fantasy.premierleague.com/api/'+endpoint+'/'
        raw=fetch(url);obj=json.loads(raw);(root/name).write_bytes(raw)
        return obj,{'file':name,'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    b,m=save('bootstrap-static','bootstrap.json');log.append(m)
    evidence=observations(b,m)
    raw=(json.dumps(evidence,indent=2)+'\n').encode()
    (root/'availability_observations.json').write_bytes(raw)
    log.append({'file':'availability_observations.json','derived_from':'bootstrap.json',
                'sha256':hashlib.sha256(raw).hexdigest(),'retrieved_utc':m['retrieved_utc']})
    f,m=save('fixtures','fixtures.json');log.append(m)
    # All listed players, including zero-minute reserves, to avoid selection/survivorship filtering.
    (root/'players').mkdir()
    def player(p):
        return save(f'element-summary/{p["id"]}',f'players/{p["id"]}.json')[1]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for i,m in enumerate(pool.map(player,b['elements']),1):
            log.append(m)
            if i%100==0: print('histories saved',i,flush=True)
    manifest={'tag':tag,'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'files':log,'player_count':len(b['elements']),'fixture_count':len(f),'atomic':False}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'data'/'current'/'LATEST').write_text(tag+'\n')
    print('Complete snapshot',tag,'players',len(b['elements']),flush=True)

if __name__=='__main__':main()
