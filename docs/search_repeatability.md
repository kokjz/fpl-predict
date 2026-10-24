# Search repeatability

The [decision-value study](SEASON_DECISION_VALUE_RESULTS_2026-10-24.md) found a
promising mean season-points gain, but repeated time-limited controls varied by
up to 110 points. A fixed elapsed-time budget changes both solver incumbents and
the chip schedules that the outer search reaches. It is not a stable work budget.

The optional research mode uses `Settings(node_limit=...)` with
`baseline_mode='feasibility'` and `Budget(..., fixed_work=True)`. It fixes the
inner branch-and-bound node cap, seed zero, parallel mode off and at most the
declared number of outer trials. Model construction and selection time do not
reduce the number of eligible schedule probes. Duplicate/illegal schedules and
remaining chip inventory can still reduce the actual trial count.

The existing two-thread limit remains. Inner time limits and the external
process/memory/storage watchdog are safety guards. Reaching a time guard raises
an error rather than accepting that result as successful fixed-work completion.
An admissible node-limited search with no feasible incumbent may retain the
separately validated baseline; that fallback is explicitly reported.

Native Solio requests opt into a validated work-control object and return a
receipt for successful and expected no-incumbent attempts. The adapter checks
source hashes, actual options, status, node count, finances and objective. The
existing explicit dominated integral paid-transfer-slack policy also covers
node-limit incumbents; strict legacy defaults remain unchanged. This is an
adapted external core, not an untouched original manager.

The initial source-only preflight stopped when the pinned upstream solver reset
parallel mode to `on`. Its raw attempt is retained. The explicit work adapter now
enforces the declared node/seed/parallel settings on every option assignment and
checks their actual values before solving. The complete preflight reruns on the
corrected source; no season scores, budgets or probability settings informed this
mechanical repair. Legacy requests retain upstream defaults.

A second preflight exposed SciPy-wrapper differences: its parallel option uses
boolean `False` for off, and the installed status mapper does not recognise HiGHS
solution-limit enum 16 even when an incumbent is returned. The adapter now passes
the documented wrapper type, makes option warnings fatal in explicit work mode,
and admits only that exact known status message as a node-limit termination.
Raw and admitted statuses remain recorded; normal incumbent/financial/objective
checks are retained. Unknown statuses and all time guards still stop the run.
Both failed preflight batches remain separate from the uniform corrected rerun.

Node caps do not bound root-node presolve/heuristic effort, equalise CPU work
between different formulations or guarantee equality across solver versions.
Runtime versions are frozen and reported. Expected-value and global chip/season
bounds remain unknown; a mean-objective dual cannot certify an expected-value
reranking objective.

The [predeclared protocol](search_repeatability_protocol_2026-10-25.json) calls
for repeated origin-only mechanical checks, then 24 continuous 38-GW paths:
two admitted seasons, two common starts, three policies and two repetitions.
The comparison retains all repetitions, failures and losses. Fingerprints cover
every deadline's financial state, selected and provisional actions and forecast
provenance; elapsed timings are excluded. Stable fingerprints measure numerical
repeatability, not predictive accuracy or independent football replications.

The [source-checkout runner](../tools/run_repeatability_study.py) accepts the
same private, checksummed origin/outcome/appearance bundles as the earlier study.
Use a fresh output outside the checkout under the experiment watchdog; no data
or binary downloads are implicit. The runner never fits or promotes weights.
Normal weekly commands and defaults are unchanged.

References checked 25 October 2026:
[SciPy MILP node-limit/status documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)
and [HiGHS node/seed/parallel options](https://ergo-code.github.io/HiGHS/dev/options/definitions/).
These document available controls; measured repeatability still requires the
declared tests on the pinned runtime and historical inputs.
