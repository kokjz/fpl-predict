# Dastan-architecture rebuilt-input reference — pre-fit protocol

Declared15October2026 before this reference fit. Method:
`dastan-architecture-cutoff-gapmask-xgb320-v1`. This independently adapted,
attributed reference uses published head structure/hyperparameters, not released
weights or the native released feature parquet. It is **not original Dastan**,
not an I4 finalist, not a promotion experiment and not an unviewed test.

## Frozen inputs, splits and comparisons

Reuse the independently rebuilt286native predictors, raw-source gap mask and
snapshot contract in [the native protocol](NATIVE_REFERENCE_PROTOCOL.md). All
163072fixture rows remain, including2mapped training appearances with unknown
statistics and25unmapped appearances; no outcome-based coverage exclusions.
The seven snapshot fields are missing(-1) before2025/26. Source arrays remain
unknown where missing; **inside this published-method learner only**, fill numeric
NaNs with0 as the upstream architecture does. This is a declared model transform,
not a claim that missing raw statistics were zero. No four pooled-role flags:
each position is trained separately, as in the published architecture.

Train2020/21–2024/25 plus2025/26GW1–19; validationGW20–27 for early stopping,
band calibration and direct blend selection; testGW28–38. No validation refit.
No observation-age weighting, matching the inspected upstream trainer; this is
a whole-method contrast, not an isolated architecture-only causal experiment.
Freeze all keys/cutoffs/raw/feature/code/environment hashes before fitting.
Independent target/cohort/source checks must pass before any head is fitted.

Primary2312snapshot-known candidate player-GWs on the exact frozen reference
keys; candidate season-history>=3and last5mean minutes>=45. Also all candidates
and all players. Compare frozen training-only incumbent-method predictions and
the existing native-window HGB pilot on identical full-score keys/actuals. Sum
double fixtures before scoring. Report RMSE/MAE/bias/Spearman/NDCG10 and paired
four-GW descriptive intervals. No new captain/transfer/season-policy claims.

## Published architecture and fixed selection

Four positions,8heads each=32fits:

- Binary60+minutes classifier on all training rows.
- Under60conditional points regressor on under60training rows.
- Four-band classifier on60+rows; point-band edges1,3,10.
- Four conditional band regressors on60+rows in each band; if training band<=10,
  use all60+training rows, matching the upstream fallback.
- One direct all-row points regressor.

XGBoost3.2.0,CPUhist,max_bin256,two threads,seed42. Classifiers:2000maximum
trees,lr.014251,depth7,subsample.6364,colsample.6427,min_child_weight17.89,
lambda1.3015,early-stop30. Regressors:6000maximum trees,lr.035966,depth6,
subsample.7366,colsample.6553,min_child_weight8.29,lambda.2567,early-stop90.
Early stopping uses corresponding validation population when>=50rows; under60
or band-classifier fallback uses allvalidation, band-regressor fallback uses all
60+validation. Train/validation class coverage is checked before fitting; no
silent new class fallback or changed training configuration. Prediction uses the
library's best iteration, verified in a small integration check.

Calibration: choose gamma(.5,.75,1),band0weight(1,1.25,1.5,2),band1weight(1,1.25),
other weights1 by validation60+log likelihood, once per position. Select direct
blend weight0,.05,…,.5 by mean within-GW .5Spearman+.5NDCG10 on aggregated
validation player-GWs with>=20players. Preserve upstream stable-tie NDCG and raw
gains for this **internal selection**; shared final evaluation uses the existing
clipped-gain/tie-averaged metric for every compared method. Clip conditional/direct
predictions at0 as upstream does; mix using p60and calibrated band probabilities.
No test-driven calibration, blend/parameter changes, extra seeds or reruns for
accuracy. Published selection grids are part of one fixed reference method.

## Cost and admission boundaries

One serial supervised reference,2threads,4GiB observed RSS,30min total method
budget,512MiB project growth/2GiB project cap/5GiB free headroom. Record each head's
fit time,best iteration,training/validation sizes and whole-job cost. A cap or
failed head yields an incomplete **unranked** reference, not a truncated model.
Do not automatically move it to another device or expand its budget. No binary
save or registry writes. Optional dependency is explicit; weekly/default tests
must not import/require XGBoost. No production dependency replacement.

Source feature repair, missing older snapshots/source gaps, modified software
environment, historical provider corrections and incomplete publication/kickoff
proof mean `benchmark_eligible=false`. All outcomes already viewed. This can
compare named retrospective methods under one disclosed regime; it cannot claim
to beat the publisher's original deployed system. Original OpenFPL archive still
endsGW24 and lacks sufficient exporter/training/capture lineage for this later
window; no backward application of shipped current weights or invented forecasts.

## Primary sources and attribution

- [Pinned Dastan model](https://github.com/qazybekb/smartplayfpl-dastan/blob/758db9247e8b3a9a870c991064f74d8339d61cd0/dastan/model.py)
- [Hyperparameters](https://github.com/qazybekb/smartplayfpl-dastan/blob/758db9247e8b3a9a870c991064f74d8339d61cd0/models/hyperparameters.json)
- [Environment](https://github.com/qazybekb/smartplayfpl-dastan/blob/758db9247e8b3a9a870c991064f74d8339d61cd0/requirements.txt)
- [XGBoost early-stopping prediction behaviour](https://xgboost.readthedocs.io/en/release_3.0.0/python/python_api.html)
- [MIT attribution](../THIRD_PARTY_NOTICES.md)
