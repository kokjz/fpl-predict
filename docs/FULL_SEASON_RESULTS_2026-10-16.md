# First continuous season-management pilot — 16 October 2026

The six-week research manager scored **2,295 net points**, versus **2,092** for
the matched one-week manager with the same forecast source and chip access:
**+203 points over the complete 2025/26 season**. Without chips, the six-week
manager led by **52 points**. These are measured continuous-squad results, not
sums of independently reset weekly teams.

This is **one reused historical season**, one own-opening path per arm, with
bounded optimisation and explicit source approximations. It does not establish
future gains, approve a policy/model or show superiority over Dastan/OpenFPL's
complete systems. All six declared runs are included in the
[aggregate evidence](FULL_SEASON_RESULTS_2026-10-16.json).

## What was fixed before scoring

The [protocol](../src/fpl_predict_resources/full_season_protocol.json) and source
`7c271e313eca1dd4237a4fa26b941e0dd982cf8f` were published before this pilot.
Each arm starts with £100m, chooses its own legal GW1 squad and maintains it for
all 38 deadlines. Purchases/sales, retained purchase basis, free transfers,
four-point hits, Wildcards, temporary Free Hits, Bench Boosts and Triple Captains
carry forward. Actual automatic substitutions and captain fallback are settled.
No configurations or winning reference were selected after seeing the results.

The forecaster is the same **prior-season-only core/EWDC research reference** used
in earlier pilots, not the deployed artifact backcast into its own training data.
Its weights use 2020/21–2024/25; 2025/26 form enters only after the origin's
completion cutoff. This fit was reconstructed retrospectively: `trained_through`
records label coverage, not a claim that the training job actually ran then.

At every origin, only the pinned roster, quotes, calendar and prior history are
used. All 38 listed-player fixture cohorts and official next-event identities
passed admission. Unsupported future chip variants are blocked until a compatible
configuration is observed. A common experimental availability rule zeros only
the origin-GW forecast when official next-GW chance is zero and status is not
available; missing values remain unknown and later targets are unchanged. It is
a source interpretation, not guaranteed absence or a known recovery date.

## Complete results

| Forecast / planner | Net points | Hit cost | Transfers after GW1 | Chips used |
|---|---:|---:|---:|---:|
| Reset reference, one week, chips | 2,092 | 24 | 94 | 8 |
| Reset reference, six weeks, chips | **2,295** | **20** | 79 | 8 |
| Prior-season carryover, six weeks, chips | 2,132 | 28 | 87 | 8 |
| Official-origin hybrid, six weeks, chips | 1,895 | 200 | 124 | 8 |
| Reset reference, one week, no chips | 1,959 | 48 | 53 | 0 |
| Reset reference, six weeks, no chips | 2,011 | 68 | 58 | 0 |

Transfers include moves made under Wildcard and Free Hit, so they are not all
paid transfers. The primary comparison has equal chip inventory, rules, forecast
source and search budgets. The no-chip comparison separately supports a benefit
from looking ahead in this particular season. The two differences cannot be
subtracted to obtain a causal estimate of chip skill: squad paths and later
decisions interact throughout the season.

The carryover reference gained points in the earlier GW1 diagnostic but finished
**163 points below** the reset six-week manager here. That is a concrete reason
not to adopt a reference from one opening gameweek's score.

The official-origin arm combines official next-GW projections with this project's
carryover/reset forecasts for later targets. It is **a mixed-horizon adaptation,
not an official provider's native season-management system**. It incurred 180
more hit-cost points than the reset six-week arm. Inconsistent forecast levels
across the mixed horizon may encourage churn; this pilot does not isolate the
cause. Its 400-point deficit must not be presented as proof that official FPL
projections are generally inferior. Matched single-horizon and coherent external
horizon comparisons remain useful follow-ups.

## Cost, uncertainty and audit

The six policy runs took **328 seconds serially**, in addition to **91.75 seconds**
of one-off source/forecast preparation. Each used two CPU threads, with no new
model fit or GPU. The largest policy-job sampled RSS was about **522 MiB**;
preparation peaked at about **622 MiB**. All storage, memory and time limits held.

Chip-enabled managers receive four seconds per origin, half a second per solver
call and at most 12 trials. No-chip managers use the same half-second fixed-solve
limit. Short budgets retain a legal candidate or baseline and report gaps. These
are resource-constrained policies, not globally optimal managers; detailed
budget-exhaustion and fixed-schedule gap statistics are in the JSON evidence.
Equal time budgets do not imply equal optimisation difficulty across horizons.
Some timed-out attempts had extremely loose solver gaps, reaching 219.75 as a
ratio in a carryover trial. A reported gap belongs to the solver attempt even
when the validated baseline is retained; it is not an optimality certificate for
the selected plan. These limits do not invalidate the realised legal-path scores,
but this operating point is not qualified as a well-solved optimiser. Improving
incumbents, bounds and budget robustness remains important follow-up work.

An independent audit reconciled **228 deadline transitions**: purchase-price
profits, cash, FT/top-up rules, chip inventory/reversion, every decision hash and
an alternative formation-count calculation of autosubs/captain/BB/TC scoring.
All totals and the unchanged approved artifact hash matched. The complete offline
suite and installed command/module/resource checks also passed.

The archive can contain later corrections, source capture/publication times are
not independently certified, and snapshot quotes approximate executable prices.
Six forecasts for one origin share its form and current roster; future prices,
news, availability changes and rearrangements are not known early. Independent
news coverage is missing for GW1–3. A single reused season cannot establish
statistical generalisation or replace a prospective track record; player rows,
gameweeks and alternative paths are not independent seasons.

Next are common-opening sensitivity and admissible full-season external forecast
and planner comparisons, followed by bounded diagnosis and joint qualification.
The approved weekly model, manual overrides and registry remain unchanged.
