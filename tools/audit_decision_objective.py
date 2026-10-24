"""Independent stdlib expectation audit for the fixed no-card appearance model.

Uses positional missing-count enumeration and feasibility capacities, rather
than the selector's NumPy bench-inclusion tensor. No ML or planner imports.
"""
from collections import Counter
from functools import lru_cache
from itertools import product
import math


def missing_distribution(probabilities):
    result = [0.] * (len(probabilities)+1)
    for active in product((0, 1), repeat=len(probabilities)):
        weight = math.prod(p if played else 1-p for p, played in zip(probabilities, active))
        result[len(active)-sum(active)] += weight
    return result


@lru_cache(maxsize=128)
def replacements(formation, bench_positions):
    table = {}
    for missing in product(*(range(n+1) for n in formation)):
        for active in product((0, 1), repeat=3):
            chosen = (0, 0, 0)
            for wanted in product((1, 0), repeat=3):
                if any(w > a for w, a in zip(wanted, active)):
                    continue
                incoming = tuple(sum(wanted[i] for i in range(3) if bench_positions[i] == p) for p in (2, 3, 4))
                count = sum(wanted)
                capacity = [min(m, n+added-minimum) for m, n, added, minimum
                            in zip(missing, formation, incoming, (3, 2, 1))]
                if min(capacity) >= 0 and sum(capacity) >= count:
                    chosen = wanted
                    break
            table[missing, active] = chosen
    return table


def expectation(selection, rows, chip=None):
    if chip not in (None, 'wildcard', 'freehit', '3xc', 'bboost'):
        raise ValueError('Unsupported chip')
    by = {r['id']: r for r in rows}
    start = selection['starters']
    bench = selection['bench']
    assert len(start) == len(set(start)) == 11 and len(bench) == len(set(bench)) == 4
    assert not set(start) & set(bench) and set(start) | set(bench) == set(by) and len(by) == 15
    assert Counter(r['position'] for r in rows) == {1: 2, 2: 5, 3: 5, 4: 3}
    formation = tuple(sum(by[i]['position'] == p for i in start) for p in (2, 3, 4))
    assert all(n >= m for n, m in zip(formation, (3, 2, 1)))
    assert sum(by[i]['position'] == 1 for i in start) == 1
    c, v = selection['captain'], selection['vice']
    assert c != v and {c, v} <= set(start)
    for r in rows:
        assert math.isfinite(r['expected_points']) and math.isfinite(r['p_play']) and 0 <= r['p_play'] <= 1
        assert r['p_play'] > 0 or r['expected_points'] == 0
    bonus = by[c]['expected_points'] + (1-by[c]['p_play'])*by[v]['expected_points']
    if chip == 'bboost':
        return sum(r['expected_points'] for r in rows)+bonus
    keeper = next(i for i in start if by[i]['position'] == 1)
    reserve = next(i for i in bench if by[i]['position'] == 1)
    value = sum(by[i]['expected_points'] for i in start)+(1-by[keeper]['p_play'])*by[reserve]['expected_points']
    outbench = [i for i in bench if by[i]['position'] != 1]
    distributions = [missing_distribution([by[i]['p_play'] for i in start if by[i]['position'] == p]) for p in (2, 3, 4)]
    table = replacements(formation, tuple(by[i]['position'] for i in outbench))
    conditional = [by[i]['expected_points']/by[i]['p_play'] if by[i]['p_play'] else 0. for i in outbench]
    for missing in product(*(range(len(d)) for d in distributions)):
        absent_weight = math.prod(d[k] for d, k in zip(distributions, missing))
        for active in product((0, 1), repeat=3):
            active_weight = math.prod(by[i]['p_play'] if played else 1-by[i]['p_play'] for i, played in zip(outbench, active))
            selected = table[missing, active]
            value += absent_weight*active_weight*sum(q for q, used in zip(conditional, selected) if used)
    return value+(2 if chip == '3xc' else 1)*bonus
