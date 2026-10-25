# Fixed-work season search repeatability

25 October 2026. All 24 declared continuous 38-GW paths completed, with
unchanged point forecasts and appearance sidecars. Read the
[method](search_repeatability.md), [original protocol](search_repeatability_protocol_2026-10-25.json)
and [resource amendment](search_repeatability_resource_amendment_2026-10-25.json).

## Complete comparison

Each cell contains both repetitions. There is no best-run selection.

| Season | Common start | H6 | Availability-aware H6 | Adapted Solio |
|---|---|---:|---:|---:|
| 2024-25 | 20261070 | 2417 / 2417 | 2442 / 2442 | 2398 / 2398 |
| 2024-25 | 20261071 | 2423 / 2423 | 2445 / 2445 | 2423 / 2423 |
| 2025-26 | 20261070 | 2266 / 2266 | 2199 / 2199 | 2225 / 2225 |
| 2025-26 | 20261071 | 2217 / 2217 | 2263 / 2263 | 2241 / 2241 |

| Comparison | 2024/25 mean | 2025/26 mean | Equal-season mean | Worst opening | Mean/downside criterion |
|---|---:|---:|---:|---:|---|
| decision minus H6 | +23.50 | -10.50 | +6.50 | -67 | Fail |
| decision minus Solio | +33.00 | -2.00 | +15.50 | -26 | Pass |
| H6 minus Solio | +9.50 | +8.50 | +9.00 | -24 | Pass |

The primary four opening effects, averaged within each numerical repetition pair,
are **+25, +22, -67, +46**, equal-season mean **+6.50 net points**.
The declared historical point criterion **does not pass**: its −67-point worst
opening exceeds the predeclared 38-point opening loss limit. The positive mean
and both season means satisfy their separate requirements, including the
19-point season-mean loss allowance. This is a material-downside criterion,
not a requirement to win every season or proof of inferior future expected value.
Strict repeated full-plan/source/financial fingerprints **all match**;
the combined historical research qualification **does not pass**.
Weights and normal weekly defaults remain unchanged; this is optional research
decision support, with no automatic production-policy approval.

## What repeatability establishes

Across twelve repeated cases, 456
of 456 deadline fingerprints match. Fingerprints cover the financial state,
actual and complete provisional actions, origin and forecast provenance, excluding
elapsed timings and unused cumulative points. Realised repeat-score differences
are retained in the aggregate, including any zero differences.

The strict gate compares executions on identical football outcomes. It is not
the earlier no-negative-season gate: individual losing openings are permitted
by the separate mean/material-downside criterion. A repeat difference would limit
a numerical-stability claim, not prove that the policy has inferior expected value.

These numerical repetitions do not provide new independent football outcomes.
Two reused seasons with two starts each are not four independent seasons or an
untouched evaluation. No confidence interval for future expected gains is inferred.
The 2024/25 profile excludes Assistant Manager for every method. Common starts
measure subsequent management rather than a new initial-squad builder.

Historical forecasts use the already admitted prior-only method references,
fitted before each evaluated year. They are not a backcast of the approved
deployment artifact into its training seasons. No point or appearance head is
refitted in this package.

The fixed-work mode uses one branch-and-bound node per proposal, seed zero,
parallel off, at most six outer probes and two CPU threads. The same input,
candidate and rule procedures apply. Different formulations and embedded/native
HiGHS versions can still do different work within a node. Expected-value reranking
remains a heuristic over mean-MILP proposals; its optimality bounds stay unknown.

The earlier [time-limited study](SEASON_DECISION_VALUE_RESULTS_2026-10-24.md)
retains its +57.50 mean versus fresh H6, all losses and control drift. Changing
logical work, parallel mode and probe allocation defines a different research
policy. Cross-study score changes are not an isolated causal effect of removing
wall-clock variation or evidence of better forecasting accuracy.

## Preflight, failures and resource decisions

Both failed source-only preflights remain retained. The first caught upstream
parallel mode overriding the declared setting; the second exposed the SciPy
wrapper's boolean parallel option and unmapped HiGHS solution-limit status.
Narrow tested adapters enforce actual native options, make option warnings fatal
in work mode and admit only the exact known enum-16 message, preserving all
incumbent, financial, objective and bound checks. No season result informed these
repairs. Legacy requests retain their former behaviour.

The corrected twelve-probe preflight completed all 24 cases and all twelve repeat
pairs matched exactly. Its native mean of 40.98 seconds per sampled origin led
to a linear estimated 1,557 seconds per season path, above the existing 900-second
guard. A documented resource-only choice selected six probes equally for all
methods, preserving capacity for a combined chip-calendar proposal. Duplicate
schedules may reuse the cache. The fresh six-probe preflight also completed all
24 cases; its complete results and any repeated differences remain in the aggregate.
The estimate is not a worst-case guarantee. Safety time/memory/storage termination
would invalidate successful fixed-work completion rather than select a partial run.

The original season batch also retains ten complete paths and one interrupted
partial path. A safety-time guard fired coincident with documented host sleep.
The [unchanged continuation](search_repeatability_resume_2026-10-25.json) references
the ten complete jobs, retries the interrupted case once, verifies all seventeen
saved prefix fingerprints and executes the remaining thirteen matrix cases.
Its failed attempt and cost remain separate; no source, settings, input or safety
budget was relaxed and no partial outcome is counted as a successful path.

The 24 final paths took **207.27 serial minutes**;
maximum sampled process-group memory was **1359.0 MiB**.
No model was fitted, no GPU/cloud was used and no dependency was installed.
Pilot and failed-attempt costs are separately retained. These timings are historical
replay costs, not the cost of an ordinary weekly forecast. Actual runtime versions,
including differences from repository pins, are disclosed in the aggregate.

The selected-schedule accounting retains
**608 known and 304 unknown**
conditional deadline bounds and **0 candidate fallbacks**.
Fallback counts include every probe, not only a chosen action. Mean-objective
bounds cannot certify the expected reranking objective; global chip/season bounds
remain unknown. Per-path trial/node/status/bound coverage stays in the aggregate.

Separate implementations reconcile **912 settlements**, **5,112 retained
provisional periods**, **1,704 expected-objective periods** and
**8664 native provisional periods**. Every native request,
expected no-incumbent failure and work receipt is retained. Independent means
separate implementations within this project, not third-party certification.

## Exploratory selection-only diagnosis

After observing a material loss, the separately declared
[diagnostic addendum](search_repeatability_selection_addendum_2026-10-25.json)
freezes selections for all sixteen saved mean-H6/adapted-Solio paths before
counterfactual scoring. Across both starts, years and repetitions, chip-aware
expected selections change net points by **+3.25**
on the saved H6 paths and **+4.50**
on saved adapted-Solio paths. The aggregate retains every opening/repetition,
both legacy and chip-aware arms, losses and expected values.

| Saved roster policy | 2024/25 start 70 | 2024/25 start 71 | 2025/26 start 70 | 2025/26 start 71 | Equal-season mean |
|---|---:|---:|---:|---:|---:|
| H6 lineup-only overlay | +12 | +22 | −8 | −13 | +3.25 |
| Adapted Solio lineup-only overlay | +22 | +22 | −11 | −15 | +4.50 |

Both repetitions give these differences, and legacy versus chip-aware expected
selection gives identical realised totals on all sixteen paths. These are not
independent extra seasons. Both newer-year openings lose under selection-only
changes for both saved policies, so changed transfer/chip decisions cannot alone
explain every weakness. This does not identify a defective probability model or
causal remedy; appearance/conditional-return calibration and joint assumptions
remain hypotheses requiring separate assessment.

The full-policy −67 case has base-XI −74, autosubs +51, captain bonus −16,
Bench Boost −10, extra Triple Captain bonus −2 and 16 additional hit points.
Rosters differ at 31 deadlines, transfers at 26 and chip use at six. These parts
sum to −67; they are accounting of diverging paths, not recoverable causal gains.

All 608 panels retain original rosters, transfers, chips and unconditional means.
Separate implementations reconcile 1,824 financial states, realised scores and
expected values. The diagnostic took 62.43 seconds
with 478.0 MiB maximum sampled group memory.
Its outcomes were already inspected: this is a post-result conditional overlay,
not an untouched test, a new adaptive transfer/chip replay, a promotion criterion
or a causal estimate of recoverable full-policy points.

## Next steps and operational scope

The fixed-work mode is now a repeatable offline comparison tool on the measured
runtime. Retain normal weekly defaults and approved weights. The next bounded
package should follow this order:

1. **Audit appearance/return coherence without fitting.** On frozen historical
   origins, examine the implied conditional return `unconditional_mean / p_play`,
   joint appearance assumptions and conditional residuals for owned/proposed
   players. Predeclare strata/diagnostics before calculating their outcomes;
   preserve all strata and label the reused data. Assess official availability
   labels and uncertainty separately from calibrated play probabilities.
2. **Separate decisions before changing objectives.** Specify a first-action
   selection-only wrapper that preserves H6 transfer/chip proposals, and test its
   ledger/report invariants against the saved overlays. A measured +3.25 pooled
   overlay with both newer-year starts losing does not itself justify adoption.
   Use that control to distinguish selection changes from whole-roster/calendar
   reranking; do not claim the latter is the sole cause of the −67 loss.
3. **Qualify one justified challenger under a new protocol.** Only if the audit
   supports a precise change, declare a bounded candidate and matched standing/
   adapted-external controls before its test. Keep fixed work and all outcomes;
   do not search node/probe/seed settings or relax inspected gates to obtain a
   win. A joint learned-head change would additionally require chronological
   error, calibration, saved-artifact and full legal-decision gates.

This scopes future work rather than silently starting another training/search
package. Additional historical years need source, rule and prior-only forecast
admission. Earlier failed availability/conditional-selector/preseason experiments
remain controls. Frozen live-week review is ongoing maintenance, not a wait needed
to complete this historical package. The code merge establishes research tooling
and published evidence, not forecast-weight or production-policy promotion.

No new Dastan/OpenFPL/AIrsenal forecasting or original full-manager comparison is
made here. Approved v1.0.0 weights, current-only manual sensitivities, normal weekly
commands and default policy remain unchanged. The new settings and APIs are
explicit opt-in research controls. Read [current policy status](season_policy_status.json)
and the [complete aggregate](search_repeatability_results_2026-10-25.json).
