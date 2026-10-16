# Forecaster-only qualification results

16 October 2026, Asia/Singapore. **The conditional forecaster is now persistable
and compatible with current API inputs, but does not qualify to replace v1.0.0.**
Its 2025 point-error improvement remains valid; broader decision evidence is mixed.
A small credible gain can justify adoption. This conclusion does not impose a
new ranking veto or establish that every conditional forecast is inferior.

[Aggregate evidence](FORECASTER_QUALIFICATION_RESULTS_2026-10-16.json) ·
[Protocol and reproduction](forecaster_qualification.md) ·
[Earlier four-arm study](CONDITIONAL_SELECTION_RESULTS_2026-10-16.md)

## Fixed candidate and qualification

One predeclared candidate: PR26's new conditional forecaster with the existing
mean selector. No expected-bench policy, new blend, threshold or parameter search.
The protocol/source was published before new fits. Existing promotion criteria
remain in force: two earlier development folds, two audit seasons, paired error
uncertainty, points relevance, full scoring, contemporary corroboration and
integrity. NDCG is diagnostic in this forecaster-only package. This does not
retroactively change the preceding experiment's failed ranking progression.

Candidate selection already used inspected 2025 outcomes. Every comparison is
retrospective, and descriptive intervals exclude training/selection uncertainty.
Historical standing-model comparisons use the same architecture refitted on
identical earlier rows, not the deployed artifact trained on later outcomes.

## Stage 1: older chronological development

| Candidate player-GW core errors | Standing RMSE | Conditional RMSE | Standing MAE | Conditional MAE |
|---|---:|---:|---:|---:|
| 2022/23, 7,222 rows | 3.06502 | 3.07071 | 2.22815 | 2.23284 |
| 2023/24, 7,385 rows | 3.09440 | 3.08853 | 2.19989 | 2.19080 |
| Pooled, 14,607 rows | 3.07991 | 3.07974 | 2.21386 | 2.21158 |

Pooled RMSE improves **0.0056%**, not 0.56%. One season worsens by 0.186%,
the other improves by 0.190%. Both meet the per-fold 0.5% stability bound, but the
pooled gain fails the existing 0.5% development requirement. There are no admitted
news labels in these older seasons; signals are explicitly missing. This tests
the fallback, not the benefit of known news in 2025.

No admitted external forecasts cover these folds, so external accuracy is
unavailable rather than fabricated. The failed development check stops expanded
2024/25/full-2025 audit fits, new current-season performance fits and final
production refitting. Those standing gates remain untested, not passed. This is
not evidence that availability information has no value. It limits the case for
replacing a forecaster that must also operate with missing inputs.

## Stage 2: artifact and current-input compatibility

The fixed 2025 model is saved as a trusted local research artifact, with exact
reload parity. Its 15,572 fixture forecasts differ from PR26 by at most 1.78e−15.
Training uses the same 147,500 earlier rows, including 60,955 appearing core rows
and 5,782 observed appearing DC rows. Appearance learns structured availability;
conditional core/minutes have no availability covariates. The rare zero-minute
card prior remains training-only and shared. Conditional minutes times learned
appearance yields expected minutes; the same fixed unconditional sixty-minute architecture is capped
at appearance probability. These auxiliary forecasts require separate validation.

The artifact is 1,263,550 bytes. Five learner fits take 35.42s; inference on
15,572 fixture rows takes 0.10s. Empirical core residual intervals use only the
inspected development window, not audit targets, and are not multiweek confidence
intervals. The artifact remains outside the public repository and approved registry.

An archived pre-GW6 official API snapshot produces finite coherent outputs for
1,334 fixture rows in 0.087s model/availability inference. Of 667 next-GW rows,
306 have known chance labels; the other 667 later-GW rows use missing availability.
No squad was read, no planning was run and no current forecast values were saved.
This is compatibility testing, **not current-season performance corroboration**.

Official percentages enter a learned model as covariates, never as assigned start
probabilities. The adapter verifies snapshot identity/hash, explicit source times,
predeadline timing, positions and next-GW scope. Duplicate/unknown IDs, late
sources, invalid chances and clock conflicts fail closed. The existing mean
selector and sourced manual sensitivity precedence remain unchanged. Forecast
provenance adds `learned_availability` (null for legacy models), with model-source
hash/caveats when active; existing numeric legacy predictions are unchanged.

## Stage 3: same-policy external and practical comparisons

All methods share the retained 2025/26 GW28–38 cohort: 9,043 fixture rows and
2,312 candidate player-GWs. No external model is refitted. The same admitted
listed market, predeadline quote times, source cutoffs, independently verified
blanks and neutral squads are reused. Newer availability observations can precede
the deadline while postdating a quote; this is equal deadline, not equal feeds.
The 23 forecast player-GWs outside the earlier listed audit roster stay in error
metrics and are uniformly excluded from selection, as before.

| Candidate player-GW forecast | RMSE | MAE | NDCG@10 |
|---|---:|---:|---:|
| Standing-method reference | 2.97780 | 2.25493 | 0.47252 |
| Conditional forecaster | **2.94125** | 2.23845 | 0.44639 |
| Native-feature adaptation | 2.95586 | 2.24939 | 0.41481 |
| Dastan-architecture adaptation | 2.95404 | **2.18962** | 0.38433 |
| OpenFPL cv1 adaptation | 3.01932 | 2.34308 | 0.38936 |
| AIrsenal-inspired component | 3.04175 | 2.27888 | 0.38662 |

The conditional model has 1.23% lower RMSE and 0.73% lower MAE than the standing
reference. RMSE is 0.43% lower than the Dastan adaptation, with paired difference
interval [−0.0348,+0.00784], crossing zero. Its MAE is worse than that adaptation:
difference +0.04883, interval [+0.02437,+0.07159]. These are named adaptations;
there is no fresh original-Dastan/OpenFPL system-superiority claim.

| Same mean selection policy | Owned points/GW | Budget reset points/GW | Rolling episode points |
|---|---:|---:|---:|
| Standing-method reference | 37.174 | **69.182** | **624.667** |
| Conditional forecaster | **37.242** | 63.455 | 611.167 |
| Native-feature adaptation | 36.841 | 63.909 | 557.500 |
| Dastan-architecture adaptation | 36.568 | 59.273 | 547.667 |
| OpenFPL cv1 adaptation | 36.606 | 58.636 | 537.500 |
| AIrsenal-inspired component | 37.129 | 60.909 | 552.833 |

Owned selection repeats 12 fixed neutral squads over 11 GWs. The conditional
model's +0.0682/GW gain reproduces all 132 previous new-mean panels. The full
six-method simultaneous block-4 interval is [−0.7955,+0.9318]; it is wider than
the earlier exploratory single-contrast interval because it covers all method
comparisons together. Both are inconclusive. Reset difference −5.7273/GW also
has a wide simultaneous interval [−14.8227,+3.3682]. Reset is an independently
optimised £100m squad each week; it is a secondary test, not a playable season.

Rolling uses six fixed opening squads per method and the same budget, legal
transfers, purchase/sale accounting, free-transfer cap and hit rules. Conditional
forecasts yield **13.5 fewer episode points** on average than the standing method,
while exceeding retained external adaptations. One path-dependent eleven-GW
window does not provide independent season replications or prove future losses.
These decision losses explain why lower overall RMSE is insufficient to establish
a better global planning engine; they do not invalidate measured error gains.

## Integrity, cost and outcome

Independent checks reconcile all 1,254 decisions, 36 rolling paths, 811 transfers,
12 development error metrics and 132 preceding conditional owned panels. All
1,045 standing/external actions retain the same players, selections and realised
scores (expected floating values agree within 1e−12). Scenario schedules match.
A stable-key public adapter and shuffled-row regression prevent positional joins.
An initial secondary replay exposed exactly that preparation error and was
invalidated in full; the corrected replay changes no model, seed, policy, quote
or outcome. The invalid evidence is retained, never treated as model performance.

Canonical supervised jobs take 127.17s combined, peak sampled RSS 1.55GiB, two
CPU threads; the invalid replay adds 32.64s. No GPU, paid compute, remote fitting
or large data download is needed. Storage, free space, memory and time are
monitored. Actual environment is Python3.12.14/NumPy2.3.5/pandas2.2.3/sklearn1.9.1;
NumPy/pandas differ from current package pins, and artifact portability is not
assumed. Source-only tests do not retrieve or redistribute historical data.

**Do not promote.** Development fails; complete multiseason/current performance
checks are not established; practical secondary results favour the standing
method. Save the candidate as research evidence and retain approved v1.0.0.
Merging compatible code does not install this artifact or authorise a forecast.
A narrowly scoped deployment or fallback redesign would be a new hypothesis,
with its own evidence plan, not a silent threshold change or extra search here.
Future frozen weekly review remains maintenance, not a completion dependency.
