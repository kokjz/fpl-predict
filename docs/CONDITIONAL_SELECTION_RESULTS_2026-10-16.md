# Conditional availability and expected bench-selection study

16 October 2026, Asia/Singapore. **Explicitly integrating improved appearance
probabilities improves historical points forecasts. The exact expected bench
selector does not establish a realised squad-points gain. Retain approved v1.0.0.**

[Aggregate results and uncertainty](CONDITIONAL_SELECTION_RESULTS_2026-10-16.json) ·
[Protocol/reproduction](conditional_selection.md) ·
[Previous availability experiment](INCUMBENT_AVAILABILITY_RESULTS_2026-10-16.md)

## What this experiment isolates

One shared fixed HGB7 model learns core points conditional on playing, from
60,955 earlier appearing fixtures. Both arms combine exactly that same return
model with previously frozen old/new appearance probabilities. Conditional DC
uses 5,782 appearing records with observed actions; conditional minutes are a
shared diagnostic. Training contains 147,500 fixtures across five earlier seasons
plus 2025/26 GW1–19. There is no availability covariate in the shared return model,
no parameter search, no calibration search and no post-validation refit.

Expected points are the appearance probability times the conditional core/DC
return, plus a shared training-only card-only contribution. The weighted prior
uses 10 card-only events among 86,545 earlier nonappearances: conditional card rate
0.00010424 and mean card return−1.18027. Card-only players block autosubs but do
not block captain fallback. A zero-minute yellow-card case in development remains
in the error data; it was not removed. None of the neutral owned squads happens
to contain that case; synthetic tests cover its distinct scoring rules.

This is a genuine conditional fit, not multiplying an already unconditional
forecast by appearance probability. The old conditional arm also remains in all
reports, so an architecture change cannot masquerade as an availability gain.
An unchanged incumbent-method anchor measures the complete pipeline against v1.
No trained binary or registry change is published.

The fixed four arms are old/new appearance probabilities crossed with the current
mean selector versus an expected legal-autosub/vice selector. The latter enumerates
all legal XIs, keeper choices and bench orders for the owned 15, optimising
captain/vice analytically under independent player-GW event probabilities. It is
exact for that assumed distribution, not guaranteed to know the real joint
availability or returns. It uses no realised outcomes to choose a lineup.

Development GW20–27 uses twelve squads opened from GW20 metadata; audit GW28–38
uses the twelve original benchmark squads opened at GW28. All 19 GWs and all
four arms plus the incumbent anchor are reported, without selecting a winner
retrospectively. Outcomes in both windows have already been inspected/reused.

## Points prediction

Candidate player-GW metrics; all fixtures of a double count together. Lower error
and higher NDCG are better. All-player metrics and paired intervals are in JSON.

| Window and method | RMSE | MAE | Mean NDCG@10 |
|---|---:|---:|---:|
| Development incumbent anchor | 2.93434 | 2.20935 | 0.35458 |
| Development conditional + old appearance | 2.94000 | 2.22612 | 0.34236 |
| Development conditional + new appearance | 2.88868 | 2.16214 | 0.35377 |
| Audit incumbent anchor | 2.97780 | 2.25493 | 0.47252 |
| Audit conditional + old appearance | 2.98069 | 2.26918 | 0.44404 |
| Audit conditional + new appearance | 2.94125 | 2.23845 | 0.44639 |

The new appearance source improves audit RMSE by 1.32% and MAE by 1.35% against
the **same conditional-return model with old probabilities**; ranking also
improves. Against the incumbent anchor, audit RMSE improves 1.23% and MAE 0.73%,
but ranking is lower. Development RMSE/MAE improve versus the anchor, while
NDCG is slightly lower 0.35377 versus 0.35458. Thus the fixed development ranking
check fails; the predeclared combined finalist is not progressed or promoted.
The study does not choose new-mean instead after seeing its better audit score.

This is a more direct positive result for appearance-information value than the
prior raw-feature points extension. It does not imply a20.6% increase in FPL points,
perfect identification of non-starters, or a guaranteed season gain.

## Realised owned-squad selection

All arms use identical squads/outcomes within each window, legal autosubs,
captain/vice fallback and zero hits. There are 96 squad-GW panels per arm in
development and 132 in audit. The opening rosters include neutral stress cases;
they are not a representative sample of strong-manager teams.

| Arm | Development mean points/GW | Audit mean points/GW |
|---|---:|---:|
| Incumbent anchor | 32.958 | 37.174 |
| Old appearance + mean selector | 33.052 | 37.106 |
| New appearance + mean selector | 33.135 | 37.242 |
| Old appearance + expected selector | 33.177 | 37.053 |
| New appearance + expected selector | 33.125 | 37.068 |

Isolating appearance estimates with the same mean selector gives+0.083/GW in
development and+0.136/GW in audit. The expected selector instead changes audit
points by−0.053/GW with old probabilities and−0.174/GW with new probabilities.
The prespecified combined arm versus old-mean is+0.073/GW development and
−0.038/GW audit; its audit simultaneous four-GW interval is [−0.530,+0.455].
All reported owned primary intervals are inconclusive, including equivalence.
No full-season transfer/chip advantage is established by these small differences.

The expected selector does improve **its own expected-value objective** in all
456 old/new paired checks. Its mean objective gain is only 0.046 points/GW for
old probabilities and 0.054 for new, across the two windows. These small expected
margins do not guarantee positive realised gains in nineteen correlated GWs.
In audit the new expected policy changes the XI in 87/132 panels and the bench
order in 104/132, showing that many lineup changes can have very small estimated
value. This is not proof that a particular forecast or correlation error caused
the realised loss; the expected gains depend on uncertain conditional returns
and the assumed availability distribution.

The fixed positive-dependence stress preserves marginals and evaluates chosen
plans rather than reoptimising. Expected-selector gains remain small under it;
it does not empirically establish the true correlations or explain the observed
loss. Persistent fixture availability is separately reoptimised on squads 0/4/8:
mean-policy scores stay identical, and expected-policy audit scores also stay
identical on the same 33-panel subset. Development sensitivity scores increase
by 0.292/GW on its 24-panel subset. Those subsets are never compared to the full
12-squad means or chosen as a preferred coupling after outcomes.

## External comparison on the existing common historical test set

Same 2,312 candidate player-GWs,8,713 total player-GWs and 9,043 fixtures in 2025/26
GW28–38. External forecasts are retained named-method adaptations; no new external
training or unequal row selection. The original 2024/25 Dastan archive and original
one-GW export results remain unchanged and separate.

| Method | RMSE | MAE | Mean NDCG@10 |
|---|---:|---:|---:|
| Incumbent-method reference | 2.97780 | 2.25493 | 0.47252 |
| New conditional + availability, unapproved | 2.94125 | 2.23845 | 0.44639 |
| Native-feature HGB reference | 2.95586 | 2.24939 | 0.41481 |
| Dastan architecture adaptation | 2.95404 | 2.18962 | 0.38433 |
| OpenFPL cv 1 adaptation | 3.01932 | 2.34308 | 0.38936 |
| AIrsenal-inspired component | 3.04175 | 2.27888 | 0.38662 |

The new arm has a measured 0.43% RMSE advantage over the Dastan adaptation and
higher top-ranking quality, but worse MAE. Its paired RMSE difference−0.01279 has
a descriptive interval [−0.03480,+0.00784], spanning zero. This is an observed
specific-method win, not confirmed general superiority or an original-Dastan
reproduction. Source/training/capture limitations of the adaptations remain.

The same mean-selection policy gives 37.242 points/GW for the new conditional
forecasts versus 37.174 incumbent,36.841 native,36.568 Dastan adaptation,36.606
OpenFPL adaptation and 37.129 component, using the original 132 panels. The new
expected-selector arm's37.068 belongs to the separate factorial policy comparison;
it must not be advertised as an equal-policy forecasting advantage.

The frozen development ranking guard failed, so no broader reset/rolling-transfer
expansion or new finalist fit was run. The existing-row error/common-policy owned
comparison above is a bounded use of already retained data, not a bypass of that
progression gate. No future-gameweek results are needed to complete this package.

## Integrity, sources and cost

All original 163,072 fixture rows stay in the admitted input; all evaluated error
rows are retained. Selection uses 15,526 independently listed player-GWs across
both windows, with 409 previously verified audit blanks. The 46 fixture-history
player-GWs absent from earlier listed rosters remain in error metrics and are
uniformly excluded from selection for all arms. Unknown nonblank coverage fails.
Published availability prefixes, bootstrap identity/deadline/hash checks and
source-before-cutoff boundaries are rechecked. Prices use captured quotes; any
newer predeadline news advances the comparison source cutoff while preserving
quote time. Mutable statistics and reconstructed historical schedules remain
limitations, especially development's fixture-history-based calendar.

Two initial assumptions were corrected without deleting evidence. A fit attempt
stopped before training because of the zero-minute card case; training-only card
events were then modelled before replacement fitting. A completed initial replay
had one neutral rotation panel reconstructed differently because of cross-season
prior minutes. Exact retained audit metadata/anchor values were restored and all
arms rerun without changing forecasts, probabilities, seeds or policies. The
canonical audit reproduces all 132 original anchor panels and opening squads.
No corrected run was chosen for its performance; the predeclared source match
was the eligibility criterion.

Independent checks reconcile 1,368 realised scores,24 point-error metrics and 456
expected-objective comparisons. The realised scorer and expected evaluator are
cross-checked on exhaustive synthetic states, including fractional three-state
cards/minutes, formation constraints and keeper/captain fallback. Source-only
CI tests do not download historical data. No raw news/archive, individual
forecasts, private team information, personal device details or fitted binaries
are published.

Canonical fit/market/pilot/replay/external jobs took 83.33s combined, peak sampled
RSS 1.54GiB, two CPU threads. Retained failed/superseded jobs add 69.46s. Conditional
core fit took 4.81s, DC 1.13s, minutes 4.84s; each 15,572-row inference took about 0.02s.
The mechanical pilot's four expected-selector calls took 0.42s combined. Exact
owned selection is practical at this bounded scale; no GPU or remote compute was
used. Actual Python 3.12.14/NumPy2.3.5/pandas 2.2.3/sklearn 1.9.1 environment differs
from current package NumPy/pandas pins. Storage/time/RSS were monitored throughout
supervised jobs; no budget was breached.

## Can a small improvement justify replacement?

Yes. A small credible benefit can justify adoption; its size alone is not a
reason to retain an incumbent. Nor must every diagnostic improve in principle.
Ranking measures are proxies for decision quality, not the ultimate objective.
The failed fixed ranking guard determines eligibility under this experiment's
rules; it does **not** prove that the conditional forecaster is inferior.

Distinguish the forecaster from the selector. Against the incumbent reference,
the conditional forecaster reduces audit RMSE by 1.23%. The descriptive paired
block interval for its RMSE difference is [−0.0520, −0.0190], favouring the
challenger. MAE falls 0.73%, with difference interval [−0.0370, +0.0056]. These
are fixed-prediction historical intervals, not uncertainty from retraining,
model selection or future seasons.

With the existing mean selector, the new forecaster scores 37.242 versus 37.174
points/GW: +0.0682. A supplementary **post-outcome, forecaster-only** paired
block-4 interval is [−0.1894, +0.3258]. Development's corresponding gain is
+0.1771, interval [+0.0417, +0.3125]. These descriptive contrasts do not replace
the predeclared combined finalist or establish a season-points advantage.
The expected selector scores less than this forecaster with the existing policy;
it should not be bundled into adoption merely because forecast errors improve.

Targeted forecaster-only qualification is therefore worth considering. It needs
an explicitly scoped promotion policy, compatibility with current availability
inputs, a saved/loadable conditional artifact and operational tests; this
research package supplies none of those production changes. Assess that scope
separately rather than silently relax a rule after inspecting results. The
historical evidence is useful progress, with reused outcomes and only one
admitted availability season limiting generalisation. No wait for future games
is necessary to finish this package.

## Outcome and next evidence boundary

Keep approved v1.0.0 and the production selector. The new source has demonstrated
historical points-forecast value when integrated explicitly, but the fixed
combined finalist fails ranking progression and does not establish a practical
points gain. Exact optimisation under a forecast distribution does not make that
distribution correct. A new source commit or an attractive metric is not approval.

Further research would need a separately declared hypothesis about conditional
returns, cameo/full-match minutes or robustness to small expected-value differences.
Do not tune thresholds, seeds, blends, coupling weights or promotion gates on this
audit to make the current challenger pass. Future frozen weekly review remains
ordinary maintenance, separate from this completed historical package.

Sources checked 16October2026: [official FPL management](https://www.premierleague.com/en/news/2174899/fpl-basics-managing-your-team)
and [chronological validation guidance](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split).
The preceding reports retain full source-publication and external-method lineage.


## Subsequent forecaster qualification — 16 October 2026

The [forecaster-only qualification](FORECASTER_QUALIFICATION_RESULTS_2026-10-16.md)
saves/reloads the fixed conditional candidate and tests current-input compatibility.
Older chronological development is nearly neutral; same-policy retained external
comparisons preserve the error advantage, but reset/rolling points favour the
standing reference. No new expected-selector adoption or model promotion occurs.
This follow-up does not rewrite the results or progression rules above.
