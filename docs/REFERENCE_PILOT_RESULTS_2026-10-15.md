# Retrospective reference pilot — 15 October 2026

**Status: completed method/pipeline diagnostic; ineligible for the strict
historical pre-deadline benchmark. No model promotion.**

The [fixed policy](reference_pilot.md) and source audit were committed at
`86231655eea44a5431f3a63076f199488c9957aa` before the fit. One seed, three fixed
HGB7 components, no search/early stopping, no validation selection/refit, no
saved experimental model binary. Training used 147,500 fixture-player rows;
validation reserved 6,529; evaluation used 9,043. See the policy for exact seasons
and windows. Evaluation features may incorporate earlier completed evaluation
matches for the next-GW horizon; estimator weights remain fixed.

## Input checks and limitations

All 18 local pinned raw-file hashes matched source revision
`9779cdbc0c07f6c900c2d0c181ddf6bb9c800f88` of the
[historical FPL archive](https://github.com/vaastav/Fantasy-Premier-League/tree/9779cdbc0c07f6c900c2d0c181ddf6bb9c800f88).
Rebuilding all 163,072 history rows reproduced identities, targets and cutoffs.
A deterministic stratified sample of 240 feature rows (40 per season, seed
20261015) reproduced cached features, including player/team/opponent source
maxima. This sample does not establish every feature value independently.
All cached source maxima passed the declared three-hour completion gap.

The cache uses final fixture assignments and reconstructed cutoffs. No archived
schedule knowledge is certified. Outcomes/windows were previously inspected;
these are reused retrospective diagnostics, not untouched tests. Full points are
2025/26-rule outcomes. They do not measure current-season deployment accuracy,
captaincy gains or full-season transfer/chip gains. External systems have not
been refitted/scored on this window, so no cross-system ranking is justified.

## Shared-row results

Double fixtures are summed per player-GW. Primary candidate membership uses only
lagged-history features and is identical across methods: 2,312 player-GWs across
11 GWs. All-player secondary metrics include 8,713 player-GWs. Both baselines
predict core points plus a lagged DC-rate estimate.

| Method | Candidate RMSE | Candidate MAE | All-player RMSE | All-player MAE |
| --- | ---: | ---: | ---: | ---: |
| Incumbent-method reference | 2.9778 | 2.2549 | 1.8655 | 0.9453 |
| EW4 core + lagged DC | 3.0862 | 2.2719 | 1.9630 | 1.1936 |
| Last-five core + lagged DC | 3.2641 | 2.5063 | 2.0314 | 1.0302 |

Paired four-GW circular-block intervals (1,000 draws, seed20261015) describe this
fixed historical panel; they do not correct model-selection bias:

| Candidate error difference, reference minus baseline | Observed | Descriptive 95% interval |
| --- | ---: | ---: |
| RMSE minus EW4 | −0.1084 | [−0.1423, −0.0777] |
| MAE minus EW4 | −0.0169 | [−0.0514, +0.0154] |
| RMSE minus last-five | −0.2863 | [−0.3640, −0.2133] |
| MAE minus last-five | −0.2514 | [−0.3188, −0.1793] |

The reference's RMSE is lower on this panel. Its small MAE difference from EW4
does not exclude zero under this descriptive interval. The all-player pool has
many non-appearances and must not replace the declared candidate primary metric.

## Resource profile and provenance

Two numerical threads; watchdog caps30minutes/4GiB RSS. The entire worker
(load/audit, three fits, predictions, metrics and output) completed in26.909s,
with peak **observed** process-group RSS604,143,616bytes (~576MiB). This is not
a separate training-only or warm-inference timing. Sampled project growth was
830,807bytes (<1MiB); no resource limit was reached. No GPU or remote compute
was needed. Larger external ensembles remain unmeasured.

The private write-once manifest/run record and raw outputs remain outside Git:

- Manifest SHA-256: `4ecc80d4bd1f014c5f6867812a248b4da7b420dc4a8dbc2f43e9f3a350c0d467`.
- Prediction export SHA-256: `bfa3ca1d9d3dae3aecd6fcacb39094e38eb1a43b403219bc20c5f54453633661`.
- Aggregate result SHA-256: `6e0d8617fe3c2061efdf8d0e5f5b84930506e85bdfa33e2ea818bdc1fb48aae6`.

Only aggregate measurements are published. Registry, approved weights, manual
overrides and weekly command behaviour remain unchanged.

## Remaining work, in dependency order

1. Establish credible historical deadline/schedule knowledge; obtain and audit
   native external features/forecast lineage, temporal evidence and identities.
   Resolve the [source-audit questions](REFERENCE_SOURCE_AUDIT.md) before declaring
   an external method eligible. This is data work, not a hardware requirement.
2. Run one bounded fixed-policy external reference fit per eligible method on a
   genuinely shared full-score cohort. Profile first; expand folds/seeds only
   where useful. Never substitute incumbent features and call it a reproduction.
3. Predeclare at most two or three targeted challengers from diagnosed gaps;
   use development-only selection and retain rejected/incomplete runs. Do not
   search this published panel and describe it as independent evidence.
4. Freeze approved/finalist forecasts prospectively through the separately
   authorised weekly workflow. Score finalised results and apply unchanged
   promotion gates. No automatic scheduling, retraining or promotion is enabled.

The first bounded incumbent-method pilot is now complete. Further historical
expansion is conditional on evidence quality and marginal value; the present
measurements do not justify a separate-compute handoff.
