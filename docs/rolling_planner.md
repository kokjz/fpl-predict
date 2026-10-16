# Multi-gameweek forecast and transfer planning

Current diagnostics distinguish the [retained plan's bound](solver_bounds.md)
from a discarded solver attempt's raw gap. The baseline objective cut is
switchable; see the [fixed diagnostic](SELECTED_PLAN_BOUNDS_2026-10-16.md).

This opt-in research planner chooses transfers and lineups together over1–8GWs.
Only its first action is eligible for the current deadline; later actions must be
reconsidered when new information arrives. Optional fixed chip schedules and a
bounded [chip/scenario strategy](adaptive_planner.md) are now available for
research. Neither is an approved weekly replacement or demonstrated season-points
improvement.

## Origin-frozen forecasts

`horizon_forecast.project` uses the audited roster/calendar and the same origin
form for every future fixture. It never rolls actual future form into later rows.
Training must finish before the origin; history has the existing three-hour
completion buffer. Missing origin-player/GW predictions fail; known doubles sum,
and no origin-known fixture yields zero with explicit future-schedule uncertainty.
Roster registrations, positions/clubs and current labels do not become known
future changes. Experimental conditional models need their own admitted adapter.

`Horizon.create` checks clocks, contiguous targets, unique complete roster coverage
and finite values. The policy interface admits only targetGW/player/point means;
no realised outcomes. Provenance records training, feature/calendar time, model
identity and supplied source hashes. Metadata assertions alone are not independent
proof that an upstream forecast producer avoided leakage.

## Planning objective and constraints

A bounded sparse mixed-integer model values starting-XI means, captain mean,
0.1reserve means, transfer hits and a0.0001transfer churn penalty. Terminal values
are fixed illustrative proxies:1point per availableFT and0.05times the last two
projectedGWs' mean per held player. Both vanish when the horizon reachesGW38.
They are not learned/calibrated future point gains.

The model carries old and newly bought purchase lots separately, with exact
integer cash and half-profit selling under constant origin quotes. It models
bankedFT/consumption/cap/topups and legal squad/lineup/captain constraints. Future
prices, club movements and buyability remain at origin assumptions. Bench/vice
order uses mean ranking; expected legal autosubs and uncertainty are later work.

Candidates retain every owned player and a full-market feasible one-GW baseline,
plus top12horizon-scoring and cheapest6 per position. Optimality applies only to
this restricted pool/objective. Any integral feasible solver incumbent is checked
against the state engine, finances, FT and recomputed objective. A validated
baseline/hold path is retained if no better incumbent is available; an opening
squad with no feasible baseline fails closed. Report solver status/gap/fallback.
Default30s total nominal budget, maximum120s, two solver threads. These bounds
are configuration, not measured routine latency or accuracy guarantees.

## Interface

```sh
fpl-predict plan-horizon --input /path/to/frozen-planning-input.json \
  --sha256 INPUT_SHA256 --output /path/to/new-plan
```

The document has `schema_version:1`, `market` (the season-state market schema),
`state` (season/GW/purchase ledger/bank/FT/chips), `forecast` and optional `settings`.
Forecast fields are `rows` (gameweek,id,expected_points), `trained_through`,
`feature_cutoff`, `source_as_of`, `model_id`, optional `source_hashes`. Dates carry
explicit zones; feature origin equals market timestamp. Outputs include immediate
and provisional actions, assumptions, objective components and source hashes.
Keep inputs/outputs and private squad state outsideGit. Existing outputs cannot
be overwritten; no account writes, registry changes or refreshes occur.

Read the [fixed protocol](../src/fpl_predict_resources/rolling_planner_protocol.json).
Known-answer/independent dynamic-programming tests precede the bounded historical
mechanical pilot. Full38GWseason-point/external comparison follows separate
benchmark stages. Existing approved forecasts and weekly commands are unchanged.

Grounding checked16October2026: [SciPy MILP](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)
and [Open FPL Solver](https://github.com/solioanalytics/open-fpl-solver).


The [completed mechanical pilot](ROLLING_PLANNER_PILOT_2026-10-16.md) reports
three origins, full finance/reload checks, computational cost and a preseason
forecast limitation. It does not change the objective weights or establish
realised season gains. All further qualification remains separate.
