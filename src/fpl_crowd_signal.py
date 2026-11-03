"""Predeclared FPL crowd signals for offline chronological research only."""
import ast
import inspect
import types
import numpy as np
import pandas as pd
from fpl_model import CORE_FEATURES, ew
import core_xg_mask as correction
import fpl_team_xg as previous

SEASONS=correction.SEASONS
DEVELOPMENT=correction.DEVELOPMENT
AUDITS=correction.AUDITS
METHODS=('control','crowd')
FIELDS=['selected','transfers_in','transfers_out','transfers_balance','value']
NEW_FEATURES=['crowd_sel_pct_last','crowd_tb_pct_last','crowd_tb_share_last','crowd_ew4_tb_pct','crowd_value','crowd_value_change']
FEATURES={'control':CORE_FEATURES,'crowd':CORE_FEATURES+NEW_FEATURES}
fold_masks=previous.fold_masks
gate_details=previous.gate_details
estimator=previous.estimator


def field_checks(history,require_seasons=True):
    """Return all schema/integrity counts before any field-driven calculation."""
    missing=[n for n in ['season','element','GW','ts',*FIELDS] if n not in history]
    absent=[s for s in SEASONS if not history.season.eq(s).any()] if 'season' in history and require_seasons else []
    report=dict(passed=False,missing_columns=missing,missing_seasons=absent,seasons={})
    if missing:return report
    if not set(history.season)<=set(SEASONS):raise ValueError('Excluded season')
    for season,g in history.groupby('season',sort=True):
        numeric={n:bool(pd.api.types.is_numeric_dtype(g[n])) for n in FIELDS}
        nan={n:int(g[n].isna().sum()) for n in FIELDS}
        counts={}
        if all(numeric.values()):
            counts=dict(balance=int(g.transfers_balance.ne(g.transfers_in-g.transfers_out).sum()),negative_selected=int(g.selected.lt(0).sum()),value_range=int((g.value.lt(35)|g.value.gt(160)).sum()),nonfinite=int((~np.isfinite(g[FIELDS].to_numpy(float))).sum()))
        inconsistent=g.groupby(['element','GW'])[FIELDS].nunique(dropna=False).gt(1)
        dgw={n:int(inconsistent[n].sum()) for n in FIELDS}
        balance_ok=bool(counts and counts['balance']*1000<=len(g))
        other_ok=not any(v for k,v in counts.items() if k!='balance')
        ok=all(numeric.values()) and balance_ok and other_ok and not any(dgw.values())
        report['seasons'][season]=dict(rows=len(g),numeric=numeric,nan_counts=nan,violations=counts,balance_share=counts['balance']/len(g) if counts else None,balance_bound=.001,balance_within_bound=balance_ok,inconsistent_player_gameweeks=dgw,value_changes_within_gw=dgw['value'],passed=ok)
    report['passed']=bool(not absent and all(x['passed'] for x in report['seasons'].values()))
    return report


def balance_discrepancies(history,targets):
    """List every discrepant row and its contribution after GW deduplication."""
    ordered=history.sort_values('ts',kind='stable')
    unique=ordered.drop_duplicates(['season','element','GW'])
    representatives=set(unique.index)
    players={k:g for k,g in unique.groupby(['season','element'],sort=False)}
    target_players={k:g for k,g in targets.groupby(['season','element'],sort=False)}
    out=[]
    for idx,r in history.loc[history.transfers_balance.ne(history.transfers_in-history.transfers_out)].iterrows():
        key=(r.season,r.element);g=players[key];target=target_players.get(key)
        last=any_ew=False
        if target is not None:
            for t in target.itertuples():
                cutoff=pd.Timestamp(t.cutoff)-pd.Timedelta(hours=3)
                eligible=g.loc[(g.GW<t.GW)&(g.ts<cutoff)]
                if len(eligible) and r.GW in set(eligible.GW):
                    any_ew=True;last=last or bool(eligible.GW.max()==r.GW)
        representative=idx in representatives
        out.append(dict(season=r.season,GW=int(r.GW),element=int(r.element),fixture=int(r.fixture) if 'fixture' in r else None,transfers_in=float(r.transfers_in),transfers_out=float(r.transfers_out),transfers_balance=float(r.transfers_balance),difference=float(r.transfers_balance-(r.transfers_in-r.transfers_out)),selected=float(r.selected),deduplicated_representative=representative,feeds_any_last=bool(representative and last),feeds_any_ew4=bool(representative and any_ew),same_player_gw_feeds_last=bool(last),same_player_gw_feeds_ew4=bool(any_ew),recorded_balance_unchanged=True))
    return out


class CrowdStore:
    def __init__(self,history):
        self.report=field_checks(history,False)
        if not self.report['passed']:raise ValueError('Crowd field schema/integrity STOP')
        d=history.sort_values('ts',kind='stable').drop_duplicates(['season','element','GW']).copy()
        for field,name in [('selected','sel_pct'),('transfers_balance','tb_pct')]:
            d[name]=d.groupby(['season','GW'])[field].rank(method='average',pct=True)
        self.players={k:g.sort_values(['GW','ts']) for k,g in d.groupby(['season','element'],sort=False)}
        self.first=history.sort_values('ts',kind='stable').groupby(['season','element']).value.first().to_dict()
        self.rank_source=d.groupby(['season','GW']).ts.max().to_dict()

    def transform(self,targets):
        rows=[];fallback=[];used=0;max_sources=[]
        for r in targets.itertuples():
            if r.season not in SEASONS:raise ValueError('Excluded season')
            cutoff=pd.Timestamp(r.cutoff)-pd.Timedelta(hours=3)
            g=self.players.get((r.season,r.element))
            h=g.loc[(g.GW<r.GW)&(g.ts<cutoff)] if g is not None else pd.DataFrame()
            if len(h):
                # Include the all-player rank's source clocks in the as-of proof.
                sources=[self.rank_source[(r.season,int(gw))] for gw in h.GW]
                if not all(ts<cutoff for ts in sources):raise ValueError('Percentile population crosses cutoff')
                if not (h.ts<cutoff).all() or not (h.GW<r.GW).all():raise ValueError('As-of proof')
                last=h.iloc[-1];sel=float(last.sel_pct);tb=float(last.tb_pct)
                share=float(np.clip(last.transfers_balance/(last.selected+1000),-1,1))
                smooth=ew(h.tb_pct.to_numpy(float),4,.5,2.)
                used+=len(h);max_sources.append(max(sources))
            else:sel=tb=smooth=.5;share=0.;max_sources.append(pd.NaT)
            first=self.first.get((r.season,r.element),r.value)
            row=[sel,tb,share,smooth,float(r.value),float(r.value-first)]
            if not np.isfinite(row).all():raise ValueError('Nonfinite feature used')
            rows.append(row);fallback.append(not len(h))
        frame=pd.DataFrame(rows,index=targets.index,columns=NEW_FEATURES,dtype=float)
        proof=dict(passed=True,rows=len(targets),history_gameweeks_used=used,strict_ts_buffer_hours=3,earlier_gameweeks_only=True,rank_population_clock_checked=True,fallback_rows=int(sum(fallback)))
        return frame,proof,np.asarray(fallback,bool)


def census(features,targets,fallback):
    if not features.index.equals(targets.index):raise ValueError('Census alignment')
    d=features.assign(season=targets.season,pos=targets.pos,points_core=targets.points_core,fallback=fallback)
    report={}
    for (season,pos),g in d.groupby(['season','pos']):
        report[f'{season}/pos{int(pos)}']=dict(rows=len(g),fallback_share=float(g.fallback.mean()),features={n:dict(min=float(g[n].min()),q25=float(g[n].quantile(.25)),median=float(g[n].median()),q75=float(g[n].quantile(.75)),max=float(g[n].max()),mean=float(g[n].mean()),spearman=None if g[n].nunique()<2 or g.points_core.nunique()<2 else float(g[n].corr(g.points_core,method='spearman'))) for n in NEW_FEATURES})
    return report


def shared_proof(a,folds):
    x=a['X_control'];z=a['X_crowd'];width=len(CORE_FEATURES)
    if z.shape!=(len(x),width+6) or x.tobytes()!=np.ascontiguousarray(z[:,:width]).tobytes():raise ValueError('Corrected CORE bytes differ')
    if not np.isfinite(z).all():raise ValueError('Nonfinite crowd')
    adapter=dict(a,X_team_xg=np.column_stack([x,np.zeros((len(x),8))]))
    proof=previous.shared_proof(adapter,folds)
    from market_stage_c import array_hash,canonical_hash
    hashes={k:array_hash(v) for k,v in sorted(a.items())}
    return dict(rows=proof['rows'],core_bytes_identical=True,shared_keys_cohort_cutoffs_weights_evaluation_targets=True,hashes=hashes,proof_sha256=canonical_hash(hashes))


def fit_predict(a,fold,method):
    fn=types.FunctionType(previous.fit_predict.__code__,dict(previous.__dict__,METHODS=METHODS,FEATURES=FEATURES,shared_proof=shared_proof,estimator=estimator))
    return fn(a,fold,method)


def analyse(a,predictions,panels,folds):
    shared_proof(a,folds)
    evaluation=previous.evaluation
    fn=types.FunctionType(evaluation.analyse.__code__,dict(evaluation.__dict__,FOLDS=folds,shared_proof=lambda _:shared_proof(a,folds),gate_details=gate_details if tuple(folds)==DEVELOPMENT else lambda *args:dict(passed=None,criteria={})))
    report,z=fn(dict(a,X_combined=a['X_crowd']),{(f,'combined' if m=='crowd' else m):p for (f,m),p in predictions.items()},panels)
    report=previous.rename(report,'combined','crowd');z=z.rename(columns={'combined':'crowd'})
    if tuple(folds)==AUDITS:
        import fpl_native_combination as audit
        for n in ('total_points','dc_rate4'):z[n]=a[n][a['season']=='2025-26']
        full=audit.full_scoring(z.rename(columns={'crowd':'fpl_native'}))
        fn=types.FunctionType(audit.audit_gates.__code__,dict(audit.__dict__,AUDITS=AUDITS))
        report['gate']=previous.rename(fn(previous.rename(report['metrics'],'crowd','fpl_native'),previous.rename(report['folds'],'crowd','fpl_native'),report['paired']['crowd'],report['pooled_fixed_squad_delta'],full),'fpl_native','crowd')
        report['full_scoring']=previous.rename(full,'fpl_native','crowd')
    return report,z


def static_audit():
    source=inspect.getsource(CrowdStore)+inspect.getsource(field_checks)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node,ast.Attribute) and node.attr.startswith('us_'):raise ValueError('Excluded source')
        if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('us_'):raise ValueError('Excluded source')
    assert not any(n.startswith(('us_','market_')) for n in FIELDS+NEW_FEATURES+CORE_FEATURES)
    return dict(passed=True,raw_fields=FIELDS,features=FEATURES,market_inputs=[],provider_inputs=[])
