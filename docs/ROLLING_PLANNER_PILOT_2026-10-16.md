# Rolling-horizon planner: mechanical pilot

16 October2026. **Multi-gameweek transfers and lineups now optimise together,
with origin-frozen forecasts and state-engine reconciliation.** This verifies
the planning mechanics; it does not establish better historical season scores.
Chips, adaptive uncertainty and fullseason competitor comparisons remain next.

[Aggregate evidence](ROLLING_PLANNER_PILOT_2026-10-16.json) ·
[Interface and assumptions](rolling_planner.md) ·
[Season foundation](SEASON_READINESS_2026-10-16.md)

## Fixed experiment

The source/protocol was published before fitting or pilot execution. One
standing-core architecture reference fits133,325rows from2020/21–2024/25 only.
Four fixed HGB7 heads cover core points, minutes, appearance and60minutes.
Defensive contribution uses the origin's lagged EW rate because those prior
seasons lack the newer award. This is a named priorseason-core/EWDC reference,
not the saved champion or a new approved forecasting model. No2025targets fit
any learner, no postpilot parameter/seed/blend search occurs.

Origins are fixedGW1,20,38. GW1 starts with the same initial budget; the others
use one neutral affordable snapshot-sampled squad at current quotes as purchase
values, with oneFT. No real manager squad or private purchase history is used.
Every target's form/history comes from its origin, not future realised form.
Source/currentfixture IDs and history clocks use the admitted calendar/roster.
Multiweek forecasts remain approximations with mutable historical-source limits.

## Mechanical results

| Origin | Horizon | Projection seconds | Plan seconds | Pool / listed | Optimal restricted objective / baseline hold path |
|---|---:|---:|---:|---:|---:|
| GW1 | 6 | 0.466 | 0.325 | 74 / 685 | 118.538 / 118.132 |
| GW20 | 6 | 0.786 | 3.534 | 84 / 780 | 327.027 / 271.369 |
| GW38 | 1 | 0.826 | 0.120 | 84 / 840 | 38.746 / 38.746 |

All three solvers prove an optimum in their declared restricted candidate pools,
with zero reported gap. These values include reserve/terminal/churn heuristics;
they are **not realisedFPLpoints or season-gain estimates**. The baseline is a
feasible oneGWsolution followed by an origin-frozen hold path, not an entire
oneGWpolicy allowed to replan with future news. TheGW20synthetic starting squad
produces a20point hit in the plan; this is a neutral mechanical stress case, not
a recommendation or proof that such a hit improves a real team.

The model supports separate original/new purchase lots, so selling a price-gainer
and buying them back cannot invent cash or preserve the old selling basis.
Every one of13provisional squad/lineup decisions reconciles against the season
engine; an independent audit rechecks all13cash/FT/hit/objective steps. Feature
forecast coverage and reload parity pass at all three origins. An independent
dynamic-programming test matches the solver's short-horizon optimum. Another
known-answer example rejects a higher immediate transfer for a larger latergain.
Time-limit incumbents are validated and not labelled provenoptimal; a checked
baseline/owned-hold path remains available when possible.

Full supervised pilot took55.29s, peak sampledRSS0.641GiB, twoCPUthreads.
Four learner fits and saving took45.74s. This measurement covers only this pilot,
not every possible squad/chip/uncertainty configuration. NoGPU/remotecompute or
large download was needed; memory/time/storage bounds were monitored.

## Important limitation: initial-season forecasts

AtGW1the standing feature store has no currentseason player/team history.
The685player means have onlyfive distinct values to eight decimals, spanning
1.264–1.578points. Position/home priors dominate; the optimiser cannot recover
missing individual information. A fast, valid initial-squad optimum on such
forecasts is not evidence of a good initial squad.

Before fullseason utility is interpreted, separately declare and evaluate an
origin-safe preseason/crossseason carryover or officialprojection reference.
Stable IDs, club/position changes and training/inference consistency must be
audited; never import laterseason form or select a hindsight GW1squad. Preserve
this pilot as-is. This finding changes the readiness work before seasonbenchmark,
not its reported result or the fixed planner parameters.

## Retained external comparison boundary

A singleGW38overlap check matches840playerGWs/212candidates. CandidateRMSE/MAE:
standing retained2.8672/2.3288; native2.8478/2.3485;
Dastan-architecture2.8255/2.2461; OpenFPLcv1adaptation2.8657/2.3770;
componentreference2.7691/2.2279; newpriorseason-core/EWDC2.8891/2.3365.

This is an unequal-training/component/source-clock diagnostic: retained methods
use their existing throughGW19training, whereas the new reference is trained on
priorseasons only and uses earlier origin features/EWDC. It neither isolates
planner quality nor ranks fullseason managers. It is included to preserve the
standing/external comparison boundary at this stage, not to claim fairness or
superiority. Controlled fullorigin grids and season-management comparisons must
follow the previously declared protocol. Native external systems remain distinct
from the named adaptations.

## Remaining stages

Resolve preseason forecast information before evaluating initialsquad quality;
add chip strategy and news/fitness scenarios; run38GWbaselines and matched
external forecast/planner/native-system comparisons; then assess joint-system
qualification. The overall adaptive-season goal remains active. Approvedv1.0.0,
normal weekly forecasts, manual sensitivities and registry remain unchanged.
