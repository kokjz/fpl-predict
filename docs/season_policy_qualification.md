# Season-management policy qualification

Qualification evaluates a continuous 38-gameweek squad, rather than adding up
independent weekly team selections. Net realised points after hits is the
primary measure. Forecast-error metrics remain diagnostics.

The research harness accepts either an inner roster solver, retaining its
existing adaptive chip policy, or an explicitly versioned whole management
policy. A whole-policy callback receives the current state, origin-frozen
market and horizon, settings, resource policy, blocked chip tokens and an
optional common opening. It never receives the hidden evaluator mapping.

The callback returns a complete provisional action path and report. Before
settlement, the harness validates every period's finances, squad, chip resources
and supplied expected objective. Disabled or blocked chips, a changed common
opening and incomplete or illegal paths are rejected before outcomes are read.
Only the first action is committed; the process repeats at the next deadline.
The callback API is for trusted research code, not a security sandbox.

This interface supports an honest fixed-calendar chip control and a descriptive
hold reference without disguising either as an inner optimisation solver.
Default replay behaviour is unchanged when no whole policy is supplied.
Policy identity is recorded in each frozen decision and final summary.

`management_policies.FixedCalendarPolicy` retains predeclared chip dates while
replanning rosters at each origin. It uses the canonical roster solver, candidate
procedure and expected objective. Within the same outer time envelope it can
repeat its single allowed schedule, retaining the best expected objective and
recording every attempt. This compares complete policies and search allocation;
it does not isolate chip timing independently of numerical solve quality.

The default reference calendar is fixed before qualification scoring:

| Chip | First window | Second window |
|---|---:|---:|
| Wildcard | GW6 | GW24 |
| Bench Boost | GW12 | GW30 |
| Free Hit | GW15 | GW33 |
| Triple Captain | GW18 | GW36 |

These are arbitrary spaced reference dates, not dates selected from realised
chip returns. The policy validates windows, token reuse and consecutive Free
Hits. Already-used or explicitly blocked resources are unavailable.

`HoldPolicy` constructs the cheapest legal opening or accepts the common opening,
then retains all 15 players and reselects the mean XI/captain/vice each deadline.
It deliberately leaves transfers and chips unused. It is a descriptive floor;
the one-week planner with all legal resources remains the primary strong anchor.

The [qualification protocol](../src/fpl_predict_resources/season_policy_qualification_protocol.json)
declares the repeat matrix, controls, limits and decision criteria. Its executable
source inventory and mechanical pilot must be frozen before historical scoring.
Synthetic tests prove mechanics, not historical performance or useful chip dates.

`approved_horizon.observe_approved(model_home, receipt_path)` records verified
approved artifact existence using the current clock, without loading the model.
The destination must be new. Keep the receipt and its SHA256 with frozen inputs.
An observation is a conservative upper bound on when training had completed;
it is not the original fit timestamp or evidence that historical forecasts existed.

`project_approved` resolves the current approved registry entry, verifies the
receipt hash/version/artifact and source clocks, then loads the verified bytes.
It rejects a changed artifact, unapproved registry entry, metadata mismatch or
observation at/after the forecast origin. The caller's timestamped source adapter
remains responsible for authenticating history and the origin-known calendar.
The deployment artifact must never be backcast into its training seasons.

Optional reviews use the existing availability-review schema with an origin-safe
bootstrap and matching deadline. The shared `forecast_sensitivity` calculation
preserves the weekly workflow's illustrative minutes/availability scaling;
reviewed assumptions apply to the current gameweek only, not an asserted future
recovery path. No new appearance multiplier is applied to unconditional forecasts.
The original weekly forecast uses the same calculation and numerical behaviour.

An actual saved-artifact compatibility check used the entirely
[invented case](../tests/fixtures/synthetic_bridge_case.json): 18 players,
1/4/6/8-week grids, 19 admitted hold-policy actions frozen before fabricated
settlement, blank/double checks, future-history mutation and current-only minutes
sensitivity. The bounded check took 3.28 seconds including startup and about
166.6 MiB sampled process-group memory. This is not a realistic full-market
latency measurement, a forecast-accuracy test or adaptive-policy qualification.
The [aggregate and source hashes](approved_bridge_compatibility.json) disclose
the observed runtime, which differs from repository dependency pins, and retain
the initial synthetic timestamp-format failure. The adaptive planner pilot remains
separate. No real player or squad forecasts
were produced by this check.

The next qualification work includes the adaptive mechanical pilot and source
lock, bounded uniform-source repeated season
comparisons, explicit policy approval status and operational handoff. These
items are not established by the callback interface or its synthetic tests.
No new historical season result, forecast-model promotion or weekly-policy
approval is claimed here.

The underlying [AIrsenal comparison](airsenal_planner_comparison.md) is a separate
integration dependency. Its results must remain tied to their frozen source;
qualification changes must not modify a running benchmark checkout.
