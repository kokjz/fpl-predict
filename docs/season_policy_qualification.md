# Season-management policy qualification

Latest follow-up, 24 October 2026: the optional
[availability-aware policy](SEASON_DECISION_VALUE_RESULTS_2026-10-24.md) keeps
point means fixed and tests legal expected subs/vice fallback in sixteen matched
38-GW paths. Its equal-season difference versus fresh H6 is
**+57.50 net points**; the predeclared historical
mean/material-downside criterion **passes**. This is a separate research policy,
with two reused years, two common starts each and no Assistant Manager in 2024/25.
Read its [method, optional API and limitations](season_decision_value.md).
No approved forecast weights or normal weekly defaults change. The earlier
studies below retain their original dates, gates and scopes.

Current evidence: the [two-season study](EXPECTED_SEASON_POINTS_RESULTS_2026-10-24.md)
reports an equal-season H6-minus-H1 mean of +129.50 net points across
four common opening cases. Its declared mean/material-downside research criterion
passes. The earlier zero-negative consistency gate remains failed;
that narrow failure does not establish H6 inferiority. Both seasons already had
research exposure, and 2024/25 explicitly excludes Assistant Manager. H6 remains
experimental support: no forecast or production-default promotion. Read the
[current scope/status](season_policy_status.json) and [framework](expected_season_points.md).

Qualification evaluates a continuous 38-gameweek squad, rather than adding up
independent weekly team selections. Net realised points after hits is the
primary measure. Forecast-error metrics remain diagnostics.

The research harness accepts either an inner roster solver, retaining its
existing adaptive chip policy, or an explicitly versioned whole management
policy. A whole-policy callback receives the current state, origin-frozen
market and horizon, settings, resource policy, blocked chip tokens and an
optional common opening. It never receives the hidden evaluator mapping.

The callback returns a complete provisional action path and report. Before
settlement, the harness validates every period's finances, squad, chip resources
and supplied expected objective. Disabled or blocked chips, a changed common
opening and incomplete or illegal paths are rejected before outcomes are read.
Only the first action is committed; the process repeats at the next deadline.
The callback API is for trusted research code, not a security sandbox.

This interface supports an honest fixed-calendar chip control and a descriptive
hold reference without disguising either as an inner optimisation solver.
Default replay behaviour is unchanged when no whole policy is supplied.
Policy identity is recorded in each frozen decision and final summary.

`management_policies.FixedCalendarPolicy` retains predeclared chip dates while
replanning rosters at each origin. It uses the canonical roster solver, candidate
procedure and expected objective. Within the same outer time envelope it can
repeat its single allowed schedule, retaining the best expected objective and
recording every attempt. This compares complete policies and search allocation;
it does not isolate chip timing independently of numerical solve quality.

The following control calendar belongs to the original 2025/26 two-set study.
Do not reuse it unchanged with the restricted 2024/25 annual-chip profile.
It was fixed before that qualification scoring:

| Chip | First window | Second window |
|---|---:|---:|
| Wildcard | GW6 | GW24 |
| Bench Boost | GW12 | GW30 |
| Free Hit | GW15 | GW33 |
| Triple Captain | GW18 | GW36 |

These are arbitrary spaced reference dates, not dates selected from realised
chip returns. The policy validates windows, token reuse and consecutive Free
Hits. Already-used or explicitly blocked resources are unavailable.

`HoldPolicy` constructs the cheapest legal opening or accepts the common opening,
then retains all 15 players and reselects the mean XI/captain/vice each deadline.
It deliberately leaves transfers and chips unused. It is a descriptive floor;
the one-week planner with all legal resources remains the primary strong anchor.

The [qualification protocol](../src/fpl_predict_resources/season_policy_qualification_protocol.json)
declares the repeat matrix, controls, limits and decision criteria. Its executable
source inventory and mechanical pilot must be frozen before historical scoring.
Synthetic tests prove mechanics, not historical performance or useful chip dates.

`approved_horizon.observe_approved(model_home, receipt_path)` records verified
approved artifact existence using the current clock, without loading the model.
The destination must be new. Keep the receipt and its SHA256 with frozen inputs.
An observation is a conservative upper bound on when training had completed;
it is not the original fit timestamp or evidence that historical forecasts existed.

`project_approved` resolves the current approved registry entry, verifies the
receipt hash/version/artifact and source clocks, then loads the verified bytes.
It rejects a changed artifact, unapproved registry entry, metadata mismatch or
observation at/after the forecast origin. The caller's timestamped source adapter
remains responsible for authenticating history and the origin-known calendar.
The deployment artifact must never be backcast into its training seasons.

Optional reviews use the existing availability-review schema with an origin-safe
bootstrap and matching deadline. The shared `forecast_sensitivity` calculation
preserves the weekly workflow's illustrative minutes/availability scaling;
reviewed assumptions apply to the current gameweek only, not an asserted future
recovery path. No new appearance multiplier is applied to unconditional forecasts.
The original weekly forecast uses the same calculation and numerical behaviour.

An actual saved-artifact compatibility check used the entirely
[invented case](../tests/fixtures/synthetic_bridge_case.json): 18 players,
1/4/6/8-week grids, 19 admitted hold-policy actions frozen before fabricated
settlement, blank/double checks, future-history mutation and current-only minutes
sensitivity. The bounded check took 3.28 seconds including startup and about
166.6 MiB sampled process-group memory. This is not a realistic full-market
latency measurement, a forecast-accuracy test or adaptive-policy qualification.
The [aggregate and source hashes](approved_bridge_compatibility.json) disclose
the observed runtime, which differs from repository dependency pins, and retain
the initial synthetic timestamp-format failure. The adaptive planner pilot remains
separate. No real player or squad forecasts
were produced by this check.

The subsequent [adaptive integration check](approved_adaptive_compatibility.json)
uses the same saved champion and invented case with two explicitly weighted
sensitivity scenarios. All 1/4/6/8-week plans and a six-week next-origin replan
passed independent accounting, formation, autosub, captain/chip scoring and
expected-objective reconciliation: 25 provisional periods in total. Deterministic
scoring replay uses the frozen actions, without refitting or rerunning the solver.

For the next-origin check, only the eight-week plan's first action is committed.
The resulting squad, bank, transfer resources and chips carry forward. Newly
revealed invented match history, one changed price, a fixture moved into the
next gameweek and current-only absence evidence then produce a revised plan.
The [invented next-origin inputs](../tests/fixtures/synthetic_bridge_replan.json)
are retained. These are fictional test events, not football news.

Each solve used a two-second outer envelope, 0.2-second inner attempts and at most
twelve trials. The full supervised check took 4.64 seconds and about 178.6 MiB
sampled group memory. Selected-schedule bounds were available in this tiny case;
global chip and season bounds remain unknown. This proves mechanical integration,
not useful forecasts, realistic full-market latency, season gain or policy approval.

The completed [historical qualification](SEASON_POLICY_QUALIFICATION_RESULTS_2026-10-17.md)
and [policy status](season_policy_status.json) report all twenty uniform-source
paths, independent audits and predeclared decisions. The synthetic checks above
prove mechanics only. Historical experimental qualification, forecast promotion
and normal weekly-policy approval remain distinct decisions. The frozen protocol's
readiness text records its pre-execution state and is not rewritten after results.

The underlying [AIrsenal comparison](airsenal_planner_comparison.md) was released
before integrating the qualification runner. Its results remain tied to their
frozen source; new qualification paths use their own immutable inventory.

## Reproducible per-arm execution

`fpl-predict qualify-season arms` lists the twenty declared paths in order.
`qualify-season lock` records input/protocol hashes, listed engine source hashes
and package versions. It requires the protocol's forecast, outcome and common
opening checksums. Custom compatible protocols define separate studies; changing
inputs never preserves the identity of the canonical qualification run.

```sh
fpl-predict qualify-season lock --decisions DECISIONS.json.gz --outcomes OUTCOMES.json.gz --opening OPENING.json --output PRIVATE_HOME/lock.json --home PRIVATE_HOME
fpl-predict qualify-season arm --name control_common_hold_no_chips --decisions DECISIONS.json.gz --outcomes OUTCOMES.json.gz --opening OPENING.json --lock PRIVATE_HOME/lock.json --lock-sha256 LOCK_SHA256 --output PRIVATE_HOME/hold-common --home PRIVATE_HOME
```

Choose an external private home or an ignored runtime directory. Existing lock
and output files cannot be overwritten. Source, runtime and input drift is checked
before and after execution. The native adapters require explicit optional runtime
paths: `--native-python`, `--solio-source`, `--solio-site-packages` and/or
`--airsenal-site-packages`. Ordinary installation does not install or start them.

All native requests and replies are retained in compressed JSON lines, alongside
individual failure evidence. Expected budget/feasibility failures retain validated
fallbacks. Unknown errors, completed-but-invalid proposals and inconsistent bounds
stop the path. Native source/runtime identities are checked by the adapter's
pinned recipe handshake. Full-season outcomes remain separate from planner inputs.

These commands execute one arm. The supervising `run-experiment`/`run_job`
workflow must enforce the protocol's process-group memory, time and storage caps;
execute historical arms serially and preserve every declared attempt. The runner
is trusted research code, not an operating-system sandbox or an approval mechanism.
The [complete matrix and independent audits](season_policy_qualification_results.json)
record the completed historical qualification; commands alone never imply approval.

From a source checkout, the standard-library-only verification tool checks one
complete frozen 2025/26 path without importing the planner or season engine:

```sh
python tools/audit_season_path.py --decisions DECISIONS.json.gz --outcomes OUTCOMES.json.gz --season-dir PRIVATE_HOME/PATH/result/season --horizon 6
```

For a common-opening path add `--opening OPENING.json`; use `--horizon 1` for
the one-week anchor. The tool checks every settled deadline and retained future
action, original purchase basis, bank, free transfers, chips, hits, formation,
captain/vice, priority autosubs, expected objective and frozen-decision checksum.
It accepts the study's mean objective (bench proxy0.1, zero terminal/churn
proxies), requires assertions enabled and reports aggregate counts and input
hashes. It deliberately rejects other season profiles or objectives. It does
not certify archive publication history, model training lineage, native proposal
admission or solver optimality; those require their separate checks. Inputs and
full frozen decisions may contain private squads and should remain outside Git.

A native-controller preflight used an entirely invented 15-player, 38-origin
market. Solio completed 38 calls; AIrsenal completed the path through 38 recorded
feasibility fallbacks because no alternative transfer existed. This checks fallback
handling, not successful native optimisation or historical performance. The initial
AIrsenal attempt stopped on its exact upstream `RuntimeError` for an unavailable
single transfer. That attempt is retained; only that typed, exact feasibility
response was admitted, with tests rejecting other types or extended messages.
The uniform rerun took 6.42 seconds/360.5 MiB for Solio and 3.34 seconds/340.0 MiB
for AIrsenal, including startup. Synthetic limits were 0.5 seconds outer/0.2 inner;
they do not select or replace the historical protocol's declared budgets.

## Fixed-schedule numerical sensitivity

The [separate quality protocol](season_policy_quality_protocol.json) fixes five
calendar anchors (GW1/6/16/30/38) and inner limits of 0.5/2/5 seconds. It uses the
first common-opening six-week path's frozen states, forecasts and retained chip
schedules, with one attempt per case. Cases are calendar-based, not selected by
realised loss or the largest observed solver gap. The declaration follows ten
completed qualification paths and precedes the diagnostic itself; it is not an
untouched historical test.

Run this diagnostic only after the twenty-path historical batch finishes. Check
legal provisional actions, expected-objective reconciliation, retained-plan
bounds, fallback behaviour and cost. Finite bounds can be compared with an
existing feasible plan only when the candidate pools and constraints match.
No future outcomes or quotes enter this probe. Differences are conditional
optimisation diagnostics, not measured season-point gains or permission to
select new settings after inspecting realised test scores.

The [source-checkout runner](../tools/probe_season_solver.py) verifies the locked
engine/runtime and input checksums, stores each frozen origin once, and retains
all fifteen attempted cases. It checks the returned provisional actions and
expected objectives using the independent verifier; evaluator files are never
read. Input/source drift, an invalid proposal or a contradictory bound stops the
probe and preserves its partial evidence. An injected test callback is explicitly
labelled and cannot be mistaken for the canonical solver.

```sh
python tools/probe_season_solver.py \
  --decisions DECISIONS.json.gz --reference FIRST_COMMON_H6/result/season \
  --opening OPENING.json --lock PRIVATE_HOME/lock.json --lock-sha256 LOCK_SHA256 \
  --protocol docs/season_policy_quality_protocol.json --protocol-sha256 QUALITY_PROTOCOL_SHA256 \
  --home PRIVATE_HOME --output PRIVATE_HOME/new-quality-probe
```

Replace placeholders with the frozen inputs and a private workspace. Run under
the existing `run-experiment`/`run_job` watchdog with the protocol's two-thread,
120-second, sampled-memory and storage limits. The command itself is not an OS
quota or sandbox. Source-checkout tests use invented data and a labelled callback;
they do not execute or establish the historical diagnostic's results.
