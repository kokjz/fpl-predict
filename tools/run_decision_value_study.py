"""Frozen-roster decision overlays; no forecasting fit or account interaction.

Freeze selections before loading evaluator outcomes. Financially unchanged
overlays are not a new adaptive transfer/chip-policy benchmark.
"""
from dataclasses import asdict
import gzip
import importlib.util
import json
from pathlib import Path
from statistics import mean
import time
from availability_evidence import utc
from decision_value import players, select, objective, realised, dependence_stress
from expected_selection import select as old_select
from experiment_runner import file_hash
from horizon_forecast import Horizon
from season_engine import State, Market, Action, prepare

ROOT = Path(__file__).resolve().parents[1]
ARMS = ('saved_mean', 'legacy_expected_no_chip', 'chip_aware_expected')


def freeze_panel(raw, spec, availability):
    market = Market.create(**spec['market'])
    horizon = Horizon.create(market, **spec['forecast'])
    if (raw['gameweek'], raw['inputs_as_of']) != (market.gameweek, market.as_of):
        raise ValueError('Saved state origin differs')
    if raw['forecast_provenance'] != dict(horizon.provenance):
        raise ValueError('Saved forecast lineage differs')
    if availability['gameweek'] != market.gameweek or availability['as_of'] != market.as_of:
        raise ValueError('Appearance origin differs')
    if utc(availability['trained_through']) >= utc(market.as_of):
        raise ValueError('Appearance fit is after origin')
    state_data = dict(raw['state_before'], total_points=0.)
    for field in ('holdings', 'used_chips'):
        state_data[field] = tuple(map(tuple, state_data[field]))
    state = State(**state_data)
    action = Action(**{k: tuple(v) if k in ('buys', 'sells', 'starters', 'bench') else v
                       for k, v in raw['action'].items()})
    prepared = prepare(state, market, action)
    xp = horizon.values()
    squad = [dict(r, expected_points=xp[market.gameweek, r['id']]) for r in prepared.squad]
    probability_rows = [r for r in availability['rows'] if r['gameweek'] == market.gameweek]
    if len(probability_rows) != len(market.players) or len({r['id'] for r in probability_rows}) != len(probability_rows):
        raise ValueError('Incomplete/duplicate appearance grid')
    all_p = {r['id']: r['p_play'] for r in probability_rows}
    d = players(squad, {r['id']: all_p[r['id']] for r in squad})
    tick = time.monotonic()
    legacy = old_select(d)
    legacy_seconds = time.monotonic()-tick
    tick = time.monotonic()
    new = select(d, action.chip) if action.chip in ('bboost', '3xc') else dict(legacy)
    new_seconds = time.monotonic()-tick if action.chip in ('bboost', '3xc') else legacy_seconds
    selections = dict(saved_mean=action.selection(), legacy_expected_no_chip=legacy, chip_aware_expected=new)
    expectations = {name: objective(value, d, action.chip) for name, value in selections.items()}
    if expectations['chip_aware_expected'] < max(expectations.values())-1e-8:
        raise ValueError('Exact selection failed its declared objective')
    return dict(gameweek=market.gameweek, as_of=market.as_of, state_before=state_data,
        original_action=asdict(action), roster=d, hits=prepared.hits, chip=action.chip,
        selections=selections, expected_values=expectations,
        dependence_stress={name: dependence_stress(value, d, action.chip) for name, value in selections.items()},
        appearance_rows=[r for r in probability_rows if r['id'] in {p['id'] for p in d}],
        new_selection_seconds=new_seconds, legacy_selection_seconds=legacy_seconds,
        expected_mean_preserved=True)


def freeze_case(decisions, availability, record_directory, output):
    out = Path(output).resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise ValueError('Require new private frozen file')
    if len(decisions) != 38 or len(availability) != 38:
        raise ValueError('Require complete source origins')
    rows = []
    for g, (spec, sidecar) in enumerate(zip(decisions, availability), 1):
        path = Path(record_directory)/f'GW{g:02d}_decision.json'
        row = freeze_panel(json.loads(path.read_text()), spec, sidecar)
        row['original_decision_sha256'] = file_hash(path)
        rows.append(row)
    if [r['gameweek'] for r in rows] != list(range(1, 39)):
        raise ValueError('Nonchronological frozen decisions')
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, 'xt') as stream:
        json.dump(dict(complete=True, rows=rows, evaluator_read=False), stream,
                  separators=(',', ':'), allow_nan=False)
    return dict(file=out.name, sha256=file_hash(out), panels=38,
                mean_new_selection_seconds=mean(r['new_selection_seconds'] for r in rows))


def independent_auditor():
    spec = importlib.util.spec_from_file_location('decision_overlay_audit', ROOT/'tools/audit_season_path.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate_case(frozen, frozen_sha256, decisions, outcomes, original_net_points):
    if file_hash(frozen) != frozen_sha256:
        raise ValueError('Frozen selection checksum differs')
    from season_benchmark import read_bundle
    data = read_bundle(frozen)
    if not data['complete'] or data['evaluator_read'] or len(data['rows']) != 38:
        raise ValueError('Incomplete/unfrozen selection evidence')
    audit = independent_auditor()
    totals = {name: 0. for name in ARMS}
    components = {name: {} for name in ARMS}
    changes = {name: 0 for name in ARMS}
    calibration = dict(n=0, raw_squared_error=0., regularised_squared_error=0.)
    for panel, spec in zip(data['rows'], decisions):
        g = panel['gameweek']
        hidden = outcomes[g]
        baseline_state = None
        for arm in ARMS:
            selection = panel['selections'][arm]
            action = dict(panel['original_action'], **{k: selection[k] for k in ('starters', 'bench', 'captain', 'vice')})
            financial, ids, hits, transfers = audit.advance(panel['state_before'], spec['market'], action, spec['blocked_tokens'])
            if baseline_state is None:
                baseline_state = financial
            if financial != baseline_state or hits != panel['hits']:
                raise ValueError('Selection overlay changed financial/chip state')
            total, parts = audit.actual(action, spec['market'], hidden, hits)
            if abs(total-realised(selection, panel['roster'], hidden, panel['chip'], hits)) > 1e-9:
                raise ValueError('Independent score does not reconcile')
            totals[arm] += total
            for k, v in parts.items():
                components[arm][k] = components[arm].get(k, 0.)+v
            saved = panel['selections']['saved_mean']
            if any(selection[k] != saved[k] for k in ('starters', 'bench', 'captain', 'vice')):
                changes[arm] += 1
        for r in panel['appearance_rows']:
            y = float(hidden[r['id']]['minutes'] > 0)
            calibration['n'] += 1
            calibration['raw_squared_error'] += (r['raw_p_play']-y)**2
            calibration['regularised_squared_error'] += (r['p_play']-y)**2
    if abs(totals['saved_mean']-original_net_points) > 1e-9:
        raise ValueError('Original full-season score differs')
    return dict(net_points=totals, components=components, changed_selections=changes,
                mean_new_selection_seconds=mean(p['new_selection_seconds'] for p in data['rows']),
                calibration=calibration, independently_reconciled_scores=38*len(ARMS),
                independently_reconciled_financial_states=38*len(ARMS),
                mean_preservation_verified=True,
                scope='Fixed-roster/chip/transfer selection overlay, not a new adaptive manager')


def progression(rows, protocol):
    """All four saved H6 cases are mandatory; never omit a losing opening."""
    p = protocol['fixed_roster_pilot']
    expected = {(s, n) for s in protocol['seasons'] for n in protocol['opening_seeds']}
    if len(rows) != len(expected) or {(r['season'], r['seed']) for r in rows} != expected:
        raise ValueError('Missing/duplicate pilot case')
    deltas = [dict(season=r['season'], seed=r['seed'], difference=
        r['net_points']['chip_aware_expected']-r['net_points']['saved_mean']) for r in rows]
    season_means = {s: mean(r['difference'] for r in deltas if r['season'] == s) for s in protocol['seasons']}
    gain = mean(season_means.values())
    cost = mean(r['mean_new_selection_seconds'] for r in rows)
    g = p['progression']
    admitted = (gain > 0 and min(season_means.values()) >= -g['season_average_loss_limit']
                and min(r['difference'] for r in deltas) >= -g['single_opening_loss_limit']
                and cost <= p['cost_limit_mean_seconds_per_selection']
                and all(r['mean_preservation_verified'] and r['independently_reconciled_scores'] == 114 for r in rows))
    return dict(equal_season_mean_gain=gain, season_means=season_means, differences=deltas,
        mean_selection_seconds=cost, integration_admitted=admitted, model_promotion=False,
        policy_promotion=False, scope='Predeclared conditional research progression; two reused seasons, no generalisation interval')


def adaptive_case(decisions, outcomes, availability, output, *, policy_id, opening_ids,
                  native_python=None, solio_source=None, solio_site_packages=None):
    """One declared continuous policy path; caller locks all sources and inputs.

    Availability and decisions are supplied separately from evaluator outcomes.
    The manager sees only its current origin. Use the existing external watchdog
    for whole-process memory/time/storage limits and retain raw attempts.
    """
    import contextlib
    from season_benchmark import run, Policy
    from decision_management import DecisionManager
    from native_planner import NativeProcess, NativePlanner, CanonicalPlanner
    from season_qualification import Trace, Guarded
    from rolling_planner import Settings
    allowed = ('standingH1_adaptive', 'standingH6_adaptive', 'decisionH6_adaptive',
               'SolioAdaptedH6_sharedAdaptiveChips')
    if policy_id not in allowed:
        raise ValueError('Undeclared adaptive policy')
    out = Path(output).resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise ValueError('Require new private output directory')
    out.mkdir(parents=True)
    trace = None
    native_metadata = None
    with contextlib.ExitStack() as stack:
        if policy_id.startswith('Solio'):
            if not all([native_python, solio_source, solio_site_packages]):
                raise ValueError('Admitted native runtime required')
            actor = stack.enter_context(NativeProcess(native_python, solio_source,
                out/'native_stderr.log', site_packages=solio_site_packages))
            trace = Trace(actor, out, 'solio', stack)
            native_metadata = actor.metadata
            inner = Guarded(CanonicalPlanner(NativePlanner(trace, canonicalise_dominated_paid=True)), out, trace)
        else:
            inner = Guarded(CanonicalPlanner(), out)
        settings = Settings(baseline_mode='feasibility', terminal_ft_value=0.,
                            terminal_squad_weight=0., churn_cost=0.)
        cfg = Policy(1 if policy_id.startswith('standingH1') else 6, True, 15., 2., 12)
        if policy_id.startswith('decision'):
            by = {r['gameweek']: r for r in availability}
            if len(by) != 38 or set(by) != set(range(1, 39)):
                raise ValueError('Incomplete appearance origins')
            def manager(state, market, horizon, **kwargs):
                return DecisionManager(by[market.gameweek], inner)(state, market, horizon, **kwargs)
            result = run(decisions, outcomes, out/'season', policy=cfg,
                opening_ids=opening_ids, settings=settings, management_policy=manager,
                management_policy_id='mean-preserving-expected-candidate-rerank-v1')
        else:
            result = run(decisions, outcomes, out/'season', policy=cfg,
                opening_ids=opening_ids, settings=settings, inner_planner=inner)
    result.update(policy_id=policy_id, native_runtime=native_metadata,
        native_calls=trace.calls if trace else 0, native_failed_attempts=trace.failed if trace else 0,
        model_promotion=False, production_policy_promotion=False)
    (out/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result
