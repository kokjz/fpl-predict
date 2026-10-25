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

The [resource amendment](search_repeatability_resource_amendment_2026-10-25.json)
uses the completed, unscored 24-case timing pilot to select six probes for the
full season study. The original twelve-probe pilot remains published separately.
All policies use the same amended cap; a reserved combined-calendar probe follows
the first eligible chip-family probes. This is a resource choice before season
scoring, not a setting selected for better realised points. The 900-second path
guard remains, and the linear timing estimate is not a worst-case guarantee.

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


## Interrupted attempt and unchanged continuation

The original full-season batch stopped on an inner safety-time guard while the
host entered lid-closed sleep. Ten complete paths and seventeen settled origins
of the next remain immutable. The [continuation rule](search_repeatability_resume_2026-10-25.json)
references the complete jobs and permits one identical retry of the interrupted
case, with its saved seventeen-origin decision prefix required to match. No
source, input, seed, node/probe cap or safety budget changes. A further failure
stops the continuation; an incomplete attempt never counts as a complete run.

## Exploratory selection-only diagnostic

The [post-result addendum](search_repeatability_selection_addendum_2026-10-25.json)
compares saved, legacy expected and chip-aware expected selections on all sixteen
mean-H6/adapted-Solio paths, retaining every roster, transfer and chip. It freezes
all 608 panels before counterfactual scoring, then separately reconciles finance,
realised scores and expected values. The outcomes were already researched; this
is mechanism diagnosis, not untouched validation or a new promotion gate.

The source-checkout helper `tools/repeatability_selection_overlay.py` exposes
`freeze_case(decisions, appearance, record_directory, new_private_file)` and
`evaluate_case(frozen_file, sha256, decisions, evaluator_outcomes, saved_net_points)`.
Freeze every declared case first; retain a hashed complete manifest before
loading evaluator outcomes. Use the same prior-only references, as-of sidecars
and immutable decision records as the primary study. `freeze_case` accepts no
evaluator input. The caller must lock sources/inputs and supervise resource
limits; API separation is not a security boundary for untrusted code.

Retained squads that exceed a club limit after a club move are admitted only
after the season engine verifies the original transaction and purchase ledger.
This exception does not permit an illegal purchase or an invalid 15-player squad.
The diagnostic makes no fit, solver call, team/account action or default change.
A selection overlay is conditional on saved transfers/chips; it does not estimate
causal recoverable gains from an independently replanned full-season manager.
