"""Frozen five-head research forecaster; no operational model writes."""
import ast
import csv
import gzip
import hashlib
import inspect
import io
import time
import types

import numpy as np
import pandas as pd
from fpl_model import CORE_FEATURES, estimator, sample_weights
from market_stage_c import array_hash, canonical_hash
import fpl_native_combination as previous

METHODS=('control','components')
DEVELOPMENT=previous.DEVELOPMENT
AUDITS=previous.AUDITS
SEASONS=previous.SEASONS
FEATURES={m:CORE_FEATURES for m in METHODS}
HEADS=('G','A','CS','B','R')
COMPONENTS=('goals_scored','assists','clean_sheets','bonus')
GOAL={1:6,2:6,3:5,4:4}
CS={1:4,2:4,3:1,4:0}
SIDECAR_KEYS=['season','GW','element','fixture','fpl_code']
SIDECAR_COLUMNS=[*SIDECAR_KEYS,'total_points','points_core','minutes',*COMPONENTS]
I4_COLUMNS=['season','gameweek','fixture','fpl_code','position','minutes','total_points',
            'goals_scored','assists','goals_conceded','saves','penalties_saved',
            'penalties_missed','yellow_cards','red_cards','own_goals','bonus','ts','deadline']
fold_masks=previous.fold_masks
control_parity=__import__('fpl_native_capacity').control_parity


def head_estimator(head):
    if head not in HEADS:raise ValueError('Undeclared head')
    return estimator('hgb7').set_params(loss='squared_error' if head=='R' else 'poisson')


def multipliers(pos):
    p=pd.Series(np.asarray(pos))
    if not p.isin(GOAL).all():raise ValueError('Invalid position')
    return p.map(GOAL).to_numpy(float),p.map(CS).to_numpy(float)


def contributions(heads,pos):
    h=np.asarray(heads,float)
    if h.shape!=(len(pos),5) or not np.isfinite(h).all():raise ValueError('Head shape/nonfinite')
    g,c=multipliers(pos)
    return h*np.column_stack([g,np.full(len(pos),3.),c,np.ones((len(pos),2))])


def targets(frame,pos):
    missing=set([*COMPONENTS,'points_core','minutes'])-set(frame)
    if missing:raise ValueError('Component gaps: '+','.join(sorted(missing)))
    h=frame[list(COMPONENTS)].to_numpy(float)
    if not np.isfinite(h).all() or (h<0).any() or (h!=np.floor(h)).any():
        raise ValueError('Components must be finite nonnegative integers')
    if not np.isin(h[:,2],[0,1]).all() or ((h[:,2]==1)&(frame.minutes.to_numpy()<60)).any():
        raise ValueError('Invalid FPL clean sheet')
    g,c=multipliers(pos);base=g*h[:,0]+3*h[:,1]+c*h[:,2]+h[:,3]
    y=frame.points_core.to_numpy(float);r=y-base
    result=np.column_stack([h,r])
    if not np.isfinite(y).all() or not np.array_equal(base+r,y):raise ValueError('Exact five-target sum')
    return result


def recombine(heads,pos):
    return np.clip(contributions(heads,pos).sum(axis=1),0,20)


def reconcile(p):
    """The frozen historical full-rule formula, on FPL fields only."""
    required=set(I4_COLUMNS)-{'gameweek','ts','deadline'}
    if required-set(p):raise ValueError('Reconciliation schema gaps')
    if p.duplicated(['season','fixture','fpl_code']).any():raise ValueError('Duplicate fixture key')
    gp,cs=multipliers(p.position)
    clean=(p.minutes.ge(60)&p.goals_conceded.eq(0)).to_numpy(float)
    return (np.where(p.minutes.ge(60),2.,np.where(p.minutes.gt(0),1.,0.))
            +gp*p.goals_scored.to_numpy(float)+3*p.assists.to_numpy(float)+cs*clean
            +np.floor(p.saves.to_numpy(float)/3)+5*p.penalties_saved.to_numpy(float)
            -2*p.penalties_missed.to_numpy(float)
            -np.where(p.position.isin([1,2]),np.floor(p.goals_conceded.to_numpy(float)/2),0.)
            -p.yellow_cards.to_numpy(float)-3*p.red_cards.to_numpy(float)
            -2*p.own_goals.to_numpy(float)+p.bonus.to_numpy(float))


def read_scoped(path,columns,seasons):
    """Project named allowed fields and season-filter before dtype parsing."""
    if not set(seasons)<=set(SEASONS):raise ValueError('Excluded later season')
    if any(n.startswith('us_') for n in columns):raise ValueError('Forbidden column')
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rt',newline='',encoding='utf-8-sig') as f:
        reader=csv.reader(f);header=next(reader)
        if len(set(header))!=len(header) or 'season' not in header:raise ValueError('CSV header')
        selected=[(i,n) for i,n in enumerate(header) if n in columns]
        buf=io.StringIO();writer=csv.writer(buf);writer.writerow([n for _,n in selected])
        si=header.index('season')
        for row in reader:
            if len(row)!=len(header):raise ValueError('Malformed CSV row')
            if row[si] in seasons:writer.writerow([row[i] for i,_ in selected])
    buf.seek(0)
    return pd.read_csv(buf)


def schema_preflight(players,control,history):
    gaps=[];tables={}
    required={'players':I4_COLUMNS,'control':[*CORE_FEATURES,'season','gameweek','fixture','fpl_code','element','minutes','points_core','total_points','pos','ts','cutoff','source_max_ts'],
              'history':[n for n in SIDECAR_COLUMNS if n!='fpl_code']}
    for name,frame in [('players',players),('control',control),('history',history)]:
        missing=sorted(set(required[name])-set(frame));tables[name]=dict(rows=len(frame),missing=missing)
        gaps.extend(dict(table=name,column=n,kind='missing_column') for n in missing)
        for n in set(required[name])&set(frame)-{'season','ts','deadline','cutoff','source_max_ts'}:
            if not pd.api.types.is_numeric_dtype(frame[n]):gaps.append(dict(table=name,column=n,kind='numeric_dtype_required'))
    return dict(passed=not gaps,gaps=gaps,tables=tables)


def sidecar(history,bridges,export,scope):
    """Same history indices/order and stable-code bridge as select_control."""
    d=scope(history)
    if not d.index.is_unique:raise ValueError('History index')
    for season in sorted(set(d.season)):
        b=bridges[season][['id','code']]
        if b.id.duplicated().any() or b.code.duplicated().any():raise ValueError('Ambiguous bridge')
        d.loc[d.season.eq(season),'fpl_code']=d.loc[d.season.eq(season),'element'].map(b.set_index('id').code)
    if d.fpl_code.isna().any():raise ValueError('Missing stable code')
    d['fpl_code']=d.fpl_code.astype(np.int64)
    s=d[SIDECAR_COLUMNS].copy()
    if s.duplicated(SIDECAR_KEYS).any():raise ValueError('Duplicate sidecar key')
    e=export.rename(columns={'gameweek':'GW'}).reset_index(drop=True)
    columns=[*SIDECAR_KEYS,'total_points','points_core','minutes']
    if len(s)!=len(e) or any(not np.array_equal(s[n].to_numpy(),e[n].to_numpy()) for n in columns):
        raise ValueError('Sidecar/export alignment')
    h=s[list(COMPONENTS)].to_numpy(float)
    if not np.isfinite(h).all() or (h!=np.floor(h)).any():raise ValueError('Component integer boundary')
    return s,dict(passed=True,rows=len(s),history_index_sha256=array_hash(d.index.to_numpy()),row_order_exact=True,columns_equal=columns,component_sha256=array_hash(h),boundary='unchanged integers in memory; original control CSV boundary unchanged')


def admission(players,control,s):
    """Accumulate per-season/position reconciliation and cross-check counts."""
    keys=['season','fixture','fpl_code']
    if any(f.duplicated(keys).any() for f in (players,control,s)):raise ValueError('Ambiguous fixture alignment')
    ix=pd.MultiIndex.from_frame(control[keys]);si=s.set_index(keys)
    if len(ix)!=len(si) or set(ix)!=set(si.index):raise ValueError('Sidecar coverage')
    s=si.reindex(ix).reset_index();h=targets(s,control.pos)
    pi=players.set_index(keys);matched=ix.isin(pi.index)
    if not matched.all():raise ValueError('Missing I4 development rows')
    p=pi.reindex(ix).reset_index()
    for n,cn in [('minutes','minutes'),('position','pos'),('total_points','total_points')]:
        if not np.array_equal(p[n].to_numpy(),control[cn].to_numpy()):raise ValueError('I4 control context')
    rec=reconcile(p);active=p.minutes.gt(0).to_numpy();ok=rec==control.points_core.to_numpy(float)
    equal={n:s[n].to_numpy()==p[n].to_numpy() for n in ('goals_scored','assists','bonus')}
    equal['clean_sheets']=s.clean_sheets.to_numpy()==(p.minutes.ge(60)&p.goals_conceded.eq(0)).to_numpy()
    groups={}
    for (season,pos),indices in control.groupby(['season','pos']).indices.items():
        i=np.asarray(indices);den=float(control.points_core.iloc[i].sum());r=h[i,4]
        groups.setdefault(season,{})[str(pos)]=dict(rows=len(i),played=int(active[i].sum()),reconciled_played=int((ok[i]&active[i]).sum()),unreconciled_played=int((~ok[i]&active[i]).sum()),sidecar_mismatches={n:int((~v[i]).sum()) for n,v in equal.items()},remainder_mean=float(r.mean()),remainder_points_sum=float(r.sum()),points_core_sum=den,remainder_share=float(r.sum()/den) if den else None)
    passed=bool(ok[active].all() and all(v.all() for v in equal.values()))
    return h,dict(passed=passed,rows=len(control),played=int(active.sum()),unreconciled_played=int((~ok&active).sum()),crosscheck_mismatches={n:int((~v).sum()) for n,v in equal.items()},groups=groups,remainder_share_definition='sum R / sum points_core over all rows within season/position; null if denominator zero',five_target_sum_exact=True)


def shared_proof(a,folds):
    n=len(a['y']);x=a['X_control']
    if x.shape!=(n,len(CORE_FEATURES)) or not np.isfinite(x).all():raise ValueError('CORE shape/nonfinite')
    if a['X_components'].dtype!=x.dtype or a['X_components'].tobytes()!=x.tobytes():raise ValueError('CORE bytes differ')
    keys=list(zip(*(a[k].tolist() for k in previous.i4.KEYS)))
    if len(set(keys))!=n or not (a['cutoff_ns']<a['ts_ns']).all():raise ValueError('Keys/clocks')
    for k in ('y','minutes','ts_ns','cutoff_ns'):
        if len(a[k])!=n or not np.isfinite(a[k]).all():raise ValueError('Shared targets/clocks')
    if not np.array_equal(a['candidate'],(x[:,CORE_FEATURES.index('n_history')]>=3)&(x[:,CORE_FEATURES.index('last5_minutes')]>=45)):raise ValueError('Candidates')
    context=pd.DataFrame({k:a[k] for k in ('season','gameweek','fpl_code','candidate','cutoff_ns')})
    if (context.groupby(['season','gameweek','fpl_code'])[['candidate','cutoff_ns']].nunique()!=1).any().any():raise ValueError('DGW context')
    h=a['targets']
    if not np.array_equal(contributions(h,a['pos']).sum(axis=1),a['y']):raise ValueError('Target sum')
    for fold in folds:
        train,test=fold_masks(a['season'],fold)
        if set(a['season'][train])!=set(SEASONS[:SEASONS.index(fold)]) or not test.any():raise ValueError('Fold coverage')
        if a['ts_ns'][train].max()>=a['cutoff_ns'][test].min():raise ValueError('Labels cross fold')
        weights=sample_weights(pd.DataFrame({'ts':pd.to_datetime(a['ts_ns'][train],utc=True)}))
        if weights.tobytes()!=a['weights_'+fold].tobytes():raise ValueError('Age weights')
    hashes={k:array_hash(v) for k,v in sorted(a.items())}
    return dict(rows=n,core_bytes_identical=True,shared_keys_cohort_cutoffs_weights_evaluation_targets=True,hashes=hashes,proof_sha256=canonical_hash(hashes))


def fit_predict(a,fold,method):
    if method not in METHODS:raise ValueError('Undeclared method')
    shared_proof(a,[fold]);train,test=fold_masks(a['season'],fold)
    frame=pd.DataFrame(a['X_control'],columns=CORE_FEATURES)
    cols=[n for n in CORE_FEATURES if frame.loc[train,n].notna().any()]
    tick=time.monotonic();details={};pred=[]
    for head in (('control',) if method=='control' else HEADS):
        model=estimator('hgb7') if head=='control' else head_estimator(head)
        y=a['y'][train] if head=='control' else a['targets'][train,HEADS.index(head)]
        model.fit(frame.loc[train,cols],y,sample_weight=a['weights_'+fold])
        p=model.predict(frame.loc[test,cols]);pred.append(p);details[head]=model.get_params()
    heads=None if method=='control' else np.column_stack(pred)
    prediction=np.clip(pred[0],0,20) if method=='control' else recombine(heads,a['pos'][test])
    if not np.isfinite(prediction).all():raise ValueError('Prediction nonfinite')
    return prediction,dict(fit_seconds=time.monotonic()-tick,parameters=details,selected_features=cols,train_rows=int(train.sum()),test_rows=int(test.sum()),heads=len(pred)),heads


def renamed(v):
    if isinstance(v,dict):return {('components' if k in ('combined','fpl_native') else k):renamed(x) for k,x in v.items()}
    if isinstance(v,list):return [renamed(x) for x in v]
    return v


def analyse(a,predictions,panels,folds):
    shared_proof(a,folds)
    namespace=dict(previous.rich.__dict__,shared_proof=lambda _:shared_proof(a,folds),FOLDS=folds)
    if tuple(folds)==AUDITS:namespace['gate_details']=lambda *args:dict(passed=None,criteria={})
    fn=types.FunctionType(previous.rich.analyse.__code__,namespace)
    report,z=fn(dict(a,X_combined=a['X_components']),{(f,'combined' if m=='components' else m):v for (f,m),v in predictions.items()},panels)
    report=renamed(report);z=z.rename(columns={'combined':'components'})
    if tuple(folds)==AUDITS:
        for n in ('total_points','dc_rate4'):z[n]=np.concatenate([a[n][a['season']==f] for f in folds])
        # Preserve the established audit formulas via an isolated name adapter.
        full=previous.full_scoring(z.rename(columns={'components':'fpl_native'}))
        report['full_scoring']=renamed(full)
        def oldkeys(v):
            if isinstance(v,dict):return {('fpl_native' if k=='components' else k):oldkeys(x) for k,x in v.items()}
            return v
        report['gate']=previous.audit_gates(oldkeys(report['metrics']),oldkeys(report['folds']),report['paired']['components'],report['pooled_fixed_squad_delta'],full)
    return report,z


def calibration(a,fold,heads):
    test=a['season']==fold;h=a['targets'][test];pos=a['pos'][test];points=contributions(heads,pos)
    return {str(p):{head:dict(rows=int((pos==p).sum()),predicted_mean=float(heads[pos==p,j].mean()),actual_mean=float(h[pos==p,j].mean()),mean_predicted_points=float(points[pos==p,j].mean())) for j,head in enumerate(HEADS)} for p in (1,2,3,4) if (pos==p).any()}


def static_audit():
    """Consumed raw fields are literal allowlists, not provider inputs."""
    fields=[*I4_COLUMNS,*SIDECAR_COLUMNS,*CORE_FEATURES]
    assert not any(n.startswith('us_') for n in fields)
    source=inspect.getsource(reconcile)+inspect.getsource(sidecar)+inspect.getsource(targets)+inspect.getsource(fit_predict)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node,ast.Constant) and isinstance(node.value,str):assert not node.value.startswith('us_')
        if isinstance(node,ast.Attribute):assert not node.attr.startswith('us_')
    return dict(passed=True,raw_fields=fields,consumed_source_sha256=hashlib.sha256(source.encode()).hexdigest(),core_features=CORE_FEATURES,sidecar_used_for_features=False)
