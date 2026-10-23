# Expected season-points and historical robustness results

24 October 2026. Twelve continuous 38-gameweek management paths compare H1, H6
and a source-pinned Solio adaptation from the same two opening squads in each of
two seasons. Forecasts, prices, transfer rules, chip rights and canonical lineup
selection are shared within each case. The [protocol](season_expected_points_protocol_2026-10-24.json)
was declared before these twelve scores; both years already had research exposure.

## Complete results

| Season | Opening seed | Policy | Net points | Hit points | Transfers | Seconds |
|---|---|---|---:|---:|---:|---:|
| 2024-25 | 20261070 | Standing one-week | 2256 | 28 | 81 | 5.02 |
| 2024-25 | 20261070 | Standing six-week | 2383 | 24 | 72 | 418.05 |
| 2024-25 | 20261070 | Adapted Solio six-week | 2400 | 12 | 70 | 389.07 |
| 2024-25 | 20261071 | Standing one-week | 2197 | 32 | 82 | 4.99 |
| 2024-25 | 20261071 | Standing six-week | 2441 | 16 | 73 | 403.77 |
| 2024-25 | 20261071 | Adapted Solio six-week | 2401 | 16 | 68 | 389.36 |
| 2025-26 | 20261070 | Standing one-week | 2127 | 32 | 95 | 6.71 |
| 2025-26 | 20261070 | Standing six-week | 2274 | 24 | 89 | 361.12 |
| 2025-26 | 20261070 | Adapted Solio six-week | 2274 | 24 | 86 | 503.80 |
| 2025-26 | 20261071 | Standing one-week | 2134 | 36 | 95 | 6.27 |
| 2025-26 | 20261071 | Standing six-week | 2134 | 28 | 91 | 371.74 |
| 2025-26 | 20261071 | Adapted Solio six-week | 2260 | 16 | 83 | 462.78 |

| Season | Opening seed | H6 minus H1 | H6 minus adapted Solio |
|---|---|---:|---:|
| 2024-25 | 20261070 | +127 | -17 |
| 2024-25 | 20261071 | +244 | +40 |
| 2025-26 | 20261070 | +147 | +0 |
| 2025-26 | 20261071 | +0 | -126 |

H6 minus H1 averages **+129.50 net points** with equal season
weighting: +185.5 in 2024/25 and +73.5 in 2025/26. Median opening gain is
+137.00, the worst opening +0,
with three wins, one tie and no losses. Opening losses
exceeding 19 points occur in 0/4 cases. The declared
mean/downside research criterion **passes**.
Against adapted Solio the equal-season mean is **-25.75**,
with one win, one tie and two losses. This comparison
is assessed separately: beating H1 is not evidence of beating Solio.

## What the criterion means

A six-point season loss alongside a 110-point gain should not by itself dismiss
a promising policy. The earlier no-negative-opening consistency gate did fail,
and that original result remains intact. Its failure is not proof of H6
inferiority or a statement about the statistical importance of six points.

This new [framework](expected_season_points.md) prioritises a positive average
season gain with declared material-downside allowances: no season-average loss
greater than 19 points and no single-opening loss greater than 38. These pragmatic
0.5/1-point-per-gameweek allowances were fixed before the new runs; they are not
confidence bounds or thresholds fitted to the new scores. These research
allowances are not universal loss limits: failing them does not establish negative
expected value. All integrity checks
remain mandatory. Neither criterion automatically promotes weights or production
policy defaults.

The observed mean describes these cases, not an estimated guaranteed future
advantage. Openings within a season share football outcomes, and the two seasons
were previously researched. Do not count four opening cases as four independent
seasons, or use an IID-gameweek bootstrap to imply certainty for a path-dependent
38-gameweek policy. Small credible improvements can be useful without winning
every case; broader evidence remains necessary for general claims.

## Historical admission and fairness

The [2024/25 inventory](season_2024_source_inventory.json) covers all 38 origin
markets/calendars and 27,158 listed player-gameweeks, including 360 confirmed
blank player-gameweeks. A derived correction to one stale merged Ferguson
fixture reconciles all 784 final footballer season totals. Fifteen club changes
between the market observation and settlement are evaluator facts only, never
backfilled into forecasts. Forecast heads are fitted only on 2020/21–2023/24;
2024/25 adds no defensive-contribution points. The 2025/26 track reuses the frozen
prior-five-season reference, including its original data vintage; the new
2024/25 correction is not silently applied to old forecasts or published metrics.
Neither is a backcast of the deployment artifact.

The 2024/25 comparison is explicitly **restricted to no Assistant Manager for
all policies**, with two Wildcard windows and one annual Free Hit, Bench Boost
and Triple Captain. It is a legal common action subset, not full 2024/25 chip
capability. That season has no AFCON transfer top-up. The 2025/26 paths retain
their admitted ordinary chip inventory and transfer rules. Common openings
condition this study on the supplied initial rosters; they do not test a fresh
initial-squad builder.

Market captures precede actual deadlines, sometimes by several hours. The GW15
origin predates the derby postponement, so its later blank is evaluated without
inserting later news into the earlier forecast. Pending cup-clash assignments
stay unknown until dated confirmation. Early archives lack `can_select`; the
reported conservative status proxy is not certification of historical UI access.
Calendar replay audits gameweek assignments; cached future kickoff times can
lag later announcements and are not predictor features in this origin-frozen
model. Archive timestamps and official publication dates remain publisher claims;
article revision completeness is not independently witnessed. Misleadingly
earlier-dated bodies with later outcomes are excluded from earlier origins.

All policies use the same forecast within a season. This isolates management
policy comparisons under those inputs; it does not measure the superiority of
the standing forecaster against Dastan or OpenFPL. Their earlier forecasting
comparisons remain separate, with their own admissions, sources and budgets.
Solio here is a rule-adapted core under shared outer chips, candidate logic and
selection, not a reproduction of its original complete manager.

## The earlier 153-point external gap

The older H6-minus-Solio loss decomposes into starting XI -79, autosubs -30,
ordinary captain bonus -22, extra Triple Captain -8, Bench Boost -10 and four
additional hit points. It accumulates as -17 in GW1–13, -66 in GW14–26 and -70
in GW27–38; first actual-action divergence is GW10. These are exact accounting
components, not isolated causes or recoverable gains. Copying eventually realised
chip dates back to earlier decisions would leak later information.

The [fixed calendar probe](season_calendar_probe_protocol_2026-10-24.json)
compares two cores and two same-origin frozen provisional schedules at eight
H6 states. Every eligible schedule is tested from the same state, with two seconds
per core and a separately reported remaining-chip reserve. Incompatible
inventories are explicitly skipped. Its complete cases, objectives, conditional
bounds and skips are retained in the aggregate. Proxy advantages are not measured
season-point gains, and neither the earlier fixed-schedule ties nor this probe
establish general solver parity or a causal explanation of all 153 points.

All 28 eligible runs passed the separate ledger/objective audit; two schedules
were skipped because they required chips already used in the common state.
For the 14 matched fixed-schedule core pairs, Solio tied H6 in 12 and returned
slightly lower conditional objectives in two (0.149 and 0.055 proxy units).
Where the two calendars differed and remained admissible, Solio's calendar
also had a lower common-state objective including the coarse reserve: by
0.313–0.368 units at GW20, 2.963 at GW30 and 9.752 at GW38.
These post-result comparisons do not reproduce the full evolving alternative
path. They give no evidence that replacing H6's inner solver or copying Solio's
chip dates alone would recover the earlier loss. Forecast errors, earlier squad
choices, path-dependent finances and bounded search remain possible contributors.

The first probe attempt stopped before its first completed case because the
diagnostic mishandled JSON chip-token lists. Its failure is retained. After a
regression-tested repair, the entire declared matrix was rerun uniformly; no
successful case was selected or discarded based on its score.

## Integrity, resources and next use

Independent arithmetic reconciles all 456 deadline settlements,
1856 retained provisional periods and 5821
completed native provisional periods. All 1015
native attempts, including 34
expected failures, are retained. Independent means separately implemented checks
within the project, not third-party certification. Selected-plan bounds are
conditional on the retained schedule, pool and proxy objective; global chip and
season bounds remain unknown.

The twelve serial paths took 55.38
minutes, with maximum sampled process-group memory
918.0 MiB and two
CPU threads. These are historical replay timings under ordinary system load,
not isolated hardware benchmarks or weekly inference times. Lightweight source,
audit and documentation checks overlapped parts of the serial batch; no other
model fitting or optimisation study ran concurrently. Observed dependency
versions are in the aggregate and differ from repository pins. No extra runtime
dependency, GPU or cloud service is required.

The next useful improvement study should isolate decision value, rather than
increase model size: compare a fixed expected-autosub/vice-aware decision policy
against the current mean selector under both cores, retaining the older negative
selection experiments as controls. Declare the new mechanism, budgets and criteria
before scoring it; do not search settings on these inspected paths until a winner
appears. This is a recommendation for a separately authorised package, not a new
experiment or a promotion in this release.

Forecast weights, normal weekly commands, manual sensitivities and production
defaults remain unchanged. The result changes the evidence available for choosing
an experimental management policy; it does not install new forecast weights or
prove full original-competitor or current-season superiority. See the
[aggregate](season_expected_points_results_2026-10-24.json),
[reproduction workflow](expected_season_points.md) and
[current policy status](season_policy_status.json).
