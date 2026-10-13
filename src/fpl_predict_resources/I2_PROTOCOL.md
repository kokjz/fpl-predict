# Experiment I2 — chance-quality target smoothing

Declared after I1 concluded with no eligible finalist, before I2 fitting. I1's best development RMSE gain was 0.1334%, below the 0.5% gate, and its exploratory fixed-squad points comparison was negative in both development seasons. No reused audit or 2026/27 terminal comparison was opened.

This is a distinct hypothesis: goal and assist outcomes are noisy labels; partial substitution with xG/xA may improve estimates of average returns. [StatsBomb's expected-goals explanation](https://blogarchive.statsbomb.com/articles/soccer/upgrading-expected-goals/) motivates using chance quality. It does not prove that this proposed FPL target transformation helps. Validate against actual FPL points, not against the transformed target.

For training rows only, define a proxy by replacing part of the observed outfield goal/assist score with its xG/xA equivalent. All remaining core-point components stay as observed. Apply only when both xG and xA are available and the player is an outfielder. Older rows without underlying stats and goalkeepers retain the original target. No match outcome or current-match xG enters predictive features. Negative target values remain valid for squared-error regression.

Test exactly four candidates, on the same two earlier forward folds as I1: 25%, 50% and 75% target substitution using the exact v1 architecture; and 50% substitution with I1's engineered feature transformation. No sweep beyond these four. Choose on development RMSE/MAE only. The same 0.5% development and subsequent audit/points/current-season/integrity promotion gates apply unchanged. If none qualifies, retain v1 and stop the present improvement goal: structural changes, regularisation, recency, hurdle modelling, ensembles and this separate label-noise hypothesis have been reasonably tested with the available information. New independent GWs or timestamped team-news/minutes information is the next useful source of progress.

This development set has been reused and optimistically selected scores are explicitly exploratory. Do not call them new independent tests. No further candidate is tried in response to a final-audit failure.
