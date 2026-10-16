# Approved model and validation limits

Approved engine model: v1.0.0. Artifact SHA256: `789e8849922116d989584ccfcb912082bb96201cb5af80ce9e70823e047fe233`. The runtime registry checks status, workspace containment and exact artifact bytes before use. Binaries and historical datasets are not included in this repository.

The original deployment fit used 163,072 public player-match records across 2020/21–2025/26. Core development/selection preceded expanding-window audits on 2024/25 and 2025/26; the deployed all-season fit is not itself a holdout. Strictly lagged player/team features have four-/twelve-match half-lives, and training records have a two-year age half-life. Player identity and same-match outcomes are excluded from predictors.

Original pooled candidate core RMSE was 2.900 versus last-five 3.175 and recency 2.982; MAE 2.101 versus 2.365 and 2.108. These are historical core-point measurements, not guaranteed contemporary full-score performance. The separate contemporary defensive-contribution/full-score test covers only eleven gameweeks. Historical assist/BPS/rule changes and incomplete as-of archives remain limitations.

A captain-bonus replay had +56 versus last-five and -19 versus recency across seventy gameweeks; uncertainty intervals included zero. No reliable captaincy or full season-management advantage was established. Forecast-error improvements do not imply the same percentage increase in FPL points.

Twenty-one development challengers were not promoted. A newer experiment filename or merged source commit is never sufficient to replace the champion. Promotion requires the explicit gates in model_registry.py and future independent evidence. Published audit outcomes must not be repeatedly searched and still labelled untouched.

Repository tests validate leakage resistance, legal selection, metadata/artifact integrity, frozen outcomes, runtime isolation and privacy checks. Four optional local-data integration checks are not exercised on a source-only checkout. They require explicitly prepared local datasets/artifacts; no such data or real squad is downloaded in CI. Packaging introduces no retraining, model promotion or current-gameweek forecast.


## Availability study — 16 October 2026

[Results and complete gates](INCUMBENT_AVAILABILITY_RESULTS_2026-10-16.md): a fixed
source augmentation improves appearance Brier against the full incumbent method,
but the full-points challenger fails audit MAE/ranking and loses owned/rolling
point means. Retain v1.0.0. This is historical research on already inspected
windows, not an untouched test or proof of general superiority. Historical
training/testing and external replay complete the package; future frozen weekly
evaluation is ongoing maintenance, not a completion dependency. No automatic
retraining, model installation or migration follows from these commands.


## Controlled conditional integration — 16 October 2026

[Full results](CONDITIONAL_SELECTION_RESULTS_2026-10-16.md) separate shared
conditional returns, old/new appearance heads and mean/expected bench selection.
The new appearance arm improves historical RMSE/MAE, but the frozen development
ranking guard fails and combined owned points do not establish superiority.
Only the declared new-expected finalist was considered; no post-test promotion of
new-mean. Existing promotion gates and approved v1.0.0 remain unchanged. All
completed-window results, sensitivities, failed admission and superseded replay
are retained. Historical data completes this package; no future-match wait.


The [forecaster-only qualification](FORECASTER_QUALIFICATION_RESULTS_2026-10-16.md)
uses standing development/multiseason/current/integrity checks, with NDCG a
separately reported diagnostic. Older development gains only0.0056%, below the
existing0.5% requirement. Untested expanded gates are not passed. Current API
compatibility is not current-season accuracy evidence. Owned points improve
slightly while reset/rolling totals fall; no artifact or selector promotion.
