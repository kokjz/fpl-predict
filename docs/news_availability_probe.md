# Experimental news and availability probe

[Measured fixed-experiment results](NEWS_AVAILABILITY_RESULTS_2026-10-16.md) are available; no production model was changed.

This fixed, small experiment tests whether timestamped availability/news observations add useful appearance information to recent match form. It does not reproduce Dastan, replace the incumbent or directly measure squad points. All historical outcome windows have already been inspected; they are reused descriptive evidence.

## Source question

The inspected [Dastan release](https://github.com/qazybekb/smartplayfpl-dastan/tree/758db9247e8b3a9a870c991064f74d8339d61cd0) lists predeadline FPL status/chance signals, set-piece information and age alongside FPL/Understat performance features. Its README's availability-only ablation reports a much smaller contribution than the overall architecture difference and cautions against inferring an advantage when ranking known starters. The release does not establish independent club-press-conference or injury-history NLP as the cause of our matched error gap. Those later ablations also do not isolate the cause in the retained original 2024/25 archive.

The available historical corpus is AIrsenal's archived **official FPL news/chance observations**, published as exact predeadline Git CSV prefixes. It is an external maintained archive, but its underlying news is FPL-syndicated, not an independent club-news corpus. The prior [source audit](AVAILABILITY_SOURCE_AUDIT_2026-10-15.md) verified eleven sample weeks. This package expands the same prefix/hash/bootstrap checks to every GW4–38 needed by the experiment. Missing observations/outcomes are not guessed or replaced with later values. Git dates are publisher evidence, not independent timestamp certification.

Independent club/league/press observations can be supplied to the evidence preflight through the schema below. Historical club articles, injury timelines and role text would require their own stable identities, publication/correction history and training-only text pipeline before entering a trained model. A crawler or live LLM summariser must not backfill what a later article says into an earlier forecast. No such broad crawler, paid feed, injury-history database or free-form LLM probability extractor is enabled here.

## Fixed experiment

The [versioned pre-fit protocol](../src/fpl_predict_resources/news_probe_protocol.json) declares four arms: prior-form logistic control, control plus structured chance/missingness, control plus news text, and control plus both. All use identical player-weeks, labels and a fixed regularised logistic estimator. Chance labels are learned inputs rather than assigned probabilities; missing chance stays an explicit unknown. Text uses training-only TF-IDF with at most 256 unigram/bigram features, min_df2. Numeric scaling fits training only. No parameter/seed search, outcome-selected vocabulary or binary model save occurs.

Train on 2025/26 GW4–19, report validation GW20–27, then report all arms on GW28–38. Validation does not choose an arm or change parameters. Primary contrast is combined-input versus form-control candidate mean per-GW Brier difference, with a descriptive four-GW moving-block interval. Reliability bins and high-probability misses accompany both all-player and predeadline-candidate results. This is a component/source-value experiment: the logistic control is **not** the production champion's full historical participation head.

Historical form is calculated strictly before publication minus a three-hour completion buffer, excluding same-GW history. Candidate membership depends on earlier history/minutes. The common cohort is the intersection of published rosters, independent bootstrap identities and available player-fixture outcome records. Missing fixture-history rows are counted/excluded uniformly, never filled with healthy/zero-minute assumptions; complete-market and unexpected-calendar handling remain separate tasks. The 35-week input contains 27,144 rows, with 409 published roster rows outside that common fixture-history cohort.

```sh
fpl-predict news-probe --input admitted-probe.csv --sha256 YOUR_SHA256 \
  --output /path/to/new/experiment
```

`prepare_frame` joins already admitted source observations to historical data; use `availability_history.admit_prefix` to verify all source prefixes first. Required normalized CSV fields are `season,gameweek,fpl_code,deadline,published_at,candidate,actual_minutes,news,chance_label` plus the `FORM` columns declared in the module. The tool verifies scope, duplicates, source timing, finite features and chance ranges, but cannot authenticate caller-supplied provenance. Keep proof records and source/input hashes. Run under the existing experiment watchdog for CPU/RSS/storage bounds. Expected outputs are immutable manifest/report/predictions; keep player rows outside Git.

## Independent news evidence, without automatic model changes

The [participation preflight](participation_audit.md) accepts optional `--evidence private/news.json`:

```json
{
  "schema_version": 1,
  "GW": 7,
  "recorded_at_utc": "2026-10-17T09:00:00Z",
  "players": [{
    "id": 123,
    "source_kind": "club",
    "source_url": "https://example.org/team-news",
    "published_at_utc": "2026-10-17T08:00:00Z",
    "checked_at_utc": "2026-10-17T08:50:00Z",
    "summary": "Synthetic example of a report that needs interpretation",
    "reported_availability": "out"
  }]
}
```

IDs/dates/text are illustrative. Use actual checked source statements; source_kind is club/league/press, reported_availability out/doubtful/available/unknown. URLs must be public HTTPS without credentials/query/fragment. Publication/check/record times must precede the evaluation time/deadline. Unknown or duplicate IDs and invalid chronology fail. Source kind/clock claims require human research; the tool does not authenticate a publisher or fetch/execute article instructions.

External reports flag inconsistencies even when official FPL status is `a`. Available/return reports never automatically clear existing flags. The output prompts an explicit sourced sensitivity review; it does not turn a headline into minutes or apply a multiplier to unconditional point forecasts.

## Integration gate

Even a positive Brier result only supports further research. A production change needs matched out-of-fold/current-method probabilities, independent chronological calibration, a properly specified conditional/full-points integration, ranking/legal-decision checks, and the existing promotion gates. One new source probe cannot establish why original Dastan wins, a current-season points gain or a safe predeadline model replacement. Keep the approved champion while using current direct news in the existing manually reviewed scenario workflow.
