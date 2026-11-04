# Compliant signal union research results

Outcome: **AUDIT_GATE_FAILED**. Approved model1.0.0 remains unchanged; this package promotes nothing.

One HGB7 candidate uses the stable ordered union of corrected CORE49, FPL-native146, market3 and crowd6 features (204 total). The control uses the same corrected CORE, estimator, points_core target, clip[0,20], rows and weights. Each block comes from its unchanged builder, joined by keys. Only training-only all-NaN omission is allowed. The protocol was frozen and pushed before calculations.

## Admission and integrity

Input/cache hashes, corrected-CORE identity and splice, original exporter CSV round trip and UTC restoration, key/cutoff alignment, training prefix, common evaluation targets/weights, fixed panels and all49 control-prefix bytes passed. The unchanged FPL-native whitelist/static audit and full-union provider-column ablation proved byte-identical204-feature arrays. Native NaNs are retained; training-only omission counts are in the companion JSON.

Crowd definitions are unchanged from the bounded recorded-balance study: recorded transfers_balance is retained, with discrepancy share≤0.1% per season and all other checks hard stops. The real as-of checks use earlier gameweeks and a strict three-hour buffer. Native coverage spans every declared season. Market rows are finite, with380/380 joins on each new season. Control predictions match PR60 corrected-arm bytes for every fold, including2025/26.

The2025/26 audit uses frozen2024/25 market parameters through the unchanged historical construction, then admits the new season. points_core reconciliation, non-GK candidate dc_rate4 finiteness inGW28–38 and20 new panels hashed before fits passed. All underlying receipt and prediction hashes are retained in the companion JSON.

## Development and audit gates

Development uses2023/24 and2024/25, with chronological training from2020/21. Gate B requires pooled RMSE≤0.995× control in both units, MAE≤1.005×, per-fold RMSE≤1.005×, NDCG@10≥control and nonnegative mean fixed-squad delta. The fixture RMSE pass is narrow. The predeclared2025/26 audit uses registry gates2–7 and full scoring inGW28–38. Paired four-GW block intervals are descriptive; fixed predictions omit training/selection uncertainty.

### Gate B: PASS

| Criterion | Candidate / delta | Threshold / control | Pass |
|---|---:|---:|---|
| pooled_player_gw_rmse_gain | 3.0122713210970686 | 3.0127758193594336 | True |
| pooled_player_gw_mae_noninferiority | 2.14654878819048 | 2.181222184449621 | True |
| pooled_fixture_rmse_gain | 2.962335334636606 | 2.9623758298676828 | True |
| pooled_fixture_mae_noninferiority | 2.119849182836191 | 2.1547420295139688 | True |
| 2023-24_candidate_player_gw_rmse_noninferiority | 3.0763165225633546 | 3.109519947477301 | True |
| 2023-24_candidate_fixture_rmse_noninferiority | 3.006256420846606 | 3.0374255718350387 | True |
| 2024-25_candidate_player_gw_rmse_noninferiority | 2.9484850818779536 | 2.9768199826180193 | True |
| 2024-25_candidate_fixture_rmse_noninferiority | 2.9180162816185224 | 2.9464469449659894 | True |
| pooled_ndcg10_not_lower | 0.45875754087044945 | 0.44707005953179685 | True |
| mean_fixed_squad_delta_nonnegative | 5.575 | See protocol | True |

| Unit | Control RMSE | Union RMSE | Control MAE | Union MAE |
|---|---:|---:|---:|---:|
| player_gw | 3.02791539634 | 3.0122713211 | 2.17037033279 | 2.14654878819 |
| fixture | 2.97726214057 | 2.96233533464 | 2.14402191991 | 2.11984918284 |

NDCG@10: 0.447070059532 control, 0.45875754087 union. Mean fixed-squad delta: 5.575.

### Gate C: FAIL

| Criterion | Candidate / delta | Threshold / control | Pass |
|---|---:|---:|---|
| 2_audit_rmse | See JSON | See protocol | False |
| 3_audit_season_stability | See JSON | See protocol | True |
| 4_audit_mae | See JSON | See protocol | False |
| 5_audit_block_interval | See JSON | See protocol | False |
| 6_fixed_squad_points | 2.35 | See protocol | True |
| 7_full_scoring | See JSON | See protocol | True |

| Unit | Control RMSE | Union RMSE | Control MAE | Union MAE |
|---|---:|---:|---:|---:|
| player_gw | 2.88281106004 | 2.87435404228 | 2.08912864303 | 2.10741529717 |
| fixture | 2.86565727123 | 2.85612593603 | 2.07420725068 | 2.09242477188 |

NDCG@10: 0.401342244829 control, 0.393396088215 union. Mean fixed-squad delta: 2.35.

### Audit interpretation

2025/26 player_gw: RMSE change -0.293360% (required at most -0.5%); MAE change 0.875324% (allowed at most +0.5%).
2025/26 fixture: RMSE change -0.332606% (required at most -0.5%); MAE change 0.878288% (allowed at most +0.5%).

Descriptive RMSE difference interval [-0.0177124373448, 0.0011591872955]. Positive upper endpoints do not satisfy the recorded gate5 condition. The audit outcome remains a research result; no model is promoted.

### 2024/25 context and full scoring

2024/25 candidate_player_gw RMSE: control2.96200993295, union2.94848508188.
2024/25 candidate_fixture RMSE: control2.93178800494, union2.91801628162.

2025/26 full-scoring check: PASS. The same strictly lagged defensive-contribution term is added to both methods, then compared with full realised points. Player-GW/fixture, per-position and interval details appear in the companion JSON.

## Access, resources and limitations

The first authorised football-data GET received a host-canonicalisation302; it was not followed. A separately authorised final GET returned the complete380-row season. Default urllib User-Agent was used; no impersonation, personal headers, redirects or real-run retry. The default execution context could not read the original downloaded file, so an explicitly authorised local-only copy into a pre-created file preserved the original, matched203438 bytes/SHA and passed the same-column380-row parse. No ACL/settings change or further source request occurred. Earlier tooling stops, correction receipts and the entire accepted development run are preserved.

Serial guarded fits: B4/C2, all admitted fit jobs completed with zero remaining descendant processes; one earlier C build hit the original storage-growth guard before any fit. Limits2threads/4GiB/900s per job/≥5GiB free. The first C build was stopped by the original package storage-growth budget, with no fit. A predeclared Stage C resource amendment then allowed2GiB growth per job from a fresh baseline in a new directory; numerical construction and other limits stayed fixed. The failed export is retained untouched and was never reused. All jobs in the new attempt passed their guards; the one historical storage-guard failure is preserved. Peak job commit2671828992 bytes, maximum job468.250s, successful guard time973.656s. Legacy runtime uses numpy2.3.5; exact-head Ubuntu CI uses numpy2.5.4.

The union was selected adaptively from earlier studies on inspected seasons. The2025/26 audit is predeclared for this candidate, but the historical season is not globally untouched. The small development error gain and fixed-squad comparison do not establish prospective transfer/chip-policy efficacy. There is no2026/27 scoring, artifact/registry change, live ingestion, prospective shadow test or weekly-pipeline update. A full audit pass establishes eligibility for a separately authorised promotion brief only.

Architect pre-merge review: **PENDING**. Stop before merge.
