# Pre-evaluation protocol — v1

Written 21 September 2026 before fitting or evaluating candidates. Goal: an acceptable, reproducible first forecasting model for decision support, not proof of an optimal full-season strategy. Source/schema inspection has occurred; model performance has not been inspected.

## Scope and splits

- Supervised pattern learning pooled across players; never feed player name or ID as a predictive feature. IDs only connect a player's earlier observations. No reinforcement-learning agent or synthetic reward optimisation.
- Core forecast target: historical FPL points excluding the separately modelled defensive-contribution award. Other historical scoring-rule changes remain a documented domain-shift limitation.
- Core development training: 2020/21–2022/23. Validation/model selection: 2023/24. Final held-out seasons: 2024/25 and 2025/26. Select candidate and blending only on validation; freeze them before opening final scores. For the second test season, refit the chosen specification on all preceding seasons without retuning. Final deployment may refit on all completed seasons after testing; do not label its in-sample fit a holdout result.
- Defensive contributions exist only in 2025/26 archive: train GW1–19, select GW20–27, test GW28–38. Consequently, full contemporary scoring has a shorter independent test than the core forecast. Exclude these features entirely from core candidate selection to avoid pretending older seasons contain them.
- Save split manifests and immutable raw-source hashes. Disjoint player-match keys and date cutoffs are required.

## Leakage controls

- Derive each historical cutoff from the earliest kickoff of its GW, minus 90 minutes. This is a conservative reconstruction, not a preserved original schedule snapshot. Only earlier matches completed at least 3 hours before the cutoff are eligible as features. Both matches of a double use the same pre-GW history. Use timestamps rather than numeric round ordering for rearranged games.
- Freeze features for the whole GW before incorporating any of its outcomes. Ban archived xP, current-match minutes/actions, future season totals, end-season strength, value/ownership/transfers and scraped current injury flags as predictors.
- Position and team describe that season/fixture. Exclude assistant managers. No future player identities or cross-season name joins are needed for fitting.
- Recent player/team outcomes have exponentially decaying weights (4- and 12-match half-lives) and priors for short histories. Training sample weights decay by age, using the training end date only, with a two-year half-life. No decay age based on test outcomes.
- Scaling/imputation/parameters fit only on training. Early stopping must not silently use randomly sampled later rows; fixed training budgets instead.
- Historical final corrections and fixture assignments are not perfectly preserved as-of data. Report this residual archival limitation. Never claim a completely reconstructed historical news/price trading strategy.

## Fixed candidate budget and baselines

- Baselines: last-five-match mean core points; recency-weighted core points with the same history boundary.
- Candidate core models: regularised linear regression and a small fixed set of histogram gradient-boosted regressors, with optional validation-selected blends with recency baseline. Use validation candidate-pool RMSE as primary selection metric; MAE as tie-breaker. Do not expand the search using final test results.
- Candidate pool is defined before outcomes: at least three earlier fixture records and last-five mean minutes of at least 45. Report all-player and position slices separately.
- Minutes/appearance probabilities and defensive-award probability get separate validation/Brier checks. Prediction intervals are empirical validation residual intervals; measure their held-out coverage and label their limitations.

## Acceptance for a first decision-support release

1. Raw-data integrity, no duplicate player-fixture keys, chronological split assertions and adversarial leakage tests pass. Forecasts and saved model reload reproducibly. Legal XI/captain selection and confirmed blank/double handling are tested.
2. Pooled held-out core candidate RMSE improves at least 1% against last-five mean; in each test season it is no more than 2% worse than the recency-weighted baseline. Report MAE as well, including any trade-off.
3. Candidate captain selection is evaluated on the same ex-ante pool for each method, using observed returns and GW-block bootstrap uncertainty. Positive realised captain gains are not required because this is a noisy secondary metric; material negative evidence must be disclosed and constrain usage.
4. For newer scoring components, disclose independent sample size and compare calibrated probabilities with simple recency baselines. Use the validation-selected baseline if ML is worse. Full-scoring test is distinct from core scoring test.
5. Produce current squad + candidate forecasts from current official data, expose minutes/injury assumptions, and supply a repeatable refresh/planning interface. Current-rule probabilities not independently validated remain explicitly labelled.
6. Document cost, training rows/seasons, measured errors, uncertainty, limits and a continuing prospective pre-deadline evaluation workflow. The model becomes an input to weekly and season planning, with human news checks; no account actions or paid services.

Failure is reported rather than changing these thresholds after seeing holdouts. Any later model redesign requires a newly labelled experiment and a fresh future test; the old test is no longer untouched.

## Research grounding

- [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html): split before fitting preprocessing; keep test data out of model choices.
- [Historical archive](https://github.com/vaastav/Fantasy-Premier-League): xP timing warning and discontinued weekly updates; retain our own current snapshots.
- [OpenFPL](https://arxiv.org/html/2508.09992v1): motivates pooled pattern learning and comparing forecasts against both simple and stronger baselines. Does not guarantee our results.
