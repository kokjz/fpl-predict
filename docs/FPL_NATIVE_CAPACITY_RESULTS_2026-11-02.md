# Capacity-matched compliant combination: development gate failed

Date: 2 November 2026. Research only; approved 1.0.0 and weekly defaults unchanged.

The existing HGB15 specification on the unchanged compliant union improves pooled candidate RMSE by 0.4604% at player-GW level and 0.4537% at fixture level. Both miss the predeclared 0.5% requirement. Pooled NDCG@10 is also below control. Seven of ten development criteria pass. **Stage C not run**; its four fits and single E0 2025/26 retrieval lapsed. Nothing promoted.

## Frozen design and provenance

The single capacity arm uses the pre-existing HGB15: 15 leaves, 180 iterations, learning rate 0.05, L2 30, minimum leaf 60, early stopping false, seed 20260921. The control remains HGB7: 7 leaves, 200 iterations, L2 20. Both retain two threads, 730.5-day age weights, clip [0, 20], points_core, unchanged I4 candidates, origins at deadline minus 3 hours, the original CSV export boundary, training-prefix guard and double-gameweek aggregation. No grid, tuning, alternative seeds, blends or feature selection.

Train 2020/21-2021/22, test 2022/23; train 2020/21-2022/23, test 2023/24. The [protocol](fpl_native_capacity_protocol_2026-11-02.json), LF SHA256 `408c348c3a3d67802521363ab2cef3afda5f08a8d1780d5cc69aea2de3f39877`, was frozen and pushed at `48e2f6fc604ab934c47e7fdf8f1c5e4993e943c1` before calculation. Numerical source `c71ca14c3073a8741b0f4fa16532df59b41f716e`. The later export repair changes only a private variable binding; scientific source, specification and gates remain unchanged.

The union has 49 CORE, 146 native FPL and 3 MARKET features, in that order. Its canonical list SHA256 is `7424ff6841b5d71e92a9ea7d91605fa846f893a98dac7a2c5db67e2a011228e5`. Training-only all-NaN omission leaves 195 capacity features for 2022/23 and 198 for 2023/24; both controls retain 49. Market features are finite on every development row.

On all 106042 development rows, the rebuilt full union exactly matches accepted PR56 array SHA256 `8982656c751dd10b7c1e30dae1f93789d22edc45e2753ab150c0af1b79ca8990`. The static FPL/result whitelist audit passes. The original ablation proof was also re-run: replacing all six us_* player fields and eight Understat team-statistic fields with NaN leaves native and full-union bytes identical. The union matches the accepted PR50 FPL-only projection. No Understat retrieval, mirror or copy access occurred. CORE contains FPL expected-statistic fields, separate from Understat.

All 13 original control/cohort/clock/target prefix arrays match. Original I4 panels and the class-A guard pass. Both refitted control prediction arrays equal frozen PR56 bytes. Shared keys, candidate universe, cutoffs, targets, age weights, double-gameweek context and evaluation/replay remain unchanged. Strictly prior market values are reused from the accepted matrix; no market retrieval occurred. Historical event clocks do not establish source publication before every old deadline.

## Errors, ranking and unchanged Gate B

Relative change %=100*(capacity/control-1); negative error change favours capacity. The [full-precision JSON](fpl_native_capacity_results_2026-11-02.json) includes all-player, minutes/cold-start, position, ranking, fixed-squad and paired-interval diagnostics.

| Scope | Unit | Control RMSE | Capacity RMSE | Relative % | Control MAE | Capacity MAE | Relative % |
|---|---|---:|---:|---:|---:|---:|---:|
| 2022-23 | candidate_player_gw | 3.065020483 | 3.051421804 | -0.443673 | 2.228148637 | 2.194307950 | -1.518781 |
| 2022-23 | candidate_fixture | 2.965629114 | 2.952081057 | -0.456836 | 2.154311647 | 2.121671402 | -1.515113 |
| 2022-23 | all_player_gw | 2.036064440 | 2.023290266 | -0.627395 | 1.098103381 | 1.084190210 | -1.267018 |
| 2022-23 | all_fixture | 1.965855425 | 1.953835176 | -0.611451 | 1.057028260 | 1.043645698 | -1.266055 |
| 2023-24 | candidate_player_gw | 3.094400016 | 3.079658086 | -0.476407 | 2.199887973 | 2.174649982 | -1.147240 |
| 2023-24 | candidate_fixture | 3.022407245 | 3.008785749 | -0.450684 | 2.155004307 | 2.129752348 | -1.171782 |
| 2023-24 | all_player_gw | 1.951863062 | 1.933590661 | -0.936152 | 0.980228339 | 0.967142155 | -1.335014 |
| 2023-24 | all_fixture | 1.908825788 | 1.891197652 | -0.923507 | 0.958794921 | 0.945768872 | -1.358586 |
| pooled | player_gw | 3.079909201 | 3.065729994 | -0.460377 | 2.213860625 | 2.184369284 | -1.332123 |
| pooled | fixture | 2.994065693 | 2.980481294 | -0.453711 | 2.154656915 | 2.125699481 | -1.343946 |
| pooled | all_player_gw | 1.991439124 | 1.975785778 | -0.786032 | 1.035011621 | 1.021541088 | -1.301486 |
| pooled | all_fixture | 1.935917036 | 1.920977434 | -0.771707 | 1.005098934 | 0.991904836 | -1.312716 |

| Criterion | Verdict | Exact comparison |
|---|---|---|
| pooled_player_gw_rmse_gain | FAIL | `{"candidate":3.0657299942369693,"threshold":3.0645096547846626,"passed":false}` |
| pooled_player_gw_mae_noninferiority | PASS | `{"candidate":2.184369283849413,"threshold":2.224929927624157,"passed":true}` |
| pooled_fixture_rmse_gain | FAIL | `{"candidate":2.980481293505151,"threshold":2.9790953648626277,"passed":false}` |
| pooled_fixture_mae_noninferiority | PASS | `{"candidate":2.125699481440618,"threshold":2.1654301992114853,"passed":true}` |
| 2022-23_candidate_player_gw_rmse_noninferiority | PASS | `{"candidate":3.051421804350705,"threshold":3.0803455858405697,"passed":true}` |
| 2022-23_candidate_fixture_rmse_noninferiority | PASS | `{"candidate":2.952081057451233,"threshold":2.9804572599627166,"passed":true}` |
| 2023-24_candidate_player_gw_rmse_noninferiority | PASS | `{"candidate":3.079658086134078,"threshold":3.1098720158737114,"passed":true}` |
| 2023-24_candidate_fixture_rmse_noninferiority | PASS | `{"candidate":3.008785748804436,"threshold":3.0375192808479308,"passed":true}` |
| pooled_ndcg10_not_lower | FAIL | `{"candidate":0.43664655966917926,"control":0.43674514166138834,"passed":false}` |
| mean_fixed_squad_delta_nonnegative | PASS | `{"delta":16.975,"passed":true}` |

Pooled NDCG@10: control 0.43674514166138834, capacity 0.43664655966917926. Mean fixed-squad delta over 40 panels: +16.975 points. These XI/captain/autosub replays are not transfer, chip or full season strategy outcomes.

## Descriptive interval and positions

Four-GW circular-block bootstrap, 1000 draws, seed 20261015: `{"scope":"descriptive fixed-prediction uncertainty, not training or selection uncertainty","difference":"left_minus_right; negative error difference favours left","samples":1000,"block_length":4,"seed":20261015,"gameweeks":69,"contiguous_segments":[3,31,35],"status":"descriptive_interval","confidence":0.95,"rmse":{"delta":-0.014179206551636625,"lower":-0.026446617942891826,"upper":-0.0029881095890119066},"mae":{"delta":-0.029491340652235867,"lower":-0.04063248155381755,"upper":-0.018658043745926892}}`. The RMSE interval lies entirely below zero. This describes fixed predictions and omits fitting and adaptive-selection uncertainty; it is not an extra development gate and does not override the failed minimum-gain and ranking criteria.

| Position | Control candidate-fixture RMSE | Capacity RMSE | Control MAE | Capacity MAE |
|---|---:|---:|---:|---:|
| 1 | 2.7785377899799397 | 2.7767802605234264 | 2.1835530619118373 | 2.1619431534073827 |
| 2 | 2.8569143097523124 | 2.8376336008089504 | 2.151987686184342 | 2.1255993650932803 |
| 3 | 3.010230626259459 | 3.000184075243822 | 2.0557925944163484 | 2.029094075253259 |
| 4 | 3.567742444584848 | 3.549719499056888 | 2.56538054933577 | 2.5101692613275537 |

## Increment over frozen PR56 union HGB7 (descriptive)

The following comparison uses frozen PR56 union HGB7 predictions. It adds zero fits and has no gate.

| Scope | Unit | HGB7 RMSE | HGB15 RMSE | Relative % |
|---|---|---:|---:|---:|
| 2022-23 | candidate_player_gw | 3.0537028894822287 | 3.051421804350705 | -0.07469898723220236 |
| 2022-23 | candidate_fixture | 2.9542581756364172 | 2.952081057451233 | -0.07369424253909074 |
| 2023-24 | candidate_player_gw | 3.0797531944405896 | 3.079658086134078 | -0.0030881794905956994 |
| 2023-24 | candidate_fixture | 3.0089732091257146 | 3.008785748804436 | -0.006230042883403897 |
| pooled | player_gw | 3.0669010457143693 | 3.0657299942369693 | -0.038183542929637326 |
| pooled | fixture | 2.9816572868846944 | 2.980481293505151 | -0.03944093054276676 |

Against frozen union HGB7, pooled NDCG@10 changes by -1.6862536078766421% and mean fixed-squad delta is -2.25 points. The paired RMSE interval spans zero: `{"scope":"descriptive fixed-prediction uncertainty, not training or selection uncertainty","difference":"left_minus_right; negative error difference favours left","samples":1000,"block_length":4,"seed":20261015,"gameweeks":69,"contiguous_segments":[3,31,35],"status":"descriptive_interval","confidence":0.95,"rmse":{"delta":-0.0011710514773999314,"lower":-0.005946560052419847,"upper":0.0034742894510676465},"mae":{"delta":-0.004861874334786393,"lower":-0.009177878124610094,"upper":-0.00043964645287618726}}`. Increasing to this capacity adds only a small error increment and worsens ranking and replay totals; the tested capacities remain near the 0.42%-0.46% compliant-input plateau. This does not establish the outcome of untested capacities.

## Export stop and bounded repair

All four fits completed before the original aggregate worker failed during CSV export. The frozen HGB7 diagnostic reused the analysed DataFrame variable name for an NPZ context manager. The report was already written correctly; the CSV was missing. Execution stopped without retry, retrieval or publication. The architect independently validated the persisted report and confirmed the failed development gate.

A private variable rename and an end-to-end synthetic aggregate/export regression preceded one explicitly authorised guarded no-fit continuation. The new report is byte-identical to the original (SHA256 `baf9dd50dbe2c7d76e28e8e8a938f23e7eaa99274287a6cd0df1e1aaa4032d58`). The CSV is now written (SHA256 `e2cf71cce66e77e28ffce400b38e56a4f6a523fde731a02e14f287740f6e2426`). The fit ledger is byte-unchanged at four completed fits, and failed output/receipts remain preserved. No public scientific code, protocol, specification or gate changed.

## Conditional audit gates and exclusions

| Stage C gate | Outcome |
|---|---|
| 2: audit_rmse | Not evaluated: Gate B failed; authority lapsed |
| 3: audit_season_stability | Not evaluated: Gate B failed; authority lapsed |
| 4: audit_mae | Not evaluated: Gate B failed; authority lapsed |
| 5: audit_block_interval | Not evaluated: Gate B failed; authority lapsed |
| 6: fixed_squad_points | Not evaluated: Gate B failed; authority lapsed |
| 7: full_scoring | Not evaluated: Gate B failed; authority lapsed |

Stage C not run. No audit admission, 2024/25 or 2025/26 candidate comparison, new panels, full-scoring audit, policy-page re-review or E0 2025/26 retrieval attempt. The unused four fits and single conditional retrieval lapsed. No current-season scoring, Stage D integrity/artifact build, promotion, live ingestion or prospective shadow evaluation. The real audit path is not qualified by this package.

## Resources, verification and limits

Seven recorded serial guarded jobs: six completed and one original aggregate failed with exit 1 and no resource guard reason. All ended with zero active processes. Four fits, zero new fits in repair, zero dataset retrievals. Maximum job time 136.48499999986961 seconds; peak committed job memory 1684766720 bytes; total guarded time 266.79699999978766 seconds. Limits: two threads, 4 GiB, 900 seconds per job, package growth at most 256 MiB, at least 5 GiB free. The original batch package size including reserve was 73339014 bytes. No numerical limit was weakened.

Targeted Windows tests, legacy tests and exact-head Ubuntu CI full tests/privacy/wheel passed before the original real batch. The new private regression covers the previously missed aggregate/export path with the diagnostic enabled; no fit is allowed in that test or the continuation. Full local Windows pytest remains blocked by an unchanged POSIX resource import; Ubuntu CI is authoritative. Non-mutating setup/recording corrections are retained privately. The sole real continuation was explicitly authorised after the stop; it was not a refit.

The capacity choice was adaptive after a near miss, and development folds have been inspected repeatedly: this is a declared forking-path risk. Development gains alone would be weak evidence. The decisive unseen-season check was not reached. Reconstructed schedules, corrected historical inputs and lagged proxies do not guarantee historical source availability. Fixed-squad and bootstrap evidence do not establish deployability or independent model selection.

**Approved 1.0.0 unchanged.** No artifact was saved, registry/default/product pipeline changed, or consumer release-notes entry added. Architect pre-merge review is PENDING. No merge, tag or branch cleanup at this boundary.
