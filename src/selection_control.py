"""Optional first-action selection control, preserving mean-manager proposals.

This is decision isolation, not a calibrated appearance model or a promotion.
The caller supplies verified, origin-matched probability/source receipts.
"""
from dataclasses import asdict, replace
import math
import time
from availability_evidence import utc
from decision_value import players, select, objective
from native_planner import retained_bound
from rolling_planner import _market, _objective
from season_engine import prepare


class FirstActionSelection:
    def __init__(self, manager, availability):
        if not callable(manager):
            raise ValueError('An explicit mean management policy is required')
        self.manager = manager
        self.availability = availability

    def __call__(self, state, market, horizon, *, settings, policy, blocked, opening_ids):
        tick = time.monotonic()
        a = self.availability
        if (a['gameweek'], a['as_of']) != (market.gameweek, market.as_of) or utc(a['trained_through']) >= utc(market.as_of):
            raise ValueError('Appearance origin/fit differs')
        rows = [r for r in a['rows'] if r['gameweek'] == market.gameweek]
        probabilities = {r['id']: r['p_play'] for r in rows}
        if len(rows) != len(probabilities) or set(probabilities) != {r['id'] for r in market.players}:
            raise ValueError('Incomplete/duplicate current appearance grid')
        xp = horizon.values()
        if any(not math.isfinite(p) or not 0 <= p <= 1 or p == 0 and xp[market.gameweek,i] != 0
               for i,p in probabilities.items()):
            raise ValueError('Invalid/incoherent appearance marginal')
        actions, original = self.manager(state, market, horizon, settings=settings,
            policy=policy, blocked=blocked, opening_ids=opening_ids)
        if len(actions) != len(horizon.gameweeks) or 'decision_objective' in original:
            raise ValueError('Require a complete mean-management proposal, without expected reranking')
        first = actions[0]
        m = _market(market, market.gameweek, xp)
        before = prepare(state, m, first)
        d = players([dict(p) for p in before.squad],
            {p['id']: probabilities[p['id']] for p in before.squad}, check_clubs=False)
        choice = select(d, first.chip, check_clubs=False)
        changed = replace(first, starters=tuple(choice['starters']), bench=tuple(choice['bench']),
            captain=choice['captain'], vice=choice['vice'])
        after = prepare(state, m, changed)
        if before.state != after.state or before.hits != after.hits:
            raise ValueError('Selection changed financial/chip transition')
        proposed = list(actions)
        selected = [changed, *proposed[1:]]
        value, parts = _objective(state, market, horizon, selected, settings)
        source_bound = original['selected_schedule_bound']
        # The mean objective/problem is unchanged, so a verified source upper
        # bound may be rebased to this feasible mean-valued plan. It says nothing
        # about the expected-autosub selection objective or global chip search.
        bound = retained_bound(value, source_bound['upper_objective'], source_bound['status'])
        if bound['status'] == 'inconsistent_dual':
            raise ValueError('Source mean bound inconsistent with selected plan')
        source_value, _ = _objective(state, market, horizon, proposed, settings)
        if abs(source_value-original['objective']) > 1e-6:
            raise ValueError('Source mean objective does not reconcile')
        original_expected=objective(first.selection(),d,first.chip,check_clubs=False)
        selected_expected=objective(choice,d,first.chip,check_clubs=False)
        report = dict(original)
        for key in ('trials', 'scenario_objectives', 'total_proxy'):
            if key in report: report['proposal_'+key] = report.pop(key)
        report.update(objective=value, components=parts, selected_schedule_bound=bound,
            global_chip_search_bound=None, proposal_selected_schedule_bound=source_bound,
            proven_optimal=bool(original.get('proven_optimal',False) and bound['relative_gap'] is not None and bound['relative_gap'] < 1e-7),
            mip_gap=None,
            proposal_mean_objective=source_value,
            objective_scope='Retained mean objective for admission; transfer/chip search unchanged, first selection uses expected legal scoring',
            selection_control=dict(origin=market.gameweek, original_first_action=asdict(first),
                expected_before_hits=original_expected,
                expected_after_hits=selected_expected,
                expected_original_before_transfer_hits=original_expected,
                expected_original_after_transfer_hits=original_expected-after.hits,
                expected_selected_before_transfer_hits=selected_expected,
                transfer_hit_points=after.hits,
                expected_selected_after_transfer_hits=selected_expected-after.hits,
                legacy_expected_fields_scope='Legacy before/after fields describe original/selected lineups; both exclude transfer hits',
                expected_objective_bound=None, financial_transition_unchanged=True,
                future_provisional_actions_unchanged=selected[1:]==proposed[1:]),
            availability_provenance={k:a[k] for k in ('gameweek','as_of','trained_through','model_sha256','decision_sha256','calendar_sha256')},
            seconds=time.monotonic()-tick,
            scope='First-action lineup/bench/captain/vice isolation only; source transfers/chips/future actions preserved; no full-manager superiority or automatic production approval')
        return selected, report
