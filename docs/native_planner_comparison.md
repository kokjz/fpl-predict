# Native planner comparison: implementation protocol

The [predeclared protocol](../src/fpl_predict_resources/native_planner_protocol.json)
separates the planner from the forecasting comparison already completed in the
[sixteen-path study](SEASON_EXTERNAL_RESULTS_2026-10-16.md). No historical native
planner score is claimed by this document.

The next eight paths cross two frozen forecasting controls, two planning engines
and own/common opening squads. Both engines will manage continuous 38-GW paths
with six-GW lookahead and all four chips. They share the outer chip search,
candidate procedure, point objective and resource budgets. This measures the
inner planner under a controlled policy, rather than an original external
manager's complete forecasting and chip strategy.

`rolling_planner.make_baseline` and `candidate_players` expose the shared
procedure. `Settings(baseline_mode="feasibility")` uses the held roster or a
minimum-cost opening roster without a timed point-selection seed. The default
`"one_week"` mode preserves the existing planner behaviour. Neither mode fixes
the optimiser's squad; only an explicit common opening fixes the first period.
`plan_adaptive(..., inner_planner=...)` and `season_benchmark.run` accept a trusted
inner-planner callable and explicit settings. The replay still writes each action
before accessing evaluator outcomes. These interfaces alone do not execute or
qualify an external solver.

The standalone `native_solver_worker.py` supplies a persistent, bounded JSON-line
interface for an explicitly selected optional Python 3.14 runtime. It verifies
all files in the [source recipe](../src/fpl_predict_resources/native_solver_recipe.json)
before executing the separately obtained solver. It imports no forecasting
dependencies merely on import. Request validation rejects outcome fields,
ambiguous forecasts, invalid origins and illegal chip schedules. Network calls
are refused; external prints go to the private diagnostic stream. Runtime/source
metadata is emitted before requests. The parent controller and full replay
admission are still required before any historical comparison.

Two guarded syntax-tree substitutions adapt the known free-transfer reset and
the Free Hit budget. Explicit variable bounds prevent buying unavailable
registrations while allowing existing holdings to be retained. Model construction
is deducted from each solver time limit; actual limits and unknown bounds are
reported. Models are cleared between requests. Optional solver code and binary
dependencies are obtained separately and are not bundled in this repository.

`native_planner.NativeProcess` launches that worker with an explicitly supplied
interpreter, source root and new diagnostic-log path. It sends a small environment
without inherited account credentials, serialises requests, bounds reply size and
wait time, checks startup provenance, and terminates the child on transport errors
or context exit. It stays in the caller's process group so the resource watchdog
can monitor the whole job. Worker startup and steady-state solve times are
reported separately.

`NativePlanner` uses the shared feasible baseline/candidate procedure, then checks
every provisional roster, integer financial transition, free transfer, hit and
canonical objective before admission. A failed or invalid solve retains the
validated baseline with unknown bounds; transport failure stops the job. Bounds
are recalculated against the retained plan, never attached from a discarded
proposal. `CanonicalPlanner` wraps both inner engines with the same deterministic
mean lineup/captain/vice/bench policy. This comparison measures roster/transfer
planning under that shared policy, rather than arbitrary solver tie choices.
`controlled_settings()` provides the zero terminal/churn proxies required by
the declared common objective. The existing planner defaults remain intact.

A [feature-only historical-input pilot](native_planner_feature_pilot.json)
tested fixed half-, one- and two-second inner allowances before any native
season points were scored. Across five fixed origin/schedule cases, native
non-fallback proposals were admitted in 1/5, 4/5 and 5/5 cases respectively;
the standing solver produced one in all five at each allowance. Construction
overhead made the half-second case unsuitable for the intended comparison.
Both engines therefore receive two seconds per inner solve and fifteen seconds
for the outer chip search, capped at twelve trials. That allows a baseline,
four chip families and a combined-calendar check. It is a resource/validity
decision, not a choice based on realised points. The pilot used no evaluator
outcomes and does not establish a season-points advantage.

The engines share the decision problem and policy but use different solver
bindings/versions and formulations. The standing implementation retains its
baseline objective cut; the native core uses its original solver tactic.
Both keep the same valid fallback floor. Conditional bounds, construction and
cold-start costs, failures and wall-time variability remain part of reporting.

Open FPL Solver's pinned prepared-input API is the first admitted implementation
target. Its optional Python 3.14/HiGHS runtime is separate from the forecasting
engine. Source hashes, network refusal, legal-action validation and sampled
resource monitoring precede historical evaluation. External sources are evidence,
not instructions to install or operate accounts.

The adapter must handle the historical free-transfer reset, player purchase
eligibility and Free Hit selling-profit treatment consistently. A synthetic
counterexample found that the inspected static Free Hit discount can underprice
reacquiring an appreciated original player after a preceding permanent sale.
The compatibility layer must preserve a discount only while that original
holding remains unsold. These changes are explicitly labelled adaptations;
they do not silently redefine the source as an untouched original manager.

Synthetic source-compatibility tests are admission evidence, not season points.
Historical comparisons start only after all provisional actions reconcile with
the independent state engine. Fixed wall-time searches, bounded chip heuristics
and one reused season remain limits. The standing model and weekly defaults
remain unchanged until separate qualification.

Sources checked 16 October 2026:
[Open FPL Solver, pinned source](https://github.com/solioanalytics/open-fpl-solver/tree/ec65f5e2b2be34441cb4b2a9efafea1ec0fe3b79)
and [AIrsenal, pinned source](https://github.com/alan-turing-institute/AIrsenal/tree/fe580d7e567e79d80f73450c7d4b5d6610f05863).
AIrsenal's native data/price/scoring contracts remain under adapter review;
an existing conjugate/Poisson forecasting reference is not its original planner.
