# Matched native planning-engine comparison — 16 October 2026

This study compares continuous 38-gameweek management using common forecasts and a common outer chip policy. It measures a pinned, rule-adapted Open FPL Solver inner optimiser against the standing inner optimiser. It does not reproduce either an untouched external manager or its original forecasting and chip strategy.

The eight predeclared paths completed, and all 304 deadline transitions passed independent finance, transfer, chip and realised-scoring reconciliation. The approved forecasting champion and weekly defaults remain unchanged. These are results on one reused historical season, not an independent prospective test or proof of general superiority.

## Net season points

| Prior-only forecast | Opening | Standing planner | Native adaptation | Standing minus native |
|---|---|---:|---:|---:|
| Four-year common core | own | 2,141 | 2,030 | +111 |
| Four-year common core | common | 2,135 | 2,157 | -22 |
| Five-prior-season standing method | own | 2,236 | 2,224 | +12 |
| Five-prior-season standing method | common | 2,224 | 2,226 | -2 |

Positive differences favour the standing planner. The common-opening track fixes the same first squad only; later transfers are unrestricted by that opening roster. The own-opening track lets each planner construct its initial squad. The two tracks are sensitivity checks, not independent seasons. Comparisons within a row isolate the configured planning implementation; comparing the four-year and five-prior-year controls also changes forecasting history.

## What was held common

- Frozen prior-only forecasts and deadline-available prices, registration status, availability overlay and fixture calendar; evaluator outcomes are accessed only after each action is written.
- Six-gameweek lookahead, a legal persistent £100m starting budget, selling-price basis, transfer banking and hits, all four chip types and historical chip windows.
- The same candidate procedure, feasibility baseline, deterministic mean lineup/captain/vice/bench policy, 0.1 bench weight and zero terminal/churn proxies.
- Fifteen seconds for the outer chip search, two seconds per inner attempt, at most twelve trials and two CPU threads per supervised job. The allowance was selected from an outcome-free construction/validity pilot before season scoring.

Only the immediate action is committed; the manager replans at each deadline. Future quotes remain origin-frozen assumptions. The shared outer chip calendar is heuristic, and further-horizon projections are approximations. This is a full-season management test, rather than a sum of independently rebuilt weekly teams.

The implementations use different formulations and solver bindings/versions. The standing solver retains its baseline objective cut; the native solver retains its original search tactic. Equal decision objectives and resource ceilings do not imply identical numerical searches.

## Cost and failure behaviour

| Forecast | Planner | Opening | Hits | Transfers | Job minutes | Peak sampled MiB | No-incumbent attempts | Unknown selected bounds |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Four-year common core | standing | own | 16 | 87 | 5.36 | 654.6 | 0 | 0/38 |
| Four-year common core | standing | common | 16 | 87 | 6.14 | 585.9 | 0 | 0/38 |
| Four-year common core | native | own | 20 | 89 | 8.19 | 823.6 | 10 | 0/38 |
| Four-year common core | native | common | 24 | 89 | 7.94 | 711.1 | 15 | 0/38 |
| Five-prior-season standing method | standing | own | 24 | 91 | 6.07 | 663.2 | 0 | 0/38 |
| Five-prior-season standing method | standing | common | 24 | 91 | 6.06 | 855.4 | 0 | 0/38 |
| Five-prior-season standing method | native | own | 28 | 92 | 7.74 | 764.6 | 11 | 0/38 |
| Five-prior-season standing method | native | common | 12 | 85 | 8.35 | 819.6 | 12 | 0/38 |

The eight serial jobs took 55.85 minutes in total; the maximum sampled process-group memory was 855.4 MiB. This excludes the earlier forecasting fits. Native startup is recorded separately in the aggregate. Memory monitoring is sampled, not a hard operating-system quota.

A native attempt without a feasible incumbent retains a validated fallback. Those attempts are not silently omitted or treated as successful solves. A completed native proposal that fails canonical admission stops its path; no such invalid-proposal path is included as a success here. All declared paths and expected no-incumbent attempts are retained.

Selected-plan bounds are unknown at 0/304 deadlines. The largest known relative gap is 0.012014. Every known bound is conditional on a fixed chip schedule, restricted pool and stated surrogate objective. Global chip-search, full-season optimality and prediction-confidence bounds remain unknown. A small reported MIP gap from a discarded attempt is not a certificate for the retained plan.

## Source compatibility and interpretation

The native core is [Open FPL Solver at ec65f5e](https://github.com/solioanalytics/open-fpl-solver/tree/ec65f5e2b2be34441cb4b2a9efafea1ec0fe3b79), run through the separately installed Python 3.14/HiGHS runtime. Source hashes and runtime versions are in the aggregate. The guarded compatibility layer handles the known historical transfer top-up, purchase eligibility and Free Hit retention of an appreciated original holding. It never supplies future realised prices or recovery information. External source and binaries are not bundled.

Wall-time searches can choose different incumbents between runs. Brief isolated mechanical admission work overlapped part of this serial batch; this was not a dedicated-machine timing study. Repeatability and solver-quality sensitivity remain qualification work. The point differences must not be attributed solely to forecast accuracy, source-rule corrections or an abstract optimisation algorithm.

The four-year and five-prior-year forecasts are chronological historical method references. The saved approved artifact was trained on the evaluation season and therefore was not backcast into that season. No forecasts, weights or budgets were selected to maximise the points reported here. Reuse of this historical season still limits claims.

AIrsenal is not a full-season comparator in this release. Its native planner needs a separate, validated adapter; an existing conjugate/Poisson forecasting reference is not its original manager. Native planning compatibility does not establish native end-to-end model reproduction.

See the [frozen protocol](../src/fpl_predict_resources/native_planner_protocol.json), [implementation contract](native_planner_comparison.md), [aggregate and hashes](native_planner_results.json), [historical source inventory](season_external_sources.json) and [forecaster comparison](SEASON_EXTERNAL_RESULTS_2026-10-16.md). The aggregate contains research summaries, not a personal squad or runtime artifacts.
