# Matched AIrsenal planning-policy comparison — 16 October 2026

This study compares continuous 38-gameweek management using common forecasts and a common outer chip policy. It measures a pinned, rule-adapted AIrsenal tree/GA planning policy against the standing inner optimiser. It does not reproduce either an untouched external manager or its original forecasting and chip strategy.

The eight predeclared paths completed, and all 304 deadline transitions passed independent finance, transfer, chip and realised-scoring reconciliation. The approved forecasting champion and weekly defaults remain unchanged. These are results on one reused historical season, not an independent prospective test or proof of general superiority.

The initial matrix retained seven completed paths and one GW1 failure when a
SQLAlchemy exception wrapped an ordinary request deadline. The
[initial attempt](airsenal_planner_initial_attempt.json) remains available.
After typed deadline-chain handling was added, all eight paths were rerun
uniformly with the same budgets, seed, objectives and candidate procedure.
Initial and corrected paths are never pooled or selected by their realised score.
The [protocol](../src/fpl_predict_resources/airsenal_planner_protocol.json) retains
its pre-run declaration; this report records the completed corrected matrix.

## Net season points

| Prior-only forecast | Opening | Standing planner | Native adaptation | Standing minus native |
|---|---|---:|---:|---:|
| Four-year common core | own | 2,202 | 2,097 | +105 |
| Four-year common core | common | 2,206 | 1,996 | +210 |
| Five-prior-season standing method | own | 2,129 | 1,998 | +131 |
| Five-prior-season standing method | common | 2,220 | 2,153 | +67 |

Positive differences favour the standing planner. The common-opening track fixes the same first squad only; later transfers are unrestricted by that opening roster. The own-opening track lets each planner construct its initial squad. The two tracks are sensitivity checks, not independent seasons. Comparisons within a row isolate the configured planning implementation; comparing the four-year and five-prior-year controls also changes forecasting history.

## What was held common

- Frozen prior-only forecasts and deadline-available prices, registration status, availability overlay and fixture calendar; evaluator outcomes are accessed only after each action is written.
- Six-gameweek lookahead, a legal persistent £100m starting budget, selling-price basis, transfer banking and hits, all four chip types and historical chip windows.
- The same candidate procedure, feasibility baseline, deterministic mean lineup/captain/vice/bench policy, 0.1 bench weight and zero terminal/churn proxies.
- Fifteen seconds for the outer chip search, two seconds per inner attempt, at most twelve trials and two CPU threads per supervised job. The allowance was selected from an outcome-free construction/validity pilot before season scoring.

Only the immediate action is committed; the manager replans at each deadline. Future quotes remain origin-frozen assumptions. The shared outer chip calendar is heuristic, and further-horizon projections are approximations. This is a full-season management test, rather than a sum of independently rebuilt weekly teams.

The standing planner uses a bounded MIP with a valid baseline objective cut. The adapted native policy searches up to two regular transfers and eight hit points per window, with ten GA individuals, ten generations and seed 42. One common cheapest-legal individual seeds its population. Serial balanced exploration changes the original multiprocessing order. These are declared native search restrictions and adaptations, not FPL rules imposed on the control. Equal objectives and resource ceilings do not imply identical search spaces or numerical searches.

## Cost and failure behaviour

| Forecast | Planner | Opening | Hits | Transfers | Job minutes | Peak sampled MiB | Failed/budget attempts | Unknown selected bounds |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Four-year common core | standing | own | 12 | 86 | 5.88 | 873.3 | 0 | 0/38 |
| Four-year common core | standing | common | 20 | 88 | 7.12 | 623.9 | 0 | 2/38 |
| Four-year common core | native | own | 48 | 85 | 9.16 | 424.3 | 2 | 38/38 |
| Four-year common core | native | common | 68 | 79 | 9.21 | 418.3 | 3 | 38/38 |
| Five-prior-season standing method | standing | own | 28 | 86 | 6.92 | 639.2 | 0 | 0/38 |
| Five-prior-season standing method | standing | common | 24 | 91 | 6.11 | 858.7 | 0 | 0/38 |
| Five-prior-season standing method | native | own | 72 | 83 | 9.03 | 423.5 | 0 | 38/38 |
| Five-prior-season standing method | native | common | 68 | 82 | 9.02 | 414.6 | 0 | 38/38 |

## Realised scoring components

| Forecast | Planner | Opening | Starting XI | Autosub change | Captain bonus | Extra Triple Captain | Bench Boost | Hits | Net |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Four-year common core | standing | own | 1852 | +73 | 246 | 8 | 35 | 12 | 2202 |
| Four-year common core | standing | common | 1906 | +38 | 249 | 4 | 29 | 20 | 2206 |
| Four-year common core | native | own | 1810 | +77 | 223 | 4 | 31 | 48 | 2097 |
| Four-year common core | native | common | 1728 | +86 | 211 | 8 | 31 | 68 | 1996 |
| Five-prior-season standing method | standing | own | 1827 | +61 | 237 | 8 | 24 | 28 | 2129 |
| Five-prior-season standing method | standing | common | 1879 | +86 | 239 | 8 | 32 | 24 | 2220 |
| Five-prior-season standing method | native | own | 1753 | +58 | 229 | 8 | 22 | 72 | 1998 |
| Five-prior-season standing method | native | common | 1852 | +86 | 235 | 22 | 26 | 68 | 2153 |

These are independently reconciled accounting components, not causal estimates. Transfers change later squads and chip/captain opportunities; component differences do not isolate a forecasting or policy effect.

The eight serial jobs took 62.44 minutes in total; the maximum sampled process-group memory was 873.3 MiB. This excludes the earlier forecasting fits. Native startup is recorded separately in the aggregate. Memory monitoring is sampled, not a hard operating-system quota.

A timed-out native attempt or an unsuccessful heuristic squad construction retains a validated fallback. Those attempts are not silently omitted or treated as successful solves. A completed native proposal that fails canonical admission stops its path; no such invalid-proposal path is included as a success here. All declared paths and expected native failures are retained.

Selected-plan bounds are unknown at 154/304 deadlines. The largest known relative gap is 0.042184. Every known bound is conditional on a fixed chip schedule, restricted pool and stated surrogate objective. Global chip-search, full-season optimality and prediction-confidence bounds remain unknown. A small reported MIP gap from a discarded attempt is not a certificate for the retained plan.

The native heuristic has no upper-bound certificate even when its capped tree finishes. Its missing bound is not a zero gap and cannot be compared directly with the standing MIP gap.

## Source compatibility and interpretation

The native core is [AIrsenal at fe580d7e](https://github.com/alan-turing-institute/AIrsenal/tree/fe580d7e567e79d80f73450c7d4b5d6610f05863), run through the separately installed Python 3.14/DEAP/SQLAlchemy planner runtime. Its forecasting/training stack is not installed or reproduced for this planning-only track. Source hashes and runtime versions are in the aggregate. The guarded compatibility layer handles the known historical transfer top-up, purchase eligibility and Free Hit reversion and retained-original selling offers/purchase basis during full rebuilds. It never supplies future realised prices or recovery information. External source and binaries are not bundled.

Wall-time searches can explore different branches and retain different plans between runs. No second historical benchmark was scheduled alongside this serial batch; synthetic development tests in an isolated checkout overlapped some jobs. It was not a dedicated-machine timing study. Repeatability and solver-quality sensitivity remain qualification work. The point differences must not be attributed solely to forecast accuracy, source-rule corrections or an abstract optimisation algorithm.

The four-year and five-prior-year forecasts are chronological historical method references. The saved approved artifact was trained on the evaluation season and therefore was not backcast into that season. No forecasts, weights or budgets were selected to maximise the points reported here. Reuse of this historical season still limits claims.

The [earlier Solio comparison](NATIVE_PLANNER_RESULTS_2026-10-16.md) is a separate pinned planning-implementation study. The [forecast-method study](SEASON_EXTERNAL_RESULTS_2026-10-16.md) covers Dastan/OpenFPL method references with a common planner. These tracks answer different questions and do not reproduce original complete managers. The approved forecasting artifact and normal weekly policy are unchanged.

See the [frozen protocol](../src/fpl_predict_resources/airsenal_planner_protocol.json), [implementation contract](airsenal_planner_comparison.md), [aggregate and hashes](airsenal_planner_results.json), [historical source inventory](season_external_sources.json) and [forecaster comparison](SEASON_EXTERNAL_RESULTS_2026-10-16.md). The aggregate contains research summaries, not a personal squad or runtime artifacts.
