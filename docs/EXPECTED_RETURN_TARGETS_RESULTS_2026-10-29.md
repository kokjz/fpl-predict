# Expected-return training targets: negative development result

29 October 2026. **Stage A PASS; Stage B FAIL (4 of 10 criteria fail). Approved 1.0.0 and weekly defaults remain unchanged.** No model promotion. The single challenger was trained on expected-return labels and evaluated on actual points against a refitted actual-label control.

Numerical source `bf2ad93b135786cf13024f4a1a840a62e9e8e5ec`; original protocol LF `a0d8a6b621684a2ec61da4840ee41a2d416fc120b91049fcb3ed9c17ac535f22` frozen at `74bd212000084f168a6b73392f2b54dc78aa830f`; amendment LF `bf45effd426040810fc906f570b20822ddf23c54db08976b2f9e970e7c86b594` frozen at `ab5711dac9e7307a4d6d701f0c7b70dd92ec8964` before resumption. [Full scalar results](expected_return_targets_results_2026-10-29.json).

## Admission and label specification

The initial attempt stopped on a missing `clean_sheets` column before any admission statistics or fit. Amendment 1 derives it per player-fixture as minutes ≥60 and FPL goals_conceded=0. Appearance, goals, assists, clean sheets, save/conceded floors, penalties, cards, own goals and bonus must reconcile exactly to actual points. Unreconciled rows fall back wholly to actual labels and are excluded from every scaling sum. No alternative source, alias or threshold change was used.

Schema preflight checks all required names, dtypes and fixture-key uniqueness before other data calculations; no gaps were found. Each training season has 100% Understat xG/xA coverage among played rows, 100% exact points reconciliation, and finite opponent xG for every training team-fixture. All fallback rows had zero minutes; there were no unreconciled played rows.

| Training season | Rows | Played | Reconciled played | Fallback | Team-fixtures |
|---|---:|---:|---:|---:|---:|
| 2020-21 | 24365 | 10393 | 10393 | 13972 | 760 |
| 2021-22 | 25447 | 10485 | 10485 | 14962 | 760 |
| 2022-23 | 26505 | 11345 | 11345 | 15160 | 760 |

Training-only k constants multiply per-match Understat xG, xA and exp(−opponent xG); the clean-sheet expectation applies only at 60+ minutes. All other point components stay actual. Whole-row fallback also applies to zero minutes or nonfinite player xG/xA. Test labels remain actual. No target clipping, variants or blending.

| Test fold | k_G | k_A | k_CS | Actual label variance | Expected-return variance |
|---|---:|---:|---:|---:|---:|
| 2022-23 | 0.9385055065431578 | 1.2171660770034034 | 0.9077087345733678 | 6.061493112440526 | 4.164767195389726 |
| 2023-24 | 0.9276400725886316 | 1.1869496198002774 | 0.9140987858814367 | 5.883744253001581 | 4.037183014552445 |

Variance is descriptive population variance (ddof=0), not an additional gate. Full per-position counts, fallback counts, scaling numerators/denominators and variances are in the JSON.

## Development errors

Unchanged I4 core: 49 identical features, seven-leaf HGB, 200 iterations, learning rate0.05, L2=20, minimum leaf60, no early stopping, seed20260921, 730.5-day age weights and final fixture prediction clip[0,20]. Folds train2020/21–2021/22→2022/23 and through2022/23→2023/24. Exactly four serial fits completed without retry. Only training labels changed; features, keys, cohort, cutoffs, age weights and evaluation targets were shared, with formula recomputation before any fit. No test-season Understat values entered that fold’s labels or k constants.

Relative percent =100×(challenger/control−1); negative error change favours the challenger. Candidate eligibility is the unchanged deadline-based predicate; all-player errors are separate diagnostics.

| Scope | Unit | Control RMSE | Expected RMSE | Relative % | Control MAE | Expected MAE | Relative % |
|---|---|---:|---:|---:|---:|---:|---:|
| 2022-23 | candidate_player_gw | 3.065020483423453 | 3.055075591401695 | -0.32446412921357526 | 2.2281486372323003 | 2.22537946747508 | -0.12428119520158099 |
| 2022-23 | candidate_fixture | 2.965629114390763 | 2.9565567554859524 | -0.30591684107721395 | 2.1543116468863786 | 2.15036722311111 | -0.18309439031113373 |
| 2022-23 | all_player_gw | 2.036064439592689 | 2.0317519986282315 | -0.2118027740477646 | 1.0981033813277787 | 1.0950926776900818 | -0.27417305955806937 |
| 2022-23 | all_fixture | 1.965855425497952 | 1.9616499148530067 | -0.213927768563138 | 1.057028259925666 | 1.0536460902911597 | -0.31996965102372155 |
| 2023-24 | candidate_player_gw | 3.0944000157947382 | 3.0940236399254384 | -0.01216312911642703 | 2.1998879734602452 | 2.2287625408960103 | 1.3125471744066974 |
| 2023-24 | candidate_fixture | 3.022407244624807 | 3.022665877958065 | 0.008557196708602888 | 2.155004306975747 | 2.1836673989154076 | 1.3300712136341541 |
| 2023-24 | all_player_gw | 1.9518630622880042 | 1.9515643164508465 | -0.015305676045096472 | 0.9802283394192596 | 0.9910021360893616 | 1.0991109149613987 |
| 2023-24 | all_fixture | 1.9088257881806183 | 1.9088807785405408 | 0.0028808474960451136 | 0.9587949209612978 | 0.9693981882376422 | 1.1058952279089596 |
| pooled | player_gw | 3.0799092007886055 | 3.0748285879800967 | -0.1649598243743 | 2.213860624501649 | 2.2270898801000936 | 0.5975649709846875 |
| pooled | fixture | 2.994065693329274 | 2.9896926613292867 | -0.14605664831370824 | 2.154656914638294 | 2.16696624045714 | 0.5712893656163454 |
| pooled | all_player_gw | 1.9914391236958255 | 1.9892342109671322 | -0.11071956468352573 | 1.0350116206891327 | 1.0393789707925998 | 0.4219614559070495 |
| pooled | all_fixture | 1.9359170364785765 | 1.933933839363286 | -0.10244225748939906 | 1.0050989339303638 | 1.0091099194118995 | 0.3990637484661441 |

Pooled candidate player-GW RMSE improves **0.1649598243743%**, and fixture RMSE improves **0.14605664831370824%**, both below the required0.5%. Pooled MAE worsens **0.5975649709846875%** and **0.5712893656163454%**, exceeding the0.5% noninferiority limits. The 2023/24 fixture RMSE worsens0.008557196708602888%; that fold’s candidate MAE worsens1.3125471744066974% (player-GW) and1.3300712136341541% (fixture).

## Every gate criterion

| Criterion | Verdict | Exact candidate/control threshold |
|---|---|---|
| pooled_player_gw_rmse_gain | **FAIL** | {"candidate":3.0748285879800967,"threshold":3.0645096547846626,"passed":false} |
| pooled_player_gw_mae_noninferiority | **FAIL** | {"candidate":2.2270898801000936,"threshold":2.224929927624157,"passed":false} |
| pooled_fixture_rmse_gain | **FAIL** | {"candidate":2.9896926613292867,"threshold":2.9790953648626277,"passed":false} |
| pooled_fixture_mae_noninferiority | **FAIL** | {"candidate":2.16696624045714,"threshold":2.1654301992114853,"passed":false} |
| 2022-23_candidate_player_gw_rmse_noninferiority | PASS | {"candidate":3.055075591401695,"threshold":3.0803455858405697,"passed":true} |
| 2022-23_candidate_fixture_rmse_noninferiority | PASS | {"candidate":2.9565567554859524,"threshold":2.9804572599627166,"passed":true} |
| 2023-24_candidate_player_gw_rmse_noninferiority | PASS | {"candidate":3.0940236399254384,"threshold":3.1098720158737114,"passed":true} |
| 2023-24_candidate_fixture_rmse_noninferiority | PASS | {"candidate":3.022665877958065,"threshold":3.0375192808479308,"passed":true} |
| pooled_ndcg10_not_lower | PASS | {"candidate":0.43793212259094255,"control":0.43674514166138834,"passed":true} |
| mean_fixed_squad_delta_nonnegative | PASS | {"delta":8.774999999999999,"passed":true} |

## Ranking, fixed squads and descriptive interval

| Fold | Control NDCG@10 | Expected NDCG@10 | Relative % | Control squad mean | Expected squad mean | Mean delta | Minimum delta | Maximum delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022-23 | 0.45655785665444754 | 0.4625161850240756 | 1.3050543940453352 | 1453.85 | 1463.2 | 9.35 | -25.0 | 45.0 |
| 2023-24 | 0.41749850423955953 | 0.41405046194161327 | -0.8258813535695464 | 1378.85 | 1387.05 | 8.2 | -29.0 | 44.0 |
| pooled | 0.43674514166138834 | 0.43793212259094255 | 0.2717788514003727 | 1416.35 | 1425.125 | 8.775 | -29.0 | 45.0 |

Original frozen I4 panels are retained verbatim:20 per fold, firstGW4,40 total; no transfers, chips or season paths. The class-A guard finds only77/600 last-bit weight differences, maximum relative2.4480719460869007e-16, with all structural fields exact. Its1e-9 fixture-admissibility tolerance is not a score tolerance. Control deltas are zero; all individual totals and deltas are in the JSON. The gate retains I4’s mean-of-two-fold-means8.774999999999999; the equivalent40-panel descriptive mean is8.775. Positive fixed-squad means and ranking do not override failed gates.

Paired candidate player-GW intervals use the unchanged descriptive four-GW block bootstrap,1,000 draws, seed20261015,69 weeks in contiguous segments3/31/35. They concern fixed predictions on reused development data, not training/selection uncertainty or independent football seasons.

```json
{
  "expected_return": {
    "scope": "descriptive fixed-prediction uncertainty, not training or selection uncertainty",
    "difference": "left_minus_right; negative error difference favours left",
    "samples": 1000,
    "block_length": 4,
    "seed": 20261015,
    "gameweeks": 69,
    "contiguous_segments": [
      3,
      31,
      35
    ],
    "status": "descriptive_interval",
    "confidence": 0.95,
    "rmse": {
      "delta": -0.005080612808509688,
      "lower": -0.009005027805345178,
      "upper": -0.0008168401324444016
    },
    "mae": {
      "delta": 0.013229255598444121,
      "lower": 0.008695669814001418,
      "upper": 0.01870810800775669
    }
  }
}
```

## Bias and position diagnostics

| Fold | Position | Control candidate bias | Expected candidate bias | Control candidate RMSE | Expected candidate RMSE |
|---|---|---:|---:|---:|---:|
| 2022-23 | 1 | -0.1088998865912917 | -0.0529053051687514 | 2.9749047071047396 | 2.963383778121028 |
| 2022-23 | 2 | 0.04517605954068671 | 0.0700484774191753 | 2.8292792241377565 | 2.820219334912639 |
| 2022-23 | 3 | -0.060006708776397445 | -0.08693657348283185 | 2.929075515518481 | 2.9215710763248888 |
| 2022-23 | 4 | -0.2339278293353597 | -0.2141112439159488 | 3.5778105536997806 | 3.564580240775657 |
| 2023-24 | 1 | 0.2233624248959958 | 0.3386944111098435 | 2.5668812579103153 | 2.5868340041881184 |
| 2023-24 | 2 | 0.06876683660109136 | 0.17813904331296976 | 2.8838826308837593 | 2.891748471329898 |
| 2023-24 | 3 | -0.0825864267733378 | -0.05135222219922106 | 3.09265711741514 | 3.088765361545278 |
| 2023-24 | 4 | -0.1696812597302779 | -0.149519130793714 | 3.558311310164854 | 3.537796392058326 |

Positions1/2/3/4 mean GK/DEF/MID/FWD. Full per-fold and pooled bias, sample sizes, actual-minutes and cold-start diagnostics remain in the JSON. Actual-minute slices are descriptive, not an available-at-deadline eligibility rule.

## Integrity, resources and limits

Pre-fit shared proof `f2f23aefae25fdea74b6b054638f3d27272be8aa25f13b22de7ad5d89db2d2eb`; original aggregate SHA256 `dcc91d3aa43192019bb2e605e604981df7d1a2753b94a11cf5a8634b7a4bbd77`. Both source CI runs passed830tests with9documented optional/platform/private skips, privacy audit403files and wheel build, before real calculations. Thirty-five targeted local tests include four actual Windows guard tests. Native memory is job-wide committed-memory accounting, not resident RSS. All six jobs completed with exit0/no guard violation/no surviving descendants.

| Job | Seconds | Peak native job bytes |
|---|---:|---:|
| StageA_admission | 21.01500000001397 | 551067648 |
| 2022-23_control | 11.375 | 395702272 |
| 2022-23_expected_return | 11.03200000000652 | 395948032 |
| 2023-24_control | 18.21799999999348 | 395071488 |
| 2023-24_expected_return | 17.14000000001397 | 394379264 |
| aggregate | 8.0 | 395796480 |

Limits: two threads,4GiB,900s per job, serial; accounted package54950799bytes including16MiBreserve, minimum free862805827584bytes. All limits passed. Legacy numerical runtime remains Python3.12.16/NumPy2.3.5/pandas2.2.3/scikit-learn1.9.1; original I4 macOS/Python3.12.14 differences were previously qualified and remain disclosed.

These are reused2022/23–2023/24 development comparisons. Corrected provider values and reconstructed clocks retain the I4 provenance limitations. A lower-variance training label did not meet the actual-point error gates. This is one core-points HGB, not a newly qualified deployment multihead model. No2024/25 or2025/26 data/scoring, downloads, extra fits/arms/seeds/k variants, blending, target clipping, Stage D, season paths or promotion. No model binary was saved. Approved1.0.0, private registry and weekly defaults are unchanged.

PR48 is being prepared for architect pre-merge review. No merge, study tag or branch cleanup is authorised at this boundary.
