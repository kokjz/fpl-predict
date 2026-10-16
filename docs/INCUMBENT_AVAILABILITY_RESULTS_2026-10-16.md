# Structured availability: incumbent ablation and external rebenchmark

16 October 2026 (Asia/Singapore). **Structured availability improved historical
appearance forecasts against the full incumbent method. The resulting points
challenger did not qualify to replace v1.0.0.** All work used retained historical
data; future gameweeks are not a completion requirement.

[Aggregate results, gates and uncertainty](INCUMBENT_AVAILABILITY_RESULTS_2026-10-16.json) ·
[Protocol and reproduction](incumbent_availability.md) ·
[Earlier practical benchmark](SELECTION_BENCHMARK_RESULTS_2026-10-15.md)

## What was fixed before scoring

The control uses the incumbent's 49 performance features, HGB7 architecture and
730.5-day training-weight half-life. The challenger adds only a chance label and
explicit missingness. Zero and unknown are distinct; the label is learned as a
covariate, not assigned as a probability. Both use the same 147,500 training fixtures
from 2020/21 through 2024/25 plus 2025/26 GW1–19. Validation is GW20–27; reused audit is
GW28–38. No post-validation refit, parameter search, seed search or text model.

All 35 GW4–38 exact published availability prefixes were re-admitted against
bootstrap identity/deadline/hash evidence. A source must precede both its recorded
deadline and the feature-cache cutoff. All 163,072 original fixture rows remain;
older seasons/unmatched observations retain unknown availability. There are
27,552 source-matched 2025/26 fixtures and 17,618 known labels. The source is
**FPL-syndicated news/availability archived by AIrsenal**, not independent club
articles or an injury-history corpus. No supplemental article scraping was needed.

Head protocol was published at `07214b9` before fitting. After its fixed gate passed,
the points protocol was published at `a618c77` before points scoring. The latter
adds the same features directly to the **unconditional** core-points learner; DC
uses one shared learner capped by each arm's own appearance probability. It never
multiplies unconditional core points by appearance probability. Minutes/p60 models
are not refitted. These are matched historical *method* refits, not forecasts
backcast from the saved champion trained on the evaluation season.

## Appearance result

Lower Brier is better. These are candidate **fixture-level**, not player-GW,
measurements; doubles are not collapsed under an independence assumption.

| Window | Control | Availability | Relative Brier reduction |
|---|---:|---:|---:|
| Development GW20–27 | 0.096781 | 0.069681 | 28.0% |
| Reused audit GW28–38 | 0.102229 | 0.081202 | 20.6% |

Both fixed progression gates passed: >=0.5% candidate reduction, no worse all-player
Brier and negative upper bounds for descriptive four-GW block differences. Audit
mean per-GW difference −0.020696, interval [−0.024059,−0.018069]. At matched coverage,
nonappearances fell 166→136 across 1,973 candidate fixture selections. Reliability
bins and all-player scores are in the JSON. Brier combines discrimination and
reliability; lower Brier does not establish better calibration in every subgroup.

## Full-points result and external comparison

All following errors/rankings use the same 2,312 candidate player-GWs in 2025/26
GW28–38, aggregating both fixtures of doubles. External forecasts are the previously
frozen named-method adaptations. Reusing their exact outputs avoids introducing
new training variation. Newly reproduced control differs from its prior output
by at most 2.1e−16, consistent with CSV floating-point round trips.

| Method | Full-points RMSE ↓ | MAE ↓ | Mean NDCG@10 ↑ |
|---|---:|---:|---:|
| Incumbent-method control | 2.97780 | 2.25493 | 0.47252 |
| Availability challenger, unapproved | 2.95959 | 2.27059 | 0.47171 |
| Native-feature HGB reference | 2.95586 | 2.24939 | 0.41481 |
| Dastan architecture adaptation | 2.95404 | 2.18962 | 0.38433 |
| OpenFPL cv 1 adaptation | 3.01932 | 2.34308 | 0.38936 |
| AIrsenal-inspired Poisson component | 3.04175 | 2.27888 | 0.38662 |

Against control, development candidate RMSE improved 2.93434→2.90796(0.90%), MAE
2.20935→2.20503, ranking 0.35458→0.35973. All development point/rank checks passed.
On reused audit RMSE improved 0.61%, descriptive paired difference −0.018208,
interval [−0.026771,−0.010500]. However, MAE worsened 0.69%, beyond the 0.5% guardrail,
and ranking fell slightly. The audit point/ranking gate therefore **failed**.

The challenger has lower measured error than the OpenFPL/component adaptations,
but remains behind the Dastan/native references on RMSE. Ranking remains much
stronger than those adaptations. No new claim about original Dastan 2024/25 is
possible: this news archive starts 2025, and no later article was backfilled into
an earlier information set. Original Dastan and original one-GW export comparisons
remain unchanged and separately reported. These adaptations do not reproduce
entire original systems or prove a general competitor ranking.

## Common-policy practical selection

Same 9,099 listed player-GWs, same verified blanks, same neutral opening rosters,
selector, budget/price quotes, transfer accounting and source-based coverage as
the prior benchmark. Primary: twelve fixed owned squads over eleven GWs. Secondary:
weekly £100m reset and six rolling eleven-GW transfer paths. No chip optimisation.

| Method | Owned mean points/GW | Reset mean points/GW | Rolling mean eleven-GW total |
|---|---:|---:|---:|
| Incumbent-method control | 37.174 | 69.182 | 624.667 |
| Availability challenger, unapproved | 37.008 | 70.818 | 621.500 |
| Native-feature HGB reference | 36.841 | 63.909 | 557.500 |
| Dastan architecture adaptation | 36.568 | 59.273 | 547.667 |
| OpenFPL cv 1 adaptation | 36.606 | 58.636 | 537.500 |
| AIrsenal-inspired component | 37.129 | 60.909 | 552.833 |

The challenger improves reset score by 1.636/GW over control but loses 0.167/GW on
the owned primary and 3.167 points over the rolling episode. All primary
simultaneous intervals are inconclusive, including equivalence within±0.25/GW.
For challenger minus control, the four-GW primary interval is[−0.879,+0.545].
A useful component improvement is therefore **not a consistent practical gain**.

The reset comparison favours the challenger over Dastan/OpenFPL adaptations
under all reported block lengths 2/4/6. Comparisons against control/native/component
are block-sensitive or inconclusive. Reset is secondary; intervals condition on
this short reused window and policy. No independent rolling-episode interval,
full-season/chip superiority or production promotion is claimed.

All 1,254 scores were independently reconciled with another scorer, along with
36 rolling ledgers and 810 transactions. The 1,045 original-method/control actions,
selections and scores exactly reproduce the earlier benchmark; the scenario
schedule is unchanged. Thus the added arm did not improve competitors by quietly
changing their scenarios or selection policy.

## Coverage and source limits

The first replay stopped before scoring because 23 fixture-history player-GWs were
not in the earlier listed roster. The tested source-only correction at `ce 58f1c`
keeps these rows in every method's error metrics and uses the same original
predeadline roster for every selection arm. No outcome-based exclusion. All 409
verified listed blank player-GWs get zero; unknown nonblank coverage still fails.
The failed attempt is preserved; no forecast/scenario/outcome was changed.

In three weeks, admitted news was newer than the retained price capture but still
predeadline. `quote_as_of` remains explicit; comparison `inputs_as_of` advances to
the latest admitted source. All methods share the same quotes/common deadline,
with unequal source feeds. This is source-value research, not equal-input
architecture superiority. Git times remain publisher history, not independent
clock certification. Mutable historical statistics, reconstructed feature-cache
cutoffs and inspected/reused outcomes remain limitations.

## Decision, cost and next useful work

**Retain approved v1.0.0.** Appearance progression passed, but full-points MAE/rank
and owned/rolling decision guardrails did not. Existing multi-season promotion
evidence is also unavailable for the new availability source. No registry,
weekly forecast schema, model weights or normal workflow changed. Do not select
this research arm for live planning just because it won one metric.

Three completed supervised jobs took 110.87s combined, peak sampled RSS 1.44GiB,
two CPU threads; the pre-scoring failed replay added 1.14s. Each full core fit took
about 12s;15,572-row core inference took about 0.02s per arm. These exclude source
research, engineering/tests/review and do not guarantee another device's timing.
Actual Python 3.12.14/NumPy 2.3.5/pandas 2.2.3/scikit-learn 1.9.1 environment differs
from current package NumPy/pandas pins. No GPU, cloud or external retraining.
No fitted binaries or raw news/data are published.

Stop this fixed experiment rather than selecting more variants on its audit.
A subsequent justified hypothesis should isolate how availability affects
conditional returns or the DC cap using chronologically separate development,
not search blends on GW28–38. Existing sourced-news/preflight/manual scenarios
remain available with the champion. Future frozen weekly review is ongoing
maintenance, not unfinished work in this package.

Methodological grounding: [scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html)
and [temporal validation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split),
checked 16 October 2026. Source lineage and the original-text negative result are in
[the earlier news study](NEWS_AVAILABILITY_RESULTS_2026-10-16.md).


## Conditional integration follow-up — 16 October 2026

[The controlled four-arm integration/selection study](CONDITIONAL_SELECTION_RESULTS_2026-10-16.md)
now isolates old/new appearance probabilities with one shared conditional-return
model and current/expected bench selection. Points RMSE and MAE improve versus
the historical incumbent reference; ranking and the fixed combined selector do
not qualify. Matched external error/common-mean-policy results are reported,
including an observed but uncertain RMSE win over the Dastan adaptation. Original
system comparisons in this document remain unchanged. No model is promoted.
