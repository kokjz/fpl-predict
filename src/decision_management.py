"""Optional expected-value reranking of bounded mean-MILP season proposals.

The inner solvers still propose rosters under their original mean objective.
Reranking does not solve the global expected-autosub problem or certify it with
an unrelated mean-objective dual. Normal planner/default behaviour is unchanged.
"""
from dataclasses import replace
import math
import time
from adaptive_planner import plan_adaptive, Budget
from availability_evidence import utc
from decision_value import players, select, objective
from rolling_planner import Settings, plan, _market, _objective
from season_engine import prepare


def unknown_bound(value, scope):
    return dict(status='unavailable_changed_objective', feasible_objective=value,
        upper_objective=None, absolute_gap=None, relative_gap=None, scope=scope)


class DecisionInner:
    def __init__(self, availability, inner=plan):
        self.availability = availability
        self.inner = inner
        self.cache = {}
        self.selection_calls = 0

    def __call__(self, state, market, horizon, settings=None, **kwargs):
        tick = time.monotonic()
        cfg = settings or Settings()
        a = self.availability
        if cfg.terminal_ft_value or cfg.terminal_squad_weight or cfg.churn_cost:
            raise ValueError('Research comparison requires zero terminal/churn proxies')
        if (a['gameweek'], a['as_of']) != (market.gameweek, market.as_of) or utc(a['trained_through']) >= utc(market.as_of):
            raise ValueError('Appearance source origin/fit differs')
        expected_keys = {(g, r['id']) for g in horizon.gameweeks for r in market.players}
        rows = [r for r in a['rows'] if r['gameweek'] in horizon.gameweeks]
        probabilities = {(r['gameweek'], r['id']): r['p_play'] for r in rows}
        if set(probabilities) != expected_keys or len(rows) != len(probabilities):
            raise ValueError('Incomplete/duplicate appearance horizon')
        actions, original = self.inner(state, market, horizon, cfg, **kwargs)
        if len(actions) != len(horizon.gameweeks):
            raise ValueError('Incomplete proposal')
        current = state
        xp = horizon.values()
        result = []
        parts = []
        for g, action in zip(horizon.gameweeks, actions):
            m = _market(market, g, xp)
            before = prepare(current, m, action)
            squad = [dict(p) for p in before.squad]
            # prepare() has already enforced new-transfer club legality and
            # permits an unchanged grandfathered squad after a real club move.
            d = players(squad, {p['id']: probabilities[g, p['id']] for p in squad}, check_clubs=False)
            key = (g, tuple(sorted(p['id'] for p in d)), action.chip)
            if key not in self.cache:
                self.cache[key] = select(d, action.chip, check_clubs=False)
                self.selection_calls += 1
            choice = self.cache[key]
            changed = replace(action, starters=tuple(choice['starters']), bench=tuple(choice['bench']),
                              captain=choice['captain'], vice=choice['vice'])
            after = prepare(current, m, changed)
            if before.state != after.state or before.hits != after.hits:
                raise ValueError('Selection changed financial/chip transition')
            value = objective(choice, d, action.chip, check_clubs=False)-after.hits
            if not math.isfinite(value):
                raise ValueError('Nonfinite decision value')
            parts.append(dict(gameweek=g, expected_score_before_hits=value+after.hits, hits=after.hits))
            result.append(changed)
            current = after.state
        value = sum(p['expected_score_before_hits']-p['hits'] for p in parts)
        mean_value, _ = _objective(state, market, horizon, result, cfg)
        # This temporary report is consumed by the generic outer chip search.
        # Its objective and bounds consistently describe the expected decision
        # value. The public management adapter restores the mean admission field.
        report = dict(original, objective=value, components=dict(expected_weeks=parts),
            selected_plan_bound=unknown_bound(value, 'Expected-value rerank; original mean dual is inapplicable'),
            proven_optimal=False, mip_gap=None, proposal_mean_objective=original['objective'],
            proposal_mean_bound=original['selected_plan_bound'], retained_mean_objective=mean_value,
            solver_diagnostics=dict(original.get('solver_diagnostics', {}),
                expected_objective_bound='unknown', proposal_mean_bound=original['selected_plan_bound']),
            seconds=time.monotonic()-tick)
        return result, report


class DecisionManager:
    def __init__(self, availability, inner=plan, *, budget=None):
        self.availability = availability
        self.inner = inner
        self.budget = budget

    def __call__(self, state, market, horizon, *, settings, policy, blocked, opening_ids):
        cfg = settings
        inner = DecisionInner(self.availability, self.inner)
        actions, raw = plan_adaptive(state, market, [('admitted', 1., horizon)], settings=cfg,
            budget=self.budget or Budget(policy.seconds, policy.solve_seconds, policy.max_trials),
            blocked=blocked, opening_ids=opening_ids, inner_planner=inner)
        mean_value, mean_parts = _objective(state, market, horizon, actions, cfg)
        report = dict(raw)
        report['decision_objective'] = report['objective']
        report['decision_total_proxy'] = report.pop('total_proxy')
        report['decision_selected_schedule_bound'] = report['selected_schedule_bound']
        report['decision_trials'] = report.pop('trials')
        report['mean_scenario_objectives'] = report.pop('scenario_objectives')
        report['objective'] = mean_value
        report['components'] = mean_parts
        report['objective_scope'] = 'Original mean proxy for mechanical admission only; ranking uses decision_objective plus coarse reserve'
        report['selected_schedule_bound'] = unknown_bound(mean_value, 'Mean value of expected-selected path; retained proposal bound not a new schedule certificate')
        report['selection_calls'] = inner.selection_calls
        report['selection_cache_entries'] = len(inner.cache)
        report['availability_provenance'] = {k: self.availability[k] for k in
            ('gameweek', 'as_of', 'trained_through', 'model_sha256', 'decision_sha256', 'calendar_sha256')}
        report['scope'] = 'Heuristic expected-value reranking of feasible mean-MILP proposals; no global optimum, calibrated joint availability, or original external full-manager claim'
        return actions, report
