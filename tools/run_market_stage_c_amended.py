"""Stage-C amendment1 entry point; original strict build remains unchanged."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

import run_market_stage_c as strict
from market_stage_c_amendment import original_fixture,FixtureGuardError
from panel_diagnostic import panel_hash

AMENDMENT=ROOT/'docs/market_strength_stage_c_amendment1_2026-10-28.json'
AMENDMENT_SHA='7ea774a75b7c82c93c23d7aa56052cd0460c405a7bbae992aa085a8e9f2eaa69'


def amendment():
    raw=AMENDMENT.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(raw).hexdigest()!=AMENDMENT_SHA:raise ValueError('Frozen amendment differs')
    cfg=json.loads(raw);ref=cfg['references']
    paths={ROOT/'docs/market_strength_stage_c_protocol_2026-10-28.json':ref['stage_c_protocol_lf_sha256'],
           ROOT/'docs/market_strength_stage_c_panel_diagnostic_2026-10-28.json':ref['panel_diagnostic_protocol_lf_sha256'],
           ROOT/'src/panel_diagnostic.py':ref['frozen_diagnostic_comparator_lf_sha256'],
           ROOT/'tools/run_market_stage_c.py':ref['strict_stage_c_tool_lf_sha256'],
           ROOT/'src/market_stage_c.py':ref['stage_c_numeric_module_lf_sha256']}
    for path,expected in paths.items():
        if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=expected:
            raise ValueError('Referenced frozen source/protocol differs: '+path.name)
    return cfg


def legacy_runtime():
    actual=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,sklearn=sklearn.__version__)
    if actual!=dict(python='3.12.16',numpy='2.3.5',pandas='2.2.3',sklearn='1.9.1'):
        raise ValueError('Require qualified legacy runtime')
    return actual


def load_original(manifest,cfg):
    original=json.loads(strict.verified(manifest['i4_manifest']).read_text(encoding='utf-8'))
    if strict.canonical_hash(original['policy'])!=cfg['input_panel_policy_sha256']:raise ValueError('I4 policy differs')
    entries=manifest['inputs']
    for key in ['players','teams','provenance']:
        if entries[key]['sha256']!=original['inputs'][key]['sha256']:raise ValueError('Not original I4 input')
    compressed=strict.verified(entries['control']);h=hashlib.sha256();size=0
    with gzip.open(compressed,'rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):
            h.update(block);size+=len(block)
            if size>200_000_000:raise ValueError('Logical control input budget')
    if h.hexdigest()!=original['inputs']['control']['sha256']:raise ValueError('Logical original control differs')
    source=strict.qualify_i4_sources(original['code'])
    return original,entries,h.hexdigest(),size,source


def guarded_load(manifest,output,cfg,amended):
    original,entries,logical_sha,logical_bytes,source=load_original(manifest,cfg)
    expected=amended['references']['original_i4_panel_canonical_sha256']
    # Validate the immutable fixture before regeneration or any feature work.
    if panel_hash(original['panels'])!=expected:
        receipt=dict(status='blocked',reason='original_fixture_hash',expected_original_sha256=expected,
                     actual_original_sha256=panel_hash(original['panels']))
        strict.write_json(output/'panel-consistency.json',receipt)
        raise FixtureGuardError('Original I4 fixture hash differs',receipt)
    p,t,c=strict.i4.load(entries)
    regenerated=strict.i4.panels(c)  # Exactly once, as the amendment consistency guard.
    try:
        fixture,receipt=original_fixture(original['panels'],regenerated,expected)
    except FixtureGuardError as error:
        strict.write_json(output/'panel-consistency.json',error.receipt)
        raise
    strict.write_json(output/'panel-consistency.json',receipt)
    return p,t,c,fixture,logical_sha,logical_bytes,source,receipt


def build(manifest,output):
    amended=amendment();runtime=legacy_runtime();cfg=strict.protocol();tick=time.monotonic()
    with threadpool_limits(limits=2):
        p,_,c,panels,logical_sha,logical_bytes,source,receipt=guarded_load(manifest,output,cfg,amended)
        lambdas=json.loads(strict.verified(manifest['lambdas']).read_text(encoding='utf-8'))
        m,evidence,origins=strict.market_rows(p,lambdas)
    # Same feature/target/cohort construction as the preserved strict build.
    base=np.ascontiguousarray(c[strict.CORE_FEATURES].to_numpy(dtype=np.float64))
    arrays=dict(X_control=base,X_market_strength=np.column_stack([base.copy(),m]),
        y=p.total_points.to_numpy(dtype=float),minutes=p.minutes.to_numpy(dtype=float),
        season=p.season.to_numpy(dtype=str),gameweek=p.gameweek.to_numpy(dtype=np.int64),
        fixture=p.fixture.to_numpy(dtype=np.int64),fpl_code=p.fpl_code.to_numpy(dtype=np.int64),
        cutoff_ns=pd.DatetimeIndex(p.deadline-pd.Timedelta(hours=3)).as_unit('ns').asi8,
        ts_ns=pd.DatetimeIndex(p.ts).as_unit('ns').asi8,candidate=strict.candidate_mask(c).to_numpy(dtype=bool),
        element=c.element.to_numpy(dtype=np.int64),pos=c.pos.to_numpy(dtype=np.int64),n_history=c.n_history.to_numpy(dtype=float),
        cold_market_team=np.asarray([z['cold_start_team'] for z in evidence],dtype=bool),
        cold_market_opponent=np.asarray([z['cold_start_opponent'] for z in evidence],dtype=bool))
    proof=strict.shared_proof(arrays)
    unique={}
    for r in evidence:
        key=(r['season'],r['fixture'],r['team'])
        if key in unique and unique[key]!=r:raise ValueError('Player fixture origins differ')
        unique[key]=r
    if any(pd.Timestamp(z['source_max'])>=pd.Timestamp(z['cutoff']) for z in unique.values()):raise ValueError('Future market source')
    if Counter(z['season'] for z in unique.values())!=Counter({s:760 for s in ['2020-21','2021-22','2022-23','2023-24']}):
        raise ValueError('Missing fixture-side market cohort')
    stage_b=json.loads(strict.verified(manifest['stage_b_metadata']).read_text(encoding='utf-8'))
    reference={(z['season'],z['fixture'],z['team']):z for z in stage_b}
    for key,r in unique.items():
        if r['cutoff']!=reference[key]['cutoff'] or r['source_max']!=reference[key]['source_max']['market']:
            raise ValueError('StageB/C market origin/source clocks differ')
    strict.save_npz(output/'bundle.npz',**arrays)
    strict.write_json(output/'market-source-clocks.json',list(unique.values()))
    cold={}
    for season in sorted(set(arrays['season'])):
        rows=arrays['season']==season
        cold[season]=dict(rows=int(rows.sum()),candidate_rows=int(arrays['candidate'][rows].sum()),
            market_neutral_team_rows=int(arrays['cold_market_team'][rows].sum()),market_neutral_opponent_rows=int(arrays['cold_market_opponent'][rows].sum()),
            control_no_history_rows=int((arrays['n_history'][rows]==0).sum()),control_history_lt3_rows=int((arrays['n_history'][rows]<3).sum()))
    summary=dict(status='built',protocol_lf_sha256=strict.PROTOCOL_SHA,amendment_lf_sha256=AMENDMENT_SHA,proof=proof,
        bundle_sha256=strict.digest(output/'bundle.npz'),rows_per_season=dict(Counter(arrays['season'])),
        cold_start_counts=cold,rating_origins=origins,source_max_checks=len(unique),panels=panels,
        panels_source='original hash-verified I4 manifest verbatim',original_fixture_sha256=panel_hash(panels),
        panel_consistency_sha256=strict.digest(output/'panel-consistency.json'),panel_consistency_class=receipt['comparison']['classification'],
        logical_control_sha256=logical_sha,logical_control_bytes=logical_bytes,inputs=manifest,
        receiving_environment=runtime,source_qualification=source,preparation_seconds=time.monotonic()-tick,
        stage_C_method_fold_fits=0,scope='Original fixture; all numerical methods/cohort/gates unchanged from StageC')
    strict.write_json(output/'summary.json',summary)
    print(json.dumps(dict(status='built',rows=proof['rows'],panel_class='A',seconds=summary['preparation_seconds'])),flush=True)


def context(build_dir):
    cfg=amendment();summary=json.loads((build_dir/'summary.json').read_text(encoding='utf-8'))
    receipt=json.loads((build_dir/'panel-consistency.json').read_text(encoding='utf-8'))
    expected=cfg['references']['original_i4_panel_canonical_sha256']
    if summary['amendment_lf_sha256']!=AMENDMENT_SHA or panel_hash(summary['panels'])!=expected:
        raise ValueError('Original shared fixture/amendment differs')
    if receipt['status']!='accepted' or receipt['comparison']['classification']!='A' or strict.digest(build_dir/'panel-consistency.json')!=summary['panel_consistency_sha256']:
        raise ValueError('Fixture consistency guard differs')
    return dict(amendment_lf_sha256=AMENDMENT_SHA,original_fixture_sha256=expected,
        build_summary_sha256=strict.digest(build_dir/'summary.json'),panel_consistency_sha256=summary['panel_consistency_sha256'])


def aggregate(build_dir,fits_dir,output):
    ctx=context(build_dir)
    cfg=strict.protocol()
    for job in cfg['fit_order']:
        p=fits_dir/(job['fold']+'_'+job['method'])/'amendment-context.json'
        if json.loads(p.read_text(encoding='utf-8'))!=ctx:raise ValueError('Fit fixture/amendment context differs')
    strict.aggregate(build_dir,fits_dir,output)
    report=json.loads((output/'report.json').read_text(encoding='utf-8'))
    delta=[v for fold in strict.i4.FOLDS for v in report['points'][fold]['market_strength']['deltas']]
    strict.write_json(output/'summary-extension.json',dict(**ctx,original_report_sha256=strict.digest(output/'report.json'),
        pooled_fixed_squad_delta=dict(mean=report['pooled_fixed_squad_delta'],minimum=min(delta),maximum=max(delta),panels=len(delta),
            mean_definition='unchanged I4 mean of two20-panel fold means; min/max over40 panel deltas')))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['build','fit','aggregate'],required=True)
    for key in ['manifest','bundle','ledger','build-dir','fits-dir']:p.add_argument('--'+key,type=Path)
    p.add_argument('--fold');p.add_argument('--method');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    amendment();legacy_runtime();a.output.mkdir(parents=True,exist_ok=True)
    if a.phase=='build':build(json.loads(a.manifest.read_text(encoding='utf-8')),a.output)
    elif a.phase=='fit':
        ctx=context(a.bundle.parent);strict.write_json(a.output/'amendment-context.json',ctx)
        strict.fit(a.bundle,a.fold,a.method,a.ledger,a.output)
    else:aggregate(a.build_dir,a.fits_dir,a.output)


if __name__=='__main__':main()
