"""Frozen FPL-native/market research, with explicit non-Understat dependencies."""
import hashlib
import inspect
import time
import types

import numpy as np
import pandas as pd

from fpl_model import CORE_FEATURES, candidate_mask, estimator, sample_weights
import native_development as i4
from native_history import WindowIndex, league_tables, _times, WINDOWS
from market_stage_c import MARKET_FEATURES, array_hash, canonical_hash
import rich_market_combination as rich
import rmc_confirmation as confirmation
from benchmark_evaluation import paired_block_errors
from benchmark_metrics import point_scores

METHODS=('control','fpl_native')
DEVELOPMENT=('2022-23','2023-24')
AUDITS=('2024-25','2025-26')
SEASONS=(*rich.SEASONS,*AUDITS)
NATIVE=list(i4.FPL)
UNION=list(dict.fromkeys([*CORE_FEATURES,*NATIVE,*MARKET_FEATURES]))
FEATURES=dict(control=CORE_FEATURES,fpl_native=UNION)
# Explicit consumed raw columns. No provider xG or other provider statistics.
PLAYER={'total_points':'fpl_points','minutes':'minutes_played','influence':'influence',
        'creativity':'creativity','threat':'threat','goals_scored':'goals_scored',
        'penalties_missed':'penalties_missed','assists':'assists','goals_conceded':'goals_conceded',
        'own_goals':'own_goals','saves':'saves','penalties_saved':'penalties_saved',
        'yellow_cards':'yellow_cards','red_cards':'red_cards','bps':'bps','bonus':'fpl_bonus_points'}
TEAM=('goals_scored','goals_conceded','league_rank','opponent_league_rank')
PLAYER_INPUTS=('season','fixture','fpl_code','position','team_name','opponent_name','home','starts','ts',*PLAYER)
TEAM_INPUTS=('season','fixture','team_name','opponent_name','ts','goals_scored','goals_conceded')
US_TEAM=('xg','xga','deep','deep_allowed','ppda_att','ppda_def','ppda_allowed_att','ppda_allowed_def')


def fold_masks(seasons,fold):
    if fold not in (*DEVELOPMENT,*AUDITS):raise ValueError('Undeclared fold')
    if not set(seasons)<=set(SEASONS):raise ValueError('Excluded later season')
    return np.asarray(seasons)<fold,np.asarray(seasons)==fold


def native_features(players,teams,targets=None):
    """Original I4 FPL windows, reading only the explicit FPL/result whitelist."""
    targets=players if targets is None else targets
    p=_times(players[list(PLAYER_INPUTS)]);t=_times(teams[list(TEAM_INPUTS)])
    targets=targets.copy();targets['deadline']=pd.to_datetime(targets.deadline,utc=True)
    if p.duplicated(['fpl_code','ts']).any() or t.duplicated(['team_name','ts']).any():raise ValueError('Ambiguous histories')
    if targets.groupby(['season','gameweek']).deadline.nunique().ne(1).any():raise ValueError('Shared deadline required')
    queries={s:list(g.deadline-pd.Timedelta(hours=3)) for s,g in targets.groupby('season')}
    leagues,historical=league_tables(t,queries)
    ranks=[historical[(r.season,r.fixture,r.team_name)] for r in t.itertuples()]
    t['league_rank']=[r[0] for r in ranks];t['opponent_league_rank']=[r[1] for r in ranks]
    pi={k:WindowIndex(g,[*PLAYER,'starts']) for k,g in p.groupby('fpl_code',sort=False)}
    ti={k:WindowIndex(g,TEAM) for k,g in t.groupby('team_name',sort=False)}
    vi={k:WindowIndex(g,['total_points']) for k,g in p.groupby(['fpl_code','home'],sort=False)}
    p['_any']=p.minutes.gt(0).astype(float);p['_sixty']=p.minutes.ge(60).astype(float)
    ai={k:WindowIndex(g,['_any','_sixty','minutes']) for k,g in p.groupby(['season','fpl_code'],sort=False)}
    out=np.empty((len(targets),len(NATIVE)),np.float32);candidates=[];maxima=[];cache={}
    for i,r in enumerate(targets.itertuples()):
        cutoff=r.deadline-pd.Timedelta(hours=3);z={};sources=[]
        values,count,latest=pi[r.fpl_code].means(cutoff);sources.append(latest)
        for w,values_w in values.items():
            for name,value in zip(pi[r.fpl_code].columns,values_w):
                if name in PLAYER:z[f'player_{PLAYER[name]}_{w}']=value
                elif name=='starts' and w in (3,5,10):z[f'ar_starts_{w}']=value
        values=vi[(r.fpl_code,r.home)].means(cutoff)[0]
        for w in WINDOWS:z[f'player_relevant_fpl_points_{w}']=values[w][0]
        for club,side in [(r.team_name,'team'),(r.opponent_name,'opp')]:
            key=(club,cutoff.value)
            if key not in cache:cache[key]=ti[club].means(cutoff)
            values,_,last=cache[key];sources.append(last)
            for w,values_w in values.items():
                for name,value in zip(TEAM,values_w):z[f'{side}_{name}_{w}']=value
        ranks,_,last=leagues[(r.season,cutoff.value)];sources.append(last)
        z.update(is_home_num=float(r.home),status_league_rank=ranks[r.team_name],opp_status_league_rank=ranks[r.opponent_name])
        values,number,_=ai[(r.season,r.fpl_code)].means(cutoff,(3,5,10))
        candidates.append(number>=3 and np.isfinite(values[5][2]) and values[5][2]>=45)
        priors={1:(.50,.48,45.),2:(.55,.42,42.),3:(.52,.38,38.),4:(.50,.35,35.)}[r.position]
        for w,values_w in values.items():
            for j,prefix in enumerate(('p_any','p60','e_minutes')):z[f'{prefix}_{w}']=float(values_w[j]) if np.isfinite(values_w[j]) else priors[j]
        z['ar_rest_days']=float(np.clip((r.deadline-latest).total_seconds()/86400,1,14)) if count else 14.
        index=ti[r.team_name];z['ar_team_matches_14d']=int(((index.times>=(r.deadline-pd.Timedelta(days=14)).value)&(index.times<cutoff.value)).sum())
        for pos in range(1,5):z[f'position_{pos}']=float(r.position==pos)
        if set(z)!=set(NATIVE):raise ValueError('FPL feature contract differs')
        out[i]=[z[n] for n in NATIVE]
        known=[s for s in sources if pd.notna(s)]
        if known and max(known)>=cutoff:raise ValueError('Future source')
        maxima.append(max(known).value if known else pd.NaT.value)
    return pd.DataFrame(out,index=targets.index,columns=NATIVE),pd.DataFrame(dict(candidate=candidates,source_max_ns=maxima),index=targets.index)


def static_audit():
    forbidden=lambda n:n.startswith('us_') or n in US_TEAM
    assert not any(forbidden(n) for n in (*PLAYER_INPUTS,*TEAM_INPUTS))
    assert UNION==list(dict.fromkeys([*CORE_FEATURES,*i4.FPL,*MARKET_FEATURES]))
    assert not any(n.startswith(f'{side}_{stat}_') for n in UNION for side in ('team','opp') for stat in US_TEAM)
    assert not any(n.startswith(f'player_{stat}_') for n in UNION for stat in i4.US_NAMES)
    # CORE is built by fpl_model from FPL statistics, not native provider columns.
    import fpl_model
    source=inspect.getsource(fpl_model)
    assert 'us_' not in source and 'understat' not in source.lower()
    return dict(passed=True,player_inputs=list(PLAYER_INPUTS),team_inputs=list(TEAM_INPUTS),selected_features=UNION,feature_sha256=canonical_hash(UNION),builder_source_sha256=hashlib.sha256(inspect.getsource(native_features).encode()).hexdigest(),core_builder_source_sha256=hashlib.sha256(source.encode()).hexdigest())


def ablation_invariance(players,teams,builder=native_features):
    original,_=builder(players,teams)
    p=players.copy();t=teams.copy();removed_p=[n for n in p if n.startswith('us_')];removed_t=[n for n in US_TEAM if n in t]
    p[removed_p]=np.nan;t[removed_t]=np.nan
    ablated,_=builder(p,t)
    if list(original)!=list(ablated) or original.to_numpy().tobytes()!=ablated.to_numpy().tobytes():raise ValueError('Understat ablation changed feature bytes')
    return original,dict(passed=True,player_columns=removed_p,team_columns=removed_t,feature_bytes_identical=True,array_sha256=array_hash(original.to_numpy()),rows=len(original),features=len(original.columns))


def union(c,native,market):
    if not c.index.equals(native.index) or market.shape!=(len(c),3) or not np.isfinite(market).all():raise ValueError('Feature alignment/market')
    return pd.concat([c[CORE_FEATURES],native[[n for n in NATIVE if n not in CORE_FEATURES]],pd.DataFrame(market,index=c.index,columns=MARKET_FEATURES)],axis=1)[UNION]


def shared_proof(a,folds):
    n=len(a['y']);x=a['X_control'];z=a['X_fpl_native']
    if x.shape!=(n,len(CORE_FEATURES)) or z.shape!=(n,len(UNION)):raise ValueError('Feature shape')
    if x.tobytes()!=np.ascontiguousarray(z[:,:len(CORE_FEATURES)]).tobytes():raise ValueError('CORE bytes differ')
    if not np.isfinite(x).all() or np.isinf(z).any() or not np.isfinite(z[:,-3:]).all():raise ValueError('Nonfinite features')
    keys=list(zip(*(a[k].tolist() for k in i4.KEYS)))
    if len(set(keys))!=n or not (a['cutoff_ns']<a['ts_ns']).all():raise ValueError('Keys/clocks')
    for k in ('y','minutes','ts_ns','cutoff_ns'):
        if len(a[k])!=n or not np.isfinite(a[k]).all():raise ValueError('Shared targets/clocks')
    if not np.array_equal(a['candidate'],(x[:,CORE_FEATURES.index('n_history')]>=3)&(x[:,CORE_FEATURES.index('last5_minutes')]>=45)):raise ValueError('Candidate universe')
    context=pd.DataFrame({k:a[k] for k in ('season','gameweek','fpl_code','candidate','cutoff_ns')})
    if (context.groupby(['season','gameweek','fpl_code'])[['candidate','cutoff_ns']].nunique()!=1).any().any():raise ValueError('DGW context')
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
    frame=pd.DataFrame(a['X_'+method],columns=FEATURES[method]);cols=[n for n in FEATURES[method] if frame.loc[train,n].notna().any()]
    model=estimator('hgb7');tick=time.monotonic();model.fit(frame.loc[train,cols],a['y'][train],sample_weight=a['weights_'+fold]);seconds=time.monotonic()-tick
    prediction=np.clip(model.predict(frame.loc[test,cols]),0,20)
    if not np.isfinite(prediction).all():raise ValueError('Prediction nonfinite')
    return prediction,dict(fit_seconds=seconds,selected_features=cols,selected_feature_count=len(cols),omitted_features=[n for n in FEATURES[method] if n not in cols],parameters=model.get_params(),train_rows=int(train.sum()),test_rows=int(test.sum()),heads=1)


def scoped_confirmation(fold):
    """Reuse original functions with a private globals mapping; no module mutation."""
    if fold not in AUDITS:raise ValueError('Undeclared audit')
    namespace=dict(confirmation.__dict__,SEASONS=SEASONS[:SEASONS.index(fold)+1],FOLD=fold)
    if fold=='2025-26':namespace['NAME_EQUIVALENCES']=dict(confirmation.NAME_EQUIVALENCES,Sunderland='Sunderland')
    for name in ('scope','read_scoped','select_control','admit_market','market_rows'):
        f=getattr(confirmation,name);namespace[name]=types.FunctionType(f.__code__,namespace,f.__name__,f.__defaults__,f.__closure__)
    return namespace


def full_scoring(frame,window=True):
    z=frame[frame.season.eq('2025-26') & frame.candidate].copy()
    if window:z=z[z.gameweek.between(28,38)].copy()
    if not len(z) or not np.isfinite(z.loc[z.pos.ne(1),'dc_rate4']).all():raise ValueError('Missing DC full-score admission')
    term=np.where(z.pos.eq(1),0,2*z.dc_rate4)
    for m in METHODS:z[m]=z[m]+term
    z['actual']=z.total_points
    g=z.groupby(['season','gameweek','fpl_code']).agg({**{m:'sum' for m in METHODS},'actual':'sum'}).reset_index()
    scores={m:dict(player_gw=point_scores(g,m),fixture=point_scores(z,m)) for m in METHODS}
    checks={k:dict(candidate=scores['fpl_native'][k]['rmse'],threshold=1.005*scores['control'][k]['rmse'],passed=bool(scores['fpl_native'][k]['rmse']<=1.005*scores['control'][k]['rmse'])) for k in ('player_gw','fixture')}
    return dict(metrics=scores,criteria=checks,passed=all(v['passed'] for v in checks.values()),rows=len(z),positions={str(pos):{m:point_scores(z[z.pos.eq(pos)],m) for m in METHODS} for pos in (1,2,3,4)})


def audit_gates(metrics,folds,interval,points,full):
    c=metrics['control'];n=metrics['fpl_native']
    gates={}
    gates['2_audit_rmse']=dict(passed=bool(all(n[k]['rmse']<=.995*c[k]['rmse'] for k in ('player_gw','fixture'))))
    gates['3_audit_season_stability']=dict(passed=bool(all(folds[f]['fpl_native']['candidate_player_gw']['rmse']<=1.005*folds[f]['control']['candidate_player_gw']['rmse'] for f in AUDITS)))
    gates['4_audit_mae']=dict(passed=bool(n['player_gw']['mae']<=1.005*c['player_gw']['mae']))
    gates['5_audit_block_interval']=dict(passed=bool(interval.get('status')=='descriptive_interval' and interval['rmse']['upper']<0),interval=interval,descriptive=True)
    gates['6_fixed_squad_points']=dict(passed=bool(points>=0),mean_delta=float(points))
    gates['7_full_scoring']=dict(passed=bool(full['passed']),criteria=full['criteria'])
    return dict(passed=all(g['passed'] for g in gates.values()),criteria=gates)


def analyse(a,predictions,panels,folds):
    """Reuse unchanged I4/RMC evaluation/replay code with isolated names/folds."""
    shared_proof(a,folds)
    arrays=dict(a,X_combined=a['X_fpl_native'])
    def proof(_):return shared_proof(a,folds)
    namespace=dict(rich.__dict__,shared_proof=proof,FOLDS=folds)
    if tuple(folds)==AUDITS:namespace['gate_details']=lambda *args:dict(passed=None,criteria={})
    f=types.FunctionType(rich.analyse.__code__,namespace,'analyse',rich.analyse.__defaults__,rich.analyse.__closure__)
    report,z=f(arrays,{(fold,'combined' if m=='fpl_native' else m):v for (fold,m),v in predictions.items()},panels)
    def rename(v):
        if isinstance(v,dict):return {('fpl_native' if k=='combined' else k):rename(x) for k,x in v.items()}
        if isinstance(v,list):return [rename(x) for x in v]
        return v
    report=rename(report);z=z.rename(columns={'combined':'fpl_native'})
    if tuple(folds)==AUDITS:
        for name in ('total_points','dc_rate4'):
            z[name]=np.concatenate([a[name][a['season']==fold] for fold in folds])
        full=full_scoring(z);report['full_scoring']=full;report['full_scoring_all_gws_descriptive']=full_scoring(z,False)
        report['gate']=audit_gates(report['metrics'],report['folds'],report['paired']['fpl_native'],report['pooled_fixed_squad_delta'],full)
    return report,z
