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
