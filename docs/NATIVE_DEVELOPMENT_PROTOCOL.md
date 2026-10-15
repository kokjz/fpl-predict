# I4: richer-history development study — pre-fit declaration

Declared 15 October 2026 before any I4 model fit or score. This study isolates
newly reconstructed history inputs, then one participation composition. It does
not tune on the inspected 2025/26 GW28–38 window or approve a new model.

## Fixed comparison

Two expanding folds: train 2020/21–2021/22, evaluate 2022/23; train through
2022/23, evaluate 2023/24. Discard all later records before feature construction,
fitting and scoring. All these seasons are already viewed development evidence.
Full historical points equal core points in these seasons; independently require
that equality. Never rescore old seasons with unavailable defensive actions.
The source archive has no2022/23GW7 fixtures (the wholly postponed round).
This explicitly permitted empty week is not fabricated as a played prediction;
fixed-squad replay awards zero and block intervals preserve the calendar gap.
All other development weeks must be present. This correction is pre-fit.

Control: one refitted incumbent seven-leaf HGB core model on the existing
checksum-verified pre-deadline features, same training rows and age weights.
This is the incumbent method, not the deployed all-seasons trained binary.

Exactly three challengers, no blends/search/refinement:

1. `fpl_windows`: independently rebuilt FPL player form, venue history,
   team/opponent goals and league context, lagged participation, starts and
   deadline-based rest/congestion, with fixed position indicators.
2. `rich_windows`: the same plus Understat player and team/opponent histories.
   Comparing1→2 isolates that additional data bundle.
3. `rich_participation`: exactly the rich inputs, a three-state no-appearance /
   1–59 / 60+ classifier, two conditional points regressors, probability-weighted
   expectation. Comparing2→3 isolates architecture. The earlier I3 composition
   failed on the smaller incumbent inputs; this retest is specifically motivated
   by the richer histories, not another trial of the same specification.

All regressors and classifier:7leaves,200iterations,learning rate0.05,L2=20,
min leaf60,early stopping disabled,seed20260921,two threads. Two-year observation
age half-life, calculated from training only. Conditional negative returns remain
valid; clip only final fixture expectation to[0,20]. No state label is an input.
No historical snapshot/news/price/ownership predictors or unavailable defensive
features in any challenger. Old missing raw numeric statistics stayNaN. Stable
FPL codes connect history, never enter a learner. Prefix histories use strict
deadline−3h cutoffs, including opponent/global league context. Snapshot frame is
empty by design. Required mapped played observations cannot have unknown source
statistics; unmapped people retain unknowns and remain in the evaluation universe.

## Evaluation, gates and stop

Primary pooled candidate player-GW RMSE, requiring>=3prior season-history records
and last-five mean minutes>=45, identical across methods. Also require the old
candidate-fixture gate to avoid passing through a metric change. Both fixtures
of a double share the cohort/cutoff; aggregate before player-GW scoring.

Report candidate/all-player errors, MAE,bias,NDCG@10,Spearman,position errors,
actual-minute and cold-start diagnostics, and descriptive paired four-GW-block
error intervals. Actual minutes never choose the candidate population.

Before fitting, generate/hash the same20deterministic squads per fold using the
existing fixed-squad procedure, seed20260921, first eligible GW, last-observed
predeadline prices,£100m,legal15positions/three-per-club. Hold squads fixed; legal
XI/captain selection and realised autosubs/vice fallback. Price proxies and final
as-played schedules are limitations. No transfer/chip/season-policy gain claim.

Development eligibility requires>=0.5% lower pooled candidate player-GW **and**
fixture RMSE than control; neither fold's two errors nor pooled two MAEs may
worsen>0.5%; pooled mean within-GW NDCG@10 may not fall; mean fixed-squad point
delta must be nonnegative across both folds. Choose only the lowest primary
RMSE eligible finalist, MAE tie-break. If none passes, stop I4 without promotion,
extra seeds or later-audit scoring. If one passes, lock it before predeclared
stability checks/separate unchanged promotion gates. Descriptive intervals do
not remove prior selection/test reuse. No automatic registry write or binary save.

## Frozen inputs and resources

Offline plain numeric CSVs: canonical players/teams from the previously audited
source joins and a separate control export with stable code/fixture/GW identities,
target,metadata and actual incumbent features/source maxima. Control input
provenance records verified raw-file and trusted-cache hashes; no pickle is loaded
by this command. Require exact key/target/minutes/position/cutoff/candidate parity,
all fold weeks, temporal separation and source-time assertions before fitting.
The source preparation and manifest lock happen before the first fit/score.
All controls/panels/feature lists/code/environment/input hashes freeze in a
write-once manifest. Frozen predictions and panels remain outside Git.

Serial supervised two-thread batch,4GiB observed RSS,2hour maximum batch,
512MiB project-growth/2GiB project cap/5GiB free disk headroom. Check resource
limits throughout; failure is incomplete, not a valid score. No paid services,
GPU, optional third-party model dependencies, or new raw-data collection needed.
One HGB pilot's runtime is not a guarantee for this entire study. Save per-fit
timings, prediction cost and all failures; do not repeat failed configurations.

## Grounding

- https://scikit-learn.org/stable/modules/cross_validation.html
- https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html
- https://github.com/qazybekb/smartplayfpl-dastan/blob/758db9247e8b3a9a870c991064f74d8339d61cd0/docs/METHODOLOGY.md
- [Native input implementation and attribution](native_reference.md)
