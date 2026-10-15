# Cutoff-safe native-window pilot — 15 October 2026

One fixed feature pilot modestly reduced prediction error against the frozen
incumbent-method reference, but worsened top-player ranking. It does **not**
justify model promotion or establish superiority over Dastan/OpenFPL.

## Method and admission

The [pre-fit protocol](NATIVE_REFERENCE_PROTOCOL.md) names
`native-window-cutoff-hgb7-gapmask-v1`: 286 rebuilt history/context predictors plus
four fixed position indicators, one pooled 200-iteration HGB7 learner, two-year
recency weighting and no search, validation refit or calibration. This tests a
feature bundle, not Dastan's original per-position multi-head ensemble.

The source implementation and amended protocol were committed at
`cc0b9ea21c8d53813aa52b4dec7e1536f10f5c2e` before fitting. All 163,072 fixture rows
were retained: 147,500 training, 6,529 reserved validation (2025/26 GW20–27),
9,043 evaluation (GW28–38). Earlier seasons and 2025/26 GW1–19 form training.
Player, own-team, opponent and league-context histories use matches strictly
before deadline minus three hours; rest/congestion use the deadline itself.

Six league and 1,368 player captures from [Understat](https://understat.com/)
were joined to pinned FPL histories using audited identities, dates, clubs,
venues and scores. Provider clock differences were recorded; matched FPL UTC
event times determine history cutoffs. Two published player-ID corrections were
applied. Provider statistics remain mutable and lack historical publication-time
certification. Raw data and row-level outputs are not redistributed here.

Strict readiness failed: two mapped training appearances (2025/26 GW9, fixture 83,
FPL codes 155408 and 168636) were absent from both player histories and the provider
match roster. The strict failure was retained. **Before any pilot fit or score**, a
separately named gap-aware variant allowed exactly these two rows with all six
Understat statistics unknown. No mapped validation/evaluation gaps were allowed.
Another 25 played rows without source mappings retained unknown statistics.
No missing-data decision excluded a prediction row or invented a zero.

Only the 38 verified 2025/26 bootstrap snapshots supplied snapshot predictors;
earlier seasons use explicit missing values. Of 9,043 evaluation fixture rows,
24 lacked a selected snapshot identity, all outside the candidate cohort.
Snapshot absence is not proof of deadline ineligibility. These limitations,
reconstructed older deadlines, manually sourced target-window event membership
and previously inspected outcomes keep `benchmark_eligible=false`.

## Measured results

Predictions are summed over fixtures to player-GW totals before scoring. The
primary snapshot-known candidate cohort requires at least three season-history
matches and last-five mean minutes of at least 45; it contains 2,312 player-GWs
over 11 weeks. The all-candidate cohort happens to be identical. All-player
diagnostics contain 8,713 player-GWs. All methods use identical keys and actuals.

| Primary candidate measure | Native-window pilot | Frozen incumbent-method reference | Last-five full-points mean |
| --- | ---: | ---: | ---: |
| RMSE (lower is better) | 2.95586 | 2.97780 | 3.28440 |
| MAE (lower is better) | 2.24939 | 2.25493 | 2.52983 |
| Mean prediction minus actual | +0.20469 | +0.08593 | +0.38537 |
| Mean within-GW Spearman | 0.42446 | 0.38965 | 0.25005 |
| Mean within-GW NDCG@10 | 0.41481 | 0.47252 | 0.34852 |

RMSE improved 0.02194 (0.74%) against the fixed reference. A descriptive paired
four-GW-block bootstrap (1,000 draws, seed 20261015) gives a 95% interval for
pilot-minus-reference RMSE of [-0.03592, -0.00811]; the MAE interval
[-0.02785, +0.01465] includes zero. These intervals condition on fixed predictions
and do not account for model selection, training uncertainty or reused outcomes.
Overall ranking improved, while NDCG@10 fell 0.05771 and positive bias increased.
No captaincy, transfer-policy or season-points benefit was measured.

All-player RMSE was 1.84762 versus 1.86552 for the reference and 2.04213 for last-five;
MAE was 0.93139 versus 0.94534 and 0.99352. This easier pool includes many low-minute
players and must not replace the predeclared candidate primary comparison.
The reference is the earlier **training-only full-score method variant**, not a
retrospective application of the deployed all-seasons binary. Last-five here is
full historical points, distinct from the previous core-plus-lagged-DC baseline.
Numbers from external models on different windows are not comparable rankings.

## Cost and reproducibility

One two-thread supervised run completed in 69.01 seconds, including auditing,
feature construction, training, inference and evaluation. Observed peak process
RSS was 1,313,996,800 bytes (1.224 GiB); project growth during the run was 762,769
bytes. It stayed within 4 GiB RSS, 30-minute time and 512 MiB growth caps. These are
sampled observations, not operating-system quotas or a hardware limit test.

| Stage | Seconds |
| --- | ---: |
| Load/audit | 1.309 |
| Feature construction, all 163,072 rows | 24.958 |
| Training, 147,500 rows | 41.233 |
| Prediction, 9,043 fixture rows from an already built matrix | 0.020 |

Prediction timing excludes source refresh, feature building, loading and scoring;
it is not an end-to-end weekly latency claim. One-off source acquisition used a
bounded partial download and verified resume, approximately15 minutes combined;
that network cost is separate from fit time. No model binary was saved.
Measured research environment: Python 3.12.14, NumPy 2.3.5, pandas 2.2.3,
scikit-learn 1.9.1; these versions are recorded rather than assumed equal to the
package installation pins.

| Frozen evidence | SHA256 |
| --- | --- |
| Pre-fit manifest | `7aa99e7dc91a40e9a22a9d25d957d2433d3f6cb549d6a021745e30392e7b51ff` |
| Provider download manifest | `d21f635bfe24859b7e24e513b23ef78e53dc79637851accf97407e15305abcd0` |
| Frozen reference predictions | `bfa3ca1d9d3dae3aecd6fcacb39094e38eb1a43b403219bc20c5f54453633661` |
| Pilot predictions | `a07182749787105de7160735f0954d8d1f17c251c4b6cb5cfc4596901a14e17c` |
| Pilot result JSON | `c288c58007e64a3fb4862c2f320bb4e7e6d3bb2ef63ab483b64275f49f6c62cc` |

See the [command/input contracts](native_reference.md) and
[third-party notices](../THIRD_PARTY_NOTICES.md). Hashes identify retained private
evidence; they do not independently certify historic data availability.

## Decision and next work

Keep the approved champion unchanged. The richer histories are inexpensive enough
for further bounded research, but this bundled experiment does not isolate which
features helped and fails to show consistent point-relevant ranking improvement.
Do not tune this pilot against GW28–38. A subsequent package should predeclare a
small development-only ablation/conditional-minutes comparison, including ranking,
coverage and fixed-squad point gates, with no new evaluation-window selection.
Future frozen shadow forecasts are needed for an operational adoption decision.
Full original-ensemble reproduction and historical source-time certification
remain separate unresolved work; more compute alone does not resolve either.
