# Multi-season fplcache availability study

Research outcome: **RETROSPECTIVE_GATES_PASS**. Approved **1.0.0 remains unchanged**; architect pre-merge review is **PENDING**. This is retrospective evidence, with no model freeze or promotion. The frozen prospective experiment remains unchanged and unscored.

## Fixed design

Train on all earlier seasons and score GW 10–38 of 2022/23, 2023/24 and 2024/25. Control is corrected CORE hgb7; conditional uses the unchanged two-stage forecaster and pre-deadline availability covariates. The unlabelled conditional arm isolates the label effect. Equal blending is descriptive. [Protocol](fplcache_availability_protocol_2026-11-05.json), [calendar amendment](fplcache_availability_protocol_amendment_2026-11-05.json), [identity amendment](fplcache_availability_protocol_amendment_2_2026-11-05.json), and [complete aggregate results](fplcache_availability_results_2026-11-05.json) record methods and gates. Fit source: `631de4d00c8779ea7c29b8aa8b89ff3cb5aba9ac`. Aggregate recovery source: `0d3f854800d3ae69215f882e9449f895c69db18f`.

## Admission and retrieval

The identity-only diagnostic found two numeric code disagreements in 2022/23 GW 1. The code-keyed join has no duplicates or position conflicts and complete bridge coverage across 189 snapshots, meeting pre-registered case 2. Admission therefore uses stable codes; absent codes remain unknown. Matched-code id-drift rows total 0; the two expected codes are absent from that snapshot. No availability or outcomes informed this remedy. The JSON includes the diagnostic totals, capture ages, Assistant Manager exclusions and identity coverage.

[fplcache](https://github.com/Randdalf/fplcache), Unlicense, listing revision `30ff880dd60a54917b3ee0befcb8c8b7fd3b9eea`. Select the latest path whose capture and first-adding commit both precede the deadline by at most 24 hours; verify the pinned Git blob. Null labels remain unknown; Assistant Manager entries are excluded. 2020/21 stays unknown. No 2026/27 snapshot was read. 2022/23 GW 7 has no fixtures and requires no deadline/download.

| Season | Admitted GWs | No source | No fixtures | Known fixture labels | Unknown share |
|---|---:|---:|---:|---:|---:|
| 2021-22 | 38 | 0 | 0 | 16484 | 35.222% |
| 2022-23 | 37 | 0 | 1 | 16242 | 38.721% |
| 2023-24 | 38 | 0 | 0 | 19575 | 34.146% |
| 2024-25 | 38 | 0 | 0 | 17058 | 37.478% |
| 2025-26 | 38 | 0 | 0 | 18099 | 39.157% |

Shared-key 2025/26 agreement against the retained AIrsenal source was 99.837% on 27553 keys. Admission passed corrected-CORE byte parity, real augmentation parity and retained 2025/26 fixed-squad replica parity. Both full-season PR 60 control prediction parity checks passed; the 2022/23 reference hash is recorded in JSON.

Cumulative retrieval: 574 API requests, 190 snapshot requests, 21597064 bytes, 0 transport retries and 2 calendar re-selections. The interrupted first segment used 167/54/4262720/0/1 respectively; the continuation re-verified all 54 files before any network request, retained its listing pin and carried the counters forward. Raw snapshots and individual forecasts remain private.

## Pooled and fold results

| Method | Player-GW RMSE | Player-GW MAE | Fixture RMSE | Fixture MAE | NDCG@10 |
|---|---:|---:|---:|---:|---:|
| control | 3.047632 | 2.196811 | 2.969461 | 2.148484 | 0.452968 |
| conditional | 2.994131 | 2.126965 | 2.920389 | 2.082077 | 0.450658 |
| conditional_unlabelled | 3.048435 | 2.193455 | 2.970618 | 2.145092 | 0.441035 |
| blend_equal | 3.010826 | 2.159024 | 2.935634 | 2.112712 | 0.452445 |

Conditional player-GW RMSE change: -1.756%; MAE change: -3.179%. These are error changes, not percentages of FPL points gained.

| Fold | Control player-GW RMSE | Conditional player-GW RMSE | Mean fixed-squad delta | Labelled training seasons |
|---|---:|---:|---:|---:|
| 2022-23 | 3.047888 | 3.011657 | +1.300 | 1 |
| 2023-24 | 3.116009 | 3.051463 | +1.900 | 2 |
| 2024-25 | 2.979177 | 2.919373 | +4.250 | 3 |

Pooled mean fixed-squad delta: **+2.483 points** across 60 squad-seasons. The JSON retains per-position/fold ranking, bias, label-history scaling, unlabelled contrasts, the descriptive equal blend and block interval. DC forecasts are zero in these earlier seasons.

The unlabelled conditional arm is slightly worse than control on RMSE and worse than the labelled conditional arm. The equal blend improves error less than the labelled conditional arm. These comparisons are descriptive; negative error differences favour the first method.

| Method | Reference | Player-GW RMSE difference | Fixture RMSE difference |
|---|---|---:|---:|
| conditional_unlabelled | control | +0.000803 | +0.001157 |
| conditional_unlabelled | conditional | +0.054304 | +0.050229 |
| blend_equal | control | -0.036806 | -0.033827 |

Conditional NDCG@10 is lower than control (0.450658 vs 0.452968), despite passing the error and fixed-squad gates. Ranking results remain descriptive.

## Gates and interpretation

| Gate | Registered requirement | Result |
|---|---|---|
| 2 | Candidate player-GW and fixture RMSE ≤ 0.995× control | PASS |
| 3 | Both RMSEs ≤ 1.005× control | PASS |
| 4 | Both MAEs ≤ 1.005× control | PASS |
| 5 | Paired block interval, descriptive | RMSE difference −0.061055 to −0.046950 |
| 6 | Mean fixed-squad delta ≥ 0 over 60 squad-seasons | PASS: +2.483333 points |
| 7 | Full-scoring player-GW RMSE ≤ 1.005× control | PASS: 1.915860 vs 1.954975 |
| Stability | Each fold's player-GW and fixture RMSE ≤ 1.005× control | PASS in all three folds |

No threshold, arm or model was changed after observing these results.

Historical error improvements do not establish future gains or promotion. Fixed-squad replay holds 20 legal squads per season and tests each method's own selection, without transfers/chips. The future frozen phase 2 study remains the deciding test.

## Resources and validation

Fourteen cumulative guarded serial attempts: two admission attempts, one identity diagnostic, nine fits and two aggregate attempts (12 completed, two retained failures), two threads, 591.907s combined and 1079676928 peak committed bytes. Every job stayed within 4 GiB/900s/fresh-baseline 2 GiB growth and 5 GiB free, leaving zero workers; no real-run retry. Per-job growth and runtime receipts are in JSON. Legacy numerical runtime uses Python 3.12.16/NumPy 2.3.5/pandas 2.2.3/sklearn 1.9.1; Ubuntu CI uses NumPy 2.5.4.

Synthetic selection/boundary/identity/augmentation/key/fold/squad/gate/end-to-end tests and continuation/routing tests passed. Ubuntu full CI is the full-suite authority; local targeted checks account for Windows' known POSIX resource import limitation. The separate identity diagnostic completed 114.047s with 287649792 peak committed bytes and 329219 combined growth bytes, leaving zero workers. Its receipt and the admission receipt record Python 3.12.16, pandas 2.2.3 and NumPy 2.3.5, versus CI pandas 3.0.6/NumPy 2.5.4. The original failed admission and safe-loader aggregate failure remain preserved and are included in cumulative resources. The single handover 141 recovery verified all nine bundle hashes before numeric-only loading, derived seasons from fold constants authenticated by result/ledger receipts, and validated ordered keys. No existing bundle was rewritten or refitted; `season.npy` stayed unopened with `allow_pickle=False`. The Unicode future-writer regression and writer-to-reader integration passed. No fitted model, raw labels or individual forecasts are published. Stop before merge, tagging or branch cleanup; these require separate review/approval.
