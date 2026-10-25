# Adaptive season management

Latest follow-up, 25 October 2026: the
[fixed-work study](SEARCH_REPEATABILITY_RESULTS_2026-10-25.md) completes 24
continuous season paths using one-node/six-probe research policies. Repeated
full-plan fingerprints all match; the availability-aware policy's equal-season
mean versus matched H6 is **+6.50 net points**. Combined historical research
qualification does not pass.
Two reused years, paired numerical repetitions and restricted 2024/25 no-AM
rules limit inference. This mode differs from the earlier timed policies.
Read the [method and resource amendment](search_repeatability.md).
Approved weights and normal weekly defaults remain unchanged. Earlier dated
results and gates below retain their original scopes.

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

The objective is net FPL points across all 38 gameweeks, including transfers and
chips. Forecast errors, fixed-owned-XI and weekly reset results remain component
diagnostics. The state engine, origin-safe multiweek planner and adaptive chip
calendar now support continuous historical management. Read the
[full qualification results](SEASON_POLICY_QUALIFICATION_RESULTS_2026-10-17.md)
and [explicit approval scope](season_policy_status.json); implementation and
historical experimental status do not establish general future superiority.

## State and scoring

`season_engine` carries purchase prices, cash, free transfers, chip windows and
cumulative points. It validates deadline actions and reuses the final scorer for
legal autosubs and vice fallback. Cards count for substitutions; minutes count
for captain fallback. Bench Boost counts all15once; Triple Captain adds another
captain return, including negatives. Wildcard changes persist; Free Hit restores
the original purchase ledger/bank. Saved transfers survive those chips without
an extra transfer. The2025GW16topup applies before that deadline's policy call.

[Versioned rules](../src/fpl_predict_resources/season_rules.json) cover2025/26 and
2026/27, including two chip sets, expiry and consecutiveFreeHit restrictions.
An additional explicitly restricted 2024/25 no-Assistant-Manager profile uses
annual Free Hit/Bench Boost/Triple Captain and no AFCON top-up; see the
[source admission](expected_season_points.md). Other seasons, special chip
variants and late joining require separately audited profiles.
Inputs use final official player-GW points, with DGWs summed; this is not a
reconstruction of uncertain assist/BPS calculations. Club transfers may leave an
untouched squad above the club limit; a subsequent FPL transfer restores it.

Execution is one set of net trades per deadline, not intraweek pricearbitrage.
Midseason starting purchase values must be supplied, never guessed.

## Information boundary

The trusted policy callback receives current immutable `State`/`Market` only.
Markets whitelist decision fields and reject outcome columns. `prepare` validates
an action without outcomes; `settle` scores final results. Full replay requires
38 consecutive deadlines; partial mechanical tests require an explicit opt-out.
Missing held-player quotes/outcomes fail closed. This is an API boundary, not a
sandbox for arbitrary Python. Forecast producers still need independent source
and chronological training checks; a whitelist alone cannot certify no leakage.

## Supplied-action replay

```sh
fpl-predict season-replay \
  --markets /path/to/markets.json --markets-sha256 MARKET_SHA256 \
  --actions /path/to/actions.json --actions-sha256 ACTION_SHA256 \
  --outcomes /path/to/outcomes.json --outcomes-sha256 OUTCOME_SHA256 \
  --output /path/to/new-replay
```

All files contain `schema_version:1` and a `weeks` list coveringGW1–38. Market
weeks have `season`, `gameweek`, `deadline`, `as_of`, `rows`; rows have integer
`id`, `position`, `price_tenths`, string `team`, boolean `can_buy`. Optional
fields are `expected_points`, `expected_minutes`, `p_play`, `status`. Actions have
`gameweek`, `buys`, `sells`, `starters`, `bench`, `captain`, `vice`, optional
`chip` (`wildcard`, `freehit`, `bboost`, `3xc`). Initial actions buy15players.
Outcome weeks have `gameweek`, `players`, each with `id`, `actual`, `minutes`,
`cards`. Input hashes are checked and existing outputs never overwritten.
Reports record actions, financial/scoring components, final state and source
hashes. They may contain private squads; keep them outside Git. Frozen-action
replay is not proof that an adaptive system generated the actions causally.

## Evaluation

The [season protocol](../src/fpl_predict_resources/season_benchmark_protocol.json)
separates forecasts/commonplanner, planners/commonforecasts and native fullsystem
comparisons. Neutral starting-state tests and GW1squad construction are distinct.
Known-answer synthetic seasons validate mechanics, not historical performance.
Origin-safe horizon forecasts, multiweek planning, adaptive chips, full-season
baselines and named external adaptations are implemented and evaluated. The
[qualification workflow](season_policy_qualification.md) separates repeated
policy tests from earlier forecaster comparisons. Approved weights and normal
weekly defaults are unchanged; code merge does not promote a model or policy.

Rules checked16October2026 against [official rules](https://www.premierleague.com/en/news/4661029),
[chip guidance](https://www.premierleague.com/en/news/4679879/whats-happening-with-fpl-chips-in-202627)
and [2025AFCON transfers](https://www.premierleague.com/en/news/4362102/whats-new-in-202526-fantasy-extra-transfers-for-afcon).
API and historical snapshot checksums are retained. The dated readiness report
separates available markets from missing calendar/horizon evidence.


## Audit historical calendar inputs

```sh
fpl-predict season-readiness \
  --calendars /path/to/calendar-manifest.json --calendars-sha256 CALENDAR_MANIFEST_SHA \
  --bootstraps /path/to/bootstrap-manifest.json --bootstraps-sha256 BOOTSTRAP_MANIFEST_SHA \
  --calendar-root /path/to/calendars --bootstrap-root /path/to/bootstraps \
  --outcome-fixtures /path/to/fixture-history.csv --outcome-fixtures-sha256 HISTORY_SHA \
  --updates /path/to/reviewed-announcements.json --updates-sha256 UPDATES_SHA \
  --output /path/to/new-source-audit.json
```

The calendar manifest has `season` and38`entries`: `gameweek`, `captured_at`,
`publication_claim`, pinned `revision`, relative compressed `file`, raw `sha256`
and `compressed_sha256`. Bootstrap manifests follow the existing deadline-audit
schema (`season`, `snapshots`, withGW/file/hash/capture). Official announcement
updates are optional but require a checksum when supplied. Outcome CSV requires
only `season`, `gameweek`, `fixture`; none of its point values enters decisions.
The command checks coverage/clock/hash/root/result-contamination and compares
memberships without fitting a model. It flags unsupported active/future chip
configurations separately. A passing audit is source readiness, not a season
benchmark or first-publication certificate. See [dated findings](SEASON_READINESS_2026-10-16.md).
