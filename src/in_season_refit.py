"""Frozen historical annual versus GW19 refit mechanics; no artifact writers."""
from decimal import Decimal
import hashlib
import json

import numpy as np
import pandas as pd

from fpl_model import CORE_FEATURES, fit_estimator, sample_weights
from benchmark_metrics import evaluate
from benchmark_evaluation import paired_block_errors
import phase2_execution

SEASONS = ('2023-24', '2024-25', '2025-26')
HISTORICAL = frozenset(('2020-21', '2021-22', '2022-23', *SEASONS))
KEYS = ['season', 'element', 'fixture']
UNITS = ('candidate_player_gw', 'candidate_fixture')


def scope(rows):
    if rows.season.isna().any() or not set(rows.season) <= HISTORICAL:
        raise ValueError('Historical seasons only; future season refused')


def validate(rows, features):
    scope(rows)
    if (not rows.index.equals(features.index) or not rows.index.is_unique
            or rows.duplicated(KEYS).any() or rows[KEYS].isna().any().any()):
        raise ValueError('Row/feature alignment or duplicate keys')
    if rows.ts.isna().any() or rows.cutoff.isna().any():
        raise ValueError('Missing timestamps')


def recipe(artifact):
    """Read only the verified incumbent's recipe; never select a learner."""
    name, blend = artifact.core_name, artifact.blend
    if not isinstance(name, str) or not name or not np.isfinite(blend) or not 0 <= blend <= 1:
        raise ValueError('Invalid incumbent recipe')
    return dict(core_name=name, blend=float(blend))


def masks(rows, season, arm):
    scope(rows)
    if season not in SEASONS or arm not in ('annual', 'refit19'):
        raise ValueError('Unregistered season/arm')
    opening = rows[rows.season.eq(season) & rows.GW.eq(20)]
    test = rows.season.eq(season) & rows.GW.between(20, 38)
    if opening.empty or not test.any():
        raise ValueError('Missing GW20 window')
    deadline = opening.cutoff.min()
    train = rows.season.lt(season)
    if arm == 'refit19':
        train = train | (rows.season.eq(season) & rows.ts.lt(deadline))
    if not train.any() or not rows.loc[train, 'ts'].max() < rows.loc[test, 'cutoff'].min():
        raise ValueError('Training leakage')
    return train, test


def training_counts(rows):
    result = {}
    for season in SEASONS:
        annual, test = masks(rows, season, 'annual')
        refit, _ = masks(rows, season, 'refit19')
        result[season] = dict(annual=int(annual.sum()), refit19=int(refit.sum()),
                              added=int((refit & ~annual).sum()), test=int(test.sum()),
                              cutoff=rows.loc[test, 'cutoff'].min().isoformat(),
                              max_train_ts={a: rows.loc[m, 'ts'].max().isoformat()
                                            for a, m in [('annual', annual), ('refit19', refit)]})
    return result


def fit_predict(rows, features, season, arm, incumbent_recipe):
    validate(rows, features)
    train, test = masks(rows, season, arm)
    name, blend = incumbent_recipe['core_name'], incumbent_recipe['blend']
    learner = fit_estimator(name, features.loc[train, CORE_FEATURES],
                            rows.loc[train, 'points_core'], sample_weights(rows[train]))
    prediction = (blend * np.clip(learner.predict(features.loc[test, CORE_FEATURES]), 0, 20)
                  + (1-blend) * features.loc[test, 'ew4_points_core'].to_numpy())
    if not np.isfinite(prediction).all():
        raise ValueError('Nonfinite predictions')
    return prediction


def decimal_precision_sample(lines, count=1000):
    """Inspect exact numeric JSON tokens, independent of float decoding."""
    maximum, seen = 0, 0
    for line in lines:
        if not line.strip():
            continue
        item = json.loads(line, parse_float=Decimal, parse_int=Decimal)
        if item['season'] not in HISTORICAL:
            raise ValueError('Future receipt season refused')
        value = item['model']
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError('Receipt model must be finite numeric')
        maximum = max(maximum, max(0, -value.as_tuple().exponent))
        seen += 1
        if seen == count:
            break
    if not seen:
        raise ValueError('Empty precision sample')
    return dict(sample_rows=seen, max_decimals=maximum,
                rule='absolute_1e-9' if maximum <= 10 else 'relative_1e-12')


def prediction_hash(values):
    values = np.asarray(values, dtype='<f8')
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError('Invalid prediction array')
    return hashlib.sha256(values.tobytes()).hexdigest()


def aligned_prediction(rows, bundle):
    scope(rows)
    scope(bundle)
    if rows.duplicated(KEYS).any() or bundle.duplicated(KEYS).any():
        raise ValueError('Duplicate prediction keys')
    expected, found = pd.MultiIndex.from_frame(rows[KEYS]), pd.MultiIndex.from_frame(bundle[KEYS])
    if len(expected) != len(found) or len(expected.difference(found)) or len(found.difference(expected)):
        raise ValueError('Prediction key sets differ')
    values = bundle.set_index(KEYS).loc[expected, 'prediction'].to_numpy(dtype=float)
    prediction_hash(values)
    return values


def parity(rows, prediction, reference, precision):
    scope(reference)
    if len(rows) != len(prediction):
        raise ValueError('Prediction length mismatch')
    stored = aligned_prediction(rows, reference.rename(columns={'model': 'prediction'}))
    new = np.asarray(prediction, dtype=float)
    prediction_hash(new)
    diff = np.abs(new-stored)
    if precision['rule'] == 'absolute_1e-9':
        allowed = np.full(len(rows), 1e-9)
    elif precision['rule'] == 'relative_1e-12':
        allowed = np.abs(stored) * 1e-12
    else:
        raise ValueError('Unknown parity rule')
    if not (diff <= allowed).all():
        raise ValueError('Annual reproduction parity failed')
    return dict(passed=True, keys=len(rows), reference_keys=len(reference),
                missing_keys=0, extra_keys=0, max_absolute_difference=float(diff.max()),
                prediction_sha256=prediction_hash(new), **precision)


def fixed_squads(rows, features, predictions, season):
    validate(rows, features)
    # The shared replay API names its baseline "control" when computing deltas.
    result = phase2_execution.fixed_squad(rows, features,
        {'control': predictions['annual'], 'refit19': predictions['refit19']},
        season, opening_gw=20, count=20)
    result['totals']['annual'] = result['totals'].pop('control')
    return result


def gates(annual, refit, by_season, squad_delta):
    """All registered conditions are inclusive; HARM is a study outcome."""
    values = [squad_delta]
    for reports in [(annual, refit), *by_season.values()]:
        for report in reports:
            values.extend(report[u][m] for u in UNITS for m in ('rmse', 'mae'))
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite gate input')
    common = {f'{s}_{u}_rmse': dict(value=c[u]['rmse'], limit=1.005*a[u]['rmse'],
                passed=bool(c[u]['rmse'] <= 1.005*a[u]['rmse']))
              for s, (a, c) in by_season.items() for u in UNITS}
    common['mean_fixed_squad_delta'] = dict(value=float(squad_delta), limit=0,
                                            passed=bool(squad_delta >= 0))
    tables = {}
    for label, rmse, mae in [('BENEFIT', .995, 1.005), ('NO_HARM', 1., 1.)]:
        table = dict(common)
        for u in UNITS:
            for m, ratio in [('rmse', rmse), ('mae', mae)]:
                value, limit = refit[u][m], ratio*annual[u][m]
                table[f'pooled_{u}_{m}'] = dict(value=value, limit=limit, passed=bool(value <= limit))
        tables[label] = table
    passed = {label: all(c['passed'] for c in table.values()) for label, table in tables.items()}
    return dict(outcome='BENEFIT' if passed['BENEFIT'] else 'NO_HARM' if passed['NO_HARM'] else 'HARM',
                criteria=tables, passed=passed)


def score_windows(rows, features, predictions):
    validate(rows, features)
    return {arm: evaluate(rows, features, values) for arm, values in predictions.items()}


def block_intervals(rows, features, predictions):
    from fpl_model import candidate_mask
    validate(rows, features)
    pool = candidate_mask(features)
    frame = rows.loc[pool, ['season', 'GW', 'element', 'points_core']].rename(
        columns={'GW': 'gameweek', 'points_core': 'actual'}).copy()
    for arm, values in predictions.items():
        frame[arm] = np.asarray(values)[pool.to_numpy()]
    grouped = frame.groupby(['season', 'gameweek', 'element'], as_index=False)[
        ['actual', *predictions]].sum()
    return {unit: paired_block_errors(f, 'refit19', 'annual', samples=1000,
                                      block_length=4, seed=20261015)
            for unit, f in [('candidate_fixture', frame), ('candidate_player_gw', grouped)]}
