"""Single pre-existing HGB15 arm on the unchanged compliant PR56 inputs.

Adapters keep PR56's proofs, evaluation and control fit unchanged. No global
state in the earlier study is modified.
"""
import types
import numpy as np
import fpl_native_combination as previous
from fpl_model import estimator
from market_stage_c import array_hash

METHODS=('control','capacity')
FEATURES=dict(control=previous.FEATURES['control'],capacity=previous.UNION)
DEVELOPMENT=previous.DEVELOPMENT
AUDITS=previous.AUDITS
SEASONS=previous.SEASONS
UNION=previous.UNION
PR56_UNION_SHA='8982656c751dd10b7c1e30dae1f93789d22edc45e2753ab150c0af1b79ca8990'

# Reuse the original whitelist and chronology implementations directly.
i4=previous.i4
rich=previous.rich
US_TEAM=previous.US_TEAM
static_audit=previous.static_audit
ablation_invariance=previous.ablation_invariance
native_features=previous.native_features
union=previous.union
fold_masks=previous.fold_masks
scoped_confirmation=previous.scoped_confirmation


def original_arrays(a):
    return {('X_fpl_native' if k=='X_capacity' else k):v for k,v in a.items()}


def shared_proof(a,folds):
    return previous.shared_proof(original_arrays(a),folds)


def union_identity(matrix,expected=PR56_UNION_SHA):
    actual=array_hash(matrix)
    if actual!=expected:raise ValueError('PR56 union byte identity differs')
    return dict(passed=True,array_sha256=actual,rows=len(matrix),features=matrix.shape[1])


def control_parity(actual,reference):
    if actual.dtype!=reference.dtype or actual.shape!=reference.shape or actual.tobytes()!=reference.tobytes():
        raise ValueError('PR56 control prediction bytes differ')
    return dict(passed=True,rows=len(actual),array_sha256=array_hash(actual))


def fit_predict(a,fold,method):
    if method not in METHODS:raise ValueError('Undeclared method')
    spec='hgb7' if method=='control' else 'hgb15'
    def selected_estimator(name):
        if name!='hgb7':raise ValueError('Unexpected original estimator')
        return estimator(spec)
    namespace=dict(previous.__dict__,estimator=selected_estimator)
    f=types.FunctionType(previous.fit_predict.__code__,namespace)
    return f(original_arrays(a),fold,'fpl_native' if method=='capacity' else method)


def renamed(v):
    if isinstance(v,dict):return {('capacity' if k=='fpl_native' else k):renamed(x) for k,x in v.items()}
    if isinstance(v,list):return [renamed(x) for x in v]
    return v


def analyse(a,predictions,panels,folds):
    report,z=previous.analyse(original_arrays(a),{(f,'fpl_native' if m=='capacity' else m):p for (f,m),p in predictions.items()},panels,folds)
    return renamed(report),z.rename(columns={'fpl_native':'capacity'})


def hgb7_increment(a,predictions,frozen_hgb7,panels):
    """Descriptive comparison only; the fixed hgb7 predictions are never fitted."""
    p={(f,m):(frozen_hgb7[f] if m=='control' else predictions[(f,m)]) for f in DEVELOPMENT for m in METHODS}
    report,_=analyse(a,p,panels,DEVELOPMENT)
    # Gate B is only defined against CORE control, not this diagnostic baseline.
    report.pop('gate',None)
    report.update(descriptive=True,baseline='frozen PR56 union hgb7',candidate='capacity hgb15',new_fits=0)
    return report
