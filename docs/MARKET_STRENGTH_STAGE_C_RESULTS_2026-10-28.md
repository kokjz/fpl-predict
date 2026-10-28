# Historical market strength: negative player-development result

**Stage C fails the unchanged I4 development gate.** Market features reduce pooled
candidate player-GW RMSE by **0.417367%** and fixture RMSE by **0.402085%**; both
fall short of the required **0.5%**. The other eight criteria pass. The study stops
without promotion, later-season evaluation or season-path runs. Approved
forecaster **1.0.0**, its artifact, registry and weekly defaults remain unchanged.

The fixed-squad comparison has a positive mean delta of **+10.175 points** across
40 fixed panels, with individual deltas from **−36 to +54**. This does not override
the failed error gates or establish a full season-management gain. PR47 is being
prepared for architect pre-merge review; publication of source is not promotion.

## Declaration and attribution

Numerical source: **68d89718d1656e68f7d97b28697e848ac87566ef**. The
[original Stage-C protocol](market_strength_stage_c_protocol_2026-10-28.json)
was frozen at 1ef34083f9468cf27e866bd9985f1e425ef09474,
LF SHA25627954e78cb1a0151f7facc0e3e17df95549bec19da477b24700eeb6023bbf6d2.
The [fixture amendment](market_strength_stage_c_amendment1_2026-10-28.json)
was frozen/pushed at**2751c46d5921b29fdd92fe72d56f76dac1b20d98**, before
market-row construction, the feature matrix, fitting or scoring;
LF SHA2567ea774a75b7c82c93c23d7aa56052cd0460c405a7bbae992aa085a8e9f2eaa69.
Original protocols and the earlier failed build remain unchanged. Both exact-source
CI runs were green before the real run. Later reporting commits retain this
numerical attribution. The [full-precision scalar results](market_strength_stage_c_results_2026-10-28.json)
include every arm, metric, gate, panel delta, resource receipt hash and diagnostic.

The [Stage-B component study](MARKET_STRENGTH_STAGE_B_RESULTS_2026-10-28.md)
passed: M has lower team-goal Poisson deviance than both goals and xG controls in
each fold. Its numerical source remains c2dfbe490a01d56f206d72133a3533decf41e720.
The 2022/23 descriptive intervals include zero, and all arms underpredict the
2023/24 scoring level. That component finding alone did not qualify a player model.

## The four declared fits

Train 2020/21–2021/22, test 2022/23; then train through 2022/23, test 2023/24.
The incumbent method is refitted here using I4's **one core-points HGB head**,
49 features, seven leaves, 200 iterations, learning rate 0.05, L2=20, min leaf 60,
early stopping disabled,seed 20260921 and 730.5-day training-age half-life. The
single challenger adds three raw `project()` outputs (52 features): expected
team goals, expected opponent goals and clean-sheet probability, to that head.
No log transform, blend, Understat player arm, additional head, search or new seed.
Final fixture expectations use I4's[0,20]clip. The deployed multi-head artifact
is not backcast or used as a comparator, and old I4 scores are not borrowed.

Projection uses only completed past-match market information at deadline−3h,
with Stage-B's fixed730-day rating operator and conservative later-of-CSV/FPL
clock. No target/next-fixture odds enter features. Already completed test-season
matches may enter a later origin's history; test labels never fit that fold's
learner. Each fixture in a double is projected first, then I4 sums fixtures into
player-GWs. Candidate eligibility is pre-deadline history≥3 and last-five mean
minutes≥45; actual minutes are diagnostic only.

The common finite cohort contains**106,042** rows. Training/test rows are
49,812/26,505 and 76,317/29,725. Keys, targets, candidate flags and cutoffs are
shared; non-market feature columns are byte-identical. Proof SHA256
**2c53c057aeeb837faec8d915a9daabe62f14429293121f83515c8ce2b7878305**
was persisted before any fit and checked again by each worker. No imputation,
row drop or arm-specific population. Held-out candidate coverage is15,323
fixture rows and14,607 player-GWs; all-player coverage56,230fixtures/53,699GWs.

## Candidate errors and ranking

Relative changes are100×(market/control−1); negative error changes favour market.
Gate decisions use full precision, not these displayed rounded values.

| Test scope | Unit | Candidate n | Control RMSE | Market RMSE | Relative RMSE | Control MAE | Market MAE | Relative MAE |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2022-23 | player-gw | 7,222 | 3.065020483 | 3.053542614 | -0.374479% | 2.228148637 | 2.212286933 | -0.711878% |
| 2022-23 | fixture | 7,685 | 2.965629114 | 2.954668229 | -0.369597% | 2.154311647 | 2.139734558 | -0.676647% |
| 2023-24 | player-gw | 7,385 | 3.094400016 | 3.080211189 | -0.458532% | 2.199887973 | 2.194096621 | -0.263257% |
| 2023-24 | fixture | 7,638 | 3.022407245 | 3.009303135 | -0.433565% | 2.155004307 | 2.147640324 | -0.341715% |
| pooled | player-gw | 14,607 | 3.079909201 | 3.067054682 | -0.417367% | 2.213860625 | 2.203090284 | -0.486496% |
| pooled | fixture | 15,323 | 2.994065693 | 2.982027017 | -0.402085% | 2.154656915 | 2.143675316 | -0.509668% |

Pooled within-GW NDCG@10 is0.43674514166138834→0.4403587667342456
(+0.827399% relative), over 69 candidate weeks. By fold it is
0.45655785665444754→0.4672538226330224 in 2022/23 and
0.41749850423955953→0.4142321410040053 in 2023/24; the latter decreases.
The unchanged gate checks pooled NDCG, not a new per-fold rank criterion.
All-player/position/minutes/cold-start errors and bias are retained in the JSON.

The unchanged I4 four-GW descriptive bootstrap gives pooled candidate player-GW
RMSE delta−0.012854519204042347,95% interval
[−0.02508319076280935,−0.00116487534126667], and MAE delta−0.010770340786536037,
interval[−0.022572549732125767,+0.0002624145953036368]. These fixed-prediction
intervals over reused dependent data do not measure training/selection uncertainty
or replace the 0.5% development gate.

## Every gate criterion

Required pooled RMSE thresholds are3.0645096547846626(player-GW) and
2.9790953648626277(fixture); market errors are3.067054681584563 and
2.9820270165428266. Both miss. Pooled MAEs may be at most 1.005×control;
both candidate RMSEs in each fold may be at most 1.005×control; pooled NDCG
must not fall and mean fixed-squad delta must be nonnegative.

| Criterion | Verdict |
|---|---|
| pooled_player_gw_rmse_gain | **FAIL** |
| pooled_player_gw_mae_noninferiority | PASS |
| pooled_fixture_rmse_gain | **FAIL** |
| pooled_fixture_mae_noninferiority | PASS |
| 2022-23_candidate_player_gw_rmse_noninferiority | PASS |
| 2022-23_candidate_fixture_rmse_noninferiority | PASS |
| 2023-24_candidate_player_gw_rmse_noninferiority | PASS |
| 2023-24_candidate_fixture_rmse_noninferiority | PASS |
| pooled_ndcg10_not_lower | PASS |
| mean_fixed_squad_delta_nonnegative | PASS |

Overall **FAIL: 2 failed, 8 passed**. There is one challenger, no selection step,
threshold relaxation, new fit or further audit after this result.

## Fixed original squads and the preserved panel failure

The first build stopped before market features/fitting because regenerated I4
panel objects did not exactly match the original manifest. It consumed zero fit
slots and was preserved without retry. An architect-authorised, separately frozen
[no-fit diagnostic](market_strength_stage_c_panel_diagnostic_2026-10-28.json)
ran once each in the legacy and product runtimes. Both were class A: identical
members/order/positions/clubs/prices/firstGW/counts,77 of600 member-weight entries
differing by at most 8.881784197001252e-16 absolute/2.4480719460869007e-16 relative.
The two regenerated panel files were byte-identical. Upstream cause was not isolated.

Original canonical panel hash917f5ca00f12ff8d9823c4b65b1da4cad7adb5f528ccc414ff8d11ce22cc4fed;
regenerated hash e5f64a45522ac95c0c4400e294d7f4fe463a4cdc0981092f193472ad6b5ff03c.
`weight` samples squads but is not read by fixed-squad replay/XI selection.
Before any outcome, Amendment1 authorised the **original manifest object** as
the shared fixture. The build still regenerates once and requires class A,
recording the full receipt; any non-A result aborts. This is fixture admissibility,
not a score tolerance. The strict old build path was preserved. Original score
comparability across machines is not claimed; both controls/challengers refit here
share the same receiving feature bytes.

Twenty original squads per fold start at GW4, use pre-deadline price proxies and
legal15-player/£100m/three-per-club selection, then hold squads fixed. Legal XI,
captain, realised autosubs and vice fallback follow I4. The postponed2022/23GW7
is an allowed empty week. No transfers, chips or season paths are added.

| Fold | Control mean points | Market mean points | Mean delta | Minimum delta | Maximum delta |
|---|---:|---:|---:|---:|---:|
| 2022/23 | 1453.85 | 1463.45 | +9.6 | −36 | +54 |
| 2023/24 | 1378.85 | 1389.60 | +10.75 | −20 | +41 |
| Pooled 40 panels | 1416.35 | 1426.525 | +10.175 | −36 | +54 |

The pooled mean is the unchanged I4 mean of two20-panel fold means; pooled
min/max cover all40 paired deltas. Every panel total/delta is retained in JSON.

## Cold starts and receiving execution

Neutral market ratings remain included; their counts differ from player-history
cold starts. All counts below are player-fixture rows, not unique clubs.

| Season | All rows | Candidate rows | Market team neutral | Market opponent neutral | Control no history | Control history<3 |
|---|---:|---:|---:|---:|---:|---:|
| 2020-21 | 24,365 | 7,691 | 77 | 83 | 730 | 2129 |
| 2021-22 | 25,447 | 7,752 | 27 | 32 | 756 | 2225 |
| 2022-23 | 26,505 | 7,685 | 55 | 60 | 794 | 2330 |
| 2023-24 | 29,725 | 7,638 | 66 | 63 | 875 | 2591 |

The existing legacy Windows runtime uses Python 3.12.16 / NumPy 2.3.5 / pandas 2.2.3 /
sklearn 1.9.1, matching I4's numerical libraries; original Python 3.12.14/macOS
differs by patch/OS. No silent runtime upgrade or platform environment copy.
Qualified inherited Windows job objects cover actual workers and descendants,
4GiB native committed memory,900s/job,2threads, serial execution, package growth
≤256MiB and≥5GiB free. Native committed peak is not resident RSS or a security
sandbox. Each job exited0 with no guard violation and zero remaining descendants.

| Job | Guard wall seconds | Native job peak bytes |
|---|---:|---:|
| build | 16.891 | 610,095,104 |
| 2022-23_control | 10.407 | 421,572,608 |
| 2022-23_market_strength | 11.032 | 421,367,808 |
| 2023-24_control | 15.906 | 421,666,816 |
| 2023-24_market_strength | 16.578 | 419,172,352 |
| aggregate | 8.281 | 421,347,328 |

Four actual fit sections took6.453,7.063,11.953,12.641seconds. Batch elapsed
100.381260seconds; package accounting194,839,480bytes including16MiB reserve;
free865,214,332,928bytes. Scope covers known package roots/logs/tests, not a
historic whole-filesystem delta. All numerical pools reported2threads.
There was no failed/repeated real fit. No executable model binary was saved.

## Failures, limitations and stopping state

Retained engineering evidence includes the pre-data lambda tolerance test,
LF/CRLF hash assertions, earlier launcher-only telemetry shortfall, refused-
allocation peak-counter assertion, whole-file source preflight differences in
unused wrappers, and the exact-panel blocker. Runtime/path/access adaptations
preserved original bytes. Worker/descendant qualification and executed-scope
source checks were resolved before fits; the panel amendment was authorised and
frozen before player feature calculation. No result or failure was discarded.
[Admission](MARKET_STRENGTH_ADMISSION_2026-10-28.md) and the Stage-B report retain
their dated scope; they are not additional experimental arms or reruns.

These are two reused development seasons, corrected historical FPL/xG/market
sources and reconstructed deadlines/schedules, not fresh holdouts or certified
publication-time data. Historical closing-average coverage and the independent-
Poisson market reconciliation remain limitations. Fixed-squad price proxies,
promoted-club neutrality and tiny receiving-runtime numerical differences remain
disclosed. Ex-post actual-minute diagnostics do not choose candidates. Positive
fixed-squad means and a descriptive error interval do not establish independence
or operational season-management gains.

No 2024/25 or 2025/26 retrieval/scoring, next-fixture odds, new arm/seed/blend/search,
extra fit, season path or Stage D. The unchanged gate stops this package.
Approved artifact SHA256789e8849922116d989584ccfcb912082bb96201cb5af80ce9e70823e047fe233
remains1.0.0; no registry write, promotion or weekly default change. Source merge,
study tag and cleanup remain subject to separate architect pre-merge review.
