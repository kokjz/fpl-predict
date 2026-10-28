"""ert-r1 training labels only; actual evaluation targets never change."""
import numpy as np
import pandas as pd

from fpl_model import CORE_FEATURES, estimator, sample_weights
from market_stage_c import array_hash, canonical_hash

SEASONS=('2020-21','2021-22','2022-23','2023-24')
FOLDS=('2022-23','2023-24')
METHODS=('control','expected_return')
REQUIRED=('season','position','minutes','total_points','goals_scored','assists','clean_sheets','us_xG','us_xA')


def check_rows(p):
    missing=set(REQUIRED)-set(p.columns)
    if missing: raise ValueError('Unsettled input columns: '+','.join(sorted(missing)))
    if not p.position.isin([1,2,3,4]).all(): raise ValueError('Unsettled position units')
    if not np.isfinite(p[['minutes','total_points','goals_scored','assists','clean_sheets']].to_numpy(float)).all():
        raise ValueError('Nonfinite actual training components')


def opponent_xg(p,t):
    """Use the opponent team's same-fixture Understat xG, not a history mean."""
    keys=['season','fixture','team_name']
    if not set(keys+['xg'])<=set(t) or not set(keys+['opponent_name'])<=set(p):
        raise ValueError('Unsettled team-fixture join columns')
    if t.duplicated(keys).any(): raise ValueError('Ambiguous team-fixture join')
    index=t.set_index(keys).xg
    target=pd.MultiIndex.from_arrays([p.season,p.fixture,p.opponent_name],names=keys)
    return index.reindex(target).to_numpy(float)


def constants(p,xga):
    """The caller passes training rows only. No evaluation-season row is read."""
    check_rows(p); xga=np.asarray(xga,float)
    if len(xga)!=len(p) or not np.isfinite(xga).all(): raise ValueError('Nonfinite training team-fixture xGA')
    eligible=p.minutes.gt(0).to_numpy() & np.isfinite(p[['us_xG','us_xA']].to_numpy(float)).all(axis=1)
    cs=p.minutes.ge(60).to_numpy() & p.position.isin([1,2,3]).to_numpy()
    numerators=[p.goals_scored.to_numpy(float)[eligible].sum(),p.assists.to_numpy(float)[eligible].sum(),p.clean_sheets.to_numpy(float)[cs].sum()]
    denominators=[p.us_xG.to_numpy(float)[eligible].sum(),p.us_xA.to_numpy(float)[eligible].sum(),np.exp(-xga[cs]).sum()]
    if not np.isfinite(denominators).all() or min(denominators)<=0: raise ValueError('Undefined training-only k')
    k=dict(zip(['k_G','k_A','k_CS'],[float(n/d) for n,d in zip(numerators,denominators)]))
    return k,dict(numerators=dict(zip(k,map(float,numerators))),denominators=dict(zip(k,map(float,denominators))),return_rows=int(eligible.sum()),cs_rows=int(cs.sum()))


def training_target(p,xga,k):
    check_rows(p); xga=np.asarray(xga,float)
    if len(p)!=len(xga) or not np.isfinite(xga).all(): raise ValueError('Nonfinite training xGA')
    y=p.total_points.to_numpy(float).copy()
    eligible=p.minutes.gt(0).to_numpy() & np.isfinite(p[['us_xG','us_xA']].to_numpy(float)).all(axis=1)
    gp=p.position.map({1:6,2:6,3:5,4:4}).to_numpy(float)
    cs=p.position.map({1:4,2:4,3:1,4:0}).to_numpy(float)
    i=eligible
    y[i]=y[i]-gp[i]*p.goals_scored.to_numpy(float)[i]-3*p.assists.to_numpy(float)[i]-cs[i]*p.clean_sheets.to_numpy(float)[i]+gp[i]*k['k_G']*p.us_xG.to_numpy(float)[i]+3*k['k_A']*p.us_xA.to_numpy(float)[i]+cs[i]*k['k_CS']*np.exp(-xga[i])*p.minutes.ge(60).to_numpy()[i]
    if not np.isfinite(y).all(): raise ValueError('Nonfinite expected-return target')
    return y,~eligible


def fold_labels(p,t,fold):
    if fold not in FOLDS: raise ValueError('Undeclared fold')
    train=p.season.lt(fold).to_numpy() & p.season.isin(SEASONS).to_numpy()
    # In particular, do not join/read any Understat test-season value here.
    q=p.loc[train]; xga=opponent_xg(q,t[t.season.lt(fold) & t.season.isin(SEASONS)])
    k,sums=constants(q,xga); target,fallback=training_target(q,xga,k)
    labels=p.total_points.to_numpy(float).copy(); labels[train]=target
    return labels,dict(k=k,sums=sums,training_rows=int(train.sum()),fallback_rows=int(fallback.sum()),training_label_sha256=array_hash(target),actual_training_label_sha256=array_hash(q.total_points.to_numpy(float))),train


def admission(p,t):
    check_rows(p); season_report={}; folds={}; passed=True
    for season in SEASONS[:3]:
        q=p[p.season.eq(season)]; xga=opponent_xg(q,t[t.season.eq(season)])
        played=q.minutes.gt(0).to_numpy(); finite=np.isfinite(q[['us_xG','us_xA']].to_numpy(float)).all(axis=1)
        coverage=float(finite[played].mean()) if played.any() else 0.
        fixture=q[['season','fixture','team_name']].copy(); fixture['finite']=np.isfinite(xga)
        fixture=fixture.groupby(['season','fixture','team_name'],sort=True).finite.all()
        positions={}
        for pos in [1,2,3,4]:
            mask=q.position.eq(pos).to_numpy(); active=mask & played
            positions[str(pos)]=dict(rows=int(mask.sum()),minutes_positive=int(active.sum()),finite_return_rows=int((active&finite).sum()),finite_return_share=float(finite[active].mean()) if active.any() else None,fallback_rows=int((mask&(~played|~finite)).sum()))
        ok=bool(coverage>=.97 and fixture.all() and len(fixture)>0)
        season_report[season]=dict(rows=len(q),minutes_positive=int(played.sum()),coverage=coverage,team_fixtures=len(fixture),nonfinite_team_fixtures=int((~fixture).sum()),positions=positions,passed=ok)
        passed &= ok
    for fold in FOLDS:
        labels,info,train=fold_labels(p,t,fold)
        q=p.loc[train]; y=q.total_points.to_numpy(float); ert=labels[train]
        info['variance_definition']='population variance (ddof=0), descriptive, no gate'
        info['label_variance']={'overall':dict(actual=float(np.var(y)),expected_return=float(np.var(ert))),'by_position':{str(pos):dict(actual=float(np.var(y[q.position.eq(pos)])),expected_return=float(np.var(ert[q.position.eq(pos)]))) for pos in [1,2,3,4]}}
        info['k_gate_passed']=all(.6<=v<=1.6 for v in info['k'].values()); passed &= info['k_gate_passed']; folds[fold]=info
    return dict(gate_A_pass=bool(passed),seasons=season_report,folds=folds,stage_A_fits=0)


def shared_proof(a):
    n=len(a['y']); x=a['X_control']; z=a['X_expected_return']
    if x.shape!=(n,len(CORE_FEATURES)) or z.shape!=x.shape or x.tobytes()!=z.tobytes(): raise ValueError('Feature bytes differ')
    if not np.isfinite(x).all(): raise ValueError('Nonfinite features')
    keys=list(zip(*(a[k].tolist() for k in ['season','gameweek','fixture','fpl_code'])))
    if len(set(keys))!=n or set(a['season'])!=set(SEASONS): raise ValueError('Shared keys/cohort differ')
    if not (a['cutoff_ns']<a['ts_ns']).all(): raise ValueError('Invalid shared origin')
    if not np.array_equal(a['candidate'],(x[:,CORE_FEATURES.index('n_history')]>=3)&(x[:,CORE_FEATURES.index('last5_minutes')]>=45)): raise ValueError('Candidate predicate differs')
    for fold in FOLDS:
        train=a['season']<fold; labels=a['label_'+fold]
        if not np.isfinite(labels).all() or not np.array_equal(labels[~train],a['y'][~train]): raise ValueError('Evaluation targets changed')
    return dict(rows=n,feature_bytes_identical=True,shared_evaluation_targets=True,hashes={k:array_hash(v) for k,v in sorted(a.items())},proof_sha256=canonical_hash({k:array_hash(v) for k,v in sorted(a.items())}))


def fit_predict(a,fold,method):
    if method not in METHODS or fold not in FOLDS: raise ValueError('Undeclared fit')
    shared_proof(a); train=a['season']<fold; test=a['season']==fold
    rows=pd.DataFrame({'ts':pd.to_datetime(a['ts_ns'][train],utc=True)})
    weight=sample_weights(rows)
    if array_hash(weight)!=array_hash(a['weights_'+fold]): raise ValueError('Age weights changed')
    model=estimator('hgb7'); x=a['X_'+method]
    label=a['y'] if method=='control' else a['label_'+fold]
    model.fit(pd.DataFrame(x[train],columns=CORE_FEATURES),label[train],sample_weight=weight)
    prediction=np.clip(model.predict(pd.DataFrame(x[test],columns=CORE_FEATURES)),0,20)
    if not np.isfinite(prediction).all(): raise ValueError('Nonfinite prediction')
    return prediction,dict(train_rows=int(train.sum()),test_rows=int(test.sum()),feature_count=x.shape[1],heads=1,parameters=model.get_params(),age_weights_sha256=array_hash(weight))


# Metrics/replay copied from market_stage_c.analyse, method names only changed.
from benchmark_metrics import evaluate, point_scores
from benchmark_evaluation import paired_block_errors
from market_stage_c import gate_details
import native_development as i4

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
    result['paired']['expected_return'] = paired_block_errors(g[g.candidate], 'expected_return', 'control')
    points = float(np.mean([result['points'][f]['expected_return']['mean_delta'] for f in FOLDS]))
    result['pooled_fixed_squad_delta'] = points
    result['pooled_fixed_squad_points'] = {m:float(np.mean([result['points'][f][m]['mean_total'] for f in FOLDS])) for m in METHODS}
    result['gate'] = gate_details(result['metrics']['expected_return'], result['metrics']['control'],
        {f:result['folds'][f]['expected_return'] for f in FOLDS}, {f:result['folds'][f]['control'] for f in FOLDS}, points)
    # Both types of candidate errors and ranks are reported per fold and pooled.
    for scope, pair in [('pooled',result['metrics']), *[(f,result['folds'][f]) for f in FOLDS]]:
        ratios = {}
        for k in (['player_gw','fixture'] if scope=='pooled' else ['candidate_player_gw','candidate_fixture']):
            ratios[k] = {metric:100*(pair['expected_return'][k][metric]/pair['control'][k][metric]-1)
                         for metric in ['rmse','mae']}
        c = pair['control']['ndcg10' if scope=='pooled' else 'mean_within_gw_ndcg10']
        m = pair['expected_return']['ndcg10' if scope=='pooled' else 'mean_within_gw_ndcg10']
        ratios['ndcg10'] = 100*(m/c-1) if c else None
        if scope != 'pooled':
            p = result['points'][scope]; c = p['control']['mean_total']; m = p['expected_return']['mean_total']
            ratios['fixed_squad_points'] = 100*(m/c-1) if c else None
        else:
            c=result['pooled_fixed_squad_points']['control'];m=result['pooled_fixed_squad_points']['expected_return']
            ratios['fixed_squad_points'] = 100*(m/c-1) if c else None
        result['relative_percent'][scope] = ratios
    return result, z
