"""Frozen compliant signal union; research only, with no product writes."""
import types
import numpy as np
import pandas as pd
from fpl_model import CORE_FEATURES, estimator
import fpl_native_combination as native
import fpl_crowd_signal as crowd
from market_stage_c import MARKET_FEATURES, canonical_hash

SEASONS=crowd.SEASONS
DEVELOPMENT=crowd.DEVELOPMENT
AUDITS=crowd.AUDITS
METHODS=('control','union')
UNION=list(dict.fromkeys([*CORE_FEATURES,*native.NATIVE,*MARKET_FEATURES,*crowd.NEW_FEATURES]))
FEATURES=dict(control=CORE_FEATURES,union=UNION)
FEATURE_SHA256=canonical_hash(UNION)
KEYS=['season','fixture','fpl_code']
fold_masks=crowd.fold_masks
gate_details=crowd.gate_details

def keyed_join(control,block,names):
    """Reject an incorrectly ordered producer, then join explicitly by identity."""
    for f in (control,block):
        if f[KEYS].isna().any().any() or f.duplicated(KEYS).any():raise ValueError('Ambiguous block keys')
    left=pd.MultiIndex.from_frame(control[KEYS]);right=pd.MultiIndex.from_frame(block[KEYS])
    if not left.equals(right):raise ValueError('Block key order/coverage differs')
    if 'cutoff' in block:
        if not np.array_equal(pd.to_datetime(control.cutoff,utc=True),pd.to_datetime(block.cutoff,utc=True)):raise ValueError('Block cutoff differs')
    joined=control[KEYS].merge(block[KEYS+names],on=KEYS,how='left',validate='one_to_one',sort=False)
    return pd.DataFrame(joined[names].to_numpy(),index=control.index,columns=names)

def union(control,native_block,market_block,crowd_block):
    parts=[control[CORE_FEATURES]]
    for block,names in [(native_block,native.NATIVE),(market_block,MARKET_FEATURES),(crowd_block,crowd.NEW_FEATURES)]:
        parts.append(keyed_join(control,block,[n for n in names if n not in CORE_FEATURES]))
    result=pd.concat(parts,axis=1)[UNION]
    if np.ascontiguousarray(result[CORE_FEATURES].to_numpy(float)).tobytes()!=control[CORE_FEATURES].to_numpy(float).tobytes():raise ValueError('Control prefix differs')
    if not np.isfinite(result[MARKET_FEATURES+crowd.NEW_FEATURES].to_numpy(float)).all():raise ValueError('Nonfinite market/crowd')
    if np.isinf(result.to_numpy(float)).any():raise ValueError('Infinite union')
    return result

def static_audit():
    return dict(passed=True,native=native.static_audit(),crowd=crowd.static_audit(),features=UNION,feature_sha256=FEATURE_SHA256)

def shared_proof(a,folds):
    fn=types.FunctionType(native.shared_proof.__code__,dict(native.__dict__,UNION=UNION,fold_masks=fold_masks,SEASONS=SEASONS))
    # The native proof requires the final three columns to be finite. Check both
    # finite blocks explicitly as the union ends with crowd, rather than market.
    z=a['X_union']
    if not np.isfinite(z[:,[UNION.index(n) for n in MARKET_FEATURES+crowd.NEW_FEATURES]]).all():raise ValueError('Nonfinite market/crowd')
    return fn(dict(a,X_fpl_native=z),folds)

def fit_predict(a,fold,method):
    fn=types.FunctionType(native.fit_predict.__code__,dict(native.__dict__,METHODS=METHODS,FEATURES=FEATURES,shared_proof=shared_proof,fold_masks=fold_masks,estimator=estimator))
    return fn(a,fold,method)

def retrieval_allowed(gate_b,attempts,season='2025-26'):
    if gate_b is not True or attempts!=0 or season!='2025-26':raise ValueError('Retrieval refused')
    return 'https://www.football-data.co.uk/mmz4281/2526/E0.csv'

def analyse(a,predictions,panels,folds):
    shared_proof(a,folds)
    previous=crowd.previous;evaluation=previous.evaluation
    fn=types.FunctionType(evaluation.analyse.__code__,dict(evaluation.__dict__,FOLDS=folds,shared_proof=lambda _:shared_proof(a,folds),gate_details=gate_details if tuple(folds)==DEVELOPMENT else lambda *args:dict(passed=None,criteria={})))
    report,z=fn(dict(a,X_combined=a['X_union']),{(f,'combined' if m=='union' else m):p for (f,m),p in predictions.items()},panels)
    report=previous.rename(report,'combined','union');z=z.rename(columns={'combined':'union'})
    if tuple(folds)==AUDITS:
        for n in ('total_points','dc_rate4'):z[n]=a[n][a['season']=='2025-26']
        full=native.full_scoring(z.rename(columns={'union':'fpl_native'}))
        gates=types.FunctionType(native.audit_gates.__code__,dict(native.__dict__,AUDITS=AUDITS))
        report['gate']=previous.rename(gates(previous.rename(report['metrics'],'union','fpl_native'),previous.rename(report['folds'],'union','fpl_native'),report['paired']['union'],report['pooled_fixed_squad_delta'],full),'fpl_native','union')
        report['full_scoring']=previous.rename(full,'fpl_native','union')
    return report,z
