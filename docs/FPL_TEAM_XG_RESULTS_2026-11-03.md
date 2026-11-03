# FPL-derived team expected-goals windows (3 November 2026)

Gate B **FAIL: 7/10 criteria**. Adding eight FPL-derived team/opponent xG windows to HGB7 CORE did not clear either pooled 0.5% RMSE-gain gate, and NDCG@10 was below control. Player-GW RMSE changed by 0.002931801863859107%; fixture RMSE by -0.006700205921195135%. Fixed-squad mean delta was 0.2250000000000001 points. Four B fit jobs completed. Stage C was not triggered; its two fits were not used. Approved forecaster **1.0.0 remains unchanged**; this is research evidence, with no artifact, registry or weekly-default change.

## Frozen design and amendment

The [r1 protocol](fpl_team_xg_protocol_2026-11-03.json) was frozen at d1b18a6; the [r2 amendment](fpl_team_xg_protocol_amendment_2026-11-03.json) at b1311b2. Numerical source: 014273b3f55de5edb697753161173ffabb4004ed. Full numeric tables, evaluation diagnostics, paired intervals and hashes are in the [results JSON](fpl_team_xg_results_2026-11-03.json).

Control is the unchanged 49 CORE features, target points_core, estimator hgb7. Candidate adds exactly team/opp × half-life 4/12 × xg/xga: the eight names in the JSON. Team xG sums **all FPL player expected_goals rows** in the fixture, including zero-minute rows and all positions. Team xGA is the reciprocal opponent xG. A missing played-row value makes the fixture xG and reciprocal xGA NaN. No other source enters these new statistics.

Windows reset by season/team and use only ts < cutoff − 3h, with unchanged ew NaN skipping, prior 1.35 and mass 4. Opponent windows use the opponent team's history. A window without finite history equals the prior. Rows, original control CSV round trip, weights (730.5-day half-life), HGB7 parameters, clipping [0,20], candidate predicate, DGW aggregation and replay evaluation are shared. Folds: train 2020/21–2022/23 → 2023/24 and train 2020/21–2023/24 → 2024/25. Training-only all-NaN omission remains unchanged.

R1 admission stopped because its 2022/23 ratio was 0.6748603321033211. Audit found unpublished GW1–15 stored as zeros. The user-approved r2 amendment was frozen **before any fit or accuracy outcome**. A season-GW is unpublished only if every row, including zero-minute rows, has finite expected_goals exactly 0 and the total team_gf is positive. The detected set must be exactly 2022/23 GW1,2,3,4,5,6,8,9,10,11,12,13,14,15; any difference stops execution. Only the team-statistics copy is masked to NaN. Partial zeros, individual zeros, CORE and player windows are untouched. Published-subset bounds remain unchanged; r1 ratios are retained. No accuracy outcome informed this amendment.

## Admission and identity

Admission PASS. All six seasons have 380 fixtures / 760 team-fixtures with reciprocal opponent/result/venue/clock integrity. Early seasons are wholly absent. The expected 14 GWs cover 272 team-fixtures, leaving 488 published in 2022/23. No published covered-season team-fixture is NaN; the ≤1% bound and corrected [0.80,1.20] ratios pass. Correlations use that same published subset. Null ratios/correlations below mean absent early-season xG.

| Season | Played | Finite after mask | Unpublished team-fixtures | Published team-fixtures | Published NaN | Corrected xG/goals | r1 xG/goals | xG/GF correlation | xGA/GA correlation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020-21 | 10393 | 0 | 0 | 760 | 760 | None | None | None | None |
| 2021-22 | 10485 | 0 | 0 | 760 | 760 | None | None | None | None |
| 2022-23 | 11345 | 7309 | 272 | 488 | 0 | 1.0541046109510088 | 0.6748603321033211 | 0.8432034779118157 | 0.8238885069121203 |
| 2023-24 | 11384 | 11384 | 0 | 760 | 0 | 0.9618619582664527 | 0.9618619582664527 | 0.92270966348213 | 0.8729224329050252 |
| 2024-25 | 11566 | 11566 | 0 | 760 | 0 | 0.9871838565022422 | 0.9871838565022422 | 0.91320141486983 | 0.962854364710714 |
| 2025-26 | 11492 | 11492 | 0 | 760 | 0 | 1.0223253588516745 | 1.0223253588516745 | 0.8504126795791431 | 0.8928504042789213 |

The authorised admission rerun reproduced admission.json, unpublished detection and the compressed fixture-statistics output byte-for-byte. Gzip reused only the accepted container timestamp for deterministic serialization; every compressed byte was still compared. The historical failed attempts remain preserved.

Real row/key/UTC cutoff/feature-index alignment passes for 133325 rows. Frozen control export parity passes for 106042 rows, training-prefix bytes match, and shared proof confirms identical CORE, cohort, targets, cutoffs, weights and evaluation rows. Synthetic own/earlier-fixture leakage exclusion passes. The 2024/25 panel canonical hash is a13bd4868a27e6554c77fe91df18d7d5bb3212c5b0e6138896929a2ab9ce2afb. Control prediction bytes match PR56 for 2023/24 and accepted PR50 for 2024/25; their hashes are in the JSON.

Before real continuation, the integration test traversed the actual select_control CSV export and make_squads path: the original missing conversion reproduced its TypeError, and the UTC restoration passed. Source timestamps are validated; source_max_ts is null only with no history, otherwise strictly before cutoff − 3h. No public numerical code changed for this repair.

## Gate B

| Criterion | Candidate | Threshold/control | Pass |
|---|---:|---:|---|
| pooled_player_gw_rmse_gain | 3.0285290590078784 | 3.013298069783865 | FAIL |
| pooled_player_gw_mae_noninferiority | 2.1665795943343107 | 2.176861502430589 | PASS |
| pooled_fixture_rmse_gain | 2.9775046042658744 | 2.962815595990542 | FAIL |
| pooled_fixture_mae_noninferiority | 2.1396639466600345 | 2.150396769942302 | PASS |
| 2023-24_candidate_player_gw_rmse_noninferiority | 3.097608751844348 | 3.1098720158737114 | PASS |
| 2023-24_candidate_fixture_rmse_noninferiority | 3.0254506431799593 | 3.0375192808479308 | PASS |
| 2024-25_candidate_player_gw_rmse_noninferiority | 2.959621053440695 | 2.9775264014029177 | PASS |
| 2024-25_candidate_fixture_rmse_noninferiority | 2.92906154206168 | 2.947250373078873 | PASS |
| pooled_ndcg10_not_lower | 0.4446921174114249 | 0.44547551863899865 | FAIL |
| mean_fixed_squad_delta_nonnegative | 0.2250000000000001 | 0 | PASS |

Descriptive only: paired 4-GW circular block bootstrap, 1000 draws, seed 20261015. Player-GW RMSE delta candidate−control is 8.878786831534313e-05, 95% interval [-0.0025237051155763803,0.0028230772264753786]. This is fixed-prediction uncertainty, not training or selection uncertainty. Per-fold/position diagnostics and all 20 fixed-squad totals per fold are in the JSON.

## Audit gates and qualification not reached

Stage C gates 2 audit RMSE, 3 stability, 4 MAE, 5 descriptive block interval, 6 fixed-squad points and 7 full scoring are **NOT EVALUATED**, because Gate B failed. No 2025/26 candidate fitting/scoring or audit panels were produced. Stage D remains out of scope: current-season gate 8, integrity/artifact gate 9, live ingestion and the prospective ≥3-deadline shadow test. No promotion is implied by a code merge.

## Resources, prior failures and limits

All real jobs ran serially through the qualified Windows guard in the unchanged legacy runtime with 2 threads, 4 GiB, ≤ 900 s/job, ≤ 256 MiB package growth and ≥ 5 GiB free. Across the retained r1/r2 admission/build attempts and successful continuation: 10 guarded jobs, 8 completed / 2 failed, 4 real fits / 0 refits, 0 C fits, 0 retrievals, total guard time174.40699999965727s, peak job committed memory1374142464bytes. All active-process counts after exit were 0; no native resource-limit breach. Per-job costs, including failures, are in the JSON.

The r1 sanity failure led to the frozen amendment. An initial r2 build then failed because CSV clock strings were passed to panel construction. The bounded private timestamp repair and real-boundary regression fixed that defect before the successful attempt; no fit was repeated. Earlier receipt-lookup tooling stops are retained in the research record. Legacy numpy 2.3.5 / pandas 2.2.3 / scikit-learn 1.9.1 were unchanged; source CI uses numpy 2.5.4. Local targeted tests passed 52, with four warnings from a constant synthetic correlation fixture. Full local pytest is unavailable on Windows due to the existing POSIX resource import; exact-head Ubuntu CI is the full-suite authority.

- Single arm selected adaptively after earlier research; seasons repeatedly inspected, not untouched holdouts
- Team xG only partially replaces unavailable advanced provider signals
- 2023/24 training has 2022/23 team-xG only from GW16
- CORE player xG/xA/xGC windows likely retain earlier 2022/23 zeros; affects control and approved training, unchanged and out of scope
- No candidate audit on 2025/26 because Gate B failed
- Historical publication clocks are not reconstructed
- Fixed-squad results do not evaluate transfers or chips
- Bootstrap is descriptive fixed-prediction uncertainty, excludes training and selection uncertainty
- No current-season qualification, artifact/integrity audit, live ingestion or prospective shadow test; no promotion

Architect pre-merge review: **PENDING**. The PR stops before merge; merge, tag and branch cleanup need separate approval. No consumer release note or model/default update.

## Per-GW coverage after team-only masking

| Season | GW | Played | Finite | Share | Unpublished |
|---|---:|---:|---:|---:|---|
| 2020-21 | 1 | 221 | 0 | 0.0 | False |
| 2020-21 | 2 | 274 | 0 | 0.0 | False |
| 2020-21 | 3 | 274 | 0 | 0.0 | False |
| 2020-21 | 4 | 275 | 0 | 0.0 | False |
| 2020-21 | 5 | 273 | 0 | 0.0 | False |
| 2020-21 | 6 | 273 | 0 | 0.0 | False |
| 2020-21 | 7 | 277 | 0 | 0.0 | False |
| 2020-21 | 8 | 267 | 0 | 0.0 | False |
| 2020-21 | 9 | 271 | 0 | 0.0 | False |
| 2020-21 | 10 | 278 | 0 | 0.0 | False |
| 2020-21 | 11 | 246 | 0 | 0.0 | False |
| 2020-21 | 12 | 270 | 0 | 0.0 | False |
| 2020-21 | 13 | 270 | 0 | 0.0 | False |
| 2020-21 | 14 | 274 | 0 | 0.0 | False |
| 2020-21 | 15 | 274 | 0 | 0.0 | False |
| 2020-21 | 16 | 217 | 0 | 0.0 | False |
| 2020-21 | 17 | 246 | 0 | 0.0 | False |
| 2020-21 | 18 | 165 | 0 | 0.0 | False |
| 2020-21 | 19 | 413 | 0 | 0.0 | False |
| 2020-21 | 20 | 277 | 0 | 0.0 | False |
| 2020-21 | 21 | 271 | 0 | 0.0 | False |
| 2020-21 | 22 | 276 | 0 | 0.0 | False |
| 2020-21 | 23 | 268 | 0 | 0.0 | False |
| 2020-21 | 24 | 329 | 0 | 0.0 | False |
| 2020-21 | 25 | 302 | 0 | 0.0 | False |
| 2020-21 | 26 | 460 | 0 | 0.0 | False |
| 2020-21 | 27 | 301 | 0 | 0.0 | False |
| 2020-21 | 28 | 271 | 0 | 0.0 | False |
| 2020-21 | 29 | 110 | 0 | 0.0 | False |
| 2020-21 | 30 | 281 | 0 | 0.0 | False |
| 2020-21 | 31 | 273 | 0 | 0.0 | False |
| 2020-21 | 32 | 274 | 0 | 0.0 | False |
| 2020-21 | 33 | 218 | 0 | 0.0 | False |
| 2020-21 | 34 | 245 | 0 | 0.0 | False |
| 2020-21 | 35 | 413 | 0 | 0.0 | False |
| 2020-21 | 36 | 214 | 0 | 0.0 | False |
| 2020-21 | 37 | 274 | 0 | 0.0 | False |
| 2020-21 | 38 | 278 | 0 | 0.0 | False |
| 2021-22 | 1 | 280 | 0 | 0.0 | False |
| 2021-22 | 2 | 275 | 0 | 0.0 | False |
| 2021-22 | 3 | 272 | 0 | 0.0 | False |
| 2021-22 | 4 | 274 | 0 | 0.0 | False |
| 2021-22 | 5 | 281 | 0 | 0.0 | False |
| 2021-22 | 6 | 277 | 0 | 0.0 | False |
| 2021-22 | 7 | 269 | 0 | 0.0 | False |
| 2021-22 | 8 | 274 | 0 | 0.0 | False |
| 2021-22 | 9 | 278 | 0 | 0.0 | False |
| 2021-22 | 10 | 278 | 0 | 0.0 | False |
| 2021-22 | 11 | 276 | 0 | 0.0 | False |
| 2021-22 | 12 | 278 | 0 | 0.0 | False |
| 2021-22 | 13 | 247 | 0 | 0.0 | False |
| 2021-22 | 14 | 275 | 0 | 0.0 | False |
| 2021-22 | 15 | 278 | 0 | 0.0 | False |
| 2021-22 | 16 | 248 | 0 | 0.0 | False |
| 2021-22 | 17 | 195 | 0 | 0.0 | False |
| 2021-22 | 18 | 110 | 0 | 0.0 | False |
| 2021-22 | 19 | 193 | 0 | 0.0 | False |
| 2021-22 | 20 | 192 | 0 | 0.0 | False |
| 2021-22 | 21 | 273 | 0 | 0.0 | False |
| 2021-22 | 22 | 305 | 0 | 0.0 | False |
| 2021-22 | 23 | 297 | 0 | 0.0 | False |
| 2021-22 | 24 | 246 | 0 | 0.0 | False |
| 2021-22 | 25 | 278 | 0 | 0.0 | False |
| 2021-22 | 26 | 383 | 0 | 0.0 | False |
| 2021-22 | 27 | 247 | 0 | 0.0 | False |
| 2021-22 | 28 | 387 | 0 | 0.0 | False |
| 2021-22 | 29 | 357 | 0 | 0.0 | False |
| 2021-22 | 30 | 114 | 0 | 0.0 | False |
| 2021-22 | 31 | 303 | 0 | 0.0 | False |
| 2021-22 | 32 | 277 | 0 | 0.0 | False |
| 2021-22 | 33 | 333 | 0 | 0.0 | False |
| 2021-22 | 34 | 304 | 0 | 0.0 | False |
| 2021-22 | 35 | 277 | 0 | 0.0 | False |
| 2021-22 | 36 | 443 | 0 | 0.0 | False |
| 2021-22 | 37 | 331 | 0 | 0.0 | False |
| 2021-22 | 38 | 280 | 0 | 0.0 | False |
| 2022-23 | 1 | 297 | 0 | 0.0 | True |
| 2022-23 | 2 | 299 | 0 | 0.0 | True |
| 2022-23 | 3 | 291 | 0 | 0.0 | True |
| 2022-23 | 4 | 302 | 0 | 0.0 | True |
| 2022-23 | 5 | 284 | 0 | 0.0 | True |
| 2022-23 | 6 | 295 | 0 | 0.0 | True |
| 2022-23 | 8 | 211 | 0 | 0.0 | True |
| 2022-23 | 9 | 303 | 0 | 0.0 | True |
| 2022-23 | 10 | 298 | 0 | 0.0 | True |
| 2022-23 | 11 | 297 | 0 | 0.0 | True |
| 2022-23 | 12 | 270 | 0 | 0.0 | True |
| 2022-23 | 13 | 298 | 0 | 0.0 | True |
| 2022-23 | 14 | 294 | 0 | 0.0 | True |
| 2022-23 | 15 | 297 | 0 | 0.0 | True |
| 2022-23 | 16 | 293 | 293 | 1.0 | False |
| 2022-23 | 17 | 299 | 299 | 1.0 | False |
| 2022-23 | 18 | 298 | 298 | 1.0 | False |
| 2022-23 | 19 | 335 | 335 | 1.0 | False |
| 2022-23 | 20 | 357 | 357 | 1.0 | False |
| 2022-23 | 21 | 290 | 290 | 1.0 | False |
| 2022-23 | 22 | 335 | 335 | 1.0 | False |
| 2022-23 | 23 | 327 | 327 | 1.0 | False |
| 2022-23 | 24 | 305 | 305 | 1.0 | False |
| 2022-23 | 25 | 296 | 296 | 1.0 | False |
| 2022-23 | 26 | 297 | 297 | 1.0 | False |
| 2022-23 | 27 | 361 | 361 | 1.0 | False |
| 2022-23 | 28 | 209 | 209 | 1.0 | False |
| 2022-23 | 29 | 478 | 478 | 1.0 | False |
| 2022-23 | 30 | 301 | 301 | 1.0 | False |
| 2022-23 | 31 | 301 | 301 | 1.0 | False |
| 2022-23 | 32 | 243 | 243 | 1.0 | False |
| 2022-23 | 33 | 297 | 297 | 1.0 | False |
| 2022-23 | 34 | 387 | 387 | 1.0 | False |
| 2022-23 | 35 | 306 | 306 | 1.0 | False |
| 2022-23 | 36 | 332 | 332 | 1.0 | False |
| 2022-23 | 37 | 362 | 362 | 1.0 | False |
| 2022-23 | 38 | 300 | 300 | 1.0 | False |
| 2023-24 | 1 | 302 | 302 | 1.0 | False |
| 2023-24 | 2 | 273 | 273 | 1.0 | False |
| 2023-24 | 3 | 297 | 297 | 1.0 | False |
| 2023-24 | 4 | 304 | 304 | 1.0 | False |
| 2023-24 | 5 | 303 | 303 | 1.0 | False |
| 2023-24 | 6 | 297 | 297 | 1.0 | False |
| 2023-24 | 7 | 336 | 336 | 1.0 | False |
| 2023-24 | 8 | 295 | 295 | 1.0 | False |
| 2023-24 | 9 | 303 | 303 | 1.0 | False |
| 2023-24 | 10 | 301 | 301 | 1.0 | False |
| 2023-24 | 11 | 297 | 297 | 1.0 | False |
| 2023-24 | 12 | 293 | 293 | 1.0 | False |
| 2023-24 | 13 | 296 | 296 | 1.0 | False |
| 2023-24 | 14 | 294 | 294 | 1.0 | False |
| 2023-24 | 15 | 291 | 291 | 1.0 | False |
| 2023-24 | 16 | 305 | 305 | 1.0 | False |
| 2023-24 | 17 | 267 | 267 | 1.0 | False |
| 2023-24 | 18 | 265 | 265 | 1.0 | False |
| 2023-24 | 19 | 296 | 296 | 1.0 | False |
| 2023-24 | 20 | 295 | 295 | 1.0 | False |
| 2023-24 | 21 | 292 | 292 | 1.0 | False |
| 2023-24 | 22 | 302 | 302 | 1.0 | False |
| 2023-24 | 23 | 303 | 303 | 1.0 | False |
| 2023-24 | 24 | 301 | 301 | 1.0 | False |
| 2023-24 | 25 | 355 | 355 | 1.0 | False |
| 2023-24 | 26 | 242 | 242 | 1.0 | False |
| 2023-24 | 27 | 301 | 301 | 1.0 | False |
| 2023-24 | 28 | 333 | 333 | 1.0 | False |
| 2023-24 | 29 | 119 | 119 | 1.0 | False |
| 2023-24 | 30 | 299 | 299 | 1.0 | False |
| 2023-24 | 31 | 298 | 298 | 1.0 | False |
| 2023-24 | 32 | 302 | 302 | 1.0 | False |
| 2023-24 | 33 | 305 | 305 | 1.0 | False |
| 2023-24 | 34 | 392 | 392 | 1.0 | False |
| 2023-24 | 35 | 324 | 324 | 1.0 | False |
| 2023-24 | 36 | 301 | 301 | 1.0 | False |
| 2023-24 | 37 | 397 | 397 | 1.0 | False |
| 2023-24 | 38 | 308 | 308 | 1.0 | False |
| 2024-25 | 1 | 307 | 307 | 1.0 | False |
| 2024-25 | 2 | 312 | 312 | 1.0 | False |
| 2024-25 | 3 | 302 | 302 | 1.0 | False |
| 2024-25 | 4 | 310 | 310 | 1.0 | False |
| 2024-25 | 5 | 305 | 305 | 1.0 | False |
| 2024-25 | 6 | 302 | 302 | 1.0 | False |
| 2024-25 | 7 | 305 | 305 | 1.0 | False |
| 2024-25 | 8 | 305 | 305 | 1.0 | False |
| 2024-25 | 9 | 304 | 304 | 1.0 | False |
| 2024-25 | 10 | 300 | 300 | 1.0 | False |
| 2024-25 | 11 | 297 | 297 | 1.0 | False |
| 2024-25 | 12 | 304 | 304 | 1.0 | False |
| 2024-25 | 13 | 310 | 310 | 1.0 | False |
| 2024-25 | 14 | 307 | 307 | 1.0 | False |
| 2024-25 | 15 | 274 | 274 | 1.0 | False |
| 2024-25 | 16 | 300 | 300 | 1.0 | False |
| 2024-25 | 17 | 303 | 303 | 1.0 | False |
| 2024-25 | 18 | 304 | 304 | 1.0 | False |
| 2024-25 | 19 | 306 | 306 | 1.0 | False |
| 2024-25 | 20 | 294 | 294 | 1.0 | False |
| 2024-25 | 21 | 296 | 296 | 1.0 | False |
| 2024-25 | 22 | 299 | 299 | 1.0 | False |
| 2024-25 | 23 | 300 | 300 | 1.0 | False |
| 2024-25 | 24 | 330 | 330 | 1.0 | False |
| 2024-25 | 25 | 335 | 335 | 1.0 | False |
| 2024-25 | 26 | 302 | 302 | 1.0 | False |
| 2024-25 | 27 | 305 | 305 | 1.0 | False |
| 2024-25 | 28 | 303 | 303 | 1.0 | False |
| 2024-25 | 29 | 246 | 246 | 1.0 | False |
| 2024-25 | 30 | 306 | 306 | 1.0 | False |
| 2024-25 | 31 | 310 | 310 | 1.0 | False |
| 2024-25 | 32 | 337 | 337 | 1.0 | False |
| 2024-25 | 33 | 372 | 372 | 1.0 | False |
| 2024-25 | 34 | 245 | 245 | 1.0 | False |
| 2024-25 | 35 | 307 | 307 | 1.0 | False |
| 2024-25 | 36 | 305 | 305 | 1.0 | False |
| 2024-25 | 37 | 309 | 309 | 1.0 | False |
| 2024-25 | 38 | 308 | 308 | 1.0 | False |
| 2025-26 | 1 | 299 | 299 | 1.0 | False |
| 2025-26 | 2 | 312 | 312 | 1.0 | False |
| 2025-26 | 3 | 302 | 302 | 1.0 | False |
| 2025-26 | 4 | 305 | 305 | 1.0 | False |
| 2025-26 | 5 | 305 | 305 | 1.0 | False |
| 2025-26 | 6 | 310 | 310 | 1.0 | False |
| 2025-26 | 7 | 311 | 311 | 1.0 | False |
| 2025-26 | 8 | 306 | 306 | 1.0 | False |
| 2025-26 | 9 | 314 | 314 | 1.0 | False |
| 2025-26 | 10 | 303 | 303 | 1.0 | False |
| 2025-26 | 11 | 303 | 303 | 1.0 | False |
| 2025-26 | 12 | 303 | 303 | 1.0 | False |
| 2025-26 | 13 | 304 | 304 | 1.0 | False |
| 2025-26 | 14 | 305 | 305 | 1.0 | False |
| 2025-26 | 15 | 310 | 310 | 1.0 | False |
| 2025-26 | 16 | 301 | 301 | 1.0 | False |
| 2025-26 | 17 | 302 | 302 | 1.0 | False |
| 2025-26 | 18 | 293 | 293 | 1.0 | False |
| 2025-26 | 19 | 294 | 294 | 1.0 | False |
| 2025-26 | 20 | 298 | 298 | 1.0 | False |
| 2025-26 | 21 | 295 | 295 | 1.0 | False |
| 2025-26 | 22 | 291 | 291 | 1.0 | False |
| 2025-26 | 23 | 303 | 303 | 1.0 | False |
| 2025-26 | 24 | 302 | 302 | 1.0 | False |
| 2025-26 | 25 | 303 | 303 | 1.0 | False |
| 2025-26 | 26 | 328 | 328 | 1.0 | False |
| 2025-26 | 27 | 297 | 297 | 1.0 | False |
| 2025-26 | 28 | 301 | 301 | 1.0 | False |
| 2025-26 | 29 | 306 | 306 | 1.0 | False |
| 2025-26 | 30 | 296 | 296 | 1.0 | False |
| 2025-26 | 31 | 243 | 243 | 1.0 | False |
| 2025-26 | 32 | 303 | 303 | 1.0 | False |
| 2025-26 | 33 | 392 | 392 | 1.0 | False |
| 2025-26 | 34 | 205 | 205 | 1.0 | False |
| 2025-26 | 35 | 305 | 305 | 1.0 | False |
| 2025-26 | 36 | 324 | 324 | 1.0 | False |
| 2025-26 | 37 | 306 | 306 | 1.0 | False |
| 2025-26 | 38 | 312 | 312 | 1.0 | False |
