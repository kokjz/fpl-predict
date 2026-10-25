"""One locked historical fixed-work season; caller supplies immutable bundles.

No fit, source download, registry/default write or account operation. Run under
the experiment_runner watchdog and retain all attempts outside the checkout.
"""
import contextlib
import json
from pathlib import Path
from native_planner import NativeProcess, NativePlanner, CanonicalPlanner
from rolling_planner import Settings
from search_repeatability import FixedWorkManager, decision_fingerprint
from season_benchmark import run, Policy
from season_qualification import Trace, Guarded


POLICIES = ('standingH6_fixedWork', 'decisionH6_fixedWork', 'decisionH6_calibrated_fixedWork', 'SolioAdaptedH6_fixedWork')


def run_case(decisions, outcomes, availability, output, *, policy_id, opening_ids,
             node_limit=1, max_trials=12, native_python=None, solio_source=None,
             solio_site_packages=None):
    if policy_id not in POLICIES:
        raise ValueError('Undeclared fixed-work policy')
    out = Path(output).resolve()
    if out.exists() or out.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError('Require new private output directory')
    out.mkdir(parents=True)
    trace = None
    metadata = None
    by = {r['gameweek']: r for r in availability}
    if len(by) != 38 or set(by) != set(range(1, 39)):
        raise ValueError('Incomplete appearance origins')
    with contextlib.ExitStack() as stack:
        if policy_id.startswith('Solio'):
            if not all([native_python, solio_source, solio_site_packages]):
                raise ValueError('Require admitted native runtime')
            actor = stack.enter_context(NativeProcess(native_python, solio_source,
                out/'native_stderr.log', site_packages=solio_site_packages))
            trace = Trace(actor, out, 'solio', stack)
            metadata = actor.metadata
            inner = Guarded(CanonicalPlanner(NativePlanner(trace,
                canonicalise_dominated_paid=True)), out, trace)
        else:
            inner = Guarded(CanonicalPlanner(), out)
        settings = Settings(seconds=120., baseline_mode='feasibility', node_limit=node_limit,
            terminal_ft_value=0., terminal_squad_weight=0., churn_cost=0.)
        def manager(state, market, horizon, **kwargs):
            a = by[market.gameweek] if policy_id.startswith('decision') else None
            return FixedWorkManager(inner, availability=a, node_limit=node_limit,
                max_trials=max_trials)(state, market, horizon, **kwargs)
        result = run(decisions, outcomes, out/'season', policy=Policy(6, True, 120., 120., max_trials),
            opening_ids=opening_ids, settings=settings, management_policy=manager,
            management_policy_id=policy_id+'-nodes-v1')
    fingerprints = [decision_fingerprint(json.loads((out/f'season/GW{g:02d}_decision.json').read_text()))
                    for g in range(1, 39)]
    result.update(policy_id=policy_id, decision_fingerprints=fingerprints,
        native_runtime=metadata, native_calls=trace.calls if trace else 0,
        native_failed_attempts=trace.failed if trace else 0,
        work_control=dict(node_limit=node_limit, max_trials=max_trials, random_seed=0,
            parallel='off', threads=2, seconds_per_inner_safety=120.),
        model_promotion=False, production_policy_promotion=False)
    (out/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result
