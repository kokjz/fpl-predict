# FPL-native and market combination: development gate failed

Date: 2 November 2026. Research only; approved 1.0.0 and weekly defaults unchanged.

The FPL-native variant improves pooled candidate player-GW RMSE by 0.4224% and fixture RMSE by 0.4144%, falling short of both predeclared 0.5% gains. Eight of ten development criteria pass. Stage C was conditional on a full development pass, so no audit-season fit or data retrieval was attempted. The positive fixed-squad result does not override the failed error gates.

## Frozen design and provenance

One control and one challenger per development fold, with unchanged HGB7 capacity, seed 20260921, 200 iterations, learning rate 0.05, L2 20, minimum leaf 60, early stopping off, two threads, 730.5-day age weights and fixture clip [0,20]. Train 2020/21â€“2021/22, test 2022/23; train 2020/21â€“2022/23, test 2023/24. Four serial guarded fits, no retry. Numerical source `c0fc0b710dc7c2eef5c0725f212159273ce55b35`. Protocol frozen at `cc51da6b6f93d18bc9ab8e330f03bd44f99db70f`, pushed before any real-data calculation; [protocol](fpl_native_combination_protocol_2026-11-02.json) LF SHA256 `a6760823ffd6b145fc7e332d21a83ffde8bf26eea6e0448fa987525987b1d188`. The earlier tooling return numbers in the protocol are superseded by the current handover; scientific content is unchanged.

The stable union is 49 CORE features, 146 native_development.FPL features and 3 MARKET features (198 total). Training-only all-NaN omission leaves195 challenger features for2022/23 and198 for2023/24; the controls retain49. The FPL builder reads an explicit FPL/result-only whitelist and uses the original WindowIndex and league-table arithmetic. Static dependency audit passes. CORE includes FPLâ€™s own expected-statistic EW features; these are separate from Understat data.

On all106042 development rows, all six us_* player columns and eight Understat team-statistic columns were replaced with NaN and the features rebuilt. All198 full-union feature bytes stayed identical (array SHA256 `8982656c751dd10b7c1e30dae1f93789d22edc45e2753ab150c0af1b79ca8990`). The resulting union also exactly matches the corresponding FPL-only projection of the accepted PR50 matrix. All13 control/cohort/clock/target arrays match the original development proof; both refitted control prediction arrays match PR50 byte-for-byte. No Understat retrieval or mirror access occurred. Frozen historical research files were read only within the admitted non-Understat feature construction and provenance checks.

The immutable original I4 panels and class-A guard passed. Market features were finite for every development row and reused the hash-verified accepted strictly-prior market matrix; no market data were retrieved. Inputs, cutoffs (deadline minus3h), candidate predicate, double-gameweek aggregation, targets, weights and fixed-squad evaluation were shared.

## Errors and ranking

Relative change %=100*(candidate/control-1); negative error change favours the candidate. Full-precision values, all-player/minutes/cold-start diagnostics, position diagnostics and all fixed-squad totals are in the [machine-readable results](fpl_native_combination_results_2026-11-02.json).

| Scope | Unit | Control RMSE | Candidate RMSE | Relative % | Control MAE | Candidate MAE | Relative % |
|---|---|---:|---:|---:|---:|---:|---:|
| 2022-23 | candidate_player_gw | 3.065020483 | 3.053702889 | -0.369250 | 2.228148637 | 2.198070472 | -1.349917 |
| 2022-23 | candidate_fixture | 2.965629114 | 2.954258176 | -0.383424 | 2.154311647 | 2.124919958 | -1.364319 |
| 2022-23 | all_player_gw | 2.036064440 | 2.024919801 | -0.547362 | 1.098103381 | 1.086494418 | -1.057183 |
| 2022-23 | all_fixture | 1.965855425 | 1.955272921 | -0.538316 | 1.057028260 | 1.045819505 | -1.060403 |
| 2023-24 | candidate_player_gw | 3.094400016 | 3.079753194 | -0.473333 | 2.199887973 | 2.180586944 | -0.877364 |
| 2023-24 | candidate_fixture | 3.022407245 | 3.008973209 | -0.444481 | 2.155004307 | 2.135298223 | -0.914434 |
| 2023-24 | all_player_gw | 1.951863062 | 1.935587880 | -0.833828 | 0.980228339 | 0.970950847 | -0.946462 |
| 2023-24 | all_fixture | 1.908825788 | 1.893264669 | -0.815219 | 0.958794921 | 0.949470216 | -0.972544 |
| pooled | player_gw | 3.079909201 | 3.066901046 | -0.422355 | 2.213860625 | 2.189231158 | -1.112512 |
| pooled | fixture | 2.994065693 | 2.981657287 | -0.414433 | 2.154656915 | 2.130093174 | -1.140030 |
| pooled | all_player_gw | 1.991439124 | 1.977607506 | -0.694554 | 1.035011621 | 1.024650560 | -1.001057 |
| pooled | all_fixture | 1.935917036 | 1.922742516 | -0.680531 | 1.005098934 | 0.994886149 | -1.016097 |

## Development gate (unchanged I4)

| Criterion | Verdict | Exact comparison |
|---|---|---|
| pooled_player_gw_rmse_gain | FAIL | `{"candidate":3.0669010457143693,"threshold":3.0645096547846626,"passed":false}` |
| pooled_player_gw_mae_noninferiority | PASS | `{"candidate":2.1892311581842,"threshold":2.224929927624157,"passed":true}` |
| pooled_fixture_rmse_gain | FAIL | `{"candidate":2.9816572868846944,"threshold":2.9790953648626277,"passed":false}` |
| pooled_fixture_mae_noninferiority | PASS | `{"candidate":2.130093173823079,"threshold":2.1654301992114853,"passed":true}` |
| 2022-23_candidate_player_gw_rmse_noninferiority | PASS | `{"candidate":3.0537028894822287,"threshold":3.0803455858405697,"passed":true}` |
| 2022-23_candidate_fixture_rmse_noninferiority | PASS | `{"candidate":2.9542581756364172,"threshold":2.9804572599627166,"passed":true}` |
| 2023-24_candidate_player_gw_rmse_noninferiority | PASS | `{"candidate":3.0797531944405896,"threshold":3.1098720158737114,"passed":true}` |
| 2023-24_candidate_fixture_rmse_noninferiority | PASS | `{"candidate":3.0089732091257146,"threshold":3.0375192808479308,"passed":true}` |
| pooled_ndcg10_not_lower | PASS | `{"candidate":0.44413581588847095,"control":0.43674514166138834,"passed":true}` |
| mean_fixed_squad_delta_nonnegative | PASS | `{"delta":19.225,"passed":true}` |

Pooled NDCG@10: control0.43674514166138834, candidate0.44413581588847095. Mean fixed-squad difference over40panels: +19.225points; equal20panels per season. This is fixed-squad XI/captain/autosub replay, not observed transfer/chip or season-strategy gain.

## Descriptive uncertainty and positions

Paired four-GW circular-block bootstrap,1000draws,seed20261015: `{"scope":"descriptive fixed-prediction uncertainty, not training or selection uncertainty","difference":"left_minus_right; negative error difference favours left","samples":1000,"block_length":4,"seed":20261015,"gameweeks":69,"contiguous_segments":[3,31,35],"status":"descriptive_interval","confidence":0.95,"rmse":{"delta":-0.013008155074236694,"lower":-0.0267285262934999,"upper":2.5534251917464218e-05},"mae":{"delta":-0.024629466317449476,"lower":-0.03647198646548876,"upper":-0.0135028113929265}}`. The development RMSE interval crosses zero. This interval describes fixed predictions on reused outcomes; it does not account for model fitting or adaptive selection. It was not an additional development gate.

| Position | Control candidate-fixture RMSE | Candidate RMSE | Control MAE | Candidate MAE |
|---|---:|---:|---:|---:|
| 1 | 2.7785377899799397 | 2.780306584031339 | 2.1835530619118373 | 2.1692688485999243 |
| 2 | 2.8569143097523124 | 2.8418650162115604 | 2.151987686184342 | 2.1342016733785796 |
| 3 | 3.010230626259459 | 2.9977852352896606 | 2.0557925944163484 | 2.028733002478675 |
| 4 | 3.567742444584848 | 3.5530220592777844 | 2.56538054933577 | 2.5164762674405594 |

## Audit gates and limits

| Stage C gate | Outcome |
|---|---|
| 2: audit_rmse | Not evaluated: Gate B failed |
| 3: audit_season_stability | Not evaluated: Gate B failed |
| 4: audit_mae | Not evaluated: Gate B failed |
| 5: audit_block_interval | Not evaluated: Gate B failed |
| 6: fixed_squad_points | Not evaluated: Gate B failed |
| 7: full_scoring | Not evaluated: Gate B failed |

No2024/25 or2025/26 audit was run. The single conditional E0 2025/26 retrieval was not attempted; no new source-policy review was needed or claimed. No2026/27 scoring. The eight-fit ceiling was not a requirement to consume unused audit fits. Audit assembly and gates have synthetic tests; their real-data path remains unqualified by this package.

All six guarded jobs completed with exit0, no guard reason and zero remaining processes. Peak committed job memory 1683148800bytes; maximum job time 139.15599999995902seconds; sum guarded time 244.63999999989755seconds. At numerical-batch completion, package size including reserve 71805581bytes, below256MiB; free space 859355918336bytes. Limits were two threads,4GiB,900seconds per job, serial execution and at least5GiB free.

This variant was proposed after PR50 outcomes had been inspected, so2022/23â€“2024/25 are adaptive-lineage evidence; this package only scored the two development folds. A small historical error gain is not independent confirmation or a deployability claim. Historical event timestamps do not establish publication before old deadlines, and corrected provider statistics, reconstructed schedules and lagged proxies remain limitations. No prospective shadow deadlines, current-season gate, integrity/artifact build or production ingestion were performed.

Engineering: prior non-mutating cwd/platform errors and a failed no-op author-identity commit were preserved in private coordination evidence, followed by a verified command-scoped identity and synchronous checks. New synthetic-test fixture mistakes were corrected before outcomes; no scientific specification changed. The numerical source passed targeted Windows tests, the legacy suite, privacy and exact-head Ubuntu CI before this single real batch. No guard was weakened or real job retried.

**Nothing promoted.** No trained artifact was saved, no registry/default/product pipeline was changed, and no consumer release-notes entry is required. Source release remains subject to architect pre-merge review; no merge, tag or branch cleanup at this boundary.
