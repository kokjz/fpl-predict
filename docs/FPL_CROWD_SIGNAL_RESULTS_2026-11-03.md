# FPL crowd signal research results

Outcome: **DEVELOPMENT_GATE_FAILED**. Approved 1.0.0 remains unchanged; nothing is promoted.

HGB7 on corrected CORE plus exactly six ownership, transfer and price features is compared with HGB7 on the same corrected CORE. Ownership and transfers use completed earlier gameweeks and a strict three-hour source buffer. Price uses the target row value; price change resets each season. The original protocol and the bounded balance amendment were frozen and pushed before their calculations.

## Admission and amendment

The original admission stopped on 14 rows where recorded transfers_balance differed from transfers_in minus transfers_out. No fits or feature census ran in that attempt. Before new calculations, fcs-r2 declared recorded balances unchanged, a maximum discrepancy share of 0.1% in every season, and a complete private row-level receipt. No balances were recomputed or imputed. All other checks remained hard stops.

| Season | Rows | Balance discrepancies | Share | NaNs | Other integrity violations |
|---|---:|---:|---:|---:|---:|
| 2020-21 | 24365 | 1 | 4.10424789657e-05 | 0 | 0 |
| 2021-22 | 25447 | 4 | 0.000157189452588 | 0 | 0 |
| 2022-23 | 26505 | 2 | 7.54574608564e-05 | 0 | 0 |
| 2023-24 | 29725 | 3 | 0.000100925147183 | 0 | 0 |
| 2024-25 | 27283 | 4 | 0.000146611443023 | 0 | 0 |
| 2025-26 | 29747 | 0 | 0 | 0 | 0 |

The strict as-of proof, finite fallbacks, descriptive distributions/correlations, correction tolerance/splice, original CSV round trip, key/cutoff alignment, training prefix and panels passed. All 49 corrected CORE columns are byte-identical between arms. Control prediction bytes matched the PR60 corrected arm for every reached fold. Full aggregate receipts and exact hashes are in the companion JSON.

## Gates and results

Gate B uses unchanged I4 criteria: pooled player-GW and fixture RMSE ≤0.995× control; pooled MAE ≤1.005×; each fold RMSE ≤1.005×; NDCG@10 at least control; mean fixed-squad delta nonnegative. The paired four-GW block bootstrap (1000 draws, seed20261015) and position errors are descriptive. Conditional 2025/26 audit uses unchanged registry gates2–7, including the full-scoring check.

### Gate B: FAIL

| Criterion | Candidate / delta | Threshold / control | Pass |
|---|---:|---:|---|
| pooled_player_gw_rmse_gain | 3.018984091788133 | 3.0127758193594336 | False |
| pooled_player_gw_mae_noninferiority | 2.1605942382698498 | 2.181222184449621 | True |
| pooled_fixture_rmse_gain | 2.9691668685682315 | 2.9623758298676828 | False |
| pooled_fixture_mae_noninferiority | 2.134728361440087 | 2.1547420295139688 | True |
| 2023-24_candidate_player_gw_rmse_noninferiority | 3.0867986410043486 | 3.109519947477301 | True |
| 2023-24_candidate_fixture_rmse_noninferiority | 3.0156539772493733 | 3.0374255718350387 | True |
| 2024-25_candidate_player_gw_rmse_noninferiority | 2.9513617926935716 | 2.9768199826180193 | True |
| 2024-25_candidate_fixture_rmse_noninferiority | 2.922219091307422 | 2.9464469449659894 | True |
| pooled_ndcg10_not_lower | 0.4457968587579405 | 0.44707005953179685 | False |
| mean_fixed_squad_delta_nonnegative | -1.4250000000000003 | See protocol | False |

| Unit | Control RMSE | Crowd RMSE | Control MAE | Crowd MAE |
|---|---:|---:|---:|---:|
| player_gw | 3.02791539634 | 3.01898409179 | 2.17037033279 | 2.16059423827 |
| fixture | 2.97726214057 | 2.96916686857 | 2.14402191991 | 2.13472836144 |

Mean fixed-squad delta: -1.425. Per-fold, ranking, position and interval results are retained in the companion JSON.

Stage C was not run because Gate B failed; its two fits remain unused.

## Limitations and resource use

All historical evaluation seasons have prior research exposure; these are not untouched holdouts. The lag loses late-breaking manager information. Bootstrap intervals condition on fixed predictions and exclude training/selection uncertainty. Fixed-squad panels do not test transfer/chip policies. Historical publication clocks are not reconstructed. Live crowd ingestion and the prospective shadow test are outside this package.

Serial guarded fits: B4, C0; retries0, retrievals0. Limits: 2threads,4GiB,900s perjob,256MiB growth,≥5GiB free. Peak job commit 1400446976 bytes; maximum job 228.125s. All guards completed with no limit violation; receipts remain private.

No artifact, registry, default or weekly-planner change. Code publication is not model promotion.

Architect pre-merge review: **PENDING**. Stop before merge.
