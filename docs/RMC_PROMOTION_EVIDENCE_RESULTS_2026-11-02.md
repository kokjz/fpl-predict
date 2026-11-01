# Rich-market promotion evidence: source-policy stop

Date: 2 November 2026. Status: stopped before data retrieval or fitting.

This package planned promotion evidence for the [PR50 rich-history and
market-strength combination](RICH_MARKET_COMBINATION_RESULTS_2026-11-02.md):
retrospective audits using frozen 2024/25 predictions and a new 2025/26 fold,
followed by 2026/27 corroboration. The historical component results remain
recorded in that earlier study; they do not establish deployability.

## Frozen design

The [promotion-evidence protocol](rmc_promotion_evidence_protocol_2026-11-02.json)
was frozen and pushed before source review or any data retrieval or calculation:

- Freeze commit: `11db028648c6a12f12f2782d219e4cbf7627fecc`.
- Protocol SHA-256 after CRLF-to-LF normalisation:
  `d5e3bc236269abd0e3146cd345d2cfba7c78fbfd7ff95cdd07016b144d963ae8`.

The initial brief, pe-r1, left the chronological defensive-contribution inputs
and final scoring window unspecified and requested a historical publication-time
replay that the sources cannot support. Before the freeze or any numerical work,
pe-r2 specified a shared, strictly lagged `2 * dc_rate4` term (zero for goalkeepers)
on 2025/26 GW28–38 candidate rows, without extra fits or an appearance-probability
cap. It also replaced the historical availability gate with a non-gating snapshot
observation. Historical source publication lag would remain unmodelled; a
prospective availability test would require a separate deployment package.

## Finding and disposition

The [Understat robots policy](https://understat.com/robots.txt), checked on
2 November 2026 and independently confirmed during review, specifies:

```text
User-agent: *
Disallow: /
```

The brief requires stopping when a source's robots policy forbids automated
retrieval. The combination's RICH inputs depend on Understat's league and
player-match data. Its specified live inputs therefore cannot be supplied in a
compliant way under the checked policy. **The PR50 combination is not a promotion
candidate in this form.** No alternative route, mirror or third-party copy was
used, and no provider was contacted.

The [Football-Data data page](https://football-data.co.uk/data) describes private
individual use and excludes commercial or data-training products using automated
bots, scrapers or AI. Its [fair-use notes](https://football-data.co.uk/contact.php)
describe personal betting or academic research use with manual or light automated
download, at most twice per week. These policy statements are reported without
adjudicating permission for this study; the Understat finding independently
stops it. The reported twice-weekly data-update schedule does not certify
availability before any particular FPL deadline.

## Execution and gates

| Item | Outcome in this package |
|---|---|
| Dataset retrievals | 0; none of the four planned retrievals attempted |
| Fits and scoring | 0 fits; no new forecasts or scores |
| Stage A admission | Stopped during source-policy review; coverage, reconciliation and eligible-row counts not evaluated |
| Promotion gates 2–8 | Not evaluated; no pass or numerical failure claimed |
| Integrity gate | Deferred; no artifact built, saved or registered |

Source review ran before the planned numerical implementation and CI; this
exposed the source restriction before any data request. The published protocol
and its synthetic test were validated. No numerical evaluation implementation
was completed, so those checks do not qualify an audit or a current-season run.
The stop is a source-feasibility finding, not a measured loss of prediction
accuracy. Earlier PR50 results and their limitations remain unchanged.

**Approved 1.0.0 unchanged; nothing promoted.** No registry, weekly defaults,
product ingestion or consumer behaviour changed. Any compliant redesign needs a
separate specification and authorisation before data retrieval or experiments.
