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

The next qualification work includes the approved-artifact integration bridge,
fixed-calendar and simple baselines, bounded uniform-source repeated season
comparisons, explicit policy approval status and operational handoff. These
items are not established by the callback interface or its synthetic tests.
No new historical season result, forecast-model promotion or weekly-policy
approval is claimed here.

The underlying [AIrsenal comparison](airsenal_planner_comparison.md) is a separate
integration dependency. Its results must remain tied to their frozen source;
qualification changes must not modify a running benchmark checkout.
