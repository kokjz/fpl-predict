"""Bounded historical fplcache availability study; no operational model writes."""
from pathlib import Path
import copy
import hashlib
import json
import re

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from availability_evidence import utc
from availability_prospective import phase2_gates, keyed_block
from conditional_forecaster import SIGNALS, missing_availability
from conditional_forecaster import fit as conditional_fit
from conditional_prospective import EXTRA, attach_loader
from deadline_provenance import read_snapshot, extract_bootstrap
from fpl_model import CORE_FEATURES, DC_FEATURES, estimator, sample_weights
from market_stage_c import canonical_hash, array_hash
from benchmark_metrics import evaluate

SEASONS = tuple(f'{y}-{str(y+1)[-2:]}' for y in range(2020, 2026))
SOURCE_SEASONS = SEASONS[1:]
FOLDS = SEASONS[2:5]
ARMS = ('control', 'conditional', 'conditional_unlabelled')
KEYS = ['season', 'fixture', 'fpl_code']
LAST_DEADLINE = '2026-05-24T13:30:00+00:00'
FEATURES = CORE_FEATURES + EXTRA + SIGNALS
PRIVATE_EXTRAS = ['status', 'news_added', 'penalties_order',
                  'corners_and_indirect_freekicks_order', 'direct_freekicks_order',
                  'ep_next', 'now_cost', 'selected_by_percent',
                  'transfers_in_event', 'transfers_out_event']


def scope(seasons):
    if not set(seasons) <= set(SEASONS):
        raise ValueError('Historical season refused')


def path_time(path):
    match = re.fullmatch(r'cache/(\d{4})/(\d{1,2})/(\d{1,2})/(\d{2})(\d{2})\.json\.xz', path)
    if not match:
        raise ValueError('Snapshot path refused')
    year, month, day, hour, minute = map(int, match.groups())
    stamp = pd.Timestamp(year=year, month=month, day=day, hour=hour, minute=minute, tz='UTC')
    if stamp > utc(LAST_DEADLINE):
        raise ValueError('Snapshot after final permitted deadline')
    return stamp


def select_snapshot(entries, deadline):
    """Entries carry the listing blob and independently looked-up adding clock."""
    deadline = utc(deadline)
    if deadline > utc(LAST_DEADLINE):
        raise ValueError('Deadline refused')
    eligible = []
    for entry in entries:
        stamp = path_time(entry['path'])
        commit = utc(entry['commit_time'])
        if stamp - commit > pd.Timedelta(minutes=5):
            raise ValueError('Adding commit precedes path clock')
        if stamp < deadline and commit < deadline and deadline-stamp <= pd.Timedelta(hours=24):
            eligible.append((stamp, entry))
    if not eligible:
        return None
    return dict(max(eligible, key=lambda pair: pair[0])[1])


def planning_calendar(rows):
    scope(rows.season)
    result = []
    for season in SOURCE_SEASONS:
        for gw in range(1, 39):
            clocks = rows.loc[rows.season.eq(season) & rows.GW.eq(gw), 'cutoff'].drop_duplicates()
            if (season, gw) == ('2022-23', 7):
                if len(clocks):
                    raise ValueError('Unexpected no-fixtures rows')
                result.append(dict(season=season, gameweek=gw, status='no_fixtures', deadline=None))
                continue
            if len(clocks) != 1:
                raise ValueError('Missing or ambiguous planning calendar')
            deadline = utc(clocks.iloc[0])
            if deadline > utc(LAST_DEADLINE):
                raise ValueError('Planning deadline refused')
            result.append(dict(season=season, gameweek=gw, status='planned', deadline=deadline.isoformat()))
    return result


def player_payload(payload):
    """Remove Assistant Managers without altering the retained source payload."""
    result = copy.deepcopy(payload)
    excluded = sum(p['element_type'] == 5 for p in result['elements'])
    if any(p['element_type'] not in (1, 2, 3, 4, 5) for p in result['elements']):
        raise ValueError('Invalid element type')
    result['elements'] = [p for p in result['elements'] if p['element_type'] != 5]
    return result, excluded


def integer_codes(values):
    """Normalize finite integral identities without float rounding or coercion."""
    result = []
    for value in values:
        if isinstance(value, (bool, np.bool_)) or pd.isna(value):
            raise ValueError('Missing or noninteger identity code')
        if isinstance(value, str) and not re.fullmatch(r'[+-]?\d+', value):
            raise ValueError('Noninteger identity code')
        try:
            integer = int(value)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError('Noninteger identity code') from exc
        if (not isinstance(value, str) and value != integer) or not 0 < integer <= np.iinfo(np.int64).max:
            raise ValueError('Noninteger or out-of-range identity code')
        result.append(integer)
    return np.asarray(result, dtype='int64')


def admit_snapshot(entry, bridge, history):
    scope([entry['season']])
    path_time(entry['path'])  # refuse forbidden paths before opening any bytes
    selected = select_snapshot([entry], entry['deadline'])
    if selected is None:
        raise ValueError('Snapshot not eligible')
    local = Path(entry['local_path'])
    if not local.is_file():
        raise ValueError('Snapshot absent')
    raw = local.read_bytes()
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != entry['blob']:
        raise ValueError('Git blob mismatch')
    payload, excluded = player_payload(read_snapshot(local, entry['sha256']))
    published = max(path_time(entry['path']), utc(entry['commit_time']))
    report, identities = extract_bootstrap(payload, entry['season'], int(entry['gameweek']), published.isoformat())
    if utc(report['deadline']) != utc(entry['deadline']):
        raise ValueError('Snapshot deadline differs from planning calendar')
    if bridge.id.duplicated().any() or bridge.code.duplicated().any():
        raise ValueError('Ambiguous season bridge')
    h = history.loc[history.season.eq(entry['season']) & history.GW.eq(entry['gameweek'])]
    codes = h.element.map(bridge.set_index('id').code)
    if codes.isna().any():
        raise ValueError('Missing history bridge')
    codes = pd.Series(integer_codes(codes), index=h.index)
    identities = identities.copy()
    identities['fpl_code'] = integer_codes(identities.fpl_code)
    if identities.fpl_code.duplicated().any():
        raise ValueError('Duplicate normalized snapshot code')
    roster = identities.set_index('fpl_code')
    matched = codes.isin(roster.index)
    used = roster.loc[codes.loc[matched].to_numpy()]
    if not np.array_equal(used.position.to_numpy(), h.loc[matched, 'pos'].to_numpy()):
        raise ValueError('Snapshot position mismatch')
    id_drift = int(np.count_nonzero(used.element.to_numpy() != h.loc[matched, 'element'].to_numpy()))
    observations = []
    for p in payload['elements']:
        row = dict(season=entry['season'], gameweek=int(entry['gameweek']), element=p['id'],
                   fpl_code=p['code'], source_position=p['element_type'], team=p['team'],
                   published_at=published.isoformat(), source_deadline=report['deadline'],
                   chance_label=p.get('chance_of_playing_next_round'), news_present=bool(p.get('news')))
        row.update({name: p.get(name) for name in PRIVATE_EXTRAS})
        observations.append(row)
    obs = pd.DataFrame(observations)
    chance = pd.to_numeric(obs.chance_label, errors='raise').to_numpy(float)
    if np.isinf(chance).any() or ((chance[np.isfinite(chance)] < 0) | (chance[np.isfinite(chance)] > 100)).any():
        raise ValueError('Invalid chance label')
    report.update(status='admitted', assistant_managers_excluded=excluded,
                  known_labels=int(np.isfinite(chance).sum()), commit_time=entry['commit_time'],
                  path_time=path_time(entry['path']).isoformat(), published_at=published.isoformat(),
                  unmatched_history_rows=int((~matched).sum()), id_drift_rows=id_drift,
                  identity_key='season/gameweek/fpl_code')
    return report, obs


def augment(rows, features, bridges, observations):
    """Same SIGNALS bytes as incumbent augment, generalized by seasonal keys."""
    scope(rows.season)
    if not rows.index.equals(features.index):
        raise ValueError('Unaligned features')
    scope(observations.season)
    if observations.duplicated(['season', 'gameweek', 'fpl_code']).any():
        raise ValueError('Duplicate observations')
    z = rows[['season', 'GW', 'element', 'fixture', 'pos', 'cutoff']].copy()
    z['row'] = np.arange(len(z))
    z['fpl_code'] = np.nan
    for season, bridge in bridges.items():
        scope([season])
        if bridge.id.duplicated().any() or bridge.code.duplicated().any():
            raise ValueError('Ambiguous bridge')
        ix = z.season.eq(season)
        z.loc[ix, 'fpl_code'] = z.loc[ix, 'element'].map(bridge.set_index('id').code)
    if z.fpl_code.isna().any():
        raise ValueError('Missing stable bridge')
    if 'fpl_code' in rows and not np.array_equal(z.fpl_code.to_numpy(), rows.fpl_code.to_numpy()):
        raise ValueError('Row stable code mismatch')
    obs = observations.loc[observations.season.ne('2020-21')].copy()
    z = z.merge(obs, left_on=['season', 'GW', 'fpl_code'], right_on=['season', 'gameweek', 'fpl_code'],
                how='left', validate='many_to_one', suffixes=('', '_source')).sort_values('row')
    matched = z.published_at.notna()
    if (z.loc[matched, 'pos'].to_numpy() != z.loc[matched, 'source_position'].to_numpy()).any():
        raise ValueError('Source position differs')
    publication = z.loc[matched, 'published_at'].map(utc)
    deadline = z.loc[matched, 'source_deadline'].map(utc)
    cutoff = z.loc[matched, 'cutoff'].map(utc)
    if publication.ge(deadline).any() or publication.ge(cutoff).any():
        raise ValueError('Source is not before both cutoffs')
    chance = pd.to_numeric(z.chance_label, errors='raise').to_numpy(float)
    if np.isinf(chance).any() or ((chance[np.isfinite(chance)] < 0) | (chance[np.isfinite(chance)] > 100)).any():
        raise ValueError('Invalid chance covariate')
    result = features.copy()
    result[SIGNALS[0]] = np.where(np.isnan(chance), 0., chance/100.)
    result[SIGNALS[1]] = np.isnan(chance).astype(float)
    coverage = z.assign(matched=matched.to_numpy(), known=np.isfinite(chance)).groupby(['season', 'GW']).agg(
        rows=('row', 'size'), matched=('matched', 'sum'), known=('known', 'sum')).reset_index()
    return result, coverage.to_dict('records')


def fold_masks(rows, season):
    scope(rows.season)
    if season not in FOLDS:
        raise ValueError('Fold refused')
    train, test = rows.season.lt(season), rows.season.eq(season)
    if not train.any() or not test.any():
        raise ValueError('Empty fold')
    if rows.loc[train, 'ts'].map(utc).max()+pd.Timedelta(hours=3) >= rows.loc[test, 'cutoff'].map(utc).min():
        raise ValueError('Training labels cross test cutoff')
    return train, test


def fit(rows, features, season, arm):
    if arm not in ARMS or not rows.index.equals(features.index) or list(features) != FEATURES:
        raise ValueError('Fit contract')
    train, test = fold_masks(rows, season)
    x = missing_availability(features) if arm == 'conditional_unlabelled' else features
    with threadpool_limits(limits=2):
        if arm == 'control':
            names = [n for n in CORE_FEATURES if not x.loc[train, n].isna().all()]
            fitted = estimator('hgb7')
            fitted.fit(x.loc[train, names], rows.loc[train, 'points_core'], sample_weight=sample_weights(rows.loc[train]))
            core = np.clip(fitted.predict(x.loc[test, names]), 0, 20)
            prediction = pd.DataFrame(dict(core_xp=core, dc_xp=np.zeros(len(core)), expected_points=core), index=rows.index[test])
        else:
            fitted = conditional_fit(rows, x, train, version='fplcache-availability-fca-r2')
            prediction = fitted.predict(x.loc[test], rows.loc[test, 'pos'])
    receipt = dict(season=season, arm=arm, training_rows=int(train.sum()), test_rows=int(test.sum()),
                   training_row_sha256=canonical_hash(rows.loc[train, KEYS].to_dict('records')),
                   feature_sha256=canonical_hash(CORE_FEATURES if arm == 'control' else FEATURES),
                   training_feature_sha256=array_hash(x.loc[train, CORE_FEATURES if arm == 'control' else FEATURES].to_numpy(float)),
                   metadata=getattr(fitted, 'metadata', None))
    return prediction, receipt


def ledger_attempt(root, season, arm):
    """An incomplete attempt is never silently reusable or retryable."""
    order = [(s, a) for s in FOLDS for a in ARMS]
    ordinal = order.index((season, arm))
    root = Path(root)
    root.mkdir(exist_ok=True)
    for i in range(ordinal):
        p = root/f'{i:02d}.json'
        if not p.is_file() or json.loads(p.read_text())['status'] != 'completed':
            raise ValueError('Earlier fit incomplete')
    target = root/f'{ordinal:02d}.json'
    with target.open('x', encoding='utf-8') as f:
        json.dump(dict(status='attempted', season=season, arm=arm), f)
    return target


def fixed_squad(rows, features, predictions, season, opening_gw=10, count=20):
    """Parameterized replica of the fixed GW20 retrospective squad selector."""
    from forecast import legal_squad, select_xi
    from points_replay import realised_points
    scope(rows.season)
    scope([season])
    if not rows.index.equals(features.index):
        raise ValueError('Squad feature alignment')
    year = rows[rows.season.eq(season)]
    opening = year[year.GW.eq(opening_gw)]
    cutoff = opening.cutoff.iloc[0]
    opening = opening.loc[(features.loc[opening.index, 'n_history'] >= 3) &
                          (features.loc[opening.index, 'last5_minutes'] >= 45)].drop_duplicates('element')
    history = year[year.ts < cutoff-pd.Timedelta(hours=3)].sort_values('ts').groupby('element').tail(1).set_index('element')
    pool = []
    for r in opening.itertuples():
        if r.element not in history.index:
            continue
        price = float(history.loc[r.element, 'value'])
        if not np.isfinite(price) or price <= 0:
            continue
        pool.append(dict(id=int(r.element), position=int(r.pos), team=int(r.team_id), price_tenths=price,
                         weight=max(float(features.loc[r.Index, 'ew4_points_core']), .1)))
    rng = np.random.default_rng(20260921)
    squads, seen = [], set()
    for _ in range(10000):
        selected = []
        for pos, n in [(1, 2), (2, 5), (3, 5), (4, 3)]:
            candidates = [p for p in pool if p['position'] == pos]
            weights = np.array([p['weight'] for p in candidates])
            ids = rng.choice(len(candidates), size=n, replace=False, p=weights/weights.sum())
            selected.extend(candidates[i] for i in ids)
        key = tuple(sorted(p['id'] for p in selected))
        if key not in seen and legal_squad(selected) and sum(p['price_tenths'] for p in selected) <= 1000:
            squads.append(selected)
            seen.add(key)
            if len(squads) == count:
                break
    if len(squads) != count:
        raise ValueError('Fixed squad count')
    test = rows.season.eq(season) & rows.GW.between(opening_gw, 38)
    z = rows.loc[test, ['GW', 'element', 'minutes', 'total_points']].copy()
    for method, values in predictions.items():
        z[method] = values
    grouped = z.groupby(['GW', 'element']).agg({m: 'sum' for m in predictions} | {'minutes': 'sum', 'total_points': 'sum'})
    totals = {m: [] for m in predictions}
    for squad in squads:
        players = {p['id']: p for p in squad}
        one = {m: 0. for m in predictions}
        for gw in range(opening_gw, 39):
            sub = grouped.loc[gw] if gw in grouped.index.get_level_values(0) else pd.DataFrame()
            actual = {i: float(sub.loc[i, 'total_points']) if i in sub.index else 0. for i in players}
            played = {i: bool(sub.loc[i, 'minutes'] > 0) if i in sub.index else False for i in players}
            for method in predictions:
                choices = [dict(p, expected_points=float(sub.loc[p['id'], method]) if p['id'] in sub.index else 0.) for p in squad]
                one[method] += realised_points(select_xi(choices), players, actual, played)
        for method in predictions:
            totals[method].append(one[method])
    deltas = {m: (np.array(v)-totals['control']).tolist() for m, v in totals.items() if m != 'control'}
    return dict(totals=totals, deltas=deltas, squad_sha256=canonical_hash(squads), count=count, first_gw=opening_gw, season=season)


def gate_table(candidate, control, fold_reports, squad_delta, full_candidate, full_control, interval):
    def units(report):
        return {k: report['candidate_'+k] for k in ['player_gw', 'fixture']}
    report = phase2_gates(units(candidate), units(control), squad_delta, full_candidate, full_control, interval)
    report['stability'] = {s: {u: bool(v['conditional']['candidate_'+u]['rmse'] <= 1.005*v['control']['candidate_'+u]['rmse'])
                                for u in ['player_gw', 'fixture']} for s, v in fold_reports.items()}
    report['passed'] = bool(report['passed'] and all(all(v.values()) for v in report['stability'].values()))
    return report


def aggregate(rows, features, predictions):
    """Predictions are keyed rows in the same order; retain season in pooling."""
    scope(rows.season)
    block = keyed_block(rows, predictions, list(predictions.columns.difference(KEYS)))
    if set(rows.season) != set(FOLDS) or not rows.GW.between(10, 38).all():
        raise ValueError('Score window refused')
    methods = {a: block[a].to_numpy(float) for a in ARMS}
    methods['blend_equal'] = .5*methods['control']+.5*methods['conditional']
    pooled = {a: evaluate(rows, features, p) for a, p in methods.items()}
    folds = {s: {a: evaluate(rows.loc[ix], features.loc[ix], p[ix.to_numpy()]) for a, p in methods.items()}
             for s in FOLDS for ix in [rows.season.eq(s)]}
    return dict(pooled=pooled, folds=folds)
