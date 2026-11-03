"""Research-only correction of unpublished FPL expected-statistic windows."""
import ast
import inspect
import types
import numpy as np
import pandas as pd
from fpl_model import CORE_FEATURES, FeatureStore
import fpl_team_xg as previous

SEASONS=previous.SEASONS
DEVELOPMENT=('2023-24','2024-25')
AUDITS=('2025-26',)
METHODS=('control','corrected')
FIELDS=('expected_goals','expected_assists','expected_goals_conceded')
COLUMNS=[f'ew{h}_{f}' for h in (4,12) for f in FIELDS]
FEATURES={m:CORE_FEATURES for m in METHODS}
EXPECTED_UNPUBLISHED=previous.EXPECTED_UNPUBLISHED
confirmation=previous.confirmation
evaluation=previous.evaluation
estimator=previous.estimator
fold_masks=previous.fold_masks
read_scoped=previous.read_scoped

def unpublished_gameweeks(history,field):
    if field not in FIELDS:raise ValueError('Undeclared field')
    out=[]
    for (season,gw),g in history.loc[history.season.isin(SEASONS[2:])].groupby(['season','GW']):
        values=g[field].to_numpy(float)
        if np.isfinite(values).all() and (values==0).all() and g.team_gf.sum()>0:out.append((season,int(gw)))
    return sorted(out)

def mask_history(history):
    if not set(history.season)<=set(SEASONS):raise ValueError('Excluded season')
    masked=history.copy();report={}
    for f in FIELDS:
        detected=unpublished_gameweeks(history,f)
        previous.validate_unpublished_set(history,detected)
        selected=pd.MultiIndex.from_frame(history[['season','GW']]).isin(detected)
        masked.loc[selected,f]=np.nan
        report[f]=dict(detected=[dict(season=s,GW=g) for s,g in detected],rows=int(selected.sum()))
    return masked,report

def schema_preflight(history):
    required=['season','GW','team_gf','minutes','ts',*FIELDS]
    gaps=[dict(column=n) for n in required if n not in history]
    for s in SEASONS:
        if not history.season.eq(s).any():gaps.append(dict(season=s))
    return dict(passed=not gaps,gaps=gaps,required=required)

def rebuild(history,targets):
    """Call the unchanged player builder, preserving season reset and priors."""
    if not targets.season.eq('2022-23').all():raise ValueError('Only 2022-23 targets')
    if not set(history.season)<=set(SEASONS):raise ValueError('Excluded season')
    store=FeatureStore(history)
    rows=[{n:z[n] for n in COLUMNS} for r in targets.itertuples()
          for z in [store.player(r.season,r.element,r.cutoff)]]
    return pd.DataFrame(rows,index=targets.index,columns=COLUMNS)

def correction_proof(control,corrected,seasons):
    x=np.ascontiguousarray(control);z=np.ascontiguousarray(corrected)
    if x.shape!=z.shape or x.shape[1]!=len(CORE_FEATURES) or not np.isfinite(z).all():raise ValueError('Feature contract')
    scope=np.asarray(seasons)=='2022-23'
    keep=[i for i,n in enumerate(CORE_FEATURES) if n not in COLUMNS]
    if x[~scope].tobytes()!=z[~scope].tobytes():raise ValueError('Non-target season differs')
    if x[:,keep].tobytes()!=z[:,keep].tobytes():raise ValueError('Other CORE columns differ')
    return dict(passed=True,non_target_season_bytes_identical=True,other_43_columns_identical=True)

def shared_proof(a,folds):
    correction=correction_proof(a['X_control'],a['X_corrected'],a['season'])
    # Reuse the established context/weight/cohort proof with unchanged CORE.
    adapter=dict(a,X_team_xg=np.column_stack([a['X_control'],np.zeros((len(a['y']),8))]))
    proof=previous.shared_proof(adapter,folds)
    from market_stage_c import array_hash,canonical_hash
    hashes={k:array_hash(v) for k,v in sorted(a.items())}
    return dict(rows=proof['rows'],correction=correction,shared_keys_cohort_cutoffs_weights_evaluation_targets=True,hashes=hashes,proof_sha256=canonical_hash(hashes))

def fit_predict(a,fold,method):
    fn=types.FunctionType(previous.fit_predict.__code__,dict(previous.__dict__,METHODS=METHODS,FEATURES=FEATURES,shared_proof=shared_proof))
    return fn(a,fold,method)

def gate_details(candidate,control,fold_candidate,fold_control,points):
    """Predeclared no-harm gate; independent of the improvement gates."""
    rules={}
    def record(name,value,threshold):rules[name]=dict(candidate=float(value),threshold=float(threshold),passed=bool(value<=threshold))
    for unit in ('player_gw','fixture'):
        for metric,ratio in [('rmse',1.0),('mae',1.005)]:record('pooled_'+unit+'_'+metric,candidate[unit][metric],ratio*control[unit][metric])
    # Gate C uses the six pooled criteria; B also checks each fold's RMSE.
    if set(fold_candidate)==set(DEVELOPMENT):
        for fold in DEVELOPMENT:
            for unit in ('candidate_player_gw','candidate_fixture'):record(fold+'_'+unit+'_rmse',fold_candidate[fold][unit]['rmse'],1.005*fold_control[fold][unit]['rmse'])
    elif set(fold_candidate)!=set(AUDITS):raise ValueError('Undeclared gate folds')
    rules['pooled_ndcg10']=dict(candidate=candidate['ndcg10'],control=control['ndcg10'],passed=bool(candidate['ndcg10']>=control['ndcg10']))
    rules['mean_fixed_squad_delta']=dict(delta=float(points),passed=bool(points>=0))
    return dict(passed=all(r['passed'] for r in rules.values()),criteria=rules)

def analyse(a,predictions,panels,folds):
    shared_proof(a,folds)
    fn=types.FunctionType(evaluation.analyse.__code__,dict(evaluation.__dict__,FOLDS=folds,shared_proof=lambda _:shared_proof(a,folds),gate_details=gate_details))
    report,z=fn(dict(a,X_combined=a['X_corrected']),{(f,'combined' if m=='corrected' else m):p for (f,m),p in predictions.items()},panels)
    report=previous.rename(report,'combined','corrected');z=z.rename(columns={'combined':'corrected'})
    if tuple(folds)==AUDITS:
        import fpl_native_combination as audit
        for n in ('total_points','dc_rate4'):z[n]=a[n][a['season']=='2025-26']
        full=previous.rename(audit.full_scoring(z.rename(columns={'corrected':'fpl_native'})),'fpl_native','corrected')
        report['full_scoring']={k:v for k,v in full.items() if k not in ('criteria','passed')}
        report['full_scoring']['descriptive_only']=True
    return report,z

def static_audit():
    source=inspect.getsource(unpublished_gameweeks)+inspect.getsource(mask_history)+inspect.getsource(rebuild)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node,ast.Attribute) and node.attr.startswith('us_'):raise ValueError('Excluded source')
        if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('us_'):raise ValueError('Excluded source')
    assert not any(n.startswith('us_') for n in [*FIELDS,*CORE_FEATURES])
    return dict(passed=True,fields=list(FIELDS),columns=COLUMNS,features=FEATURES)
