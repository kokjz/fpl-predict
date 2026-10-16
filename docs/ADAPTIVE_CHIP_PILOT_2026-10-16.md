# Chip/scenario mechanical pilot — 16 October 2026

The optional [adaptive planner](adaptive_planner.md) now supports the four chip
types, a legal remaining-season opportunity calendar and shared scenario plans.
This pilot checks integration and resource cost. **It does not measure actual
season points or establish superiority over an equally equipped planner.**

Source and the [fixed protocol](../src/fpl_predict_resources/adaptive_chip_protocol.json)
were published at `7845f65e07a47bc9b09cf1f12574f1315214fb34` before this run.
The [aggregate results](ADAPTIVE_CHIP_PILOT_2026-10-16.json) retain input hashes,
search limits, scenario objectives, financial ledgers and the following caveats.

Two previously frozen historical inputs were reused: a six-week horizon from
2025/26 GW20 and a one-week horizon at GW38, both from neutral research squads.
There was no new fit, download, model selection or user-squad recommendation.
For each, the two illustrative equal-weight scenarios were the original grid and
a manually halved forecast for one snapshot-flagged owned player where available,
otherwise the highest-mean owned player. The scale/weights are stress assumptions,
not calibrated injury or recovery probabilities.

| Origin | No-chip objective on the same scenarios | Chip-plan detailed objective | Coarse reserve | Search time | Trials |
|---|---:|---:|---:|---:|---:|
| GW20, six weeks | 327.027 / 327.027 | 378.603 | 8 | 60.18s | 33 |
| GW38, one week | 38.746 / 38.702 | 59.580 | 0 | 0.58s | 5 |

These objective values include terminal, reserve and churn proxies. The adaptive
planner has chip access; the control does not. Their difference checks that chips
enter the expected objective correctly, rather than proving better management.
The selected squads avoided the affected player in both cases, so their scenario
objectives coincide. The pilot demonstrates no measured news-response gain;
synthetic tests separately verify that fresh injury assumptions can change a
replanned captain.

The GW20 research plan uses WC/TC/BB inside its horizon and reserves FH outside it.
The reported coarse FH position at GW38 is an arbitrary tie under constant future
values, **not an evidence-based recommendation to wait until GW38**. The GW38
research plan uses a Free Hit. No such decision applies to a current manager.
Every first/provisional action and financial transition is validated; Free Hit
returns the original ledger and bank. Single-chip probe gains are only scheduling
approximations; combined candidates are re-evaluated using their actual objective.

The six-week search reached its configured budget and retained a validated
candidate. Some individual solves stopped with a gap, at most **0.2711%** among
these trials. This is a fixed-schedule solver gap, not a bound on the outer chip
search's quality. Search budgets are checked between calls; ordinary setup and
validation overhead explains the small overshoot beyond 60 seconds. The one-week
case finished without exhausting its budget.

The complete supervised job took **69.36 seconds**, with **595,689,472 bytes**
(about 568 MiB) peak sampled RSS and two CPU threads. Storage/memory/time limits
held; no separate GPU or larger compute system was required. There was no new
training or model/policy promotion. Tests include exhaustive two-week squad/chip
searches, Free Hit purchase-basis/terminal restoration, saved-FT interactions,
chip expiry/calendar collisions/consecutive restrictions, weighted scenario
objectives, fresh-evidence replanning and the write-once command contract.

The next stage must carry initial choices through all 38 deadlines, with prices,
news and schedules revealed at each origin. Compare common chip access, own
opening squads and common-state variants. Then compare admitted external
forecasts and planners on those same rules and origins. Full-season utility,
native external superiority and exact expected autosub optimisation remain
unestablished; the approved weekly forecaster is unchanged.
