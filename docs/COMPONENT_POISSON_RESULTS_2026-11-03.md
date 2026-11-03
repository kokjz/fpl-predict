# Component-decomposed Poisson forecast: development gate failed

Date: 3 November 2026. Research only. **Approved 1.0.0 and weekly defaults remain unchanged.**

The fixed five-head component model worsens pooled candidate RMSE by 0.0466% per player-GW and 0.0606% per fixture against direct HGB7. Both miss the required 0.5% improvement. Pooled NDCG@10 also falls; seven of ten development criteria pass. Stage C was not triggered. Nothing is promoted.

## Frozen design

Both methods use the same 49 CORE features, training rows, two threads, 730.5-day age weights, training-only feature omission, I4 candidates and original replay panels. Origins retain the deadline-minus-three-hours clock and training-prefix guard. Fixture predictions use the original control CSV boundary and double-gameweek player-GW aggregation. Train 2020/21–2021/22, test 2022/23; train 2020/21–2022/23, test 2023/24.

The control is the unchanged squared-error HGB7 on points_core. Each component head has the same structure: max_leaf_nodes=7, max_iter=200, learning_rate=0.05, L2=20, min_samples_leaf=60, early_stopping=False, random_state=20260921. Only the head loss differs.

| Head | Per-fixture training target | Loss | Points multiplier (GK/DEF/MID/FWD) |
|---|---|---|---|
| G | goals_scored | Poisson |6/6/5/4 |
| A | assists | Poisson |3/3/3/3 |
| CS | FPL clean_sheets | Poisson |4/4/1/0 |
| B | bonus | Poisson |1/1/1/1 |
| R | points_core minus weighted G/A/CS/B | squared_error |1/1/1/1 |

Prediction is m_G·G_hat+3·A_hat+m_CS·CS_hat+B_hat+R_hat, then clip[0,20], as for control. R may be negative. Five weighted targets sum exactly to points_core. G/A/CS/B must be finite nonnegative integers; CS is binary and implies at least 60 minutes. FPL clean_sheets is preserved as the target, never imputed or derived.

The targets come from a keyed sidecar of the frozen history rows used by the unchanged control exporter. Its original index/order and stable-code mapping are retained; after the control CSV round trip, keys, total_points, points_core and minutes must agree exactly. The sidecar never feeds features. Explicit FPL/CORE field allowlists exclude provider inputs. No data retrieval occurred.

The write-once [protocol](component_poisson_protocol_2026-11-03.json), LF SHA256 `2916312d24f9fc5033edaca494adb1d4b069cbf55ca5fa154ef2420f1ff8346d`, was pushed at freeze `038bcf5c04372153f345f69b075fda236f3068dc` before any calculation. Numerical source `e495ff9d88d25e27fafe8fdfc5af959e310c8d6c` is unchanged by the private receipt repair and documentation publication. The [complete aggregate JSON](component_poisson_results_2026-11-03.json) preserves all metrics, gates, panel totals and head diagnostics.

## Admission and control parity

Stage A passed on 106,042 development rows. All 43,607 played rows reconcile exactly to the historical scoring rules; zero failures. Sidecar/I4 goals, assists, bonus and clean-sheet cross-checks have zero mismatches in every season/position group. The original export/CORE bytes, row alignment, panel identity, integer component integrity and exact five-target sum passed. No selected feature, target or check reads provider columns.

Full-rule reconciliation uses appearance 2 at 60 minutes (1 for a shorter appearance), position goal/CS multipliers above, floor(saves/3), 5 points per penalty saved, −2 per penalty missed, −floor(goals_conceded/2) for GK/DEF, −1 yellow card, −3 red card, −2 own goal and recorded bonus. It was checked against the established formula on synthetic rows before real admission.

| Control fold | Test rows | Exact prediction byte parity with PR56 | Array SHA256 |
|---|---:|---|---|
| 2022-23 | 26505 | PASS |`f943829bb2679e0333ac5ee3543d4827d5703e2d34d135374b8d4a58d4d98728` |
| 2023-24 | 29725 | PASS |`7638759dcd146c009d20e6910935f23913b42ba99e149b44f4da674251c5f2b9` |

R share is sum R / sum points_core over all rows within a season/position; mean R includes nonappearances. Position 1=GK, 2=DEF, 3=MID, 4=FWD. The JSON also preserves the exact numerator and denominator.

| Season | Pos | Rows | Played (=reconciled) | Mean R | R share |
|---|---:|---:|---:|---:|---:|
| 2020-21 | 1 | 2768 | 765 | 0.618135838150289 | 0.5957520891364902 |
| 2020-21 | 2 | 8626 | 3486 | 0.5325759332251333 | 0.4391549565051142 |
| 2020-21 | 3 | 9858 | 4713 | 0.7522824102251978 | 0.5462178684540031 |
| 2020-21 | 4 | 3113 | 1429 | 0.6993254095727593 | 0.47972675187307184 |
| 2021-22 | 1 | 2910 | 763 | 0.5718213058419244 | 0.6108663729809104 |
| 2021-22 | 2 | 8620 | 3572 | 0.5269141531322505 | 0.4297880393641181 |
| 2021-22 | 3 | 10519 | 4747 | 0.698260290902177 | 0.5302100628022811 |
| 2021-22 | 4 | 3398 | 1403 | 0.6200706297822248 | 0.49355821035371283 |
| 2022-23 | 1 | 2791 | 770 | 0.5994267287710499 | 0.6017985611510791 |
| 2022-23 | 2 | 9183 | 3776 | 0.5065882609169117 | 0.4678668409936639 |
| 2022-23 | 3 | 11418 | 5322 | 0.6952180767209669 | 0.544780728844966 |
| 2022-23 | 4 | 3113 | 1477 | 0.665274654673948 | 0.4674943566591422 |
| 2023-24 | 1 | 3413 | 776 | 0.4761207149135658 | 0.6563004846526656 |
| 2023-24 | 2 | 9611 | 3843 | 0.4512537717199043 | 0.46644439664443965 |
| 2023-24 | 3 | 12847 | 5320 | 0.6014633766638126 | 0.516407137606095 |
| 2023-24 | 4 | 3854 | 1445 | 0.537104307213285 | 0.4565505072783414 |

## Unchanged development gates — FAIL 7/10

| Criterion | Candidate / observed | Threshold | Outcome |
|---|---:|---:|---|
| pooled_player_gw_rmse_gain | 3.0813435290232567 | 3.0645096547846626 | FAIL |
| pooled_player_gw_mae_noninferiority | 2.209231274622962 | 2.224929927624157 | PASS |
| pooled_fixture_rmse_gain | 2.9958800678983035 | 2.9790953648626277 | FAIL |
| pooled_fixture_mae_noninferiority | 2.1499826773877353 | 2.1654301992114853 | PASS |
| 2022-23_candidate_player_gw_rmse_noninferiority | 3.0669374859733356 | 3.0803455858405697 | PASS |
| 2022-23_candidate_fixture_rmse_noninferiority | 2.9696295576558622 | 2.9804572599627166 | PASS |
| 2023-24_candidate_player_gw_rmse_noninferiority | 3.0953667626685095 | 3.1098720158737114 | PASS |
| 2023-24_candidate_fixture_rmse_noninferiority | 3.022061989379357 | 3.0375192808479308 | PASS |
| pooled_ndcg10_not_lower | 0.4250789147250448 | 0.43674514166138834 | FAIL |
| mean_fixed_squad_delta_nonnegative | 1.6749999999999998 | 0 | PASS |

The pooled RMSE limits are 0.995×control; pooled MAE and per-fold RMSE limits are 1.005×control. NDCG must not fall and the mean fixed-squad delta must be nonnegative. Thresholds were fixed before any component outcome.

| Scope | Unit | Control RMSE | Components RMSE | RMSE relative% | Control MAE | Components MAE | MAE relative% |
|---|---|---:|---:|---:|---:|---:|---:|
| pooled | player_gw | 3.0799092007886055 | 3.0813435290232567 | 0.046570471437412664 | 2.213860624501649 | 2.209231274622962 | -0.20910755751523125 |
| pooled | fixture | 2.994065693329274 | 2.9958800678983035 | 0.06059902336383871 | 2.154656914638294 | 2.1499826773877353 | -0.21693649781563407 |
| 2022-23 | candidate_player_gw | 3.065020483423453 | 3.0669374859733356 | 0.06254452654559373 | 2.2281486372323003 | 2.217287957366488 | -0.48743067155980757 |
| 2022-23 | candidate_fixture | 2.965629114390763 | 2.9696295576558622 | 0.1348935794326822 | 2.1543116468863786 | 2.1442731328323084 | -0.46597315985265064 |
| 2023-24 | candidate_player_gw | 3.0944000157947382 | 3.0953667626685095 | 0.031241819701288698 | 2.1998879734602452 | 2.2013524171045136 | 0.06656900996484527 |
| 2023-24 | candidate_fixture | 3.022407244624807 | 3.022061989379357 | -0.01142318746303328 | 2.155004306975747 | 2.1557273553019094 | 0.033552059447017335 |

Pooled NDCG@10: control 0.43674514166138834, components 0.4250789147250448; relative change -2.671174976775925%. Both folds rank worse. Mean fixed-squad delta is +1.6749999999999998 points. All panel totals/deltas, fold/pooled position, minute and cold-start diagnostics are retained in the JSON.

The descriptive paired 4-GW circular-block bootstrap uses 1000 draws, seed 20261015. RMSE difference is 0.001434328234650728, with 95% interval[-0.004246051312613996,0.0069839601297669186]; the interval spans zero. MAE difference is-0.004629349878686422, interval[-0.011555217939156596,0.001071142207843748]. This is fixed-prediction uncertainty, excluding training and selection uncertainty.

## Descriptive head calibration

Means below cover all test rows by position/fold, not only candidates. G/A/CS/B are event counts; R is points. Contributions apply the frozen position multipliers before the final total clip. These diagnostics produced no adjustment or tuning.

| Fold | Pos | Head | Rows | Predicted mean | Actual mean | Mean predicted points |
|---|---:|---|---:|---:|---:|---:|
| 2022-23 | 1 | G | 2791 | 0.0016150683143820637 | 0.0 | 0.009690409886292384 |
| 2022-23 | 1 | A | 2791 | 0.0023848386085259412 | 0.0014331780723754925 | 0.007154515825577822 |
| 2022-23 | 1 | CS | 2791 | 0.07687679183937525 | 0.07452525976352561 | 0.307507167357501 |
| 2022-23 | 1 | B | 2791 | 0.07659493746728874 | 0.09423145825868864 | 0.07659493746728874 |
| 2022-23 | 1 | R | 2791 | 0.6077333921669614 | 0.5994267287710499 | 0.6077333921669614 |
| 2022-23 | 2 | G | 9183 | 0.015894643457130153 | 0.011869759337907002 | 0.0953678607427809 |
| 2022-23 | 2 | A | 9183 | 0.02318930133360178 | 0.019601437438745508 | 0.06956790400080534 |
| 2022-23 | 2 | CS | 9183 | 0.09733622973872512 | 0.09180006533812479 | 0.3893449189549005 |
| 2022-23 | 2 | B | 9183 | 0.08423507372445425 | 0.07895023412828052 | 0.08423507372445425 |
| 2022-23 | 2 | R | 9183 | 0.5117188444243749 | 0.5065882609169117 | 0.5117188444243749 |
| 2022-23 | 3 | G | 11418 | 0.048591629547018206 | 0.05141005430022771 | 0.24295814773509103 |
| 2022-23 | 3 | A | 11418 | 0.047019223079452256 | 0.05062182518829918 | 0.14105766923835678 |
| 2022-23 | 3 | CS | 11418 | 0.09571009623968671 | 0.08854440357330531 | 0.09571009623968671 |
| 2022-23 | 3 | B | 11418 | 0.0882812049776067 | 0.08346470485198809 | 0.0882812049776067 |
| 2022-23 | 3 | R | 11418 | 0.6828256108192652 | 0.6952180767209669 | 0.6828256108192652 |
| 2022-23 | 4 | G | 3113 | 0.09063611844229542 | 0.10986186957918406 | 0.3625444737691817 |
| 2022-23 | 4 | A | 3113 | 0.05043904259238064 | 0.053003533568904596 | 0.15131712777714193 |
| 2022-23 | 4 | CS | 3113 | 0.08650793756405203 | 0.07998715065852875 | 0.0 |
| 2022-23 | 4 | B | 3113 | 0.14534456673370472 | 0.159331834243495 | 0.14534456673370472 |
| 2022-23 | 4 | R | 3113 | 0.6613276128561746 | 0.665274654673948 | 0.6613276128561746 |
| 2023-24 | 1 | G | 3413 | 0.001276820691585833 | 0.0 | 0.007660924149514999 |
| 2023-24 | 1 | A | 3413 | 0.0022593251541646133 | 0.0005859947260474656 | 0.00677797546249384 |
| 2023-24 | 1 | CS | 3413 | 0.061517632776833954 | 0.04600058599472605 | 0.24607053110733582 |
| 2023-24 | 1 | B | 3413 | 0.06534969170098107 | 0.06358042777615001 | 0.06534969170098107 |
| 2023-24 | 1 | R | 3413 | 0.4942498444458833 | 0.4761207149135658 | 0.4942498444458833 |
| 2023-24 | 2 | G | 9611 | 0.014407309401217665 | 0.016543543855998336 | 0.086443856407306 |
| 2023-24 | 2 | A | 9611 | 0.023742603813176874 | 0.025179481843720736 | 0.07122781143953062 |
| 2023-24 | 2 | CS | 9611 | 0.08874864124581186 | 0.06752679221725107 | 0.35499456498324744 |
| 2023-24 | 2 | B | 9611 | 0.0726974373514231 | 0.07127250026011861 | 0.0726974373514231 |
| 2023-24 | 2 | R | 9611 | 0.47432093768023875 | 0.4512537717199043 | 0.47432093768023875 |
| 2023-24 | 3 | G | 12847 | 0.04518982105862692 | 0.05191873589164785 | 0.2259491052931346 |
| 2023-24 | 3 | A | 12847 | 0.05028843030826248 | 0.051296022417685064 | 0.15086529092478745 |
| 2023-24 | 3 | CS | 12847 | 0.08031462754220536 | 0.06803144703043512 | 0.08031462754220536 |
| 2023-24 | 3 | B | 12847 | 0.07558011066012531 | 0.08173114345761656 | 0.07558011066012531 |
| 2023-24 | 3 | R | 12847 | 0.6130642301739785 | 0.6014633766638126 | 0.6130642301739785 |
| 2023-24 | 4 | G | 3854 | 0.07393380160963992 | 0.096004151530877 | 0.29573520643855966 |
| 2023-24 | 4 | A | 3854 | 0.04413877276123183 | 0.043591074208614425 | 0.13241631828369546 |
| 2023-24 | 4 | CS | 3854 | 0.06813166842222101 | 0.05786196159833939 | 0.0 |
| 2023-24 | 4 | B | 3854 | 0.11522466294772066 | 0.12454592631032693 | 0.11522466294772066 |
| 2023-24 | 4 | R | 3854 | 0.5403404951864508 | 0.537104307213285 | 0.5403404951864508 |

## Receipt failure and no-refit repair

The first 2022/23 control fit completed numerically and passed exact PR56 parity, but the private worker failed when updating its attempted ledger through a write-once JSON helper. Its prediction, result and parity files were already complete. Execution stopped; the failed guard, traceback, attempted token and blocked batch were retained.

An independently reviewed private-only repair kept ledger creation exclusive and added an exact attempted-record check, exclusive temporary sibling and atomic replacement for completion. Before any real step, a native-guard synthetic test covered consecutive ordinals, result hashes and refusals for repeated completed jobs, pending tokens and tampering; the aggregate/export regression also passed.

A separate no-fit script verified saved-output bytes against accepted receipts, prediction/bundle hashes, the precise failure location, unchanged attempted token and recomputed PR56 parity. Only ordinal 00 was completed with an explicit no-refit repair marker. Every file in that fit directory remained byte-identical. A new continuation batch reused Stage A and the saved control prediction, running only ordinals 1–3 and the aggregate. No numerical/public study code or specification changed.

**Real fit counts: B 4/4 jobs, C 0/4 jobs.** B includes the original numerical fit whose receipt was repaired. It contains 12 fitted heads: two direct controls and two five-head component models. The continuation added 3 jobs / 11 heads; ordinal 00 was never rerun. No Stage A rerun, real-run retry or retrieval.

A subsequent repeated optional read-only documentation lookup also caused a conservative tooling stop. The already-running continuation reached its recorded exit; no further scientific stage began. Publication resumed separately from the saved result after review. No source or data changed from those failed reads.

## Conditional audit gates and exclusions

| Stage C gate | Outcome |
|---|---|
| 2: audit_rmse | Not evaluated: Gate B failed |
| 3: audit_season_stability | Not evaluated: Gate B failed |
| 4: audit_mae | Not evaluated: Gate B failed |
| 5: audit_block_interval | Not evaluated: Gate B failed |
| 6: fixed_squad_points | Not evaluated: Gate B failed |
| 7: full_scoring | Not evaluated: Gate B failed |

Stage C was not triggered. No 2024/25 or 2025/26 candidate audit, audit admission, DC/full-scoring check or new panels occurred. Its four conditional jobs remain unused and no further fit is authorised. No E0 file was needed/read; retrieval attempts 0. No 2026/27 scoring, Stage D integrity/artifact build, promotion, live ingestion or prospective shadow qualification. The real audit path is not qualified by this study.

## Resources, verification and limitations

6 real guarded jobs are retained: 5 completed and 1 original receipt failure. Total 152.0610000002198 s; maximum 60.937000000150874 s/job; peak committed job memory 914874368 bytes. All jobs ended with zero active processes and no native resource-limit breach. Limits remained two threads, 4 GiB, 900 s/job, package growth 256 MiB, minimum free disk 5 GiB. The final numerical package size including reserve was 46228835 bytes, free disk 859493044224 bytes. Synthetic guard costs are recorded separately from real fit counts.

Targeted Windows tests, privacy and exact-head Ubuntu full tests/wheel checks passed before the original real batch. Private ledger and aggregate/export regressions passed before the repair/continuation. Full local Windows collection is limited by the existing POSIX resource import; Ubuntu CI is the full-suite authority. All failures, repairs, numerical output hashes and costs remain preserved. Publication only transcribes saved receipts; it adds no fit, scoring or re-aggregation.

The modest prior was that matched event losses might improve learning efficiency despite added estimation variance. This frozen decomposition does not improve candidate RMSE and worsens ranking; the small MAE benefit and +1.675 fixed-squad delta do not rescue the gate. The result is specific to the declared head set and specifications, not every possible decomposition.

Architecture selection followed earlier input/capacity studies, and development folds have been inspected repeatedly: this is an adaptive/forking-path risk. The later seasons were also inspected in earlier work, so even a conditional audit would not have been an untouched test. Historical publication clocks are unmodelled, and fixed squads are not transfer/chip strategy outcomes. These results do not establish current-season deployability.

**Approved 1.0.0 remains approved and unchanged.** No model artifact was saved, registry/default/product pipeline changed, or consumer release-notes entry added. Scientific interpretation is accepted; architect pre-merge review of this publication is PENDING. No merge, tag or branch cleanup at this boundary.
