"""Frozen rich-history/market union: one challenger, shared I4 universe."""
import csv
import gzip
import io
from collections import Counter
from pathlib import Path
import time

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_string_dtype
from benchmark_metrics import evaluate, point_scores
from benchmark_evaluation import paired_block_errors
from fpl_model import CORE_FEATURES, candidate_mask, estimator, sample_weights
import native_development as i4
from native_history import NativeHistory, PLAYER_STATS, TEAM_STATS, DEFENSIVE, SNAPSHOT_FEATURES
from market_stage_c import MARKET_FEATURES, array_hash, canonical_hash, gate_details

SEASONS = ('2020-21', '2021-22', '2022-23', '2023-24')
FOLDS = i4.FOLDS
METHODS = ('control', 'combined')
COMBINED = list(dict.fromkeys([*CORE_FEATURES, *i4.RICH, *MARKET_FEATURES]))
FEATURES = dict(control=CORE_FEATURES, combined=COMBINED)


def fold_masks(seasons, fold, confirmation=False):
    """Closed season allowlist; confirmation design cannot admit 2025/26."""
    seasons = np.asarray(seasons)
    allowed = (*SEASONS, '2024-25') if confirmation else SEASONS
    if not set(seasons) <= set(allowed): raise ValueError('Excluded season')
    if (confirmation and fold != '2024-25') or (not confirmation and fold not in FOLDS):
        raise ValueError('Undeclared fold')
    train = np.isin(seasons, SEASONS) & (seasons < fold)
    return train, seasons == fold


def selected_columns(x, train, method):
    names = FEATURES[method]
    return [name for name in names if x.loc[train, name].notna().any()]


def schema_preflight(frames):
    """Collect every required schema/key gap; values are development rows only."""
    pnum = set(PLAYER_STATS) | set(DEFENSIVE) | {'fixture','gameweek','fpl_code','position','starts','understat_id'}
    tnum = set(TEAM_STATS) - {'league_rank','opponent_league_rank'} | {'fixture'}
    cnum = set(CORE_FEATURES) | {'gameweek','fixture','fpl_code','element','pos','points_core','total_points','minutes'}
    specs = dict(players=(pnum, {'season','team_name','opponent_name','ts','deadline'}, ['season','gameweek','fixture','fpl_code']),
                 teams=(tnum, {'season','team_name','opponent_name','ts'}, ['season','fixture','team_name']),
                 control=(cnum, {'season','ts','cutoff','source_max_ts'}, ['season','gameweek','fixture','fpl_code']))
    report = dict(tables={},gaps=[])
    for name,(numeric,text,keys) in specs.items():
        frame = frames[name]; missing = (numeric | text | ({'home'} if name=='players' else set())) - set(frame)
        issues = [dict(table=name,kind='missing_column',column=k) for k in sorted(missing)]
        for k in sorted(numeric & set(frame)):
            if not is_numeric_dtype(frame[k]): issues.append(dict(table=name,kind='numeric_dtype_required',column=k))
        for k in sorted(text & set(frame)):
            if not is_string_dtype(frame[k]): issues.append(dict(table=name,kind='text_dtype_required',column=k))
        if name=='players' and 'home' in frame and frame.home.dtype != bool:
            issues.append(dict(table=name,kind='boolean_dtype_required',column='home'))
        unique = None
        if set(keys) <= set(frame):
            unique = not frame.duplicated(keys).any() and not frame[keys].isna().any().any()
            if not unique: issues.append(dict(table=name,kind='null_or_duplicate_key',columns=keys))
        if name=='players' and {'season','fixture','ts','gameweek'} <= set(frame):
            if frame[['season','fixture','ts','gameweek']].drop_duplicates().duplicated(['season','fixture']).any():
                issues.append(dict(table=name,kind='ambiguous_fixture_context'))
        report['tables'][name] = dict(inventory=[dict(name=k,dtype=str(frame[k].dtype)) for k in frame],missing_columns=sorted(missing),key=keys,key_unique=bool(unique) if unique is not None else None)
        report['gaps'].extend(issues)
    report['passed'] = not report['gaps']
    return report


def preflight_files(paths):
    """One CSV pass per input; later seasons only increment a season counter."""
    frames={}; counts={}; gaps=[]
    for name in ('players','teams','control'):
        path=Path(paths[name]); opener=gzip.open if path.suffix=='.gz' else open
        with opener(path,'rt',newline='',encoding='utf-8-sig') as f:
            reader=csv.reader(f); header=next(reader); buffer=io.StringIO(); writer=csv.writer(buffer)
            writer.writerow(['gameweek' if k=='GW' else k for k in header]); seasons=Counter()
            if len(set(header))!=len(header): gaps.append(dict(table=name,kind='duplicate_columns'))
            if 'season' not in header:
                gaps.append(dict(table=name,kind='missing_season')); frames[name]=pd.DataFrame(columns=header); counts[name]={}; continue
            si=header.index('season')
            for row in reader:
                if len(row)!=len(header): gaps.append(dict(table=name,kind='malformed_row')); continue
                seasons[row[si]]+=1
                if row[si] in SEASONS: writer.writerow(row)
            buffer.seek(0); frames[name]=pd.read_csv(buffer); counts[name]=dict(sorted(seasons.items()))
    report=schema_preflight(frames)
    report['gaps'].extend(gaps);report['passed']=not report['gaps'];report['season_counts']=counts
    report['confirmation_rows_present']={k:counts[k].get('2024-25',0)>0 for k in ('players','teams')}
    report['scope']='All column names/dtypes and development keys; later-season row counts only; no later values parsed'
    return report


def align_union(p, c, rich, rich_evidence, market):
    if not p.index.equals(c.index) or not p.index.equals(rich.index) or not p.index.equals(rich_evidence.index):
        raise ValueError('Feature row index differs')
    if not p[i4.KEYS].equals(c[i4.KEYS]): raise ValueError('Feature keys differ')
    if not np.array_equal(rich_evidence.candidate.to_numpy(bool),candidate_mask(c).to_numpy(bool)):
        raise ValueError('Rich candidate universe differs')
    if market.shape!=(len(p),3) or not np.isfinite(market).all(): raise ValueError('Nonfinite market')
    names=[n for n in i4.RICH if n not in CORE_FEATURES]
    x=pd.concat([c[CORE_FEATURES],rich[names],pd.DataFrame(market,index=p.index,columns=MARKET_FEATURES)],axis=1)
    return x[COMBINED].copy()


def shared_proof(a):
    n=len(a['y']); x=a['X_control']; z=a['X_combined']; width=len(CORE_FEATURES)
    if x.shape!=(n,width) or z.shape!=(n,len(COMBINED)): raise ValueError('Feature shape differs')
    if x.tobytes()!=np.ascontiguousarray(z[:,:width]).tobytes(): raise ValueError('Core feature bytes differ')
    if not np.isfinite(x).all() or np.isinf(z).any() or not np.isfinite(z[:,-3:]).all(): raise ValueError('Nonfinite feature contract')
    keys=list(zip(*(a[k].tolist() for k in i4.KEYS)))
    if len(set(keys))!=n or set(a['season'])!=set(SEASONS): raise ValueError('Keys/cohort differ')
    for k in ('y','minutes','ts_ns','cutoff_ns'):
        if len(a[k])!=n or not np.isfinite(a[k]).all(): raise ValueError('Shared targets/clocks differ')
    if not (a['cutoff_ns']<a['ts_ns']).all(): raise ValueError('Invalid shared cutoff')
    if not np.array_equal(a['candidate'],(x[:,CORE_FEATURES.index('n_history')]>=3)&(x[:,CORE_FEATURES.index('last5_minutes')]>=45)):
        raise ValueError('Candidate universe differs')
    g=pd.DataFrame({k:a[k] for k in ['season','gameweek','fpl_code','candidate','cutoff_ns']})
    if (g.groupby(['season','gameweek','fpl_code'])[['candidate','cutoff_ns']].nunique()!=1).any().any(): raise ValueError('DGW universe differs')
    for fold in FOLDS:
        train,valid=fold_masks(a['season'],fold)
        if set(a['season'][train])!=set(SEASONS[:SEASONS.index(fold)]) or not valid.any(): raise ValueError('Missing fold')
        if a['ts_ns'][train].max()>=a['cutoff_ns'][valid].min(): raise ValueError('Training labels cross fold')
        weights=sample_weights(pd.DataFrame({'ts':pd.to_datetime(a['ts_ns'][train],utc=True)}))
        if weights.tobytes()!=a['weights_'+fold].tobytes(): raise ValueError('Age weights differ')
    hashes={k:array_hash(v) for k,v in sorted(a.items())}
    return dict(rows=n,core_bytes_identical=True,shared_keys_cohort_cutoffs_weights_evaluation_targets=True,hashes=hashes,proof_sha256=canonical_hash(hashes))


def fit_predict(a, fold, method):
    if method not in METHODS: raise ValueError('Undeclared method')
    shared_proof(a);train,valid=fold_masks(a['season'],fold)
    frame=pd.DataFrame(a['X_'+method],columns=FEATURES[method]);cols=selected_columns(frame,train,method)
    if not cols: raise ValueError('No observed training features')
    model=estimator('hgb7');tick=time.monotonic()
    model.fit(frame.loc[train,cols],a['y'][train],sample_weight=a['weights_'+fold])
    fit_seconds=time.monotonic()-tick;tick=time.monotonic()
    prediction=np.clip(model.predict(frame.loc[valid,cols]),0,20)
    if not np.isfinite(prediction).all(): raise ValueError('Nonfinite prediction')
    return prediction,dict(fit_seconds=fit_seconds,prediction_seconds=time.monotonic()-tick,selected_feature_count=len(cols),selected_features=cols,omitted_features=[n for n in FEATURES[method] if n not in cols],train_rows=int(train.sum()),test_rows=int(valid.sum()),heads=1,parameters=model.get_params())


# Same fixed metrics/replay as market_stage_c; challenger name only changes.
def analyse(arrays, predictions, panels):
    shared_proof(arrays); exports = []; result = dict(folds={}, metrics={}, points={}, paired={}, relative_percent={})
    for fold in FOLDS:
        valid = arrays['season'] == fold
        z = pd.DataFrame({k: arrays[k][valid] for k in ['season','gameweek','fixture','fpl_code','minutes','candidate','element','pos','n_history']})
        z['actual'] = arrays['y'][valid]
        z['last5_minutes'] = arrays['X_control'][valid, CORE_FEATURES.index('last5_minutes')]
        result['folds'][fold] = {}
        for method in METHODS:
            z[method] = predictions[(fold,method)]
            # This is exactly I4's per-fold evaluate(), including position/rank diagnostics.
            d = z.rename(columns={'gameweek':'GW','actual':'points_core'})
            result['folds'][fold][method] = evaluate(d, d, z[method].to_numpy())
        # Replay each original panel once; expose all20 totals rather than only mean/min/max.
        totals = {m: [] for m in METHODS}
        for squad in panels[fold]['squads']:
            one = i4.replay(z, dict(first_gw=panels[fold]['first_gw'], squads=[squad]), METHODS)
            for m in METHODS: totals[m].append(one[m]['mean_total'])
        result['points'][fold] = {}
        for m in METHODS:
            delta = np.asarray(totals[m]) - totals['control']
            result['points'][fold][m] = dict(totals=totals[m], deltas=delta.tolist(),
                mean_total=float(np.mean(totals[m])), mean_delta=float(delta.mean()),
                minimum_delta=float(delta.min()), maximum_delta=float(delta.max()))
        exports.append(z)
    z = pd.concat(exports, ignore_index=True)
    g = z.groupby(['season','gameweek','fpl_code']).agg(
        {**{m:'sum' for m in METHODS}, 'actual':'sum','candidate':'first'}).reset_index()
    for m in METHODS:
        result['metrics'][m] = dict(player_gw=point_scores(g[g.candidate],m), fixture=point_scores(z[z.candidate],m),
            all_player_gw=point_scores(g,m), all_fixture=point_scores(z,m),
            ndcg10=point_scores(g[g.candidate],m)['mean_within_gw_ndcg10'],
            actual_minutes_diagnostics={str(lo)+'_'+str(hi):point_scores(z[z.minutes.between(lo,hi)],m) for lo,hi in [(0,0),(1,59),(60,90)]},
            cold_start=point_scores(z[z.n_history.lt(3)],m))
    result['paired']['combined'] = paired_block_errors(g[g.candidate], 'combined', 'control')
    points = float(np.mean([result['points'][f]['combined']['mean_delta'] for f in FOLDS]))
    result['pooled_fixed_squad_delta'] = points
    result['pooled_fixed_squad_points'] = {m:float(np.mean([result['points'][f][m]['mean_total'] for f in FOLDS])) for m in METHODS}
    result['gate'] = gate_details(result['metrics']['combined'], result['metrics']['control'],
        {f:result['folds'][f]['combined'] for f in FOLDS}, {f:result['folds'][f]['control'] for f in FOLDS}, points)
    # Both types of candidate errors and ranks are reported per fold and pooled.
    for scope, pair in [('pooled',result['metrics']), *[(f,result['folds'][f]) for f in FOLDS]]:
        ratios = {}
        for k in (['player_gw','fixture'] if scope=='pooled' else ['candidate_player_gw','candidate_fixture']):
            ratios[k] = {metric:100*(pair['combined'][k][metric]/pair['control'][k][metric]-1)
                         for metric in ['rmse','mae']}
        c = pair['control']['ndcg10' if scope=='pooled' else 'mean_within_gw_ndcg10']
        m = pair['combined']['ndcg10' if scope=='pooled' else 'mean_within_gw_ndcg10']
        ratios['ndcg10'] = 100*(m/c-1) if c else None
        if scope != 'pooled':
            p = result['points'][scope]; c = p['control']['mean_total']; m = p['combined']['mean_total']
            ratios['fixed_squad_points'] = 100*(m/c-1) if c else None
        else:
            c=result['pooled_fixed_squad_points']['control'];m=result['pooled_fixed_squad_points']['combined']
            ratios['fixed_squad_points'] = 100*(m/c-1) if c else None
        result['relative_percent'][scope] = ratios
    result['pooled_position_candidate_fixture']={m:{str(pos):point_scores(z[z.candidate & z.pos.eq(pos)],m) for pos in (1,2,3,4)} for m in METHODS}
    for scope,pair in [('pooled',result['metrics']),*[(f,result['folds'][f]) for f in FOLDS]]:
        for k in ['all_player_gw','all_fixture']:
            result['relative_percent'][scope][k]={metric:100*(pair['combined'][k][metric]/pair['control'][k][metric]-1) for metric in ['rmse','mae']}
    return result, z
