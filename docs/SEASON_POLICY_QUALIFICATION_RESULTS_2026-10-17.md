# Adaptive season-management qualification

17 October 2026. Twenty complete continuous 38-gameweek paths and 760 independently reconciled deadline decisions. The comparison measures season points after transfer hits, carrying squads, cash, purchase prices, transfer resources and chips forward. It does not sum independent weekly team selections.

At each deadline the planner sees only the admitted current market, origin-frozen forecasts and known calendar. It commits its first action, then revises the plan at the next origin. The six-week planner combines detailed roster decisions with a coarse remaining-season chip calendar.

## All predeclared paths

| Policy | Opening | Repeat | Net points | Hits | Transfers | Chips used | Seconds |
|---|---|---:|---:|---:|---:|---:|---:|
| standingH1_adaptive | own | 1 | 2041 | 0 | 89 | 8 | 6.95 |
| standingH6_adaptive | own | 1 | 2250 | 24 | 90 | 8 | 362.89 |
| SolioAdaptedH6_sharedAdaptiveChips | own | 1 | 2224 | 28 | 92 | 8 | 458.52 |
| AIrsenalAdaptedH6_sharedAdaptiveChips | own | 1 | 2012 | 72 | 83 | 6 | 541.80 |
| standingH1_adaptive | common | 1 | 2087 | 0 | 88 | 8 | 7.51 |
| standingH6_adaptive | common | 1 | 2220 | 24 | 91 | 8 | 358.71 |
| SolioAdaptedH6_sharedAdaptiveChips | common | 1 | 2239 | 20 | 86 | 8 | 496.68 |
| AIrsenalAdaptedH6_sharedAdaptiveChips | common | 1 | 2141 | 64 | 78 | 6 | 540.94 |
| standingH1_adaptive | own | 2 | 2041 | 0 | 89 | 8 | 7.24 |
| standingH6_adaptive | own | 2 | 2236 | 24 | 91 | 8 | 358.65 |
| SolioAdaptedH6_sharedAdaptiveChips | own | 2 | 2250 | 24 | 88 | 8 | 499.46 |
| AIrsenalAdaptedH6_sharedAdaptiveChips | own | 2 | 1949 | 80 | 85 | 6 | 553.72 |
| standingH1_adaptive | common | 2 | 2087 | 0 | 88 | 8 | 6.94 |
| standingH6_adaptive | common | 2 | 2220 | 24 | 91 | 8 | 357.82 |
| SolioAdaptedH6_sharedAdaptiveChips | common | 2 | 2200 | 24 | 87 | 8 | 497.54 |
| AIrsenalAdaptedH6_sharedAdaptiveChips | common | 2 | 2144 | 68 | 86 | 7 | 545.96 |
| fixed_calendar | own | control | 2095 | 56 | 79 | 8 | 426.71 |
| fixed_calendar | common | control | 2202 | 56 | 93 | 8 | 422.38 |
| hold_no_chips | own | control | 300 | 0 | 0 | 0 | 8.58 |
| hold_no_chips | common | control | 1449 | 0 | 0 | 0 | 8.61 |

Own openings permit each policy to construct its initial squad. Common openings use the same neutral fifteen. Controls have one run per opening; repeated policies have two. All are dependent paths from one reused season, not independent season replications. Hits are already deducted.

## Predeclared decision and matched external comparisons

The primary anchor is the one-week planner with the same forecasts and legal chip resources. The points gate requires a positive mean difference separately for each opening, with no negative paired repetition; it has no minimum gain threshold beyond zero. Full independent integrity and bounded-cost checks are also required. Passing permits historical experimental status, not production promotion.

- standingH6_adaptive: own: +209, +195; common: +133, +133. Points gate passes.
- SolioAdaptedH6_sharedAdaptiveChips: own: +183, +209; common: +152, +113. Points gate passes.
- AIrsenalAdaptedH6_sharedAdaptiveChips: own: -29, -92; common: +54, +57. Points gate does not pass.

Standing-six-week minus external-adapted-six-week paired totals:

- SolioAdaptedH6_sharedAdaptiveChips, own: +26, -14.
- AIrsenalAdaptedH6_sharedAdaptiveChips, own: +238, +287.
- SolioAdaptedH6_sharedAdaptiveChips, common: -19, +20.
- AIrsenalAdaptedH6_sharedAdaptiveChips, common: +79, +76.

Adaptive six-week minus the declared single-run controls:

- fixed_calendar, own: +155, +141.
- hold_no_chips, own: +1950, +1936.
- fixed_calendar, common: +18, +18.
- hold_no_chips, common: +771, +771.

Each control has one path per opening. These differences are descriptive; fixed-calendar search allocation differs from adaptive calendar exploration, so they do not isolate a causal chip-timing gain.


These adaptations share the admitted forecasts, candidate selection, canonical lineup selection and outer chip policy. They test different roster-planning cores under the stated limits. AIrsenal is configured with max_opt_transfers=2, max_total_hit=8, GA effort 10, seed 42 and serial tree search; time limits can truncate exploration. These heuristic restrictions differ from an unrestricted manager. Solio uses its pinned rule-adapted numerical core. This is not a reproduction of either original complete manager.

The [separate full-season forecasting comparison](SEASON_EXTERNAL_RESULTS_2026-10-16.md) covers prior-only standing-method, Dastan-architecture, OpenFPL and component adaptations under a shared planner. It has its own frozen source, forecasts and smaller solve budgets. It remains valid as that distinct track; its scores are not interchangeable with these repeated planner results. There is no fully reproduced original Dastan season manager in this study.

## Integrity, cost and interpretation

All 760 deadline finance/transfer/chip/captain/bench/autosub scores and 20 run provenance signatures reconcile. Every completed native RPC was separately checked for the integer ledger and common mean objective. The twenty supervised jobs took 107.79 measured minutes in serial, with maximum sampled group memory 992.2 MiB and two CPU threads. These are observed research costs, not guaranteed routine-planning latency.

The aggregate records every chip date, component score, transfer hit, native failure/fallback, conditional-bound coverage and repeated difference. Component differences reconcile the total but are not causal estimates of chip timing independent of roster/solver changes. Fixed-calendar search allocates the same envelope to one schedule rather than exploring calendars; the hold control deliberately uses no chips or transfers and is descriptive only.

The approved artifact bridge and changed-next-origin integration were separately tested on invented cases, preserving registry verification and current-only manual minutes sensitivities. The historical study uses a prior-only standing-method reference; the deployment artifact trained on the evaluation season is never backcast.

Observed parent Python/package versions and source-pinned native startup identities are in the aggregate. They differ from repository dependency pins and are not an exact-pinned-environment claim. Small synthetic development/verification checks overlapped parts of this serial historical batch; these are ordinary-load measurements, not isolated timing benchmarks.

The source-checkout tool `tools/audit_season_path.py` independently reconciles all 760 settlements and every retained future action using standard-library integer ledger/formation/count scoring, without importing the planner or season engine. Independent verification here means separately implemented arithmetic within this project, not third-party certification. Separate checks cover run signatures and completed native RPCs. The aggregate retains two auditor assumptions that required repair (reserve-keeper index and an older synthetic reply field); original evidence was preserved, engine/policy outputs were unchanged, and all paths were audited again.

## Numerical quality and decision

The separately [declared fixed-schedule probe](season_policy_quality_protocol.json) ran all fifteen cases in 11.03 supervised seconds, with about 452.3 MiB sampled group memory. All 75 new provisional periods, 39 inputs and 21 output hashes passed the separate ledger/candidate-pool/signature audit. It did not load future outcome or settlement files.

| Frozen origin | 0.5-second objective difference | 2-second difference | 5-second difference |
|---|---:|---:|---:|
| GW1 | +0.00 | +0.00 | +0.00 |
| GW6 | +0.00 | +0.00 | +0.00 |
| GW16 | -27.81 | +0.00 | +0.00 |
| GW30 | +0.00 | +0.00 | +0.00 |
| GW38 | +0.00 | +0.00 | +0.00 |

Differences use the retained frozen plan as the reference and include the bench proxy; they are not realised FPL points. At GW16 the 0.5-second cap lost 27.81 objective units, while 2 and 5 seconds reached the same retained objective. The longer cap tightened that conditional certificate without finding a better feasible plan. Keep the declared 2-second reference setting: this small diagnostic supports neither a blanket reduction to 0.5 nor a realised-points claim for 5 seconds. Five selected calendar anchors do not prove universal budget sufficiency.

The six-week policy meets the predeclared historical points/integrity/cost criteria and is available as experimental decision support. No new forecast weights, retraining or production-default change is justified by this package. The rule-adapted Solio planning core also meets the historical gate; tiny, mixed differences between these planners do not justify a claim of reliable superiority or a more complex default. The capped AIrsenal adaptation fails the own-opening consistency gate. Prospective frozen review remains maintenance, not an unfinished historical stage.

## Limits and next use

- One reused season, not 20 independent seasons. No independent-season confidence interval.
- Restricted candidate pool, mean objective and shared outer chip search and native adaptations, not original complete providers.
- Different solver libraries and wall-clock variability; all declared repetitions retained.
- No global chip/season optimality bound; conditional bounds describe fixed schedule/pool only.
- Historical market/calendar publication clocks reconstructed from mutable archives, not independent historic availability certification.
- Actual approved deployment artifact was not backcast; its compatibility was separately checked on invented cases.
- Expected autosub/vice fallback and scenario-tree recourse are not optimised; actual settlement applies autosubs/vice correctly.
- Forecasting adaptations in earlier comparison use a separate budget/source track; their scores are not pooled into this qualification.

Read the [policy status](season_policy_status.json), [fixed protocol](../src/fpl_predict_resources/season_policy_qualification_protocol.json), [qualification workflow](season_policy_qualification.md) and [machine-readable results](season_policy_qualification_results.json). Model weights and normal weekly defaults remain unchanged. New deadline evidence should lead to a fresh bounded plan; historical gains do not promise future season gains. Prospective weekly review is maintenance, not a reason to delay completing this historical study.
