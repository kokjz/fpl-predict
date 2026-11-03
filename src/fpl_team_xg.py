"""Frozen FPL player-derived team xG research; no operational writes."""
import ast
import hashlib
import inspect
import time
import types
import numpy as np
import pandas as pd
from fpl_model import CORE_FEATURES, ew, estimator, sample_weights
from market_stage_c import array_hash, canonical_hash
import rich_market_combination as evaluation
import market_stage_c as gates
import rmc_confirmation as confirmation
import component_poisson as source_tools

SEASONS=('2020-21','2021-22','2022-23','2023-24','2024-25','2025-26')
DEVELOPMENT=('2023-24','2024-25')
AUDITS=('2025-26',)
METHODS=('control','team_xg')
NEW_FEATURES=[f'{s}_ew{h}_{v}' for s in ('team','opp') for h in (4,12) for v in ('xg','xga')]
FEATURES=dict(control=CORE_FEATURES,team_xg=CORE_FEATURES+NEW_FEATURES)
HISTORY_COLUMNS=['season','GW','element','fixture','team_id','opponent_team','was_home','minutes','ts','expected_goals','team_gf','team_ga']
read_scoped=source_tools.read_scoped

def fold_masks(seasons,fold):
    if fold not in (*DEVELOPMENT,*AUDITS) or not set(seasons)<=set(SEASONS):raise ValueError('Excluded season/fold')
    s=np.asarray(seasons);return s<fold,s==fold

def schema_preflight(history):
    gaps=[]
    for n in HISTORY_COLUMNS:
        if n not in history:gaps.append(dict(column=n,kind='missing_column'))
    for season in SEASONS:
        if not history.season.eq(season).any():gaps.append(dict(season=season,kind='missing_season'))
    return dict(passed=not gaps,gaps=gaps,columns=list(history.columns))

def fixture_statistics(history):
    """Literal FPL-only projection; missing played-row xG propagates both ways."""
    d=history[HISTORY_COLUMNS].copy()
    if not set(d.season)<=set(SEASONS):raise ValueError('Excluded season')
    keys=['season','fixture','team_id']
    if d[keys+['element','opponent_team','ts','was_home','minutes']].isna().any().any() or d.duplicated(['season','fixture','element']).any():raise ValueError('Missing/duplicate fixture context')
    out=[]
    for key,g in d.groupby(keys,sort=False):
        context=['opponent_team','ts','was_home','team_gf','team_ga','GW']
        if g[context].nunique(dropna=False).ne(1).any():raise ValueError('Ambiguous team-fixture context')
        x=pd.to_numeric(g.expected_goals,errors='coerce').to_numpy(float)
        played=g.minutes.to_numpy()>0
        value=np.nan if ((played & ~np.isfinite(x)).any() or not np.isfinite(x).any()) else float(x[np.isfinite(x)].sum())
        if np.isfinite(x).any() and (x[np.isfinite(x)]<0).any():raise ValueError('Negative FPL xG')
        r=g.iloc[0];out.append(dict(zip(keys,key),opponent_team=r.opponent_team,ts=r.ts,was_home=r.was_home,GW=r.GW,team_gf=r.team_gf,team_ga=r.team_ga,xg=value))
    f=pd.DataFrame(out)
    if f.groupby(['season','fixture']).size().ne(2).any():raise ValueError('Expected reciprocal team pair')
    lookup=f.set_index(keys)
    xga=[]
    for r in f.itertuples():
        other=lookup.loc[(r.season,r.fixture,r.opponent_team)]
        if other.opponent_team!=r.team_id or other.was_home==r.was_home or other.ts!=r.ts or other.team_gf!=r.team_ga or other.team_ga!=r.team_gf:raise ValueError('Nonreciprocal fixture')
        xga.append(other.xg)
    f['xga']=xga
    return f

class TeamXGStore:
    def __init__(self,fixtures):
        self.teams={k:g.sort_values('ts') for k,g in fixtures.groupby(['season','team_id'],sort=False)}
        self.cache={}
    def team(self,season,team,cutoff):
        key=(season,team,cutoff.value)
        if key not in self.cache:
            g=self.teams.get((season,team));h=g[g.ts<cutoff-pd.Timedelta(hours=3)] if g is not None else pd.DataFrame()
            self.cache[key]={f'ew{half}_{stat}':ew(h[stat] if len(h) else [],half,1.35,4.) for half in (4,12) for stat in ('xg','xga')}
        return self.cache[key]
    def transform(self,targets):
        out=[]
        for r in targets.itertuples():
            if r.season not in SEASONS:raise ValueError('Excluded season')
            out.append({f'{side}_{k}':v for side,team in [('team',r.team_id),('opp',r.opponent_team)] for k,v in self.team(r.season,team,r.cutoff).items()})
        return pd.DataFrame(out,index=targets.index,columns=NEW_FEATURES)

def admission(history,fixtures):
    """All-season admission, including per-GW coverage and hard sanity bounds."""
    seasons={};passed=True
    for season in SEASONS:
        d=history.loc[history.season.eq(season)];f=fixtures.loc[fixtures.season.eq(season)]
        coverage={}
        for gw,g in d.groupby('GW'):
            p=g.loc[g.minutes.gt(0),'expected_goals'];finite=int(np.isfinite(p.to_numpy(float)).sum())
            coverage[str(int(gw))]=dict(played=len(p),finite=finite,share=finite/len(p) if len(p) else None)
        p=d.loc[d.minutes.gt(0),'expected_goals'];finite=int(np.isfinite(p.to_numpy(float)).sum())
        missing=int(f.xg.isna().sum());ratio=None;correlation={}
        count=int(f.fixture.nunique());early=season<'2022-23'
        ok=count==380 and len(f)==760
        if early:ok=ok and not np.isfinite(d.expected_goals.to_numpy(float)).any() and missing==len(f)
        else:
            ratio=float(f.xg.sum()/f.team_gf.sum())
            totals=f.groupby('team_id')[['xg','xga','team_gf','team_ga']].sum()
            correlation=dict(xg_goals=float(totals.xg.corr(totals.team_gf)),xga_conceded=float(totals.xga.corr(totals.team_ga)))
            ok=ok and missing/len(f)<=.01 and .80<=ratio<=1.20
        seasons[season]=dict(passed=bool(ok),fixtures=count,team_fixtures=len(f),nan_team_fixtures=missing,nan_share=missing/len(f) if len(f) else None,played=len(p),finite=finite,finite_share=finite/len(p) if len(p) else None,coverage_by_gw=coverage,xg_goals_ratio=ratio,correlations=correlation)
        passed=passed and ok
    return dict(passed=bool(passed),seasons=seasons,reciprocal_integrity=True)

def shared_proof(a,folds):
    n=len(a['y']);x=a['X_control'];z=a['X_team_xg'];width=len(CORE_FEATURES)
    if x.shape!=(n,width) or z.shape!=(n,width+8) or not np.isfinite(x).all() or not np.isfinite(z).all():raise ValueError('Feature contract')
    if x.tobytes()!=np.ascontiguousarray(z[:,:width]).tobytes():raise ValueError('CORE bytes differ')
    keys=list(zip(*(a[k].tolist() for k in evaluation.i4.KEYS)))
    if len(set(keys))!=n or not (a['cutoff_ns']<a['ts_ns']).all():raise ValueError('Keys/clocks')
    for k in ('y','minutes','ts_ns','cutoff_ns'):
        if len(a[k])!=n or not np.isfinite(a[k]).all():raise ValueError('Shared targets/clocks')
    if not np.array_equal(a['candidate'],(x[:,CORE_FEATURES.index('n_history')]>=3)&(x[:,CORE_FEATURES.index('last5_minutes')]>=45)):raise ValueError('Candidate identity')
    context=pd.DataFrame({k:a[k] for k in ('season','gameweek','fpl_code','candidate','cutoff_ns')})
    if (context.groupby(['season','gameweek','fpl_code'])[['candidate','cutoff_ns']].nunique()!=1).any().any():raise ValueError('DGW context')
    for fold in folds:
        train,test=fold_masks(a['season'],fold)
        if set(a['season'][train])!=set(SEASONS[:SEASONS.index(fold)]) or not test.any():raise ValueError('Fold coverage')
        if a['ts_ns'][train].max()>=a['cutoff_ns'][test].min():raise ValueError('Training labels cross fold')
        w=sample_weights(pd.DataFrame({'ts':pd.to_datetime(a['ts_ns'][train],utc=True)}))
        if w.tobytes()!=a['weights_'+fold].tobytes():raise ValueError('Age weights')
    hashes={k:array_hash(v) for k,v in sorted(a.items())}
    return dict(rows=n,core_bytes_identical=True,shared_keys_cohort_cutoffs_weights_evaluation_targets=True,hashes=hashes,proof_sha256=canonical_hash(hashes))

def fit_predict(a,fold,method):
    if method not in METHODS:raise ValueError('Undeclared method')
    shared_proof(a,[fold]);train,test=fold_masks(a['season'],fold)
    frame=pd.DataFrame(a['X_'+method],columns=FEATURES[method]);cols=[c for c in FEATURES[method] if frame.loc[train,c].notna().any()]
    tick=time.monotonic();m=estimator('hgb7');m.fit(frame.loc[train,cols],a['y'][train],sample_weight=a['weights_'+fold]);pred=np.clip(m.predict(frame.loc[test,cols]),0,20)
    if not np.isfinite(pred).all():raise ValueError('Nonfinite prediction')
    return pred,dict(fit_predict_seconds=time.monotonic()-tick,selected_features=cols,train_rows=int(train.sum()),test_rows=int(test.sum()),parameters=m.get_params(),heads=1)

def gate_details(candidate,control,fold_candidate,fold_control,points):
    # Bind both independent established gate implementations to these two folds.
    i4_gate=types.FunctionType(evaluation.i4.gate.__code__,dict(evaluation.i4.__dict__,FOLDS=DEVELOPMENT))
    adapter=types.SimpleNamespace(gate=i4_gate)
    fn=types.FunctionType(gates.gate_details.__code__,dict(gates.__dict__,FOLDS=DEVELOPMENT,i4=adapter))
    return fn(candidate,control,fold_candidate,fold_control,points)

def rename(v,old='combined',new='team_xg'):
    if isinstance(v,dict):return {(new if k==old else k):rename(x,old,new) for k,x in v.items()}
    if isinstance(v,list):return [rename(x,old,new) for x in v]
    return v

def analyse(a,predictions,panels,folds):
    shared_proof(a,folds)
    fn=types.FunctionType(evaluation.analyse.__code__,dict(evaluation.__dict__,FOLDS=folds,shared_proof=lambda _:shared_proof(a,folds),gate_details=gate_details if tuple(folds)==DEVELOPMENT else lambda *args:dict(passed=None,criteria={})))
    report,z=fn(dict(a,X_combined=a['X_team_xg']),{(f,'combined' if m=='team_xg' else m):p for (f,m),p in predictions.items()},panels)
    report=rename(report);z=z.rename(columns={'combined':'team_xg'})
    if tuple(folds)==AUDITS:
        import fpl_native_combination as audit
        for n in ('total_points','dc_rate4'):z[n]=a[n][a['season']=='2025-26']
        old=z.rename(columns={'team_xg':'fpl_native'})
        full=audit.full_scoring(old)
        fn=types.FunctionType(audit.audit_gates.__code__,dict(audit.__dict__,AUDITS=AUDITS))
        report['gate']=rename(fn(rename(report['metrics'],'team_xg','fpl_native'),rename(report['folds'],'team_xg','fpl_native'),report['paired']['team_xg'],report['pooled_fixed_squad_delta'],full),'fpl_native','team_xg')
        report['full_scoring']=rename(full,'fpl_native','team_xg')
    return report,z

def static_audit():
    assert not any(n.startswith('us_') for n in HISTORY_COLUMNS+CORE_FEATURES)
    source=inspect.getsource(fixture_statistics)+inspect.getsource(TeamXGStore)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node,ast.Attribute):assert not node.attr.startswith('us_')
        if isinstance(node,ast.Constant) and isinstance(node.value,str):assert not node.value.startswith('us_')
    return dict(passed=True,raw_history_fields=HISTORY_COLUMNS,i4_team_fields_read=[],features=FEATURES,consumed_source_sha256=hashlib.sha256(source.encode()).hexdigest())
