"""Optional mean-preserving, chip-aware fixed-squad decision research.

Appearance marginals and conditional returns are modelling assumptions, not a
joint calibrated injury model. This module never fits or promotes a forecaster.
"""
from itertools import combinations, permutations
import math
import numpy as np
from expected_selection import validate, bench_value, objective as legacy_objective
from expected_selection import select as legacy_select
from selection_benchmark import score

CHIPS = (None, 'wildcard', 'freehit', 'bboost', '3xc')


def players(squad, probabilities):
    """Keep unconditional means exactly; do not multiply them by appearance.

    The caller supplies a source-validated player-GW probability. Zero probability
    and a nonzero unconditional mean are incoherent and fail explicitly.
    """
    if set(probabilities) != {r['id'] for r in squad}:
        raise ValueError('Appearance coverage differs from squad')
    result = []
    for r in squad:
        p = probabilities[r['id']]
        xp = r['expected_points']
        if not math.isfinite(p) or not 0 <= p <= 1 or not math.isfinite(xp):
            raise ValueError('Invalid marginal forecast')
        if p == 0 and xp != 0:
            raise ValueError('Nonzero unconditional mean with zero appearance')
        result.append(dict(id=r['id'], position=r['position'], team=r['team'],
                           expected_points=xp, p_play=p,
                           conditional_points=xp / p if p else 0.))
    return validate(result)


def captain_value(selection, by):
    c, v = by[selection['captain']], by[selection['vice']]
    return c['expected_points'] + (1 - c['p_play']) * v['expected_points']


def objective(selection, rows, chip=None):
    if chip not in CHIPS:
        raise ValueError('Unsupported chip')
    d = validate(rows)
    if any(r.get('p_card_only', 0.) for r in d):
        raise ValueError('This fixed policy assumes no predicted card-only events')
    by = {r['id']: r for r in d}
    ordinary = legacy_objective(selection, d)  # Includes selection/formation guards.
    bonus = captain_value(selection, by)
    if chip == 'bboost':
        return float(sum(r['expected_points'] for r in d) + bonus)
    return float(ordinary + (bonus if chip == '3xc' else 0.))


def select(rows, chip=None):
    """Exact optimum under the stated independent-marginal mean model.

    Normal chips reuse the earlier exact selector as a control. TC optimises a
    doubled armband/fallback bonus; BB counts all 15 without adding autosubs.
    The optimum is conditional on this fixed roster and probability assumption.
    """
    if chip not in CHIPS:
        raise ValueError('Unsupported chip')
    d = validate(rows)
    if any(r.get('p_card_only', 0.) for r in d):
        raise ValueError('This fixed policy assumes no predicted card-only events')
    if chip not in ('bboost', '3xc'):
        return legacy_select(d)
    out = [r for r in d if r['position'] != 1]
    keepers = [r for r in d if r['position'] == 1]
    by_id = {r['id']: k for k, r in enumerate(d)}
    xp = np.array([r['expected_points'] for r in d])
    p = np.array([r['p_play'] for r in d])
    bonus = xp[:, None] + (1 - p[:, None]) * xp[None, :]
    np.fill_diagonal(bonus, -np.inf)
    best = None
    for ix in combinations(range(13), 10):
        starts = [out[i] for i in ix]
        if any(sum(r['position'] == pos for r in starts) < minimum
               for pos, minimum in ((2, 3), (3, 2), (4, 1))):
            continue
        used = set(ix)
        bench = [out[i] for i in range(13) if i not in used]
        bench_best = (0., bench) if chip == 'bboost' else None
        if bench_best is None:
            for ordered in permutations(bench):
                value = bench_value(starts, ordered)
                if bench_best is None or value > bench_best[0] + 1e-12:
                    bench_best = (value, ordered)
        for keeper in keepers:
            reserve = next(r for r in keepers if r['id'] != keeper['id'])
            eleven = sorted([*starts, keeper], key=lambda r: r['id'])
            indices = [by_id[r['id']] for r in eleven]
            pair = bonus[np.ix_(indices, indices)]
            ci, vi = np.unravel_index(np.argmax(pair), pair.shape)
            if chip == 'bboost':
                value = float(xp.sum() + pair[ci, vi])
            else:
                value = (sum(r['expected_points'] for r in eleven) + bench_best[0]
                         + (1 - keeper['p_play']) * reserve['expected_points']
                         + 2 * pair[ci, vi])
            if best is None or value > best['expected_points'] + 1e-12:
                best = dict(starters=[r['id'] for r in eleven],
                            bench=[r['id'] for r in bench_best[1]] + [reserve['id']],
                            captain=eleven[ci]['id'], vice=eleven[vi]['id'],
                            expected_points=float(value))
    if best is None:
        raise ValueError('No legal selection')
    return best


def realised(selection, rows, outcomes, chip=None, hits=0):
    """Evaluate separately supplied results, including real card-only events."""
    if chip not in CHIPS:
        raise ValueError('Unsupported chip')
    result = score(selection, {r['id']: r for r in rows}, outcomes, hits)
    if chip == 'bboost':
        return float(sum(outcomes[r['id']]['actual'] for r in rows)
                     + result['captain_bonus'] - hits)
    return float(result['net_points'] +
                 (result['captain_bonus'] if chip == '3xc' else 0.))


def dependence_stress(selection, rows, chip=None, rho=.25):
    """Chosen-plan stress preserves marginals; rho is not estimated or tuned."""
    d = validate(rows)
    if not 0 <= rho <= 1:
        raise ValueError('Invalid dependence mixture')
    bounds = sorted({0., 1., *(r['p_play'] for r in d)})
    common = 0.
    for lo, hi in zip(bounds, bounds[1:]):
        u = (lo + hi) / 2
        outcomes = {r['id']: dict(actual=r['conditional_points'] if u < r['p_play'] else 0.,
                                  minutes=float(u < r['p_play']), cards=0.) for r in d}
        common += (hi - lo) * realised(selection, d, outcomes, chip)
    return float((1 - rho) * objective(selection, d, chip) + rho * common)
