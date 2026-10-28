"""Offline frozen Stage-C build / one method-fold fit / fixed-prediction analysis.

Use the qualified receiving worker guard. Four exclusive fit slots, no retry,
no executable model output, no network, registry or operational forecast write.
"""
import argparse
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits, threadpool_info

from fpl_model import CORE_FEATURES, candidate_mask, estimator
import native_development as i4
from native_reference import environment
from market_stage_c import METHODS, FEATURES, market_rows, shared_proof, fit_predict, analyse, canonical_hash

PROTOCOL = Path(__file__).resolve().parents[1] / 'docs/market_strength_stage_c_protocol_2026-10-28.json'
PROTOCOL_SHA = '27954e78cb1a0151f7facc0e3e17df95549bec19da477b24700eeb6023bbf6d2'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified(entry):
    p = Path(entry['path'])
    if p.stat().st_size > 200_000_000 or digest(p) != entry['sha256']:
        raise ValueError('Input hash/size differs: ' + str(p))
    return p


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write('\n')


def save_npz(path, **arrays):
    with Path(path).open('xb') as f: np.savez_compressed(f, **arrays)


def protocol():
    raw = PROTOCOL.read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA: raise ValueError('Frozen protocol changed')
    cfg = json.loads(raw)
    if cfg['features'] != FEATURES or cfg['methods'] != list(METHODS): raise ValueError('Feature/method declaration differs')
    if cfg['hgb_parameters'] != estimator('hgb7').get_params(): raise ValueError('I4 parameters changed')
    for name, expected in cfg['references'].items():
        if hashlib.sha256((PROTOCOL.parent/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise ValueError('Referenced protocol differs')
    return cfg


def qualify_i4_sources(original, source_root=None):
    """Qualify executed I4 code, explicitly isolating later unused API wrappers."""
    root = Path(source_root) if source_root else Path(i4.__file__).parent
    exceptions = {
        'fpl_model.py':'92c837537621f78e99c2ba8ed39130137481d6c3f0cf7d7eedd673d20c6cce7c',
        'native_history.py':'f9f66a5e375137163315ff9813d55f4b7a7f4f8bcd5401854e7876ee0160ad65',
        'forecast.py':'8fd006ce27a013d140b79a7d2b0ddc957f3748849a8344014d7af364e7dbd635'}
    receipt = {}
    for name, expected in original.items():
        raw=(root/name).read_bytes().replace(b'\r\n',b'\n'); actual=hashlib.sha256(raw).hexdigest()
        receipt[name]=dict(original_lf_sha256=expected,receiving_lf_sha256=actual,whole_file_equal=actual==expected)
        if name not in exceptions:
            if actual!=expected: raise ValueError('I4 source differs: '+name)
            continue
        tree=ast.parse(raw)
        if name=='fpl_model.py':
            tree.body=[n for n in tree.body if not (isinstance(n,ast.ClassDef) and n.name=='ForecastModel')]
        elif name=='native_history.py':
            for node in tree.body:
                if isinstance(node,ast.ClassDef) and node.name=='NativeHistory':
                    node.body=[n for n in node.body if not (isinstance(n,ast.FunctionDef) and n.name in ['transform','transform_at_origins'])]
        else:
            tree=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['legal_squad','select_xi']],type_ignores=[])
        fingerprint=hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest()
        if fingerprint!=exceptions[name]: raise ValueError('Executed I4 source changed: '+name)
        receipt[name].update(executed_scope_ast_sha256=fingerprint,executed_scope_equal_original=True)
    return receipt


def build(manifest, output):
    cfg = protocol(); tick = time.monotonic()
    original = json.loads(verified(manifest['i4_manifest']).read_text(encoding='utf-8'))
    if canonical_hash(original['policy']) != cfg['input_panel_policy_sha256']:
        raise ValueError('I4 policy differs')
    # Original source remains immutable. Path/container adaptation is explicit.
    entries = manifest['inputs']
    for key in ['players','teams','provenance']:
        if entries[key]['sha256'] != original['inputs'][key]['sha256']: raise ValueError('Not original I4 input')
    compressed = verified(entries['control']); h = hashlib.sha256(); logical_bytes = 0
    with gzip.open(compressed, 'rb') as f:
        for block in iter(lambda: f.read(1024**2), b''):
            h.update(block); logical_bytes += len(block)
            if logical_bytes > 200_000_000: raise ValueError('Logical control exceeds input budget')
    if h.hexdigest() != original['inputs']['control']['sha256']:
        raise ValueError('I4 logical control cannot be reproduced')
    source_qualification = qualify_i4_sources(original['code'])
    with threadpool_limits(limits=2):
        p, _, c = i4.load(entries)
        panels = i4.panels(c)
        if panels != original['panels'] or canonical_hash(panels) != cfg['panels']['canonical_sha256']:
            raise ValueError('Original I4 squads cannot be reproduced')
        lambdas = json.loads(verified(manifest['lambdas']).read_text(encoding='utf-8'))
        m, evidence, origins = market_rows(p, lambdas)
    base = np.ascontiguousarray(c[CORE_FEATURES].to_numpy(dtype=np.float64))
    arrays = dict(X_control=base, X_market_strength=np.column_stack([base.copy(), m]),
        y=p.total_points.to_numpy(dtype=float), minutes=p.minutes.to_numpy(dtype=float),
        season=p.season.to_numpy(dtype=str), gameweek=p.gameweek.to_numpy(dtype=np.int64),
        fixture=p.fixture.to_numpy(dtype=np.int64), fpl_code=p.fpl_code.to_numpy(dtype=np.int64),
        cutoff_ns=pd.DatetimeIndex(p.deadline-pd.Timedelta(hours=3)).as_unit('ns').asi8,
        ts_ns=pd.DatetimeIndex(p.ts).as_unit('ns').asi8, candidate=candidate_mask(c).to_numpy(dtype=bool),
        element=c.element.to_numpy(dtype=np.int64), pos=c.pos.to_numpy(dtype=np.int64),
        n_history=c.n_history.to_numpy(dtype=float),
        cold_market_team=np.asarray([z['cold_start_team'] for z in evidence], dtype=bool),
        cold_market_opponent=np.asarray([z['cold_start_opponent'] for z in evidence], dtype=bool))
    proof = shared_proof(arrays)
    # Keep one source-clock receipt per fixture side, avoiding duplicate player records.
    unique = {}
    for r in evidence:
        key = (r['season'], r['fixture'], r['team'])
        if key in unique and unique[key] != r: raise ValueError('Player fixture origins differ')
        unique[key] = r
    if any(pd.Timestamp(z['source_max']) >= pd.Timestamp(z['cutoff']) for z in unique.values()):
        raise ValueError('Future market source')
    if Counter(z['season'] for z in unique.values()) != Counter({s:760 for s in ['2020-21','2021-22','2022-23','2023-24']}):
        raise ValueError('Missing fixture-side market cohort')
    # Same per-origin source clocks as accepted Stage B, without refitting its GLMs.
    stage_b = json.loads(verified(manifest['stage_b_metadata']).read_text(encoding='utf-8'))
    reference = {(z['season'],z['fixture'],z['team']):z for z in stage_b}
    for key, r in unique.items():
        if r['cutoff'] != reference[key]['cutoff'] or r['source_max'] != reference[key]['source_max']['market']:
            raise ValueError('StageB/C market origin/source clocks differ')
    save_npz(output/'bundle.npz', **arrays)
    write_json(output/'market-source-clocks.json', list(unique.values()))
    cold = {}
    for season in sorted(set(arrays['season'])):
        rows = arrays['season'] == season
        cold[season] = dict(rows=int(rows.sum()), candidate_rows=int(arrays['candidate'][rows].sum()),
            market_neutral_team_rows=int(arrays['cold_market_team'][rows].sum()),
            market_neutral_opponent_rows=int(arrays['cold_market_opponent'][rows].sum()),
            control_no_history_rows=int((arrays['n_history'][rows]==0).sum()),
            control_history_lt3_rows=int((arrays['n_history'][rows]<3).sum()))
    summary = dict(status='built', protocol_lf_sha256=PROTOCOL_SHA, proof=proof,
        bundle_sha256=digest(output/'bundle.npz'), rows_per_season=dict(Counter(arrays['season'])),
        cold_start_counts=cold, rating_origins=origins, source_max_checks=len(unique),
        panels=panels, panels_equal_original=True, logical_control_sha256=h.hexdigest(),
        logical_control_bytes=logical_bytes, inputs=manifest, original_environment=original['environment'],
        receiving_environment=environment(), source_qualification=source_qualification, preparation_seconds=time.monotonic()-tick,
        stage_C_method_fold_fits=0, scope='I4 core only + three raw market columns; identical nonmarket bytes; no later-season target/fit/score')
    write_json(output/'summary.json', summary)
    print(json.dumps(dict(status='built', rows=proof['rows'], rating_origins=origins, seconds=summary['preparation_seconds'])))


def load_bundle(bundle):
    cfg = protocol(); parent = json.loads((bundle.parent/'summary.json').read_text(encoding='utf-8'))
    if digest(bundle) != parent['bundle_sha256'] or parent['protocol_lf_sha256'] != PROTOCOL_SHA:
        raise ValueError('Frozen bundle differs')
    with np.load(bundle, allow_pickle=False) as z: arrays = {k:z[k] for k in z.files}
    if shared_proof(arrays) != parent['proof']: raise ValueError('Shared-cohort proof changed')
    return arrays, parent, cfg


def fit(bundle, fold, method, ledger, output):
    arrays, summary, cfg = load_bundle(bundle)
    if dict(fold=fold, method=method) not in cfg['fit_order']: raise ValueError('Undeclared fit')
    ordinal = cfg['fit_order'].index(dict(fold=fold, method=method)); ledger.mkdir(exist_ok=True)
    if len(list(ledger.glob('*.json'))) != ordinal: raise ValueError('Fit ledger order/count differs; no retry')
    for previous in sorted(ledger.glob('*.json')):
        if json.loads(previous.read_text(encoding='utf-8'))['status'] != 'completed': raise ValueError('Previous fit incomplete')
    token = ledger/f'{ordinal:02d}_{fold}_{method}.json'
    record = dict(status='attempted', ordinal=ordinal, fold=fold, method=method,
        protocol_lf_sha256=PROTOCOL_SHA, bundle_sha256=summary['bundle_sha256'])
    write_json(token, record)  # Reserve before any estimator fit. Never remove/reuse a token.
    with threadpool_limits(limits=2):
        prediction, timing = fit_predict(method, arrays, fold)
        pools = threadpool_info()
    if any(p['num_threads'] != 2 for p in pools): raise ValueError('Numerical thread limit differs')
    save_npz(output/'predictions.npz', prediction=prediction)
    result = dict(status='completed', fold=fold, method=method, timing=timing,
        threadpools=pools, proof_sha256=canonical_hash(summary['proof']), protocol_lf_sha256=PROTOCOL_SHA,
        bundle_sha256=summary['bundle_sha256'], predictions_sha256=digest(output/'predictions.npz'))
    write_json(output/'result.json', result)
    record.update(status='completed', result_sha256=digest(output/'result.json'))
    token.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='completed',fold=fold,method=method,**timing)))


def aggregate(build_dir, fits_dir, output):
    arrays, summary, cfg = load_bundle(build_dir/'bundle.npz'); predictions={}; timings={}
    for job in cfg['fit_order']:
        fold, method = job['fold'], job['method']; directory = fits_dir/(fold+'_'+method)
        record = json.loads((directory/'result.json').read_text(encoding='utf-8'))
        if record['status']!='completed' or record['bundle_sha256']!=summary['bundle_sha256'] or record['proof_sha256']!=canonical_hash(summary['proof']):
            raise ValueError('Fit source/cohort differs')
        if record['predictions_sha256']!=digest(directory/'predictions.npz'): raise ValueError('Predictions changed')
        with np.load(directory/'predictions.npz',allow_pickle=False) as z:
            predictions[(fold,method)] = z['prediction']
        timings[fold+'_'+method]=record['timing']
    with threadpool_limits(limits=2): result, frame = analyse(arrays,predictions,summary['panels'])
    frame.to_csv(output/'predictions.csv.gz',index=False,mode='x')
    result.update(status='completed', protocol_lf_sha256=PROTOCOL_SHA, proof=summary['proof'],
        timings=timings, cold_start_counts=summary['cold_start_counts'], method_fold_fits=4,
        scope='Development only; no later audits, season paths, promotion, registry or default changes')
    write_json(output/'report.json',result)
    print(json.dumps(dict(status='completed',gate_C_pass=result['gate']['passed'],method_fold_fits=4)))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['build','fit','aggregate'],required=True)
    for key in ['manifest','bundle','ledger','build-dir','fits-dir']:p.add_argument('--'+key,type=Path)
    p.add_argument('--fold');p.add_argument('--method');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    if a.phase=='build':build(json.loads(a.manifest.read_text(encoding='utf-8')),a.output)
    elif a.phase=='fit':fit(a.bundle,a.fold,a.method,a.ledger,a.output)
    else:aggregate(a.build_dir,a.fits_dir,a.output)


if __name__=='__main__':main()
