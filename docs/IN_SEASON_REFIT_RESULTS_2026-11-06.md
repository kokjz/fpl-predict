# Annual versus GW19 refits of the 1.0.0 recipe

Outcome: **NO_HARM**. This retrospective study leaves approved 1.0.0 unchanged. Architect pre-merge review: **PENDING**.

[Aggregate JSON](IN_SEASON_REFIT_RESULTS_2026-11-06.json) · [Frozen protocol](in_season_refit_protocol_2026-11-06.json)

The same original core recipe predicts GW20–38 in 2023/24, 2024/25 and 2025/26. Annual fits use earlier seasons; refit19 adds current-season matches strictly before the minimum GW20 cutoff. The target is points_core. No auxiliary or defensive-contribution heads are refitted.

Recipe from the hash-verified incumbent: `hgb7`, blend `1.0`. Original uncorrected CORE features, sample_weights measured from each training set’s latest row, and the existing fit_estimator are reused. Predictions blend the clipped core forecast with ew4_points_core.

Numerical source `a1f665616a90a53c84c6eb8dbf1e7cff5e2cefb0`; freeze commit `19279d5b8bf845c94cd5da8bdf5c8d9f43124976`; protocol LF SHA256 `bc03200cf30ca275c328acfab7f1ac7546148aa75fe67e45ad36a8d90f25f72a`.

## Admission and reproduction

| Season | Annual rows | Refit19 rows | Added rows | Test fixtures |
|---|---|---|---|---|
| 2023-24 | 76317 | 90031 | 13714 | 16011 |
| 2024-25 | 106042 | 118785 | 12743 | 14540 |
| 2025-26 | 133325 | 147500 | 14175 | 15572 |

All six training sets passed max(train.ts) < min(test.cutoff), with postponed fixtures excluded by match time. The future-season refusal passed. Stage A ran no fit.

The first 1000 receipt tokens had at most 10 decimal places; the applied parity rule was `absolute_1e-9`. The reference was filtered to each tested season and GW20–38. Both key sets matched exactly, with no missing, extra or duplicate keys. The gate ran inside the second annual fit job before any further fit.

| Season | Keys | Maximum absolute difference | New full-precision prediction SHA256 |
|---|---|---|---|
| 2024-25 | 14540 | 4.99982277802e-11 | 418daf53f037da0faed42ed4bd7f31c4cc23d04d6b10d2ffb6b97ddf70dbd287 |
| 2025-26 | 15572 | 4.99968955125e-11 | 22327fe4f37115ed8cd55156179508ae34dd39f8460403b7518393f6d5ad4605 |

## Forecast errors and ranking

| Window | Unit | Annual RMSE | Refit19 RMSE | Annual MAE | Refit19 MAE | Annual bias | Refit19 bias |
|---|---|---|---|---|---|---|---|
| Pooled | candidate_player_gw | 2.988473205 | 2.983851551 | 2.139258607 | 2.137932530 | -0.011864750 | -0.013265030 |
| Pooled | candidate_fixture | 2.917352198 | 2.912731156 | 2.100877160 | 2.098784336 | -0.011436850 | -0.012786629 |
| 2023-24 | candidate_player_gw | 3.169727683 | 3.163843930 | 2.229225926 | 2.217115309 | -0.031662896 | -0.061500940 |
| 2023-24 | candidate_fixture | 3.042744653 | 3.035696238 | 2.153216239 | 2.140740164 | -0.029905941 | -0.058088290 |
| 2024-25 | candidate_player_gw | 2.970933968 | 2.968205753 | 2.120227829 | 2.127880459 | -0.039039818 | -0.020504911 |
| 2024-25 | candidate_fixture | 2.914693550 | 2.912021383 | 2.105027541 | 2.110495302 | -0.038019108 | -0.019968803 |
| 2025-26 | candidate_player_gw | 2.818496331 | 2.813246843 | 2.070320153 | 2.070552135 | 0.034707439 | 0.041160997 |
| 2025-26 | candidate_fixture | 2.788012211 | 2.784011699 | 2.043956457 | 2.044763799 | 0.033790796 | 0.040073912 |

| Window | Annual NDCG@10 | Refit19 NDCG@10 | Annual Spearman | Refit19 Spearman |
|---|---|---|---|---|
| Pooled | 0.435737472 | 0.421147467 | 0.402683079 | 0.406285798 |
| 2023-24 | 0.420254889 | 0.404030617 | 0.435763167 | 0.446666944 |
| 2024-25 | 0.489111010 | 0.458846328 | 0.385099145 | 0.379372265 |
| 2025-26 | 0.397846517 | 0.400565456 | 0.387186925 | 0.392818185 |

## Registered gates

All limits are inclusive. BENEFIT requires pooled RMSE ≤0.995× and MAE ≤1.005× in both units; NO_HARM requires pooled RMSE/MAE ≤1.000× in both units. Both require each season’s RMSE ≤1.005× and nonnegative mean squad delta. NO_HARM applies only when BENEFIT does not. Otherwise the outcome is HARM.

| Gate | Condition | Refit19 value | Limit | Pass |
|---|---|---|---|---|
| BENEFIT | 2023-24_candidate_player_gw_rmse | 3.163843930 | 3.185576322 | True |
| BENEFIT | 2023-24_candidate_fixture_rmse | 3.035696238 | 3.057958376 | True |
| BENEFIT | 2024-25_candidate_player_gw_rmse | 2.968205753 | 2.985788638 | True |
| BENEFIT | 2024-25_candidate_fixture_rmse | 2.912021383 | 2.929267017 | True |
| BENEFIT | 2025-26_candidate_player_gw_rmse | 2.813246843 | 2.832588812 | True |
| BENEFIT | 2025-26_candidate_fixture_rmse | 2.784011699 | 2.801952272 | True |
| BENEFIT | mean_fixed_squad_delta | 2.750000000 | 0.000000000 | True |
| BENEFIT | pooled_candidate_player_gw_rmse | 2.983851551 | 2.973530839 | False |
| BENEFIT | pooled_candidate_player_gw_mae | 2.137932530 | 2.149954900 | True |
| BENEFIT | pooled_candidate_fixture_rmse | 2.912731156 | 2.902765437 | False |
| BENEFIT | pooled_candidate_fixture_mae | 2.098784336 | 2.111381546 | True |
| NO_HARM | 2023-24_candidate_player_gw_rmse | 3.163843930 | 3.185576322 | True |
| NO_HARM | 2023-24_candidate_fixture_rmse | 3.035696238 | 3.057958376 | True |
| NO_HARM | 2024-25_candidate_player_gw_rmse | 2.968205753 | 2.985788638 | True |
| NO_HARM | 2024-25_candidate_fixture_rmse | 2.912021383 | 2.929267017 | True |
| NO_HARM | 2025-26_candidate_player_gw_rmse | 2.813246843 | 2.832588812 | True |
| NO_HARM | 2025-26_candidate_fixture_rmse | 2.784011699 | 2.801952272 | True |
| NO_HARM | mean_fixed_squad_delta | 2.750000000 | 0.000000000 | True |
| NO_HARM | pooled_candidate_player_gw_rmse | 2.983851551 | 2.988473205 | True |
| NO_HARM | pooled_candidate_player_gw_mae | 2.137932530 | 2.139258607 | True |
| NO_HARM | pooled_candidate_fixture_rmse | 2.912731156 | 2.917352198 | True |
| NO_HARM | pooled_candidate_fixture_mae | 2.098784336 | 2.100877160 | True |

## Fixed squads and descriptive intervals

The unchanged historical fixed_squad replay uses opening GW20, 20 squads per season and seed 20260921. Both arms share the same sampled squads and each selects its own XI/captain from its forecasts. Replay uses realised total_points under the existing rules. This is not a transfer or full-season strategy trial.

| Season | Annual mean total | Refit19 mean total | Mean delta |
|---|---|---|---|
| 2023-24 | 789.000000000 | 800.950000000 | 11.950000000 |
| 2024-25 | 827.800000000 | 823.900000000 | -3.900000000 |
| 2025-26 | 826.950000000 | 827.150000000 | 0.200000000 |

Mean refit19 minus annual delta over 60 squad-seasons: **2.750000000** points. Anonymous squad totals and squad hashes are in the JSON.

The paired moving-block intervals use 1,000 draws, four-GW blocks and seed 20261015. Differences are refit19 minus annual; negative error differences favour refit19. They describe fixed-prediction uncertainty, not fitting or selection uncertainty.

| Unit | Metric | Delta | 95% lower | 95% upper |
|---|---|---|---|---|
| candidate_fixture | rmse | -0.004621041 | -0.009514969 | 0.000468252 |
| candidate_fixture | mae | -0.002092824 | -0.005533484 | 0.001044915 |
| candidate_player_gw | rmse | -0.004621653 | -0.011157943 | 0.002562117 |
| candidate_player_gw | mae | -0.001326077 | -0.005077784 | 0.002062506 |

## Descriptive slices

| Slice | Unit | Annual RMSE | Refit19 RMSE | Annual MAE | Refit19 MAE |
|---|---|---|---|---|---|
| position_1 | candidate_player_gw | 2.761730989 | 2.759392206 | 2.094087562 | 2.078790910 |
| position_1 | candidate_fixture | 2.700310551 | 2.696078064 | 2.058766898 | 2.043811502 |
| position_2 | candidate_player_gw | 2.852851359 | 2.850096848 | 2.115819137 | 2.118546864 |
| position_2 | candidate_fixture | 2.788433579 | 2.784004169 | 2.077506539 | 2.078927465 |
| position_3 | candidate_player_gw | 3.001987527 | 2.998847060 | 2.043343522 | 2.042287850 |
| position_3 | candidate_fixture | 2.928021635 | 2.925701496 | 2.004705596 | 2.002648958 |
| position_4 | candidate_player_gw | 3.582774918 | 3.565176528 | 2.695879242 | 2.690788012 |
| position_4 | candidate_fixture | 3.490480720 | 3.476403538 | 2.651843379 | 2.648064995 |
| GW20-28 | candidate_player_gw | 2.963352367 | 2.950368665 | 2.133401711 | 2.130732046 |
| GW20-28 | candidate_fixture | 2.920778897 | 2.910463242 | 2.108913768 | 2.105761111 |
| GW29-38 | candidate_player_gw | 3.011590859 | 3.014581657 | 2.144692146 | 2.144612537 |
| GW29-38 | candidate_fixture | 2.914262433 | 2.914772282 | 2.093638851 | 2.092500584 |

The JSON also includes bias, ranking and row counts for every slice.

## Resources and limitations

| Job | Seconds | Peak committed bytes | Output growth bytes | Processes after |
|---|---|---|---|---|
| stage-A | 10.828000000 | 360599552 | 3599 | 0 |
| annual-2024-25 | 19.968000000 | 456912896 | 758541 | 0 |
| annual-2025-26 | 25.844000000 | 537784320 | 813063 | 0 |
| annual-2023-24 | 15.359000000 | 444416000 | 835036 | 0 |
| refit19-2023-24 | 18.344000000 | 450539520 | 835039 | 0 |
| refit19-2024-25 | 22.890000000 | 464191488 | 758546 | 0 |
| refit19-2025-26 | 25.219000000 | 491819008 | 812211 | 0 |
| aggregate-B | 5.906000000 | 488075264 | 38320 | 0 |

All eight serial guarded jobs completed: one admission, six fits and one aggregate. Two threads, 4 GiB committed-memory cap, 900 s/job, 2 GiB output-growth cap and ≥5 GiB free storage. Zero retries or retrievals. Total guarded time 144.358 s; peak committed memory 537784320 bytes.

2025/26 was inspected during 1.0.0 development audits. These are retrospective, reused-season results; the historical test cannot measure the effect of 2026/27 scoring changes. No 2026/27 data were read. Phase 2 frozen material, the approved artifact, registry, defaults and legacy runtime are unchanged. No operational artifact was built or saved. Any deployment or refresh requires a separately authorised package.

Prior engineering stops concerned specification ordering and read-only tooling; no scientific jobs were spent before the successful execution recorded here. The frozen protocol was not changed after outcomes.

Interpretation: BENEFIT makes a refresh eligible for separate operational review; NO_HARM leaves adoption to the user under separate approval; HARM favours retaining annual fits. No merge, promotion or deployment is implied.
