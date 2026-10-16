# Bounds for the plan actually retained

The rolling planner keeps a validated feasible baseline if a solver attempt
does not improve it. A solver's raw `mip_gap` can describe a worse, discarded
incumbent. It must not be presented as the retained plan's gap.

`selected_plan_bound` now gives the feasible retained objective, an upper bound
when available, and absolute/relative gaps between them. For SciPy's minimisation
form, the maximisation objective is `-c @ x + C`; the upper bound is therefore
`-mip_dual_bound + C`. The constant matters, for example when a final Free Hit's
terminal value belongs to the restored original squad. Relative gaps divide by
the retained absolute value, with a small denominator floor; use the absolute
gap for near-zero objectives.

Missing/nonfinite duals remain unknown. A dual inconsistent with a better known
feasible value is explicitly flagged, never silently clipped into a zero-gap
certificate. Small differences within the existing numerical feasibility
tolerance are treated as rounding. A validated solver-optimal result can supply
the optimum if an explicit dual is unavailable. These remain numerical solver
diagnostics, not independent mathematical proof certificates.

Bounds apply only to the **fixed chip schedule, restricted player pool, constant
quotes and stated heuristic objective**. They are not bounds on the complete
chip search, season points or forecast uncertainty. The adaptive planner exposes
the chosen schedule's bound and leaves `global_chip_search_bound` unknown.

For compatibility, `mip_gap` and the adaptive trial's `gap` still hold the raw
attempt diagnostic, explicitly labelled. `solver_diagnostics` and
`fallback_retained` make that distinction visible. Nonfinite reported values are
written as JSON null, not misleading infinite/NaN values or zero.

## Feasible baseline objective cut

`Settings.use_baseline_cut` defaults to true. It adds the valid objective
constraint `c @ x <= C - baseline_value + tolerance`, keeping all solutions at
least as good as the validated baseline. Baseline players are already retained
in the candidate pool. This does not provide a warm start or guarantee better
time-limited results: a mathematically equivalent bound can change the search
trajectory. Set it false for explicitly declared engineering comparisons.

The [fixed diagnostic protocol](../src/fpl_predict_resources/solver_bound_protocol.json)
uses existing frozen inputs and no realised-outcome selection. The old full-season
report remains an earlier-source measurement; it cannot be retrospectively given
bounds that were never saved or rewritten as a result for this new solver.

Research checked 16 October 2026 against [SciPy's documented dual and gap semantics](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html).
