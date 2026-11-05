from types import SimpleNamespace
import json

import numpy as np
import pandas as pd
import pytest

import in_season_refit as m


def example():
    # The low-GW postponed match is after GW20's deadline and must be excluded.
    d = pd.DataFrame(dict(season=['2022-23', '2023-24', '2023-24', '2023-24', '2023-24'],
        element=[1]*5, fixture=range(1, 6), GW=[38, 18, 7, 20, 21],
        ts=pd.to_datetime(['2023-05-01', '2023-12-18', '2024-01-21', '2024-01-03', '2024-01-10'], utc=True),
        cutoff=pd.to_datetime(['2023-04-30', '2023-12-17', '2023-09-01', '2024-01-01', '2024-01-08'], utc=True),
        points_core=[1., 2., 3., 4., 5.]))
    x = pd.DataFrame(1., index=d.index, columns=m.CORE_FEATURES)
    return d, x


def test_match_time_cutoff_excludes_postponement_and_strict_boundary():
    d, x = example()
    annual, test = m.masks(d, '2023-24', 'annual')
    refit, _ = m.masks(d, '2023-24', 'refit19')
    assert list(d.index[annual]) == [0]
    assert list(d.index[refit]) == [0, 1]
    assert list(d.index[test]) == [3, 4]
    d.loc[1, 'ts'] = d.loc[3, 'cutoff']
    assert list(d.index[m.masks(d, '2023-24', 'refit19')[0]]) == [0]


def test_leakage_refuses_earlier_season_played_after_deadline():
    d, _ = example()
    d.loc[0, 'ts'] = d.loc[3, 'cutoff']
    with pytest.raises(ValueError, match='leakage'):
        m.masks(d, '2023-24', 'annual')


@pytest.mark.parametrize('where', ['validate', 'masks', 'squads', 'precision'])
def test_future_refused_before_work(where):
    d, x = example()
    d.loc[0, 'season'] = '2026-27'
    with pytest.raises(ValueError, match='[Ff]uture|[Hh]istorical'):
        if where == 'validate':
            m.validate(d, x)
        elif where == 'masks':
            m.masks(d, '2023-24', 'annual')
        elif where == 'squads':
            m.fixed_squads(d, x, {}, '2023-24')
        else:
            m.decimal_precision_sample(['{"season":"2026-27","model":1.0}'])


def test_recipe_is_reused_and_clipped_with_original_ewm(monkeypatch):
    d, x = example()
    x.loc[3:, 'ew4_points_core'] = [4., 8.]
    recipe = m.recipe(SimpleNamespace(core_name='incumbent_test_name', blend=.75))
    seen = {}
    def fit(name, xx, yy, weights):
        seen.update(name=name, index=list(xx.index), target=list(yy), weights=weights)
        return SimpleNamespace(predict=lambda xx: np.array([-2., 30.]))
    monkeypatch.setattr(m, 'fit_estimator', fit)
    result = m.fit_predict(d, x, '2023-24', 'annual', recipe)
    assert seen['name'] == 'incumbent_test_name' and seen['index'] == [0]
    assert seen['target'] == [1.] and seen['weights'].tolist() == [1.]
    np.testing.assert_array_equal(result, [1., 17.])


def keys():
    return pd.DataFrame({'season': ['2024-25']*2, 'element': [8, 9], 'fixture': [1, 2]})


def test_parity_rounding_and_reordering():
    d = keys()
    ref = d.assign(model=[1.123456789, 0.]).iloc[::-1]
    precision = m.decimal_precision_sample([
        '{"season":"2024-25","model":1.1234567890}',
        '{"season":"2024-25","model":0}'])
    result = m.parity(d, [1.12345678904, 1e-10], ref, precision)
    assert result['keys'] == result['reference_keys'] == 2
    assert result['max_decimals'] == 10 and result['rule'] == 'absolute_1e-9'
    assert result['max_absolute_difference'] == pytest.approx(1e-10)
    with pytest.raises(ValueError, match='parity failed'):
        m.parity(d, [1.1234568, 0.], ref, precision)


def test_high_precision_uses_original_relative_rule_and_exact_zero():
    precision = m.decimal_precision_sample(['{"season":"2024-25","model":1.12345678901}'])
    assert precision['rule'] == 'relative_1e-12' and precision['max_decimals'] == 11
    d = keys()
    ref = d.assign(model=[10., 0.])
    m.parity(d, [10.+1e-12, 0.], ref, precision)
    with pytest.raises(ValueError, match='parity failed'):
        m.parity(d, [10., 1e-16], ref, precision)


@pytest.mark.parametrize('bad', ['missing', 'extra', 'duplicate', 'changed'])
def test_key_set_mismatch_refused(bad):
    d = keys(); ref = d.assign(model=[1., 2.])
    if bad == 'missing': ref = ref.iloc[:1]
    if bad == 'extra': ref = pd.concat([ref, ref.iloc[:1].assign(element=22)])
    if bad == 'duplicate': ref.loc[1, ['element', 'fixture']] = [8, 1]
    if bad == 'changed': ref.loc[1, 'element'] = 99
    with pytest.raises(ValueError, match='keys|sets'):
        m.parity(d, [1., 2.], ref, {'rule': 'absolute_1e-9'})


def report(rmse=3., mae=2.):
    return {u: dict(rmse=rmse, mae=mae) for u in m.UNITS}


@pytest.mark.parametrize('ratio,mae,delta,label', [(.995, 1.005, 0., 'BENEFIT'),
    (1., 1., 0., 'NO_HARM'), (1.000001, 1., 0., 'HARM'), (.99, .99, -.01, 'HARM')])
def test_gate_boundaries(ratio, mae, delta, label):
    a, c = report(), report(3.*ratio, 2.*mae)
    result = m.gates(a, c, {s:(a,c) for s in m.SEASONS}, delta)
    assert result['outcome'] == label


def test_season_guard_can_override_pooled_benefit():
    a, c = report(), report(2.9, 1.9)
    seasons = {s:(a,c) for s in m.SEASONS}
    seasons['2024-25'] = (a, report(3.*1.0050001, 1.9))
    assert m.gates(a,c,seasons,10.)['outcome'] == 'HARM'


def test_fixed_squad_uses_exact_shared_historical_call(monkeypatch):
    d, x = example(); p = {'annual': np.array([1.,2.]), 'refit19': np.array([3.,4.])}
    def shared(rows, features, predictions, season, **kw):
        assert rows is d and features is x
        assert predictions['control'] is p['annual'] and predictions['refit19'] is p['refit19']
        assert season == '2023-24' and kw == dict(opening_gw=20, count=20)
        return {'totals': {'control': [1.]*20, 'refit19': [2.]*20}}
    monkeypatch.setattr(m.phase2_execution, 'fixed_squad', shared)
    assert m.fixed_squads(d,x,p,'2023-24')['totals']['refit19'] == [2.]*20


def test_alignment_and_bad_prediction_refused():
    d, x = example()
    with pytest.raises(ValueError, match='alignment'):
        m.validate(d,x.iloc[::-1])
    with pytest.raises(ValueError, match='prediction'):
        m.prediction_hash([float('nan')])


def test_empty_and_non_numeric_precision_refused():
    for lines in [[], ['{"season":"2024-25","model":"1.2"}']]:
        with pytest.raises(ValueError): m.decimal_precision_sample(lines)
