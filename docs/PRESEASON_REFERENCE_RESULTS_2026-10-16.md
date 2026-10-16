# Preseason reference pilot — 16 October 2026

**Opening differentiation improved; pooled six-gameweek forecast error did not.**
No forecaster, planner policy or model-registry promotion follows this experiment.
The [complete aggregate results](PRESEASON_REFERENCE_RESULTS_2026-10-16.json)
retain every fixed arm, source hashes, per-GW diagnostics and resource measures.

## Fixed comparison

The [protocol](../src/fpl_predict_resources/preseason_protocol.json) and source
`233c4dc4d9ba611b4ce220e093dd04b646ca5ffd` were published before the pilot.
There was no parameter search, new training or post-outcome choice of reference.
All three arms reuse the earlier prior-season-only core/EWDC research model:
the season-reset control, stable-code carryover and carryover with an official
origin-GW projection replacement. This is not a backcast of the deployed model,
which was trained on data later than these historical deadlines.

Each of 2025/26 GW1–6 uses its own pinned pre-deadline bootstrap and admitted
calendar. All horizon targets share that origin's information. Official
`ep_next` applies only to the next event, verified to be the origin GW. Source
capture and publisher timestamps remain claims, not independently witnessed
publication certificates. Corrected historical results retain their usual caveat.

The scored cohort contains **4,311 listed player-gameweeks**. A separate group of
**1,102 player-gameweeks** uses eligibility based only on prior-season records:
at least three records and a last-five mean of at least 45 minutes. Eventual
appearance is never used to choose this group. Its membership differs from the
usual within-season candidate definition, so errors must not be compared directly
with earlier reports that use that definition.

| Reference | All RMSE | All MAE | Prior-eligible RMSE | Prior-eligible MAE |
|---|---:|---:|---:|---:|
| Season-reset control | 2.0945 | 1.2221 | 2.6689 | 1.7943 |
| Carryover | 2.0998 | 1.2339 | 2.6881 | 1.9981 |
| Official origin + carryover later | 2.2184 | 1.2741 | 2.7333 | 1.7929 |

Carryover improves the opening candidate RMSE from **3.2182 to 2.9736**;
official origin projections reach **2.8688**. Their improvement does not persist
across the whole six-GW window. Carryover's old roles/club context and missing new
players are material limitations; this experiment does not isolate the cause of
each later error. More distinct predictions alone do not prove better forecasts.

## Initial-squad diagnostic

At GW1, a common six-GW financial planner builds each arm's own legal £100m squad,
XI, bench and captain. Only its first action is scored, including actual automatic
substitutions and captain fallback. No chips or paid transfers are used.

| Reference | GW1 realised net points |
|---|---:|
| Season-reset control | 36 |
| Carryover | 47 |
| Official origin + carryover later | 52 |

These are **one opening deadline's results**, not full-season gains, repeated
independent-week team selection or evidence of consistent superiority. The
official arm also uses carryover later in its planning horizon; its squad result
cannot be attributed solely to the one-week official projection. Initial-squad
choices must next be carried through actual finances, transfers and chip choices
before assessing season-management utility.

## Coverage, runtime and verification

GW1's 685 listed players have five distinct reset means, 402 carryover means and
38 official means (rounded to eight decimals). Stable-code links exist for 511;
500 have compatible prior positions and receive active carryover. The remaining
11 changed position. Missing/changed-position players retain reset forecasts
except where the explicit official-origin replacement applies.

The supervised completed run took **22.72 seconds**, with approximately **626 MiB**
peak sampled RSS and two CPU threads. There was **no new model fit**. Building
all three references took 1.76–2.19 seconds per origin; the three initial-squad
plans took 0.24–1.52 seconds each. Time, memory and storage limits held. This does
not justify separate GPU hardware.

An independent calculation reconciled **25,866 horizon cells**, all six origin
point aggregations and metrics, initial finance/score components, and the unchanged
approved artifact hash. Three short failed research-script runs are retained:
fixture-audit fields, settlement signature and metric grouping-key integration
errors. Corrected runs preserve byte-identical GW1 forecasts/actions wherever
those had already been frozen. No failed run caused a model/parameter change.

Validation also includes the complete source test suite and installed-wheel
module/resource checks. A source merge makes these optional research APIs
available; it does not authorise automatic forecast/model adoption.

## What follows

The references resolve a source/interface gap and provide explicit opening
comparisons, but have not qualified as general replacements for the control.
Keep all declared arms for later full-season diagnosis rather than selecting the
GW1 winner after seeing its score. Continue chip/uncertainty planning and then
complete the 38-GW management replay. Dastan/OpenFPL's retained late-season grids
cannot fairly be used in these opening weeks; matched earlier refits and common
season-planner comparisons remain a separate stage. No full-season external
superiority or useful season-point improvement has yet been established.
