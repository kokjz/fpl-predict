# Season-management robustness and decision findings

24 October 2026. Six additional continuous 38-gameweek paths test two new opening squads. Every policy uses the same opening squad, forecasts, budget and chip rights within each comparison. Points are net of transfer hits. The [protocol](season_robustness_protocol_2026-10-24.json) was frozen before these cases were scored, but the 2025/26 outcomes had already been studied. These are starting-state sensitivity tests, not independent seasons or an untouched holdout.

## Complete results

| Opening seed | Policy | Net points | Hit points | Transfers | Seconds |
|---|---|---:|---:|---:|---:|
| 20261024 | Standing one-week | 2154 | 32 | 95 | 6.19 |
| 20261024 | Standing six-week | 2264 | 32 | 91 | 358.07 |
| 20261024 | Adapted Solio six-week | 2266 | 24 | 87 | 502.24 |
| 20261025 | Standing one-week | 2160 | 32 | 96 | 6.17 |
| 20261025 | Standing six-week | 2154 | 28 | 91 | 373.14 |
| 20261025 | Adapted Solio six-week | 2307 | 24 | 86 | 469.75 |

Six-week minus one-week returns are **+110 and −6 points**. The predeclared consistency gate requires both differences to be nonnegative and their mean to be positive, so it **fails**. A positive average does not override that rule. Against adapted Solio, the six-week differences are **−2 and −153 points**.

The [original twenty-path qualification](SEASON_POLICY_QUALIFICATION_RESULTS_2026-10-17.md) remains a valid dated result. These additional openings make the broader H6 evidence mixed. Solio wins both new cases, but earlier matched comparisons were mixed; neither study establishes general superiority of an original complete external manager.

All 228 deadline settlements and 928 retained provisional periods passed the separate finance and scoring audit. The two native paths passed independent ledger and mean-objective checks for 3,451 completed provisional periods. All 602 native attempts and 21 expected failures were retained; invalid completed proposals would stop a path. All source, input, runtime and output signatures reconcile. Independent verification here means separately implemented arithmetic within this project, not third-party certification.

The six serial jobs took 28.59 minutes, with a maximum sampled process-group memory of 892.7 MiB and two CPU threads. Small development checks overlapped parts of the batch, so these describe ordinary load rather than isolated timing or routine weekly latency. Observed package versions are recorded in the aggregate and differ from repository pins; this is not an exact-pinned-environment reproduction claim.

## Where the points came from

The diagnostic first reconciled all 20 original qualification paths and the 16 earlier forecasting-comparison paths. In the first own-opening H6–H1 comparison, the 209-point difference decomposes into starting XI +141, autosubs +50, captain +32, extra Triple Captain +6 and Bench Boost +4, less 24 additional hit points. The common-opening 133-point difference decomposes into XI +91, autosubs +35, captain +19, extra Triple Captain +1 and Bench Boost +11, less 24 hits. These are scoring identities, not causal estimates of separate choices.

H6 had more zero-minute starters in those cases—30 versus 22 with own openings and 24 versus 17 with the common opening—yet finished ahead. Bench cover and squad composition matter alongside absence prediction. Zero-minute and cameo overprediction remains visible, but actual-minute groups are known only after the outcome; they are not forecast correction factors.

The new six-point loss has a different composition: XI +8, autosubs −16, captain −4, extra Triple Captain +6, Bench Boost −4 and four saved hit points. Both policies had 23 zero-minute starters; H6 had 33 cameos versus 28. This motivates further independent investigation of bench and playing-time decisions, but does not identify an advance-knowable correction or prove those points recoverable.

Within-owned hindsight XI/captain headroom is explicitly an unattainable diagnostic, not expected recoverable gain. Owned cohorts differ across policies, so their RMSEs cannot fairly rank forecasters. Dastan-architecture, OpenFPL and component adaptations remain in the separate 16-path forecasting track, with its own source and smaller solve budgets. Their totals are not pooled into these new planner comparisons.

## Same-state numerical diagnosis

After all six scores were known, a separately [declared probe](solver_comparison_protocol_2026-10-24.json) compared both cores at the same ten frozen H6 states: both new openings at GW1, 6, 16, 30 and 38. Each solver received two seconds, identical forecasts, the same pool procedure and objective, and the retained chip schedule. No outcome or settlement files were read.

The cores tied in eight states. Standing achieved higher conditional expected objectives by 2.017 and 0.149 units in the two GW16 states. The 153-point season gap therefore is not evidence of a uniformly stronger fixed-schedule native solve. Different calendar and roster paths, and noisy realised returns, remain possible explanations rather than isolated causes. These ten states do not prove parity everywhere or justify a solver portfolio.

All 20 cases, 100 new provisional periods, 32 output hashes and ten raw native replies covering 50 provisional periods passed separate pool, ledger and objective checks. The supervised probe took 20.63 seconds and 720.5 MiB sampled group memory with two threads. It is post-result diagnosis, not independent-season validation or a realised-points test.

## Another season: source readiness

All 38 pre-deadline 2024/25 market receipts passed bounded compressed/content hash, player/club/price schema, chronological deadline and capture-time checks. Sources are pinned to [Randdalf/fplcache](https://github.com/Randdalf/fplcache/tree/3ab1f91f61258a3e4bd27c74d5cfb3c6b72380e7); individual URLs, hashes and observed manager/chip inventories are in the aggregate. Archive publication and capture clocks remain claims, not independently witnessed certification.

This is source readiness, **not a completed second-season benchmark**. Remaining admission work covers fixture calendars and announcements as known at all 38 origins, prior-only 2024 forecasts, complete listed-player outcome/blank reconciliation and a compatible rule profile. The [2024/25 transfer rules](https://www.premierleague.com/en/news/4058895) and [three-week Assistant Manager chip](https://www.premierleague.com/ar/news/4192707) differ from the two-set profile. A restricted no-Assistant-Manager comparison would need a separate declaration and label; it would not test full chip capability. These are data and implementation requirements, not evidence of a hardware limit or unavailable sources.

## Decision and next use

Forecast weights, normal weekly commands, dependencies and production defaults are unchanged. The diagnosis identifies no new calibrated signal or demonstrated correction that justifies another immediate forecaster/selector trial. Previously failed conditional and expected-selector variants remain rejected. Unconditional points were not multiplied by appearance probabilities, and no settings search was added to erase the failed consistency result.

Keep H6 as experimental/shadow decision support with fresh deadline evidence, first-action commitment and replanning. Preserve its original qualification as dated evidence; do not promote it to the normal weekly default from these results. Frozen weekly evaluation continues as separate maintenance. The next substantial robustness expansion is a fully admitted second season with its own rules and chronological forecasts. A later targeted challenger needs a new mechanism, declared development/audit boundaries and matched standing/external comparisons.

Read the [aggregate](season_robustness_results_2026-10-24.json), [reproduction workflow](season_robustness.md) and [current policy status](season_policy_status.json). No GPU, new runtime dependency or model migration is required by this package.
