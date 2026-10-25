"""Post-result fixed-roster selections; never a new adaptive policy or fit.

The caller freezes every panel before supplying evaluator outcomes. More than
three players at one club may be legally retained after a club move: financial
admission belongs to season_engine.prepare, not a fresh-squad club-count test.
"""
from dataclasses import asdict
from pathlib import Path
import gzip
import json
import time
from availability_evidence import utc
from decision_value import players, objective, select, realised
from expected_selection import select as legacy_select
from experiment_runner import file_hash
from horizon_forecast import Horizon
from season_engine import State, Market, Action, prepare
from run_decision_value_study import independent_auditor
from audit_decision_objective import expectation

ARMS = ('saved_mean', 'legacy_expected_no_chip', 'chip_aware_expected')
ROOT = Path(__file__).resolve().parents[1]


def freeze_panel(raw, spec, availability):
    market = Market.create(**spec['market'])
    horizon = Horizon.create(market, **spec['forecast'])
    if (raw['gameweek'], raw['inputs_as_of']) != (market.gameweek, market.as_of):
        raise ValueError('Saved state origin differs')
    if raw['forecast_provenance'] != dict(horizon.provenance):
        raise ValueError('Saved forecast lineage differs')
    if (availability['gameweek'], availability['as_of']) != (market.gameweek, market.as_of):
        raise ValueError('Appearance origin differs')
    if utc(availability['trained_through']) >= utc(market.as_of):
        raise ValueError('Appearance fit is after origin')
    state_data = dict(raw['state_before'], total_points=0.)
    for field in ('holdings', 'used_chips'):
        state_data[field] = tuple(map(tuple, state_data[field]))
    action = Action(**{k: tuple(v) if k in ('buys', 'sells', 'starters', 'bench') else v
                       for k, v in raw['action'].items()})
    prepared = prepare(State(**state_data), market, action)
    current = [r for r in availability['rows'] if r['gameweek'] == market.gameweek]
    if len(current) != len(market.players) or {r['id'] for r in current} != {r['id'] for r in market.players}:
        raise ValueError('Incomplete/duplicate appearance grid')
    probability = {r['id']: r['p_play'] for r in current}
    xp = horizon.values()
    squad = [dict(r, expected_points=xp[market.gameweek, r['id']]) for r in prepared.squad]
    d = players(squad, {r['id']: probability[r['id']] for r in squad}, check_clubs=False)
    tick = time.monotonic()
    legacy = legacy_select(d, check_clubs=False)
    new = select(d, action.chip, check_clubs=False) if action.chip in ('bboost', '3xc') else dict(legacy)
    selections = dict(saved_mean=action.selection(), legacy_expected_no_chip=legacy, chip_aware_expected=new)
    expected = {name: objective(value, d, action.chip, check_clubs=False) for name, value in selections.items()}
    if expected['chip_aware_expected'] < max(expected.values())-1e-8:
        raise ValueError('Exact selection fails its stated objective')
    return dict(gameweek=market.gameweek, as_of=market.as_of, state_before=state_data,
        original_action=asdict(action), roster=d, hits=prepared.hits, chip=action.chip,
        selections=selections, expected_values=expected, selection_seconds=time.monotonic()-tick,
        mean_preservation_verified=all(r['expected_points'] == xp[market.gameweek, r['id']] for r in d))


def freeze_case(decisions, availability, record_directory, output):
    out = Path(output).resolve()
    if out.exists() or out.is_relative_to(ROOT) or len(decisions) != 38 or len(availability) != 38:
        raise ValueError('Require new private output and 38 complete origins')
    rows = []
    for g, (spec, sidecar) in enumerate(zip(decisions, availability), 1):
        path = Path(record_directory)/f'GW{g:02d}_decision.json'
        panel = freeze_panel(json.loads(path.read_text()), spec, sidecar)
        if panel['gameweek'] != g:
            raise ValueError('Nonchronological origin')
        panel['original_decision_sha256'] = file_hash(path)
        rows.append(panel)
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, 'xt') as stream:
        json.dump(dict(complete=True, rows=rows, evaluator_read=False), stream,
                  separators=(',', ':'), allow_nan=False)
    return dict(file=out.name, sha256=file_hash(out), panels=38)


def evaluate_case(frozen, frozen_sha256, decisions, outcomes, original_net_points):
    if file_hash(frozen) != frozen_sha256:
        raise ValueError('Frozen selections changed')
    with gzip.open(frozen, 'rt') as stream:
        data = json.load(stream)
    if not data['complete'] or data['evaluator_read'] or len(data['rows']) != 38 or len(decisions) != 38:
        raise ValueError('Incomplete frozen case')
    audit = independent_auditor()
    totals = {name: 0. for name in ARMS}
    changes = {name: 0 for name in ARMS}
    expectations = {name: 0. for name in ARMS}
    for g, (panel, spec) in enumerate(zip(data['rows'], decisions), 1):
        if panel['gameweek'] != g or spec['market']['gameweek'] != g or not panel['mean_preservation_verified']:
            raise ValueError('Origin/mean identity differs')
        financial_control = None
        for arm in ARMS:
            selection = panel['selections'][arm]
            action = dict(panel['original_action'], **{k: selection[k] for k in ('starters', 'bench', 'captain', 'vice')})
            financial, ids, hits, _ = audit.advance(panel['state_before'], spec['market'], action, spec['blocked_tokens'])
            if financial_control is None:
                financial_control = financial
            if financial != financial_control or hits != panel['hits'] or set(ids) != {r['id'] for r in panel['roster']}:
                raise ValueError('Selection changed financial/chip/roster state')
            total, _ = audit.actual(action, spec['market'], outcomes[g], hits)
            if abs(total-realised(selection, panel['roster'], outcomes[g], panel['chip'], hits, check_clubs=False)) > 1e-9:
                raise ValueError('Independent scoring differs')
            totals[arm] += total
            if abs(expectation(selection, panel['roster'], panel['chip'])-panel['expected_values'][arm]) > 1e-8:
                raise ValueError('Independent expectation differs')
            expectations[arm] += panel['expected_values'][arm]
            if any(selection[k] != panel['selections']['saved_mean'][k] for k in ('starters', 'bench', 'captain', 'vice')):
                changes[arm] += 1
    if abs(totals['saved_mean']-original_net_points) > 1e-9:
        raise ValueError('Saved score differs from primary path')
    return dict(net_points=totals, expected_scores_without_hits=expectations,
        changed_selections=changes, mean_preservation_verified=True,
        independently_reconciled_scores=114, independently_reconciled_financial_states=114,
        independently_reconciled_expectations=114,
        scope='Post-result fixed-roster/chip/transfer selection overlay, not a new adaptive policy')
