# Selected-plan bound diagnostic — 16 October 2026

The [bound repair](solver_bounds.md) now distinguishes the feasible plan retained
from a solver attempt's possibly discarded incumbent. Missing/inconsistent bounds
remain explicit; the outer chip search has no global optimality certificate.

The source/protocol was published at
`1837ac9ef2bc9935534e0897cd41457d7b66ca9e` before a fixed engineering diagnostic:
three existing frozen-input cases, each run once with the baseline objective cut
off and on, at a nominal half-second budget and two CPU threads. No realised
season outcomes were scored, no forecaster fitted and no parameters searched.
The [complete results](SELECTED_PLAN_BOUNDS_2026-10-16.json) retain all six runs.

| Frozen case | Cut | Retained objective | Retained relative gap | Raw attempt gap |
|---|---|---:|---:|---:|
| Neutral GW20 | Off | 305.781 | 7.13% | 7.13% |
| Neutral GW20 | On | 323.605 | 1.22% | 1.22% |
| Neutral GW38 | Off | 38.746 | 0% | 0% |
| Neutral GW38 | On | 38.746 | 0% | 0% |
| Diagnostic GW27, FH32 | Off | 320.758 | **5.99%** | **29.57%** |
| Diagnostic GW27, FH32 | On | 320.758 | **Unknown** | **Unknown** |

The last uncut run retained its validated baseline. The raw attempt gap therefore
overstates the retained plan's gap. In the cut run, the solver supplied no usable
dual before the time limit; the retained plan remains feasible, but its gap is
unknown. Reporting zero or reusing another run's bound would be incorrect.

The cut improved the objective in one pair and left it unchanged in two, but did
not improve bound availability in every case. It is mathematically valid and
switchable, not a guaranteed acceleration. These are unreplicated short runs
under ordinary background load, not a robust latency study or evidence of extra
FPL points. Objective values include the existing planning proxies.

The GW27 case was deliberately selected because it contained the largest raw
gap in the earlier season pilot. It is a diagnostic, not a blind holdout. Its new
half-second run does not reconstruct that original attempt's exact remaining
budget or dual, and must not be used to retrofit the old published gap.

The supervised job completed in **3.83 seconds**, with **366,477,312 bytes**
(about 350 MiB) peak sampled RSS. Resource/storage bounds held; no new model fit,
download, season replay or model/policy promotion occurred. An independent numeric
check reconciled the selected objectives, converted bounds and gap arithmetic.
Known-optimum, missing/nonfinite/inconsistent-bound, Free Hit terminal-constant,
fallback and adaptive-propagation regressions passed with the full suite.

The earlier [38-GW results](FULL_SEASON_RESULTS_2026-10-16.md) remain measurements
of their earlier source. Future matched comparisons must record the new planner
source and configuration. Fixed-schedule bounds still exclude alternative chip
schedules and players outside the candidate pool; they are not forecast-error
intervals or season-point guarantees.
