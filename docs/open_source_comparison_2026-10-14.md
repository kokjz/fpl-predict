# Open-source FPL comparison and bounded I3 results

Research/evaluation: 14 October 2026. **Retain approved v1.0.0.** No lightweight
challenger passed the predeclared gate. This does not claim parity with the best
external systems: a matched retrospective Dastan comparison reveals a real gap.

## Projects inspected and ideas worth considering

| Project | Approach/evidence inspected | Viability for a small local engine |
|---|---|---|
| [OpenFPL](https://github.com/daniegr/OpenFPL) | Per-position forest/XGBoost ensembles, FPL/Understat rolling features, current availability. Paper evaluated prospective 2024/25 GW32–38 forecasts; outcome buckets are descriptive. | Test cheap position specialists/diverse trees first. Full 50-model-per-position search and additional data maintenance need evidence to justify cost. No measured local runtime for that full system. |
| [Dastan](https://github.com/qazybekb/smartplayfpl-dastan) | Participation, conditional return bands, direct regression and blends; 36 inference artifacts, 286 features; chronological windows, deadline anchoring, seed checks and retained negative results. | Best benchmark target. Test simple minutes composition now; richer bands/calibration and timestamped role information later. Do not assume its inference is too expensive without measuring. |
| [AIrsenal](https://github.com/alan-turing-institute/AIrsenal) | Team scorelines plus player involvement/event components; recent minutes distribution. Inspected closed-form Dirichlet update and optional MCMC implementation. | Closed-form shrinkage is cheap; a full team/event rewrite and player-history joins add maintenance. Our existing priors/recency capture some of this benefit. No comparable exact-row forecast archive found in inspected files. |
| [OpenFPL Scout AI](https://github.com/elcaiseri/OpenFPL-Scout-AI) | Ridge/XGBoost/CatBoost/MLP ensemble; report exposes forward validation and 2025/26 aggregate error (~1.924 RMSE). It uses richer identity/ownership/historical-xP information. | An ensemble's reported number is not directly comparable to ours. Verify as-of provenance of every archived field before adopting it; extra libraries/training need incremental benefit. No compatible full prediction export used here. |
| [Lionel](https://github.com/jotohow/lionel) | Extensible Bayesian hierarchical model with PyMC NUTS, and constrained selection. | Partial pooling is useful, but sampling-heavy fitting is lower priority than role/minutes data. No matched accuracy evidence found in inspected source/docs. |
| [FPL decision engine](https://github.com/Linus-J/FPL-decision-engine) | De-vigged odds or Dixon–Coles team goals; empirical-Bayes shrinkage and uncertainty-aware optimisation. | Possible cheap fixture/event challenger later; odds add quotas/as-of archiving. No licence identified: do not copy code. Optimisation features do not themselves establish better predictions. |

First five source projects identify MIT licensing. We implemented independent
method adaptations, copied no third-party code/weights, executed no downloaded
project code, and redistributed no football dataset. Exact inspected revisions,
retrieval dates, URLs and file hashes: [source manifest](open_source_sources_2026-10-14.json).
Methods were assessed from code as well as README claims; absence of a comparable
archive in the inspected material is not proof one exists nowhere.

## Matched comparison against an existing external model

Dastan's retained 2024/25 GW15–38 walk-forward table matches **all 17,622** of the
original v1 expanding-window predictions after mapping football IDs and summing
double fixtures to player-GW totals. **Zero outcome conflicts, zero unmatched
external rows.** Both predict the same full-score target in this season (no DC
award). No current or private-manager decisions were evaluated.

Our pre-deadline candidate predicate (>=3 prior records, last-five minutes>=45)
selects **5,145** paired player-gameweeks. Actual 60+ minutes is reported separately
only as a diagnostic; it does not determine this candidate pool.

| Method | Candidate RMSE | Candidate MAE | Mean within-GW Spearman | Mean within-GW NDCG@10 |
|---|---:|---:|---:|---:|
| v1 | 2.9765 | 2.1354 | 0.379 | 0.494 |
| dastan | 2.8910 | 2.0204 | 0.469 | 0.488 |
| dastan_without_ep_next | 2.8893 | 2.0194 | 0.471 | 0.492 |
| last5 | 3.2435 | 2.3803 | 0.265 | 0.405 |
| ewm | 3.0423 | 2.1247 | 0.314 | 0.432 |

Dastan reduces candidate RMSE by **2.87%** versus v1 in this archive. On all
17,622 matched rows, RMSE is 1.9043 for v1 and 1.8456 for Dastan. The candidate
four-GW circular-block bootstrap interval for Dastan-minus-v1 RMSE is
-0.1043 to -0.0683; it describes this inspected sample,
not independent confirmation after selection. Ranking is mixed: v1's candidate
NDCG@10 is slightly higher, so better average error does not establish better
captain/season points.

This is **retrospective, not a prospective fair contest**. Dastan updates fits
within season; v1 uses the original annual expanding fit. Feature/news inputs
and selection histories differ, and Dastan's configuration was researched after
these seasons. The source's missing-ep_next coverage cannot be recovered cleanly
from the retained filled column, so that column is not presented as a verified
full-coverage official baseline. Do not compare headline errors across other
projects' unmatched seasons, cohorts, horizons or scoring rules. OpenFPL ships
only five example forecast rows in the inspected predictions file, insufficient
for a representative head-to-head.

Reproduction: optional PyArrow 26.0.0 was installed in a temporary reader directory,
not the operational environment. Run `tools/compare_dastan.py --help` for explicit
archived-export paths. Obtain Dastan's pinned parquet from the source manifest;
use the original v1 heldout JSONL and 2024/25 players_raw ID mapping. The comparator
rejects duplicate keys, missing IDs, differing targets/outcomes and inconsistent
candidate predicates. Raw/paired rows and individual outputs stay outside Git.

## Fixed lightweight adaptations tested

[Protocol](I3_PROTOCOL.md) preceded fitting. Two forward development folds,
2022/23 and 2023/24, contain 15,323 pre-deadline candidate fixtures. Later seasons
were removed before selection. These are reused **development** outcomes, not
new untouched tests. Three distinct adaptations plus fixed 50/50 blends were
compared with a freshly fitted incumbent on identical features/windows.

| Method | Core RMSE | Core MAE | RMSE reduction vs incumbent |
|---|---:|---:|---:|
| incumbent | 2.994066 | 2.154657 | +0.000% |
| position | 3.011082 | 2.150084 | -0.568% |
| minutes_mixture | 2.995551 | 2.155618 | -0.050% |
| extra_trees | 2.994459 | 2.156868 | -0.013% |
| position_blend50 | 2.994894 | 2.148213 | -0.028% |
| minutes_mixture_blend50 | 2.991402 | 2.153225 | +0.089% |
| extra_trees_blend50 | 2.990871 | 2.153492 | +0.107% |

Best reduction: **0.107%**, below the unchanged 0.5% gate. No finalist, no seed
selection/retries, no later audit or current-season scoring, no promotion. The
external comparison scored only the incumbent; it did not select an I3 model.
The original approved artifact and original evaluation evidence remain intact.

## Resource results and stopping decision

On the local Apple Silicon environment with two computation threads/two forest
workers: whole development search **53.8s**, peak process RSS **0.520 GiB**.
Warm inference on 1,000 fixtures took about 0.002s for the incumbent, 0.005s for
position specialists, 0.012s for the minutes mixture and 0.013s for ExtraTrees.
Blend estimates add component timings (up to 0.015s); these are not cold-start or
complete weekly-run timings. Downloads, feature generation, news review and
planning are excluded. Limits are checked between fits, not enforced by the OS.
No additional paid API/cloud/GPU cost. Power/thermal effects were not measured.

The computation budget was ample; the available features/evidence, rather than
M4 inference speed, limited the measured gain. Stop this fixed search instead of
adding tiny tuned improvements on repeatedly used data. Keep lightweight research
code as opt-in tooling and retain the current champion for operational forecasts.

Next highest-value work: timestamped expected role/minutes and actual availability
snapshots, richer conditional-return/calibration features with proper forward
validation, and external forecasts captured alongside ours before identical
future deadlines. Avoid treating historic xP/current injury fields as known
pre-deadline inputs. A broader Dastan reproduction needs validated feature joins
and a new bounded protocol; it is not justified as an automatic replacement.
No current-gameweek forecast or squad plan is created by this research.

[Aggregate results](I3_RESULTS.json) retain failed trials, matched comparison
metrics and provenance. The original run used source commit
`3d01957280f18d6a936f2d2552be3f7547529b30`; later metadata-only timestamp support
does not change the fitted maths. Code merges do not establish model approval.
