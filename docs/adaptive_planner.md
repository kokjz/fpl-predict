# Adaptive chip and scenario planning

`plan-adaptive` is an optional research planner. It combines a detailed one-to-eight
gameweek financial plan with a coarse remaining-season chip calendar. Only the
first action is eligible for execution after review. Rebuild the forecasts,
calendar, availability evidence and finances at each next deadline and replan.
The approved forecaster and ordinary weekly workflow are unchanged.

For a **fixed chip schedule**, the financial solver supports all four chips:
Wildcard rebuilds persist, Free Hit squads revert to the original purchase-price
ledger and bank, Triple Captain adds another captain multiplier, and Bench Boost
includes all 15 means. Transfers remain free under WC/FH and their banked free
transfers persist. Every hypothetical action is checked against the independent
[season-state engine](season_management.md). Prices and roster stay fixed within
each origin's hypothetical plan; later actual prices are never supplied early.

The outer search starts with a feasible no-chip plan. It probes individual chip
slots, jointly assigns estimated opportunities to a legal calendar, evaluates the
combined schedule and tries one bounded adjustment pass. This can capture some
Wildcard/Bench Boost interaction but is **not globally optimal chip search**.
Exact solver optimality, when found, applies only to a fixed schedule, restricted
player pool and the stated objective. Search limits and per-trial gaps are reported.

Outside the detailed horizon, default chip opportunities are constant illustrative
proxies: WC 12, FH 8, TC 5 and BB 10. They are neither learned point gains nor
precise far-horizon forecasts. Callers can supply alternatives. The calendar uses
these values jointly, enforcing chip windows, expiry, one chip per GW and the
consecutive-Free-Hit restriction. This prevents reserving four chips for the same
last deadline. Realised season tests and sensitivity to these assumptions remain
necessary before adoption.

The producer must audit the origin's bootstrap against the rule profile and pass
unsupported future chip tokens in `blocked_tokens`. For example, an unsupported
future second Free Hit cannot be planned as a verified standard 15-player chip.
Ignoring an unsupported variant is not evidence that it was available historically.

## Scenarios and evidence

Provide one to three complete forecast grids from the same origin and target
gameweeks, with explicit positive assumption weights summing to one. The solver
uses their weighted mean, then reports the **same action sequence's** objective in
each scenario. All detailed actions are shared: there is no access to a scenario's
identity or future injury recovery before it is revealed. Fresh evidence leads
to a new invocation at a real deadline. This is conservative shared-plan analysis,
not a scenario tree with optimised future recourse or calibrated joint outcomes.

The `adaptive_planner.scenario` helper applies cell-specific XP multipliers from
zero to two with a reason, public HTTPS evidence link and availability timestamp
no later than the origin. These are manual sensitivity assumptions. An injury
percentage is not automatically converted into a probability, and a guessed
return date is not asserted as fact. Actual schedule changes belong in a newly
admitted calendar; hypothetical changes may be separate, explicitly named grids.

The objective retains the detailed planner's reserve/terminal/churn proxies. It
does not yet optimise exact expected automatic substitutions or captain/vice
fallback under non-appearance. Actual settlement still applies those rules.

## Usage

```sh
fpl-predict plan-adaptive --input private-adaptive-input.json \
  --sha256 INPUT_SHA256 --output new-research-plan
```

Input schema version 1 uses the same `market`, `state` and optional `settings` as
[plan-horizon](rolling_planner.md). Supply `scenarios`, each containing `name`,
`weight` and a `forecast` object accepted by `Horizon.create`. Optional `budget`
contains `seconds` (default 60, maximum 120), `solve_seconds` (2) and `max_trials`
(40, maximum 80). `coarse_values` maps all four chip names to nonnegative proxy
values. `blocked_tokens` contains `[chip_name, window_start]` pairs. The command
checks its input checksum and refuses an existing output directory. It writes
actions and diagnostics, with no account operation or registry/model change.

For supplied schedules, `plan-horizon` also accepts optional `chip_schedule`, a
JSON object mapping target gameweek strings to chip names. Its default remains
no chips. Names are `wildcard`, `freehit`, `bboost`, and `3xc`.

The [fixed protocol](../src/fpl_predict_resources/adaptive_chip_protocol.json)
defines the pilot, budgets and nonclaims before historical evaluation. Sources
checked 16 October 2026: [official chip guidance](https://www.premierleague.com/en/news/4679879/whats-happening-with-fpl-chips-in-202627)
and [SciPy solver diagnostics](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html).
Full-season and external-manager superiority remain unmeasured by these mechanics.
