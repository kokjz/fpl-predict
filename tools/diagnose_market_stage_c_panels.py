"""Bounded no-fit I4 panel regeneration and structured comparison only."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits,threadpool_info

import native_development as i4
from panel_diagnostic import canonical_bytes,panel_hash,compare_panels
from run_market_stage_c import verified,qualify_i4_sources,write_json

PROTOCOL=ROOT/'docs/market_strength_stage_c_panel_diagnostic_2026-10-28.json'
PROTOCOL_SHA='5cef97920b14bbc03ffcccee1d2f867427dfbbe624ce8ded2f141640b89fa14b'


def versions():
    return dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,sklearn=sklearn.__version__)


def protocol():
    raw=PROTOCOL.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(raw).hexdigest()!=PROTOCOL_SHA:raise ValueError('Frozen diagnostic protocol differs')
    cfg=json.loads(raw);ref=cfg['references']
    stage_c=ROOT/'docs/market_strength_stage_c_protocol_2026-10-28.json'
    if hashlib.sha256(stage_c.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=ref['stage_c_protocol_lf_sha256']:
        raise ValueError('Frozen StageC protocol differs')
    helper=Path(__file__).with_name('run_market_stage_c.py')
    if hashlib.sha256(helper.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=ref['verified_loader_lf_sha256']:
        raise ValueError('Verified StageC loader/source qualification differs')
    return cfg,json.loads(stage_c.read_text(encoding='utf-8'))


def load_and_regenerate(manifest,cfg,stage_c):
    original=json.loads(verified(manifest['i4_manifest']).read_text(encoding='utf-8'))
    if panel_hash(original['panels'])!=cfg['references']['original_i4_panels_canonical_sha256']:
        raise ValueError('Original panel fixture differs')
    if hashlib.sha256(canonical_bytes(original['policy'])).hexdigest()!=stage_c['input_panel_policy_sha256']:
        raise ValueError('Original I4 policy differs')
    entries=manifest['inputs']
    if set(entries)!={'players','teams','control','provenance'}:raise ValueError('Input entries differ')
    for key in entries:
        if original['inputs'][key]['sha256']!=stage_c['input_manifest_original_inputs'][key]['sha256']:
            raise ValueError('Not the frozen original I4 input')
        if key!='control' and entries[key]['sha256']!=original['inputs'][key]['sha256']:
            raise ValueError('Receiving input differs')
    compressed=verified(entries['control']);h=hashlib.sha256();logical_bytes=0
    with gzip.open(compressed,'rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):
            h.update(block);logical_bytes+=len(block)
            if logical_bytes>200_000_000:raise ValueError('Logical control input budget')
    if h.hexdigest()!=original['inputs']['control']['sha256']:raise ValueError('Logical I4 control differs')
    source=qualify_i4_sources(original['code'])
    # Same verified I4 load/panels calls as the failed build, once. No transform,
    # market_rows, feature matrix, estimator fit, prediction or evaluation call.
    with threadpool_limits(limits=2):
        p,t,c=i4.load(entries)
        panels=i4.panels(c)
        pools=threadpool_info()
    if any(x['num_threads']!=2 for x in pools):raise ValueError('Numerical thread limit differs')
    receipt=dict(logical_control_sha256=h.hexdigest(),logical_control_bytes=logical_bytes,
        source_qualification=source,original_environment=original['environment'],
        admitted_input_rows=dict(players=len(p),teams=len(t),control=len(c)),threadpools=pools)
    return original['panels'],panels,receipt


def diagnose(manifest,run_id,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if any((output/name).exists() for name in ['panels.canonical.json','diagnostic.json','comparison.json']):
        raise ValueError('Diagnostic output exists; no retry')
    tick=time.monotonic();record=dict(run_id=run_id,protocol_lf_sha256=PROTOCOL_SHA,
        stage_C_fit_attempts=0,market_rows=False,feature_matrix=False,prediction=False,score=False,
        scope='Panel diagnostic only; original fixed fixture and StageC equality rule unchanged')
    phase='qualification'
    try:
        cfg,stage_c=protocol();run=next(r for r in cfg['runs'] if r['id']==run_id)
        actual=versions()
        if actual!=run['expected']:raise ValueError('Receiving runtime differs from declared run')
        record['runtime']=actual;phase='load_and_panels'
        original,regenerated,receipt=load_and_regenerate(manifest,cfg,stage_c)
        record.update(receipt)
        phase='persist_panels'
        raw=canonical_bytes(regenerated)
        with (output/'panels.canonical.json').open('xb') as f:f.write(raw)
        record['panels_canonical_sha256']=hashlib.sha256(raw).hexdigest()
        with (output/'panels.sha256').open('x',encoding='utf-8') as f:f.write(record['panels_canonical_sha256']+'\n')
        phase='compare'
        comparison=compare_panels(original,regenerated,cfg['relative_tolerance'])
        write_json(output/'comparison.json',comparison)
        record.update(status='completed',classification=comparison['classification'],
            original_panels_canonical_sha256=panel_hash(original),comparison_sha256=hashlib.sha256((output/'comparison.json').read_bytes()).hexdigest(),
            elapsed_seconds=time.monotonic()-tick)
        write_json(output/'diagnostic.json',record)
        print(json.dumps({k:record[k] for k in ['run_id','status','classification','panels_canonical_sha256','elapsed_seconds']}),flush=True)
        return True
    except Exception as error:
        record.update(status='cannot_run',classification='C',phase=phase,error=repr(error),
            traceback=traceback.format_exc(),elapsed_seconds=time.monotonic()-tick)
        write_json(output/'diagnostic.json',record)
        print(json.dumps(dict(run_id=run_id,status='cannot_run',classification='C',phase=phase,error=repr(error))),flush=True)
        return False


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--run',choices=['D1','D2'],required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not diagnose(json.loads(a.manifest.read_text(encoding='utf-8')),a.run,a.output):raise SystemExit(2)


if __name__=='__main__':main()
