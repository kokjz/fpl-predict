# I3: lightweight open-source-inspired comparison

Predeclared 14 October 2026, before fitting. This is a bounded extension prompted
by new source research, not another unrestricted search of old test outcomes.

## Fixed methods and boundaries

Use the existing identity-free, deadline-safe feature whitelist and core points.
Do not import third-party model binaries or execute downloaded project code.
All implementations below are independent adaptations, not reproductions of the
named systems, whose features, training data and scoring differ.

1. Incumbent: refit the approved seven-leaf HGB specification on each fold.
2. Position specialists: four copies of the incumbent, one per position
   (OpenFPL's position-specific decomposition).
3. Minutes mixture: a three-state classifier (no appearance, 1–59, 60+ minutes)
   and conditional regressors for the two playing states (Dastan-inspired
   participation composition). Class states are training labels, never inputs.
4. ExtraTrees: 128 trees, depth 12, minimum leaf 40, half the features per split,
   two workers (cheap diversity inspired by forest/tree ensembles).
5. Exactly one 50/50 blend of each challenger with the incumbent: six challengers
   total. No further hyperparameter, feature, seed or blend-weight search.

Train 2020/21–2021/22 -> evaluate 2022/23, then train through 2022/23 -> evaluate
2023/24. Drop later seasons before any training/selection computation. Two-year
age weighting; no random early-stopping split. Imputation fits training only.
Primary: pooled candidate-fixture core RMSE using n_history>=3 and lagged
last-five minutes>=45. Also report MAE, each fold, player-GW aggregation and
within-GW ranking. Actual 60+ minutes is a diagnostic cohort, never selection.

Development gate: >=0.5% lower primary RMSE; neither fold RMSE nor pooled MAE
>0.5% worse. Lock the single best eligible candidate. Only if one passes, repeat
that candidate at two additional fixed seeds (7, 2026); require the mean gain
still >=0.5%. Then apply ALL existing I1 historical/full-score/points/current
corroboration/integrity promotion gates once. Previously inspected audits stay
labelled reused, not untouched. Do not retry another finalist on failed audits.
No candidate automatically promotes. If none passes, stop; leave champion intact.

## Resource and evidence limits

Two native computation threads, two forest workers; no GPU, cloud or new library.
Whole development search target <=600 seconds and peak process RSS <=2 GiB.
Each challenger must forecast 1,000 fixtures in <=1 second, measured after
feature preparation. Budget checks run between bounded fits; they are soft
stopping limits, not an OS sandbox or a guarantee against transient overruns.
Record runtimes, RSS, package versions, input hashes and protocol/source hash.
Stop on budget breach; do not promote incomplete runs. Freeze outputs in a new
directory and refuse overwrites. Do not load or score current-season forecasts.

Training/reference fixtures are public historical football records, not a real
manager's squad. Code and aggregate results may be public; data, individual
predictions and fitted artifacts remain in the external runtime workspace.
Better historical error does not prove better season points.

## Grounding

- https://github.com/daniegr/OpenFPL and https://arxiv.org/html/2508.09992v1
- https://github.com/qazybekb/smartplayfpl-dastan/blob/main/docs/METHODOLOGY.md
- https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html
- https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html
- https://scikit-learn.org/stable/modules/cross_validation.html
