"""Select approved evidence-backed model versions; never select by file date."""
import hashlib
import json
from pathlib import Path

REQUIRED_GATES=('development','audit_rmse','audit_season_stability','audit_mae','audit_block_interval','fixed_squad_points','full_scoring','current_season','integrity')

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def resolve_champion(root):
    root=Path(root);registry=json.loads((root/'model_registry.json').read_text())
    version=registry['champion'];record=registry['versions'][version]
    if record['status']!='approved':raise ValueError('Registry champion is not approved')
    path=(root/record['artifact']).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Model artifact must be inside the project model directory')
    if digest(path)!=record['sha256']:raise ValueError('Model hash mismatch; do not silently load another model')
    return path,version,record

def register_candidate(registry,experiment,path,hash_value,metrics):
    updated=json.loads(json.dumps(registry))
    updated.setdefault('experiments',{})[experiment]={'status':'candidate','artifact':path,'sha256':hash_value,'metrics':metrics}
    return updated

def approve(registry,version,artifact,sha256,evidence):
    gates=evidence.get('gates',{})
    failed=[k for k in REQUIRED_GATES if gates.get(k) is not True]
    if failed:raise ValueError('Promotion rejected: '+', '.join(failed))
    if version in registry['versions']:raise ValueError('Version IDs are immutable')
    old=registry['champion'];updated=json.loads(json.dumps(registry))
    updated['versions'][version]={'status':'approved','artifact':artifact,'sha256':sha256,'previous_champion':old,'evidence':evidence}
    updated['champion']=version
    return updated

def save_registry(root,registry):
    root=Path(root);target=root/'model_registry.json';tmp=root/'model_registry.json.tmp'
    tmp.write_text(json.dumps(registry,indent=2)+'\n');tmp.replace(target)
