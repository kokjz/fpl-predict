# Reading comparisons for FPL decisions

FPL planning needs useful rankings, sensible budgets and transfers, and a way to identify selection risk before the deadline. A model can perform better on those tasks without winning every average-error metric. Conversely, lower RMSE does not automatically buy more FPL points.

## A measured strength against original Dastan

On the same 5,145 predeadline candidate player-gameweeks across all 24 GWs in the retained 2024/25 GW15–38 archive:

| Metric | fpl-predict v1 | Original Dastan |
| --- | ---: | ---: |
| Mean NDCG@10, higher is better | **0.49370** | 0.48781 |
| GWs with higher NDCG@10 | **13** | 11 |
| Points RMSE, lower is better | 2.97650 | **2.89097** |

NDCG@10 rewards placing eventual high-point returns near the top of the forecast ranking. This is relevant to shortlisting promising options. All declared weeks and the same prior-history/minutes eligibility predicate are used; no favourable weeks or actual-minute filters were chosen to create this win. Negative realised scores are clipped to zero for this ranking metric, as in the existing comparator. It does not enforce positions, prices, owned players or chip/transfer constraints.

The ranking advantage is a **measured historical result**, not established general superiority. A subsequent exploratory four-GW block interval for v1-minus-Dastan NDCG is approximately [-0.0150, +0.0258], spanning zero; two- and six-GW sensitivities do too. The interval is post-hoc, conditional on inspected data and not adjusted for searching across metrics. Original information, fitting and selection histories also differ. It cannot establish repeatability, equivalence or a future points gain.

## How much does non-appearance handling matter?

Players already known before a deadline to be unavailable or outside the realistic selection pool usually deserve less attention in a comparison of viable transfer targets. A vast all-player pool of easy zero predictions can flatter errors while adding little to decisions. This project therefore already reports a main candidate cohort based on **earlier** history and minutes, alongside all-player coverage and actual net-point tests.

But a candidate who subsequently does not play is a real planning risk. The model must identify that risk **before** the deadline. Those misses affect starting XI choices, bench depth, transfers and captain fallback. Removing them after seeing actual minutes would assume away one of the prediction tasks.

A complete error decomposition within the same 5,145 candidates gives:

| Actual minutes, diagnostic only | Player-GWs | v1 RMSE | Dastan RMSE | Contribution to v1-minus-Dastan MSE gap |
| --- | ---: | ---: | ---: | ---: |
| Zero | 685 | 2.29922 | 1.78858 | +0.27792 |
| 1–59 | 697 | 2.05633 | 2.08485 | -0.01600 |
| 60+ | 3,763 | 3.21990 | 3.16855 | +0.23995 |
| All candidates | 5,145 | 2.97650 | 2.89097 | +0.50186 |

Approximately **55.4% of Dastan's net mean-squared-error advantage comes from the zero-minute group**, which is 13.3% of this candidate pool. Around 47.8% comes from the 60+ group, offset by a 3.2% contribution favouring v1 among 1–59-minute appearances. These are additive **MSE contributions**, not RMSE shares or percentages of fantasy points. Dastan's error advantage therefore extends beyond nonplayers; it cannot be dismissed as merely predicting irrelevant zeros.

These outcome-defined groups diagnose where errors occurred; they cannot select future transfers or establish which feature/architecture caused the gap. They motivate checking participation probability, recent role and timestamped team news. A causal comparison would hold other choices fixed while varying source information, refit frequency or participation/conditional-return modelling separately on chronological development data. Past participation challengers did not pass the project's promotion gates; this diagnosis does not justify automatic recalibration or multiplying unconditional point predictions by appearance probability again.

## What the practical benchmark adds

The incumbent-method reference outscored the tested Dastan architecture adaptation in the shared 2025/26 GW28–38 budget resets (69.182 versus 59.273 points/GW) and six rolling paths (624.667 versus 547.667 mean net points over eleven GWs). This is a genuine measured win **against that adaptation under the common policy**, with short-window, price-quote, source and inference limits. It is not a full original-Dastan system comparison. Primary owned-squad intervals remain inconclusive.

The separate **original** Dastan owned-panel replay instead favours Dastan by 0.198 points/GW, with an interval [-0.295, +0.691]. Those broad conditional rosters are stress scenarios, not representative strong-manager teams. Neither that point result nor our top-ranking win proves general superiority.

Use the [full practical results](SELECTION_BENCHMARK_RESULTS_2026-10-15.md), [forecast-error study](HISTORICAL_EXTERNAL_RESULTS_2026-10-15.md), and [original archive comparison](open_source_comparison_2026-10-14.md) together. A defensible public description is that v1 has a narrow original-Dastan top-ranking win and stronger measured decision totals against certain tested adaptations, while overall accuracy, repeatability and original-system season superiority remain distinct questions.

## Before a planning deadline

Prioritise a fresh, sourced review of plausible candidates and owned players, especially conflicts between model minutes/probabilities and official status/news. Keep missing information unknown, preserve base forecasts, and record manual sensitivity assumptions with source/publication/check times. Evaluate frozen forecasts after finalisation, including probability reliability and decision-point outcomes. The [availability workflow](availability_workflow.md) describes the process; operational squad planning is a separate action.

No production forecasting weights or approved registry entry changes because of this report. The [fixed news/availability probe](news_availability_probe.md) tests source value separately without automatic promotion. The read-only [participation audit](participation_audit.md) adds risk attribution and an evidence preflight; it does not choose players or claim to improve points.

## Reproducibility and grounding

The retained matched CSV SHA256 is `722fedeee8e76c3a1cfb1f3aa6fc80cb0875d3de2ef844f5def70513ac591990`. Values above use the original paired forecasts without refitting; the private diagnostic input/output is retained rather than overwriting the earlier reports. [Aggregate diagnostic evidence](COMPARISON_DIAGNOSIS_2026-10-15.json) records the decomposition and exploratory interval settings. No individual forecasts or manager data are redistributed.

Research checked 15 October 2026: [scikit-learn probability-calibration guidance](https://scikit-learn.org/stable/modules/calibration.html) explains why Brier score alone does not isolate calibration and why fitting a calibrator requires separate data. [Official FPL team management](https://www.premierleague.com/en/news/2174899) explains bench priority, formation and captain fallback. These support the evaluation/review procedure, not an observed model gain.


## Availability follow-up — 16 October 2026

The [matched incumbent availability study and six-method rebenchmark](INCUMBENT_AVAILABILITY_RESULTS_2026-10-16.md)
now tests structured labels against the full participation method, followed by
unconditional points-feature augmentation on historical data. Appearance error
improves, but points MAE/ranking and owned/rolling decisions do not jointly pass
the progression checks. The challenger is unapproved; original-system comparisons
in this report remain unchanged. New aggregates/provenance/cost are linked above.
