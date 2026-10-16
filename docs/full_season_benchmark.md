# Continuous full-season management benchmark

`season-benchmark` evaluates a manager across all 38 deadlines. It builds a squad
at GW1, then carries the actual purchase ledger, bank, free transfers, paid hits
and chip inventory forward. Lineups, captain fallback and automatic substitutions
are scored against official player-gameweek totals after each decision is saved.
This is different from resetting a £100m squad every gameweek.

The [fixed first-pilot protocol](../src/fpl_predict_resources/full_season_protocol.json)
declares six runs before scoring: one- versus six-week planners with identical
forecasts and chip access, the two explicit preseason-reference variants, and
one- versus six-week planners without chips. The primary comparison is the
season-reset six-week manager minus its one-week counterpart with chips. All
references are reported; the opening-week winner is not selected retrospectively.

Each origin contains its own market and complete forecast horizon, with training,
feature and source cutoffs. The policy receives only that origin. Future actual
prices, outcomes, injuries and rearrangements cannot influence earlier actions.
Historical source timestamps remain publisher/capture claims; writing a replay
decision now does not mean the forecast actually existed at the historical
deadline. Corrected archive and schedule-coverage caveats remain material.

The initial availability experiment is deliberately narrow: a pre-deadline
official next-GW chance of zero, paired with a status other than available,
zeros only the origin-GW forecast. Later targets are unchanged. This is a fixed
experimental interpretation of the source, not calibrated certainty or a known
recovery date. Missing values stay unknown. All forecast/planner arms receive the
same treatment. It does not replace sourced manual judgment in weekly planning.

## Repeatable replay

```sh
fpl-predict season-benchmark \
  --decisions private-decisions.json --decisions-sha256 DECISIONS_SHA256 \
  --outcomes private-outcomes.json --outcomes-sha256 OUTCOMES_SHA256 \
  --output new-private-season --horizon 6 \
  --seconds 4 --solve-seconds 0.5 --max-trials 12
```

Plain JSON or losslessly compressed `.json.gz` inputs are accepted (128 MiB
decoded limit per bundle). Both inputs use schema version 1. The decision bundle's `weeks` is an ordered
38-entry list of `market`, `forecast` and `blocked_tokens` objects, using the
[adaptive planner](adaptive_planner.md) contracts. An optional `opening_ids`
list forces a common legal 15-player GW1 roster for starting-state sensitivity;
lineups and subsequent management still use each arm's forecasts. Without it,
each arm chooses its own opening squad. The outcome bundle's `weeks` maps GW to
player IDs with `actual`, `minutes` and `cards` totals. Blanks must be verified,
not inferred from unexplained missing results. Use `--no-chips` for the matched
horizon ablation. The command checks both input hashes and refuses an existing
output directory, retaining failed or completed evidence.

Each deadline writes `GWxx_decision.json` before accessing that GW's evaluator
outcomes. Settlement references the decision hash and records the next state.
The final summary reports net points, hits, transfers, chip use, runtime and
budget exhaustion. This API separation is not a sandbox for arbitrary Python
policies. The installed command makes no model-registry or account changes.

For small search budgets, chip probes alternate families within each expiry/date
instead of exhausting every date for the first family. With at least ten trials,
two trials and a portion of wall time are reserved for combined-calendar checking.
This is a bounded heuristic, not a global season optimum. Compare equal budgets
and disclose gaps/fallbacks; never present the four-second setting as fully solved
if it times out. Coarse chip values and terminal/reserve proxies remain fixed
experimental assumptions until qualification.

The first season is a reused historical pilot with one own-opening path per arm,
not independent prospective evidence. Later stages add common-start sensitivity,
admissible external forecasts/planners and further seasons where rules/sources
permit. No model or policy is promoted solely by this pilot, and no future
gameweek results are required to conduct it.

The [subsequent external-forecast comparison](SEASON_EXTERNAL_RESULTS_2026-10-16.md)
adds matched prior-only forecast adaptations and common-opening paths. It uses
the revised planner and reports both controls; its results do not overwrite this
first pilot or establish original external-manager superiority.

## Repeated policy qualification

The [twenty-path study](SEASON_POLICY_QUALIFICATION_RESULTS_2026-10-17.md) adds
uniform-source repetitions, common openings, matched native planner adaptations
and fixed-calendar/hold controls. Its budgets and forecast reference are declared
separately from the first pilot. The
[standalone verifier](../tools/audit_season_path.py) reconciles both actual
settlement and every retained future action without importing the planner.
Do not pool the initial pilot with later repeats or relabel it as new-source data.
