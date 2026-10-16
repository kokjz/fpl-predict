# Practical selection results — 15 October 2026

**The incumbent performed well under the shared selection policy, but superiority or parity with the original external systems is not established.** In particular, the original Dastan archive gives a small, inconclusive lineup advantage to Dastan. Better prediction RMSE and better squad decisions are distinct questions.

This study uses the [fixed protocol and reproduction workflow](selection_benchmark.md). It reuses already inspected historical forecasts/outcomes; it is retrospective, conditional and descriptive. No parameters were searched, no models were fitted, and no approved weights or weekly forecasts changed. [Machine-readable aggregates, intervals, decomposition and evidence hashes](SELECTION_BENCHMARK_RESULTS_2026-10-15.json) accompany this report.

The [decision-relevance interpretation](comparison_interpretation.md) explains
v1's original-Dastan top-10 ranking win, the complete candidate-pool
non-appearance error decomposition, and why outcome-based exclusions cannot
establish general superiority. Original figures below remain unchanged.

## Shared 2025/26 window: GW28–38

Five forecast methods use the same reconstructed market, common rules and selection policy. Twelve neutral owned squads are held for eleven GWs, giving **132 paired squad-weeks per method**. Verified predeadline roster captures cover 9,099 listed player-weeks; club-calendar evidence establishes blanks, while played-club forecasts require complete fixture coverage. Doubles are summed. Every declared panel completed.

The primary measure is realised points after automatic substitutions and captain fallback. Intervals below are simultaneous 95% four-GW-block descriptive intervals across the four incumbent comparisons, after averaging squads within GW. Negative differences favour the incumbent. The predeclared material margin is 0.25 points/GW.

| Method | Owned-squad points/GW | Difference vs incumbent | Simultaneous interval |
| --- | ---: | ---: | --- |
| Incumbent-method reference | 37.174 | — | — |
| Native HGB adaptation | 36.841 | -0.333 | [-1.197, +0.530] |
| Dastan architecture adaptation | 36.568 | -0.606 | [-1.470, +0.258] |
| OpenFPL cv1 adaptation | 36.606 | -0.568 | [-1.432, +0.295] |
| AIrsenal-inspired component adaptation | 37.129 | -0.045 | [-0.909, +0.818] |

**All primary comparisons are inconclusive**, including equivalence at the material margin. That conclusion also holds with two- and six-GW blocks. These are shared-policy forecasting comparisons, not reproductions of the external projects' complete selection engines. The incumbent is a training-only reference fit of the approved method, not the production artifact blindly applied backwards.

### Secondary budget and transfer experiments

Weekly resets independently optimise a fresh £100m squad each GW. Six rolling paths per method start from identical neutral squads, with one free transfer and £100m total capital; subsequent decisions preserve purchase prices, bank, half-profit selling, banked transfers and four-point hits. Only that week's forecasts and snapshot price quotes are available to the policy. No chip or future-price hindsight is used.

| Method | Weekly reset points/GW | Reset difference | Rolling net points, mean over eleven-GW paths | Rolling difference |
| --- | ---: | ---: | ---: | ---: |
| Incumbent-method reference | 69.182 | — | 624.667 | — |
| Native HGB adaptation | 63.909 | -5.273 | 557.500 | -67.167 |
| Dastan architecture adaptation | 59.273 | -9.909 | 547.667 | -77.000 |
| OpenFPL cv1 adaptation | 58.636 | -10.545 | 537.500 | -87.167 |
| AIrsenal-inspired component adaptation | 60.909 | -8.273 | 552.833 | -71.833 |

The incumbent leads these measured secondary totals. Four-GW reset intervals favour it beyond the material margin against the Dastan and OpenFPL **adaptations**, but all reset comparisons are inconclusive with two-GW blocks. The result is sensitive to the short window and uncertainty method; do not elevate the most favourable sensitivity into a general superiority claim. Rolling totals are path dependent: there is no independent-season confidence interval from these six correlated scenarios in one eleven-GW window.

Snapshot quotes approximate execution prices; they are not certified deadline transaction ticks. The one-GW mean policy does not value future fixtures, saved-transfer optionality or joint chip scheduling. These totals cannot establish full-season optimal management.

### Previously frozen squads: calendar repair

The earlier report covered 181/220 fixed-squad panels because some blank weeks lacked player rows. A separate replay now admits **all 220**, filling zero only where the archived roster and as-of club calendar positively establish a blank. Original reports and prediction bytes are preserved; no arbitrary missing forecast is filled.

| Method | All 220 panels: mean points/GW |
| --- | ---: |
| Incumbent-method reference | 41.955 |
| Native HGB adaptation | 41.532 |
| Dastan architecture adaptation | 41.286 |
| OpenFPL cv1 adaptation | 41.586 |
| AIrsenal-inspired component adaptation | 41.132 |

These are different coverage and scenario distributions from the primary experiment and the earlier 181-panel table. Lower means after adding blank weeks are not model deterioration. This sensitivity is not substituted for the declared primary result.

## Original Dastan archive: 2024/25 GW15–38

Original exported forecasts are compared directly with retained v1 predictions and averaging baselines, without replacing Dastan by the later architecture adaptation. The 17,622 matched archived player-weeks reconcile with actual points, minutes and positions. **91 lack earlier metadata**, leaving 17,531 for model-neutral weekly scenario construction. Twelve newly sampled owned squads each GW give **288 paired panels per method**.

| Original archived method | Points/GW | Difference vs v1 | Simultaneous four-GW interval |
| --- | ---: | ---: | --- |
| v1 | 21.847 | — | — |
| Dastan | 22.045 | +0.198 | [-0.295, +0.691] |
| Dastan without ep_next | 22.073 | +0.226 | [-0.267, +0.719] |
| Last-five average | 21.628 | -0.219 | [-0.712, +0.274] |
| Recency average | 21.562 | -0.285 | [-0.778, +0.208] |

**Neither Dastan superiority, v1 superiority nor equivalence is established.** Two- and six-GW sensitivities are also inconclusive. This does not erase Dastan's lower matched historical RMSE; it measures a different decision outcome.

This archive omits some blank-player weeks and lacks a complete predeadline market. Squads are sampled independently within each week's shared admitted export; they are not a continuous season squad. Earlier fixture prices and clubs support scenario sampling only, not financial execution. Clubs can lag transfers, ownership is unavailable, and the analysis cutoff is reconstructed rather than a verified original forecast capture. Original methods have unequal fitting/input/selection histories. The broad roster includes inactive players, explaining the low absolute points: these are stress scenarios, not a representative population of strong FPL squads. No favourable subset was chosen after scoring.

## Separate original fpl-forecast archive: 2026/27 GW6

On twelve neutral owned squads from the **562 shared exported players**, the saved approved method averages **36.167 points**, versus **36.667** for the original external forecast: **+0.500 to the external method** in one completed GW. There is no gameweek-level interval or season-ranking inference. The external forecast was generated on 22 September, whereas the local forecast was generated on 9 October, before the 10 October deadline. Information cutoffs differ materially. No actual manager squad was used or assessed.

This is a separate diagnostic, not pooled with either historical window. Public CSV bytes and frozen-manifest hashes, stable player identities, positions and finalised outcomes were checked. [Original archive and source limitations](HISTORICAL_EXTERNAL_RESULTS_2026-10-15.md#separate-archived-external-forecast-completed-202627-gw6).

## Coverage, cost and verification

Original OpenFPL, AIrsenal, Scout and Lionel full systems are **not** scored here without compatible original forecast/training/input evidence. Their [admission inventory](EXTERNAL_MODEL_ADMISSION_2026-10-15.md) explains each disposition. OpenFPL and AIrsenal results above refer only to the explicitly modified methods. Missing original-system evidence is not evidence that those systems perform poorly or require heavier hardware.

The completed four studies took **40.17 seconds** under sampled resource monitoring, with peak process-group RSS **0.269 GiB**, two solver threads and no fitting/GPU/remote compute. Including the five-solve probe and a failed pre-scoring sampler, supervised time was **55.43 seconds**. The initial uniform sampler could not populate the £90–100m rotation-risk stratum within its attempt limit; its directory is retained. Protocol v2's source-only price tilt was committed before any replacement scoring. No result-driven parameter search followed.

All **3,609 model-panel scores** were independently checked against the existing replay scorer; no evaluated row had a zero-minute card, while synthetic tests cover that distinct rule. The **30 rolling paths and 669 transactions** were separately reconstructed to check bank balances, selling profits, buy eligibility, free-transfer carry and hit deductions. Score decomposition into XI, autosubs, captain bonus and hits is retained in the JSON. An additional source-only scenario audit matches every owned-panel action to its frozen IDs or committed seed-plus-GW rule. The original Dastan run manifest contained an unused preliminary sample; the preserved supplemental audit records the actual weekly schedules and their hashes. The final tool writes the full schedule directly. This metadata repair changes no scored choices or totals. Independent algorithm checks are useful validation, not independent statistical replication.

The watchdog monitored disk growth/free space throughout each job. There were no storage-limit breaches or artifact offloads. Raw inputs, scenario/action rows, frozen forecasts, source manifests and failed-run evidence remain outside Git; the repository contains tools, protocols and aggregate findings only. Local execution used Python 3.12.14, NumPy 2.3.5, pandas 2.2.3, SciPy 1.18.1 and scikit-learn 1.9.1; the environment is recorded rather than assumed equal to every dependency-pinned installation.

Pre-scoring implementation: `caed44f`; exact source/input/output hashes are in the aggregate JSON. Later input-guard hardening does not alter these retained predictions, admitted input bytes or actions. Data sources include the pinned [Vaastav archive](https://github.com/vaastav/Fantasy-Premier-League), [Dastan revision](https://github.com/qazybekb/smartplayfpl-dastan/tree/758db9247e8b3a9a870c991064f74d8339d61cd0), the [fpl-forecast frozen publication](https://github.com/daniel-mehta/fpl-forecast/tree/f76514676147dad7e6d7e247576c9d19ce90b330/data), archived bootstraps and the [dated fixture-source audit](PROVENANCE_FINDINGS_2026-10-15.md). Publisher capture claims, manual calendar transcription, historical corrections and reused-test selection remain limitations.

The approved model remains unchanged. This benchmark improves the evidence and tooling; it does not prove a future points gain or automatically select a new champion.


## Availability follow-up — 16 October 2026

The [matched incumbent availability study and six-method rebenchmark](INCUMBENT_AVAILABILITY_RESULTS_2026-10-16.md)
now tests structured labels against the full participation method, followed by
unconditional points-feature augmentation on historical data. Appearance error
improves, but points MAE/ranking and owned/rolling decisions do not jointly pass
the progression checks. The challenger is unapproved; original-system comparisons
in this report remain unchanged. New aggregates/provenance/cost are linked above.


## Conditional integration follow-up — 16 October 2026

[The controlled four-arm integration/selection study](CONDITIONAL_SELECTION_RESULTS_2026-10-16.md)
now isolates old/new appearance probabilities with one shared conditional-return
model and current/expected bench selection. Points RMSE and MAE improve versus
the historical incumbent reference; ranking and the fixed combined selector do
not qualify. Matched external error/common-mean-policy results are reported,
including an observed but uncertain RMSE win over the Dastan adaptation. Original
system comparisons in this document remain unchanged. No model is promoted.
