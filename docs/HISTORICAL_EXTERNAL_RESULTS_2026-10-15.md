# Historical external-method results — 15 October 2026

A later [practical selection study](SELECTION_BENCHMARK_RESULTS_2026-10-15.md) adds
calendar-verified 220-panel replay, neutral owned squads, budgeted resets and
rolling transfers. This original forecast-error/181-panel report is preserved.

**Keep the approved model.** Two new independently fitted adaptations did not
beat the incumbent-method reference. A separate real archived external forecast
was also scored, with mixed metrics and different capture dates. None of these
results establishes an original-system overall ranking or a model promotion.

The [decision-relevance interpretation](comparison_interpretation.md) explains
v1's original-Dastan top-10 ranking win, the complete candidate-pool
non-appearance error decomposition, and why outcome-based exclusions cannot
establish general superiority. Original figures below remain unchanged.

## Shared 2025/26 retrospective reference fits

Frozen protocol: [HISTORICAL_EXTERNAL_PROTOCOL.md](HISTORICAL_EXTERNAL_PROTOCOL.md).
Train through2025/26GW19, validationGW20–27, evaluationGW28–38; exactly
9,043fixture rows/8,713player-GWs, primary2,312snapshot-known candidates.
Prior incumbent/native/conditional predictions were reused without refitting.

| Named method | Candidate RMSE | MAE | Bias | Spearman | NDCG10 | Mean fixed-squad points |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Incumbent-method reference | 2.97780 | 2.25493 | +0.08593 | 0.38965 | 0.47252 | 43.674 |
| Native-window HGB adaptation | 2.95586 | 2.24939 | +0.20469 | 0.42446 | 0.41481 | 43.282 |
| Dastan-architecture adaptation (prior run) | 2.95404 | 2.18962 | -0.01070 | 0.42047 | 0.38433 | 43.050 |
| OpenFPL cv1 chronological median10 adaptation | 3.01932 | 2.34308 | +0.24204 | 0.34812 | 0.38936 | 43.381 |
| AIrsenal-inspired conjugate/Poisson adaptation | 3.04175 | 2.27888 | +0.08557 | 0.35237 | 0.38662 | 42.724 |

OpenFPL-adaptation RMSE was1.395%higher than the incumbent reference; the
component-adaptation RMSE was2.148%higher. Both also worsened primary ranking.
Descriptive paired4GW-block95%RMSE-difference intervals versus incumbent:
OpenFPL[+.02696,+.05956], component[+0.01555,+0.11898]. These condition on
fixed predictions and reused outcomes; they do not include training/selection
uncertainty or certify future performance. No extra seeds, parameter searches,
calibration trials, promotion tests or binary saves followed the results.

Twenty squads were frozen before fitting from GW28inputs, then held across11GWs.
181/220squad-week panels had complete shared predictions/outcomes;39are explicitly
ineligible. The means above use identical181panels, not selected favourable runs.
The replay excludes incomplete panels rather than inventing blank/player returns.
It is conditional on coverage, correlated and retrospective; it is not a full
transfer/chip strategy backtest, certified blank-GW handling, or season-points gain.

The reduced OpenFPL adaptation preserves40published cv1 member configurations
and positional196/206feature schemas, with chronological splitting, no search,
training-only scaling/weighting and median aggregation. It replaces the original
fivefold club-CV50member-per-position ensemble. Older availability is unknown,
the input reconstruction/scoring/environment differ, and current full points
include defensive contributions. Thus this does not say original OpenFPL is worse.
Quantile bin collapse warnings are retained; no outcome-driven bin changes were made.

The component adaptation uses AIrsenal-inspired closed-form involvement and recent
minutes, but replaces its bpl-next/NumPyro Dixon–Coles team model with regularised
Poisson, pools residual points and changes time/history conventions. Team/pooled
priors are training-only; individual counts use only prior available match data.
It does not benchmark the complete AIrsenal system. Full assumptions and limits
are in the pre-fit protocol, not hidden behind original project names.

## Measured compute and storage

The initial two-reference run, feature reconstruction and fixed-squad diagnostics took **105.48seconds**, peak sampled process-group RSS **1.555GiB**, twoCPUthreads.
A scoring-only engineering repair then took **32.60seconds/0.762GiB**, reusing the
frozen40OpenFPLforecasts without refitting. Total supervised computation was
**138.09seconds** across both jobs. The corrected component results are shown above.
Feature reconstruction took25.36seconds. Forty OpenFPL
members fitted serially; no published binary collection was downloaded.
Their total fitting time was71.70seconds and prediction batches0.082seconds.
Corrected component fit0.653seconds, prediction3.425seconds.
Prediction timings exclude upstream source refresh and shared feature construction.
The job used the already isolated XGBoost3.2.0 research runtime; ordinary forecasting
dependencies/weights are unchanged. No GPU, remote compute, paid service, heavy
ensemble search or future-gameweek wait was needed. Sampled monitoring is not a
hard OS quota. Project growth within the supervised job was under2MiB; private
raw/frozen/champion evidence is retained.

## Separate archived external forecast: completed 2026/27 GW6

A newly inspected project, [fpl-forecast](https://github.com/daniel-mehta/fpl-forecast),
publishes versioned forecasts. The CSV at frozen commit
[f76514676147dad7e6d7e247576c9d19ce90b330](https://github.com/daniel-mehta/fpl-forecast/tree/f76514676147dad7e6d7e247576c9d19ce90b330/data)
is319,715bytes; SHA256matches its frozen manifest. Stable player codes and
positions reconcile with independent official snapshot identities. Its Git commit
records22September11:07:20UTC; generated forecast22September11:06:58UTC.
The saved approved-model forecast was generated9October17:12:50UTC; both precede
the10October10:00UTCdeadline. Different information cutoffs are material.
Git metadata/publisher declarations are not independent clock/training certification.

All562external players match among667saved model predictions; all226pre-outcome
candidate players are covered. The cohort is fixed by the saved model, not by
realised minutes/points. Missing105external players are not filled or silently
counted as zeros. Official outcomes were already finalised/checked.

| GW6 matched candidates (226) | Approved saved model | Original archived external forecast |
| --- | ---: | ---: |
| RMSE | 2.71269 | 2.81545 |
| MAE | 2.07980 | 2.04171 |
| Spearman | 0.32295 | 0.16855 |
| NDCG10 | 0.34363 | 0.39878 |

The external forecast has worse RMSE/Spearman but better MAE/NDCG in this single
gameweek. This secondary comparison was chosen after results existed; neither
the pair nor the metric winner was designated prospectively. No one-GW interval,
overall accuracy winner or season conclusion is warranted. It is separate from
the2025/26table and is not pooled into it. No forecasts or team decisions were
generated, no user squad/transfer/chip assessment was performed, and no existing
weekly evidence was overwritten. The new read-only adapter supports future
explicitly supplied archives; it does not enable automatic collection/retraining.

## Scoring repair and frozen evidence

Final review found a goalkeeper-goal rule defect in the new component reference.
FPL increased goalkeeper goals from6to10points in2024/25
([official source](https://www.premierleague.com/en/news/4059044)). The v2amendment
was committed before the corrected component fit; historical residual decomposition
uses each season's rule and2025/26prediction uses10. The original component run
is retained but invalid/superseded for this defect, not a candidate selected by
error. The corrected error is slightly worse and is reported regardless. Other
settings/squads/input rows are unchanged. No model or OpenFPL member was retuned.

Initial-run evidence:

| Item | SHA256 |
| --- | --- |
| Pre-fit manifest | `9077c8bf5822b8277dc810245e53021dfefa36b7aa362edeeb4ababec6fd93aa` |
| progress.jsonl | `91f729da3a0778699c1231a2ace5016bb2b7bdb1eedc6df89e0446b4fb5671c0` |
| predictions.csv | `be5cf98eff8430e936110070fe99436cdf995abd8f6bc2b429ef059fd03fade5` |
| results.json | `0117d1c59b4ec18899e8d583ce7b21a66126eeba9e81d56efd16f58cef2ad305` |

Pre-fit implementation commit2dfdcded839acd6e2025458d1cc80f5efe000b8d.
Raw source snapshots, input paths, private forecasts and individual rows stay
outside Git. The committed recipe contains only public feature/member definitions
and source hashes. Source-family admission/dispositions are in
[EXTERNAL_MODEL_ADMISSION_2026-10-15.md](EXTERNAL_MODEL_ADMISSION_2026-10-15.md).

Recurring future validation is a separate workflow, not a completion requirement
for this implementation package. The approved model and all promotion gates remain.

Corrected pre-fit source commitb78077b; full revision is recorded privately.

| Corrected v2 item | SHA256 |
| --- | --- |
| Manifest | `9ef3179e0dc5a938bd332978a29784e2170ad8e673908fbe705d930e6d753d4f` |
| progress.jsonl | `cb246cf8507655ae1dd5543e21d28a398b25ccc0ffe757907f0f311560f575c5` |
| predictions.csv | `862eab96bc6411ced5b990c80bb08397d8ad013ea243a69a7b1d81706dd7a916` |
| results.json | `b3a71e16dce4f84e2d798dbb7f25bed64be1f9cc64c793d618183c72fdbe54d2` |


## Availability follow-up — 16 October 2026

The [matched incumbent availability study and six-method rebenchmark](INCUMBENT_AVAILABILITY_RESULTS_2026-10-16.md)
now tests structured labels against the full participation method, followed by
unconditional points-feature augmentation on historical data. Appearance error
improves, but points MAE/ranking and owned/rolling decisions do not jointly pass
the progression checks. The challenger is unapproved; original-system comparisons
in this report remain unchanged. New aggregates/provenance/cost are linked above.


## Conditional integration follow-up — 16 October 2026

[The controlled four-arm integration/selection study](CONDITIONAL_SELECTION_RESULTS_2026-10-16.md)
now isolates old/new appearance probabilities with one shared conditional-return
model and current/expected bench selection. Points RMSE and MAE improve versus
the historical incumbent reference; ranking and the fixed combined selector do
not qualify. Matched external error/common-mean-policy results are reported,
including an observed but uncertain RMSE win over the Dastan adaptation. Original
system comparisons in this document remain unchanged. No model is promoted.


## Subsequent forecaster qualification — 16 October 2026

The [forecaster-only qualification](FORECASTER_QUALIFICATION_RESULTS_2026-10-16.md)
saves/reloads the fixed conditional candidate and tests current-input compatibility.
Older chronological development is nearly neutral; same-policy retained external
comparisons preserve the error advantage, but reset/rolling points favour the
standing reference. No new expected-selector adoption or model promotion occurs.
This follow-up does not rewrite the results or progression rules above.
