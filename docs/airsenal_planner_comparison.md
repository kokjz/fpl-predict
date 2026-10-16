# AIrsenal planning comparison: admission protocol

The [protocol](../src/fpl_predict_resources/airsenal_planner_protocol.json) and
[source recipe](../src/fpl_predict_resources/airsenal_solver_recipe.json) define
the next native planning comparison. The optional worker is implemented;
the parent controller, historical-input pilot and season comparison remain.
No AIrsenal historical performance result is claimed.

The intended eight paths cross two frozen prior-only forecasting controls,
standing/adapted-native planners and own/common opening squads. Each manages a
continuous 38-gameweek ledger with six-week lookahead, transfers, finances and
all four chips. Both use the common outer chip policy and canonical mean
lineup/captain/bench selection. The native tree/GA search retains its declared
two-transfer search cap and eight-point hit cap; these are algorithm settings,
not FPL rule changes imposed on the standing control.

The optional runtime uses separately obtained, hash-verified
[AIrsenal source](https://github.com/alan-turing-institute/AIrsenal/tree/fe580d7e567e79d80f73450c7d4b5d6610f05863).
Only planner dependencies are needed for this track. It does not require fitting
the original Bayesian forecasting stack, and is not a reproduction of that
forecaster or the original manager's full chip strategy. External source and
binaries are not bundled.

`airsenal_solver_worker.py` uses only standard-library imports until explicitly
started. Its source root is the optional installation directory containing
the pinned `airsenal/` package: the actual import location, all 143 Python files,
distribution license and declared dependency versions must match the recipe.
Supply a new, unused research-home path. A standalone worker can be started with
`python3.14 -m airsenal_solver_worker --source-root OPTIONAL_SITE_PACKAGES --home NEW_RESEARCH_HOME`.
It exchanges bounded JSON lines; ordinary engine installation does not install
AIrsenal or initialise a research database. The interval timer currently requires
a POSIX runtime. This is a trusted research adapter, not a security sandbox.

The worker supports native GA opening construction or a supplied common opening
for the first period, then permits future transfers. It explores each immediate
move family depth first and rotates after a complete plan, instead of retaining
the original breadth-first multiprocessing order. A per-request timer includes
database and GA construction; only completed full-horizon plans survive a
timeout. Guarded hooks and query views are restored between origins. Upstream
daemon stall threads are replaced by parent resource supervision.

Admission requires an explicit empty research home and isolated database before
any source import, without inherited account configuration. Python HTTP and the
compiled curl HTTP entry points must be refused. No fixture outcomes, realised
future prices, later news or past manager-point totals enter native requests.
Aggregate gameweek forecasts may use a clearly labelled database view; that view
must not masquerade as physical fixture/opponent evidence. Quote views at later
planning periods repeat the current origin's assumptions only.

The compatibility layer must cover the known transfer top-up, purchase
eligibility, Free Hit reversion and retained purchase basis. Full rebuilds need
economically consistent offers for retained originals when the native GA works
against a liquidation-value budget. Any temporary quote view must be restored
even after a timeout. Every proposed full horizon must reconcile against the
canonical financial and scoring engine before admission.

The source's fork-based progress wrapper is unsuitable for the tested macOS
runtime. Serial execution can preserve native strategy generation and scoring.
A bounded queue order may be declared to produce complete plans early and
cover immediate transfer families; this changes exploration order and must be
reported as an adaptation. An incomplete prefix is never a full-horizon plan.
The native tree/GA provides no solver upper-bound certificate: report unknown
bounds rather than inventing a zero optimality gap.

Before scoring any seasons, run mechanical chip/reset/registration/price tests,
both opening-construction modes, persistent timeout recovery and the fixed
feature-only latency pilot. The pilot compares two- and five-second inner
allowances without evaluator outcomes; its validity/cost rule chooses and
freezes equal control/native budgets before the season matrix. Actual hardware
limitations must be measured rather than inferred from the full project's
optional forecasting dependencies.

Publish all declared paths, failures, conditional objectives, net season points
and computing costs. One reused season and wall-time heuristic variability
limit conclusions. This work cannot promote a forecasting artifact or weekly
policy by code merge. See the earlier [native Solio comparison](NATIVE_PLANNER_RESULTS_2026-10-16.md)
for the distinction between inner-planner comparisons and original managers.
