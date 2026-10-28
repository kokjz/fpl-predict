"""One fixed market augmentation of the I4 core control; no promotion."""
from datetime import timedelta
import hashlib
import json
import time

import numpy as np
import pandas as pd

from benchmark_metrics import evaluate, point_scores
from benchmark_evaluation import paired_block_errors
from fpl_model import CORE_FEATURES, estimator, sample_weights
from market_stage_b import SEASONS, FOLDS, identity, source_clock, check_clubs
from market_strength import fit_ratings, project, timestamp
import native_development as i4

METHODS = ('control', 'market_strength')
MARKET_FEATURES = ['mkt_lambda_for', 'mkt_lambda_against', 'mkt_cs_prob']
FEATURES = {'control': CORE_FEATURES, 'market_strength': CORE_FEATURES + MARKET_FEATURES}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def array_hash(value):
    a = np.ascontiguousarray(value)
    return hashlib.sha256(str(a.dtype).encode() + str(a.shape).encode() + a.tobytes()).hexdigest()


def market_rows(players, lambdas):
    """Project each player's own fixture, strictly before its common GW cutoff."""
    markets = []; targets = {}; seen = set()
    for raw in lambdas:
        if raw['season'] not in ('2019-20', *SEASONS):
            raise ValueError('Later market season prohibited')
        r = dict(raw, date=raw['csv_kickoff'][:10], fpl_kickoff=raw['canonical_kickoff'])
        check_clubs(r); key = identity(r)
        if key in seen: raise ValueError('Duplicate market identity')
        seen.add(key)
        markets.append(dict(season=r['season'], fixture=r['fixture'], identity=key,
                            kickoff=source_clock(r), home=r['home'], away=r['away'],
                            lambda_home=r['lambda_home'], lambda_away=r['lambda_away']))
        if r['season'] != '2019-20': targets[(r['season'], int(r['fixture']))] = r
    markets.sort(key=lambda r: (r['kickoff'], r['identity']))
    ratings = {}; projections = {}; values = []; evidence = []
    for r in players.itertuples():
        if r.season not in SEASONS: raise ValueError('Later/warmup player target')
        target = targets[(r.season, int(r.fixture))]
        if not isinstance(r.home, (bool, np.bool_)): raise ValueError('Invalid venue')
        home = bool(r.home)
        if (r.team_name, r.opponent_name) != ((target['home'], target['away']) if home else (target['away'], target['home'])):
            raise ValueError('Player fixture/club/venue mismatch')
        if timestamp(r.ts) != timestamp(target['fpl_kickoff']): raise ValueError('Player fixture clock mismatch')
        cutoff = timestamp(r.deadline) - timedelta(hours=3)
        key = (r.season, 'fpl', int(r.fixture))
        if timestamp(r.ts) <= cutoff: raise ValueError('Invalid origin')
        if cutoff not in ratings:
            eligible = [m for m in markets if m['kickoff'] < cutoff]
            ratings[cutoff] = (fit_ratings(eligible, cutoff), {m['identity'] for m in eligible})
        rating, used = ratings[cutoff]
        if key in used:
            raise ValueError('Target odds entered history')
        cache = (cutoff, r.team_name, r.opponent_name, home)
        if cache not in projections:
            projections[cache] = project(rating, r.team_name, r.opponent_name, home)
        z = projections[cache]
        values.append([z[n] for n in MARKET_FEATURES])
        evidence.append(dict(season=r.season, fixture=int(r.fixture), team=r.team_name,
            cutoff=cutoff.isoformat(), source_max=rating.source_max.isoformat(),
            cold_start_team=z['cold_start_team'], cold_start_opponent=z['cold_start_opponent']))
    result = np.asarray(values, dtype=np.float64)
    if result.shape != (len(players), 3) or not np.isfinite(result).all():
        raise ValueError('Non-finite/incomplete market features; fail closed')
    return result, evidence, len(ratings)


def shared_proof(arrays):
    """No method may change any nonmarket byte or the shared decision universe."""
    a, b = arrays['X_control'], arrays['X_market_strength']
    n = len(arrays['y']); width = len(CORE_FEATURES)
    if a.shape != (n, width) or b.shape != (n, width + 3): raise ValueError('Feature shape differs')
    for name in ['X_control', 'X_market_strength', 'y', 'minutes', 'cutoff_ns', 'ts_ns']:
        if len(arrays[name]) != n or not np.isfinite(arrays[name]).all():
            raise ValueError('Non-finite/shared cohort mismatch: ' + name)
    if np.ascontiguousarray(a, dtype=np.float64).tobytes() != np.ascontiguousarray(b[:, :width], dtype=np.float64).tobytes():
        raise ValueError('Nonmarket feature bytes differ')
    keys = list(zip(arrays['season'].tolist(), arrays['gameweek'].tolist(), arrays['fixture'].tolist(), arrays['fpl_code'].tolist()))
    if len(set(keys)) != n: raise ValueError('Duplicate player-fixture keys')
    if set(arrays['season']) != set(SEASONS): raise ValueError('Missing/later cohort seasons')
    if not (arrays['cutoff_ns'] < arrays['ts_ns']).all(): raise ValueError('Invalid fixture origin')
    if not np.array_equal(arrays['candidate'], (a[:, CORE_FEATURES.index('n_history')] >= 3) & (a[:, CORE_FEATURES.index('last5_minutes')] >= 45)):
        raise ValueError('Candidate predicate differs')
    g = pd.DataFrame({k: arrays[k] for k in ['season','gameweek','fpl_code','candidate','cutoff_ns']})
    if (g.groupby(['season','gameweek','fpl_code'])[['candidate','cutoff_ns']].nunique() != 1).any().any():
        raise ValueError('Double-gameweek candidate/cutoff mismatch')
    return dict(rows=n, nonmarket_bytes_identical=True,
                hashes={k: array_hash(v) for k, v in sorted(arrays.items())},
                shared_keys_targets_cohort_cutoffs_sha256=canonical_hash([
                    [*k, float(y), bool(c), int(t)] for k,y,c,t in zip(keys, arrays['y'], arrays['candidate'], arrays['cutoff_ns'])]))


def fit_predict(method, arrays, fold):
    if method not in METHODS or fold not in FOLDS: raise ValueError('Undeclared method/fold')
    shared_proof(arrays)
    train = arrays['season'] < fold; valid = arrays['season'] == fold
    if set(arrays['season'][train]) != set(SEASONS[:SEASONS.index(fold)]) or not valid.any():
        raise ValueError('Missing/invalid fold')
    if arrays['ts_ns'][train].max() + int(pd.Timedelta(hours=3).value) >= arrays['cutoff_ns'][valid].min() + int(pd.Timedelta(hours=3).value):
        raise ValueError('Training labels cross fold')
    rows = pd.DataFrame({'ts': pd.to_datetime(arrays['ts_ns'][train], utc=True)})
    x = arrays['X_' + method]
    # Same one HGB head, age weights, feature order and final clip as I4 control.
    a = pd.DataFrame(x[train], columns=FEATURES[method]); b = pd.DataFrame(x[valid], columns=FEATURES[method])
    model = estimator('hgb7'); tick = time.monotonic()
    model.fit(a, arrays['y'][train], sample_weight=sample_weights(rows))
    fitted = time.monotonic() - tick; tick = time.monotonic()
    prediction = np.clip(model.predict(b), 0, 20)
    if not np.isfinite(prediction).all(): raise ValueError('Non-finite prediction')
    return prediction, dict(fit_seconds=fitted, prediction_seconds=time.monotonic()-tick,
        train_rows=int(train.sum()), test_rows=int(valid.sum()), selected_feature_count=x.shape[1],
        heads=1, parameters=model.get_params())


def gate_details(candidate, control, fold_candidate, fold_control, points):
    rules = {}
    def record(name, left, right):
        rules[name] = dict(candidate=float(left), threshold=float(right), passed=bool(left <= right))
    for k in ['player_gw', 'fixture']:
        record('pooled_' + k + '_rmse_gain', candidate[k]['rmse'], .995 * control[k]['rmse'])
        record('pooled_' + k + '_mae_noninferiority', candidate[k]['mae'], 1.005 * control[k]['mae'])
    for fold in FOLDS:
        for k in ['candidate_player_gw', 'candidate_fixture']:
            record(fold + '_' + k + '_rmse_noninferiority', fold_candidate[fold][k]['rmse'], 1.005 * fold_control[fold][k]['rmse'])
    rules['pooled_ndcg10_not_lower'] = dict(candidate=candidate['ndcg10'], control=control['ndcg10'], passed=bool(candidate['ndcg10'] >= control['ndcg10']))
    rules['mean_fixed_squad_delta_nonnegative'] = dict(delta=points, passed=bool(points >= 0))
    verdict = i4.gate(candidate, control, fold_candidate, fold_control, points)
    if verdict != all(r['passed'] for r in rules.values()): raise ValueError('Gate implementation differs from I4')
    return dict(passed=verdict, criteria=rules)


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
    result['paired']['market_strength'] = paired_block_errors(g[g.candidate], 'market_strength', 'control')
    points = float(np.mean([result['points'][f]['market_strength']['mean_delta'] for f in FOLDS]))
    result['pooled_fixed_squad_delta'] = points
    result['pooled_fixed_squad_points'] = {m:float(np.mean([result['points'][f][m]['mean_total'] for f in FOLDS])) for m in METHODS}
    result['gate'] = gate_details(result['metrics']['market_strength'], result['metrics']['control'],
        {f:result['folds'][f]['market_strength'] for f in FOLDS}, {f:result['folds'][f]['control'] for f in FOLDS}, points)
    # Both types of candidate errors and ranks are reported per fold and pooled.
    for scope, pair in [('pooled',result['metrics']), *[(f,result['folds'][f]) for f in FOLDS]]:
        ratios = {}
        for k in (['player_gw','fixture'] if scope=='pooled' else ['candidate_player_gw','candidate_fixture']):
            ratios[k] = {metric:100*(pair['market_strength'][k][metric]/pair['control'][k][metric]-1)
                         for metric in ['rmse','mae']}
        c = pair['control']['ndcg10' if scope=='pooled' else 'mean_within_gw_ndcg10']
        m = pair['market_strength']['ndcg10' if scope=='pooled' else 'mean_within_gw_ndcg10']
        ratios['ndcg10'] = 100*(m/c-1) if c else None
        if scope != 'pooled':
            p = result['points'][scope]; c = p['control']['mean_total']; m = p['market_strength']['mean_total']
            ratios['fixed_squad_points'] = 100*(m/c-1) if c else None
        else:
            c=result['pooled_fixed_squad_points']['control'];m=result['pooled_fixed_squad_points']['market_strength']
            ratios['fixed_squad_points'] = 100*(m/c-1) if c else None
        result['relative_percent'][scope] = ratios
    return result, z
