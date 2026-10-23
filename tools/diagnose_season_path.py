"""Read-only, outcome-aware attribution of an already frozen 38-GW path.

Hindsight headroom is diagnostic, not an executable strategy or causal loss.
This tool never alters a forecast, selects a policy, or writes account state.
Run from source with PYTHONPATH=src and keep all per-path outputs private.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
from forecast import select_xi
from season_benchmark import read_bundle, forecast
from season_engine import State, Market, Action, prepare, settle


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _state(raw):
    return State(**dict(raw, holdings=tuple(map(tuple, raw['holdings'])),
                        used_chips=tuple(map(tuple, raw['used_chips']))))


def _action(raw):
    return Action(**{k: tuple(v) if k in ('buys', 'sells', 'starters', 'bench') else v
                     for k, v in raw.items()})


def diagnose(bundle, outcomes, directory, horizon):
    """Reconcile every frozen action before computing outcome-aware diagnostics."""
    if type(horizon) is not int or not 1 <= horizon <= 8:
        raise ValueError('Invalid horizon')
    weeks = bundle['weeks']
    if len(weeks) != 38 or len(outcomes['weeks']) != 38:
        raise ValueError('Require a complete season, including confirmed blanks')
    directory = Path(directory)
    rows = []; components = Counter(); groups = defaultdict(list); revisions = []
    previous = None; cumulative = 0.; signatures = {}; forecast_fingerprints = []
    for spec in weeks:
        m = Market.create(**spec['market']); g = m.gameweek
        if g != len(rows) + 1:
            raise ValueError('Origins must be chronological 1..38')
        h = forecast(m, spec['forecast'], horizon); xp = h.values()
        decision = directory / f'GW{g:02d}_decision.json'
        settlement = directory / f'GW{g:02d}_settled.json'
        d = json.loads(decision.read_text()); z = json.loads(settlement.read_text())
        if z['score']['decision_sha256'] != digest(decision):
            raise ValueError('Frozen decision checksum mismatch')
        if d['gameweek'] != g or d['inputs_as_of'] != m.as_of:
            raise ValueError('Decision origin differs')
        expected_prov = {**dict(h.provenance), 'source_hashes': dict(h.provenance['source_hashes'])}
        if d['forecast_provenance'] != expected_prov:
            raise ValueError('Forecast identity differs')
        s = _state(d['state_before']); a = _action(d['action'])
        if previous is not None:
            # Topups are revealed at this actual origin by the benchmark.
            from dataclasses import replace
            from season_engine import available_transfers, rules_for
            previous = replace(previous, free_transfers=available_transfers(previous, rules_for(previous.season)))
            if asdict(s) != asdict(previous):
                raise ValueError('Discontinuous carried state')
        elif s.gameweek != 1 or s.holdings or s.bank != 1000 or s.total_points != 0:
            raise ValueError('Invalid opening state')
        if asdict(a) != asdict(_action(d['provisional_actions'][0])):
            raise ValueError('Executed action differs from frozen first action')
        hidden = {int(i): v for i, v in outcomes['weeks'][str(g)].items()}
        prepared = prepare(s, m, a)
        if not set(i for i, _ in prepared.state.used_chips).issubset({'wildcard', 'freehit', 'bboost', '3xc'}):
            raise ValueError('Unsupported chip')
        if set(prepared.state.used_chips).intersection(map(tuple, spec['blocked_tokens'])):
            raise ValueError('Used blocked token')
        after, score = settle(prepared, hidden)
        if asdict(after) != asdict(_state(z['state_after'])):
            raise ValueError('Frozen final state differs')
        supplied = dict(z['score']); supplied.pop('decision_sha256')
        # JSON turns scoring tuples into lists; canonical serialisation compares both.
        if json.dumps(score, sort_keys=True) != json.dumps(supplied, sort_keys=True):
            raise ValueError('Frozen score differs')
        by = {p['id']: dict(p) for p in prepared.squad}; ids = set(by)
        if not ids <= set(hidden):
            raise ValueError('Missing outcomes')
        if any(not math.isfinite(v[k]) for i in ids for k in ('actual', 'minutes', 'cards') for v in [hidden[i]]):
            raise ValueError('Nonfinite outcome')
        # Optimistic within-owned hindsight XI. This ignores forecasts on purpose
        # and is never fed back into the policy or interpreted as attainable gain.
        oracle = select_xi([dict(p, expected_points=hidden[i]['actual']) for i, p in by.items()])
        playing = [hidden[i]['actual'] for i in ids if hidden[i]['minutes'] > 0]
        oracle_cap = max([0., *playing])
        actual_cap = score['captain_bonus']
        base_actual = score['base_xi'] + score['autosub_delta']
        if a.chip == 'bboost':
            oracle_base = sum(hidden[i]['actual'] for i in ids)
            base_actual += score['bench_boost_points']
        else:
            oracle_base = sum(hidden[i]['actual'] for i in oracle['starters'])
        factor = 2 if a.chip == '3xc' else 1
        row = dict(gameweek=g, net_points=score['net_points'], hits=score['hits'],
                   transfers=score['transfers'], chip=a.chip, bank_tenths=after.bank,
                   free_transfers=after.free_transfers,
                   owned_hindsight_base_headroom=oracle_base-base_actual,
                   owned_hindsight_captain_headroom=factor*(oracle_cap-actual_cap),
                   zero_minute_starters=sum(hidden[i]['minutes'] == 0 for i in a.starters),
                   cameos_in_xi=sum(0 < hidden[i]['minutes'] < 60 for i in a.starters))
        if row['owned_hindsight_base_headroom'] < -1e-7 or row['owned_hindsight_captain_headroom'] < -1e-7:
            raise ValueError('Impossible hindsight upper comparator')
        for i in ids:
            error = xp[g, i] - hidden[i]['actual']
            key = 'zero' if hidden[i]['minutes'] == 0 else 'cameo' if hidden[i]['minutes'] < 60 else '60plus'
            groups[key].append(error); groups[f'GW{1 if g <= 13 else 14 if g <= 26 else 27}onward'].append(error)
        for key in ('base_xi', 'autosub_delta', 'captain_bonus', 'extra_captain_bonus', 'bench_boost_points', 'hits'):
            components[key] += score.get(key, 0.)
        if rows and len(prior_actions) > 1:
            planned = prior_actions[1]
            revisions.append(dict(gameweek=g, changed_buys=set(planned['buys']) != set(a.buys),
                                  changed_sells=set(planned['sells']) != set(a.sells),
                                  changed_chip=planned['chip'] != a.chip))
        prior_actions = d['provisional_actions']; previous = after; rows.append(row)
        cumulative += score['net_points']; signatures[str(g)] = dict(decision=digest(decision), settlement=digest(settlement))
        forecast_fingerprints.append(hashlib.sha256(json.dumps(expected_prov, sort_keys=True).encode()).hexdigest())
    expected = json.loads((directory/'summary.json').read_text())
    if expected['net_points'] != cumulative or expected['hits'] != components['hits']:
        raise ValueError('Path summary mismatch')
    stats = {key: dict(n=len(e), bias=sum(e)/len(e), mae=sum(map(abs, e))/len(e),
                      rmse=math.sqrt(sum(v*v for v in e)/len(e))) for key, e in sorted(groups.items())}
    return dict(schema_version=1, complete=True, season=previous.season, deadlines=38,
                net_points=cumulative, components=dict(components), rows=rows,
                owned_error_groups=stats, provisional_revisions=revisions,
                input_decision_hashes=signatures, forecast_identity_hashes=forecast_fingerprints,
                scope='Outcome-aware fixed-path attribution; hindsight gaps are unattainable diagnostics, not causal or achievable losses. Owned error cohorts differ by policy; no across-policy predictive ranking. No policy/forecast promotion.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('decisions', 'outcomes'):
        p.add_argument('--'+name, type=Path, required=True); p.add_argument('--'+name+'-sha256', required=True)
    p.add_argument('--season-dir', type=Path, required=True); p.add_argument('--horizon', type=int, required=True)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    if a.output.exists(): p.error('Output exists; preserve evidence')
    for name in ('decisions', 'outcomes'):
        if digest(getattr(a, name)) != getattr(a, name+'_sha256'): p.error('Input checksum mismatch')
    result = diagnose(read_bundle(a.decisions), read_bundle(a.outcomes), a.season_dir, a.horizon)
    result['input_sha256'] = {name: digest(getattr(a, name)) for name in ('decisions', 'outcomes')}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as stream: json.dump(result, stream, indent=2, allow_nan=False)


if __name__ == '__main__': main()
