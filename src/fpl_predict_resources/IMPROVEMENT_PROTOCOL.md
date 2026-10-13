# Model improvement experiment I1 — predeclared protocol

Written before fitting candidates for user prompt 6, 21 September 2026. Incumbent: v1.0.0. The objective is better real historical prediction and decision performance; improvements in future realised FPL points cannot be guaranteed.

## Evidence boundaries

The 2024/25 and 2025/26 results were already inspected in the v1 project. They are **reused retrospective audits**, not pristine holdouts. Do not relabel them. Candidate design is motivated by general forecasting research, not searches over their outcomes. Final current-season GW1–5 results have been seen in football research but never scored against this model; reserve this short, retrospective comparison until a finalist is locked. It is not a prospective trial. Genuine prospective evidence starts with forecasts frozen for GW6 onwards.

## Fixed development and stopping plan

1. Two expanding-window development folds: train 2020/21–2021/22, evaluate 2022/23; then train 2020/21–2022/23, evaluate 2023/24. Every transformation and weight uses only the respective training data. Refit the incumbent's fixed architecture on identical training windows for comparison.
2. Stage A, structural candidates: derived per-90 attacking rates, conditional-on-appearance performance, position/fixture interactions, minutes trends; shallow and moderately deeper regularised trees; one hurdle model separating appearance probability and returns conditional on playing; heavier candidate-pool weighting; stronger recent-season weighting. All derived features use the existing pre-deadline feature boundary.
3. Stage B, local refinement: at most four fixed variants around the best Stage A specification (tree size/training budget, regularisation, recency/candidate weights). Use development folds only. If Stage A offers no improvement, refinements still test the strongest structural family once.
4. Stage C, ensembles: a fixed set of 50/50 and 75/25 blends of the best two distinct development candidates and the incumbent/recency baseline. No model is chosen on audit results. Prefer lower candidate-pool RMSE, with MAE as tie-breaker. Record every trial, including rejected candidates.
5. Stop after these three reasonable families of work if the final stage improves development RMSE by less than 0.15%, or if no eligible promotion survives the final gates. If Stage C improves by at least 0.15%, allow one additional predeclared 25/75 blend refinement on development folds, then stop at the evidence boundary. Do not respond to a failed final test by trying another candidate on the same final data.

## Candidate promotion gates

- Development: at least 0.5% lower pooled candidate RMSE than v1; neither fold more than 0.5% worse.
- Historical audits: at least 0.5% lower pooled candidate RMSE; neither season worse by more than 0.5%; pooled MAE no more than 0.5% worse. A paired four-GW circular-block bootstrap must have its 95% interval for RMSE improvement above zero. Because the audit seasons were already seen, this interval is descriptive and does not erase selection bias.
- Points relevance: on a fixed, deterministic set of identical historically affordable 15-player squads, choose legal XIs/captains from one-GW forecasts each GW, then score actual historical returns. Require non-negative pooled improvement over v1. No hidden optimisation of evaluation squad seeds. This tests selection/captain decisions, not a full transfer/chip policy. Keep an unrestricted captain comparison as a separate diagnostic.
- Contemporary scoring: retain v1's minutes/DC modules unless separately justified; no silent post-test retuning. Evaluate full-score final 2025/26 GWs where a chronological DC fit is available. Full-score candidate RMSE must not worsen by more than 0.5%.
- Current 2026/27 GW1–5 corroboration: fit both core models only on completed prior seasons. With at least 150 predeclared eligible rows, require no higher candidate RMSE and no more than 1% worse MAE; otherwise mark the check inconclusive and do not promote on it. Only two GWs have three previous records, so disclose the small sample.
- Integrity: all existing and new leakage/reload/registry tests pass. Save all candidate metrics and immutable version artifacts. A rejected candidate receives an experiment ID, not a new approved model version.

## Point replay definition

At the first eligible GW in each audit season, generate 20 deterministic squads with two GKs, five defenders, five midfielders and three forwards, at most three per club and £100m budget. Candidate membership, weighted sampling and price estimates use only pre-deadline history. Use last-observed historical prices, not end-season or current-GW price fields. Prices are proxies for exact contemporaneous affordability and must be labelled accordingly. Random seed is fixed at 20260921. Hold each squad fixed for the rest of the season: this isolates lineup/captain quality. No transfer deductions or chips apply because none are used. Missing player-fixture rows score zero with the known blank/as-played schedule limitation. Expected-autosub effects are not included in selection; realised autosubs should be scored under legal formation rules. Report distributions across squads and seasons, not just the best squad.

## Version policy and limitations

Only an approved champion may be used by default. Newest file does not mean best model. Store a registry linking champion version, artifact hash, experiment evidence and previous champion. Keep v1 available for rollback. Finite historical evidence cannot ensure monotonic future performance. If no challenger passes, retain v1 and complete the current search with the concrete reasons; meaningful further progress then requires new independent GWs or new pre-deadline information, rather than unbounded tuning of reused tests.

## Grounding

- [Cawley and Talbot, JMLR](https://jmlr.org/papers/v11/cawley10a.html): repeated model selection can overfit validation criteria and bias performance estimates.
- [scikit-learn cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html): preserve temporal ordering for dependent observations and separate parameter selection from evaluation.
- [Nested validation guidance](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html): tune within an inner loop; assess the procedure outside it. Our already-inspected outer audits are explicitly not claimed pristine.
- [Ensemble methods](https://scikit-learn.org/stable/modules/ensemble.html): regularisation and model averaging motivate the bounded candidates, without guaranteeing improvement.
