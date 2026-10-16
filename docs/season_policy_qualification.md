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

The next qualification work includes the approved-artifact integration bridge,
bounded uniform-source repeated season
comparisons, explicit policy approval status and operational handoff. These
items are not established by the callback interface or its synthetic tests.
No new historical season result, forecast-model promotion or weekly-policy
approval is claimed here.

The underlying [AIrsenal comparison](airsenal_planner_comparison.md) is a separate
integration dependency. Its results must remain tied to their frozen source;
qualification changes must not modify a running benchmark checkout.
