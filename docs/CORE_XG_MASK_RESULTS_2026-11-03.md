# CORE expected-statistic masking: no-harm research results

Outcome: **ADOPT_FOR_RESEARCH**. This package promotes nothing. Approved forecaster 1.0.0 remains unchanged.

The correction replaces unpublished 2022/23 expected statistics with missing values before rebuilding six existing player windows. Every field independently flags a season-GW only when every row (including zero-minute rows) is finite and exactly zero and its total team goals is positive. Partly zero weeks and individual zero rows are unchanged. The expected set was frozen: 2022/23 GW1–6 and GW8–15, exactly 14 weeks per field. Any mismatch was a mandatory stop.

Both arms use the same 49 CORE names, rows, order, targets, age weights, HGB7 estimator, two threads and [0,20] clipping. Only ew4/ew12 expected_goals, expected_assists and expected_goals_conceded differ, on 2022/23 rows only. The unchanged FeatureStore and its existing priors build them. The original CSV export/read boundary is retained, followed immediately by UTC clock restoration. The r1 byte-identity admission stopped before any fit. A separate unmasked forensic diagnostic found last-bit floating-point noise in both target and control columns and in another season, with exact alignment. Before any r2 calculation, a frozen amendment declared the raw tolerance identity abs(cache-unmasked) <= 1e-12 * max(1,abs(cache)), with both values finite, over six xG windows plus ew4_minutes and ew12_points_core. The original cache build runtime is unrecorded. The splice keeps exact cached raw values where masked equals unmasked, and uses the masked rebuild elsewhere. The real CSV boundary preserves unchanged control bytes; all 43 other columns and all other seasons remain byte-identical. Changed rows are computed in the qualified current legacy runtime; no accuracy outcome informed this amendment.

Numerical source `f0d5fddeb2d9eb70d6a7f710bcb3a168f3e6bcfe`; protocol freeze `66cee8b80a2f908afb3926a7ba2bfc5ffe212aed`, LF SHA256 `faf466b268217634b4afce93eca879ac1ea3227ed567507673694380ea245d65`. The protocol was pushed before real-data calculation. Legacy numerical runtime: numpy 2.3.5, pandas 2.2.3, scikit-learn 1.9.1. Ubuntu CI uses numpy 2.5.4 and pandas 3.0.6.

## Admission and change census

| Field | Detected weeks | History rows masked |
|---|---:|---:|
| expected_goals | 14 | 8491 |
| expected_assists | 14 | 8491 |
| expected_goals_conceded | 14 | 8491 |

| Column | Changed target rows | Share of 2022/23 | Mean absolute change | Substantive changes | Last substantive GW |
|---|---:|---:|---:|---:|---:|
| ew4_expected_goals | 23957 | 90.386719487% | 0.0241297317417 | 23957 | 38 |
| ew4_expected_assists | 23957 | 90.386719487% | 0.0159938519295 | 23957 | 38 |
| ew4_expected_goals_conceded | 23957 | 90.386719487% | 0.170362515575 | 23957 | 38 |
| ew12_expected_goals | 23957 | 90.386719487% | 0.0313515711085 | 23957 | 38 |
| ew12_expected_assists | 23957 | 90.386719487% | 0.0206403823127 | 23957 | 38 |
| ew12_expected_goals_conceded | 23957 | 90.386719487% | 0.234244645558 | 23957 | 38 |

Substantive change means abs(masked-unmasked) > 1e-9 on the raw rebuild. Rows changed and mean absolute change are measured after the real CSV boundary against control. Raw mask-change counts and last changed GW are also recorded in JSON.

Amendment freeze `5d22185ac40193c02e162a5835f3537e034466cc`, LF SHA256 `f59dead130444838ddf78732ee3fbda35a59f44d89c9e9cec9241d957ebcde5a`; forensic evidence SHA256 `987e226fa2f0573788f850eff38732b220364d5c02d439805947b80fb7cdd546`.

Real key/cutoff alignment, frozen control export, training prefix, cohort, weights, targets and the accepted 2024/25 panel hash `a13bd4868a27e6554c77fe91df18d7d5bb3212c5b0e6138896929a2ab9ce2afb` passed. Control prediction bytes matched PR56 for 2023/24 and accepted PR50 confirmation for 2024/25. Full receipt hashes, per-fold metrics, bootstrap intervals and per-position errors are in the companion JSON.

## Predeclared no-harm gates

Gate B trains through 2022/23 for test 2023/24 and through 2023/24 for test 2024/25. Pooled player-GW and fixture RMSE must be at most control (1.000x), MAE at most 1.005x, each fold RMSE at most 1.005x, pooled NDCG@10 at least control, and mean fixed-squad delta nonnegative. Gate C applies the pooled criteria to 2025/26 only, conditional on a B pass. The bootstrap (1000 draws, circular four-GW blocks, seed 20261015) and per-position relative RMSE are descriptive.

### Gate B: PASS

| Criterion | Candidate / delta | Threshold / control | Pass |
|---|---:|---:|---|
| pooled_player_gw_rmse | 3.02791539634 | 3.02844027114 | True |
| pooled_player_gw_mae | 2.17037033279 | 2.17686150243 | True |
| pooled_fixture_rmse | 2.97726214057 | 2.97770411657 | True |
| pooled_fixture_mae | 2.14402191991 | 2.15039676994 | True |
| 2023-24_candidate_player_gw_rmse | 3.09404969898 | 3.10987201587 | True |
| 2023-24_candidate_fixture_rmse | 3.02231400183 | 3.03751928085 | True |
| 2024-25_candidate_player_gw_rmse | 2.96200993295 | 2.9775264014 | True |
| 2024-25_candidate_fixture_rmse | 2.93178800494 | 2.94725037308 | True |
| pooled_ndcg10 | 0.447070059532 | 0.445475518639 | True |
| mean_fixed_squad_delta | 4.875 | 0 | True |

| Unit | Control RMSE | Corrected RMSE | Control MAE | Corrected MAE |
|---|---:|---:|---:|---:|
| player_gw | 3.02844027114 | 3.02791539634 | 2.1660313457 | 2.17037033279 |
| fixture | 2.97770411657 | 2.97726214057 | 2.13969827855 | 2.14402191991 |

Per-position candidate fixture RMSE (descriptive):

| Position | Control | Corrected | Relative change |
|---|---:|---:|---:|
| 1 | 2.70547540952 | 2.70844372278 | 0.109715034% |
| 2 | 2.83025677377 | 2.83035296716 | 0.0033987515% |
| 3 | 3.00954119443 | 3.00771075944 | -0.0608210645% |
| 4 | 3.56455843733 | 3.56524957824 | 0.0193892433% |

Mean fixed-squad delta: 4.875. Full tables, all panel totals, relative errors and descriptive intervals appear in the companion JSON.

### Gate C: PASS

| Criterion | Candidate / delta | Threshold / control | Pass |
|---|---:|---:|---|
| pooled_player_gw_rmse | 2.88281106004 | 2.88297250418 | True |
| pooled_player_gw_mae | 2.08912864303 | 2.10102990125 | True |
| pooled_fixture_rmse | 2.86565727123 | 2.86586604058 | True |
| pooled_fixture_mae | 2.07420725068 | 2.08623979603 | True |
| pooled_ndcg10 | 0.401342244829 | 0.394520161685 | True |
| mean_fixed_squad_delta | 2 | 0 | True |

| Unit | Control RMSE | Corrected RMSE | Control MAE | Corrected MAE |
|---|---:|---:|---:|---:|
| player_gw | 2.88297250418 | 2.88281106004 | 2.09057701617 | 2.08912864303 |
| fixture | 2.86586604058 | 2.86565727123 | 2.07586049356 | 2.07420725068 |

Per-position candidate fixture RMSE (descriptive):

| Position | Control | Corrected | Relative change |
|---|---:|---:|---:|
| 1 | 2.59945874992 | 2.59885373225 | -0.0232747558% |
| 2 | 2.83582736892 | 2.83760730088 | 0.0627658783% |
| 3 | 2.83517247154 | 2.83428964805 | -0.031138264% |
| 4 | 3.30787277525 | 3.30388912377 | -0.120429404% |

Mean fixed-squad delta: 2. Full tables, all panel totals, relative errors and descriptive intervals appear in the companion JSON.

The 2025/26 GW28–38 total-points comparison adds the same 2*dc_rate4 term to both arms (zero for goalkeepers). It is descriptive only; see full_scoring in the companion JSON.

## Limits and resource use

Fit jobs: B 4, C 2; refits 0, retries 0, retrievals 0. Serial Windows guard limits: 2 threads, 4 GiB, 900 seconds per job, 256 MiB growth, at least 5 GiB free. Peak committed job memory 1320955904 bytes; maximum guarded job 114.235 seconds. Resource receipts retained privately.

- All evaluation seasons have prior research exposure; none is an untouched holdout.
- No-harm correction test was chosen and frozen before calculation; it is distinct from the 0.5% improvement gates required for future promotion.
- Fixed-prediction block bootstrap excludes training and selection uncertainty.
- Fixed-squad panels do not test transfer or chip decisions.
- Historical publication clocks are not reconstructed.
- No 2026/27 scoring, current-season qualification, artifact production, live ingestion, prospective shadow test or promotion.
- Research adoption, if any, is applied only in a separately briefed package.
- Approved 1.0.0, registry, weekly defaults, control exporter and fpl_model remain unchanged.

Architect pre-merge review: **PENDING**. Stop before merge.
