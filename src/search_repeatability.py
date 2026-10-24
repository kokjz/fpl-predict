"""Optional fixed-node/probe management and strict repeat fingerprints.

Logical work caps do not equalise CPU effort across different formulations.
Safety guards must never be treated as successful fixed-work completion.
"""
import hashlib
import json
from adaptive_planner import Budget, plan_adaptive
from decision_management import DecisionManager
from rolling_planner import plan


class FixedWorkManager:
    def __init__(self, inner=plan, *, availability=None, node_limit=1, max_trials=12,
                 safety_seconds=120.):
        self.inner = inner
        self.availability = availability
        self.node_limit = node_limit
        self.budget = Budget(safety_seconds, safety_seconds, max_trials, fixed_work=True)

    def __call__(self, state, market, horizon, *, settings, policy, blocked, opening_ids):
        if settings.node_limit != self.node_limit or settings.baseline_mode != 'feasibility':
            raise ValueError('Fixed-work manager/inner controls differ')
        if self.availability is not None:
            return DecisionManager(self.availability, self.inner, budget=self.budget)(
                state, market, horizon, settings=settings, policy=policy,
                blocked=blocked, opening_ids=opening_ids)
        return plan_adaptive(state, market, [('admitted', 1., horizon)],
            settings=settings, budget=self.budget, blocked=blocked,
            opening_ids=opening_ids, inner_planner=self.inner)


def decision_fingerprint(record):
    """Include entire provisional decisions and financial state, omit timings.

    Cumulative realised points are not a decision input to this policy. Repeated
    actions, state, source provenance and provisional plans must all match.
    This diagnoses numerical repeatability, not out-of-sample football accuracy.
    """
    state = {k: v for k, v in record['state_before'].items() if k != 'total_points'}
    payload = dict(gameweek=record['gameweek'], inputs_as_of=record['inputs_as_of'],
        state_before=state, action=record['action'],
        provisional_actions=record['provisional_actions'],
        forecast_provenance=record['forecast_provenance'])
    raw = json.dumps(payload, sort_keys=True, allow_nan=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode()).hexdigest()
