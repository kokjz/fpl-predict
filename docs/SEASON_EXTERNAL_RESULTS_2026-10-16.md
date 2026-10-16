# Matched full-season forecast references

16 October 2026. **Sixteen complete 38-GW research paths, not a validated general winner or model promotion.** The primary outcome is realised season points after transfer hits. Every path maintains its squad, cash, original purchase basis, free transfers and chips across all 38 deadlines. It replans from origin-available information and commits only the immediate action.

See the [frozen protocol and contracts](season_external.md), [machine-readable aggregate](season_external_results.json) and [dated source inventory](season_external_sources.json). The five forecasting learners use the same six-GW planner, restricted-pool procedure, four-second outer budget, half-second inner limit and at most twelve chip trials. All four chips are managed across the two historical chip windows. Own-opening paths choose a squad; common-opening paths start with the same source-only neutral fifteen and retain the full future transfer market.

## Revised source: all sixteen paths

| Forecast / planner | Own opening: net / hits | Common opening: net / hits |
|---|---:|---:|
| Standing-method HGB, four-year fit | 2088 / 28 | 2134 / 44 |
| Native-window HGB reference | 2041 / 36 | 1971 / 60 |
| Dastan-architecture adaptation | 2116 / 16 | 2014 / 32 |
| OpenFPL cv1 adaptation | 2130 / 12 | 2132 / 12 |
| Conjugate/Poisson component adaptation | 2032 / 44 | 2037 / 64 |
| Standing-method HGB, five-prior-season fit | 2157 / 28 | 2156 / 36 |
| Four-year HGB, one-week planner | 2121 / 44 | 2109 / 48 |
| Archived official EP, one-week planner | 1862 / 184 | 1907 / 188 |

The first six rows use the six-week planner. The last two use a one-week planner with the same chip machinery. Official EP is never extended into future gameweeks. Hits are already subtracted from net points.

Within the matched four-year HGB forecast, six-week minus one-week totals are -33 points with own openings and +25 with the common opening. These are two dependent starting-state sensitivity cases from one season, not independent season replications.

Both the four-year matched-training control and the separately predeclared five-prior-season standing-method control are retained. A favourable control is not selected after seeing results. The saved approved artifact includes part of this evaluation season in its training and is therefore not backcast; these are prior-only research fits of methods. External references are named adaptations, not original providers’ released systems.

## Secondary point errors

Current-origin player-GW totals use 29,645 complete market records, including verified blanks. The shared pre-deadline candidate cohort has 7,627 records across 35 ranking weeks: at least three current-season prior records and last-five mean minutes of at least 45. Candidate identity never depends on eventual minutes or points.

| Forecast | Candidate RMSE | Candidate MAE | Mean within-GW NDCG@10 |
|---|---:|---:|---:|
| Standing-method HGB, four-year fit | 2.96883 | 2.11565 | 0.38123 |
| Native-window HGB reference | 2.96316 | 2.09903 | 0.38062 |
| Dastan-architecture adaptation | 2.95843 | 2.08453 | 0.38472 |
| OpenFPL cv1 adaptation | 2.97615 | 2.18057 | 0.35200 |
| Conjugate/Poisson component adaptation | 3.02472 | 2.26293 | 0.38553 |
| Standing-method HGB, five-prior-season fit | 2.96319 | 2.11261 | 0.39774 |
| Archived official EP, one-week only | 3.32934 | 2.39521 | 0.34487 |

Core learners fit 2020/21–2023/24; 2024/25 is used only where a recipe requires early stopping or calibration. No 2025/26 outcome fits or selects a learner. The fixed HGB learners do not use the validation season for selection. Recent-data weighting and intrinsic calibration usage differ by recipe. A common prior-only appearance-capped EWDC component is added after removing identified historical DC awards from core labels and point-history features. Other historical scoring differences remain limitations.

Error and ranking are diagnostics. Lower RMSE does not by itself establish better 38-GW management, and this table is not directly comparable to the separate original-Dastan 2024/25 archive.

## Retained initial experiment and repair

The initial fixed protocol attempted every path before the repair. Fifteen completed; the component own-opening path failed before GW1 when a short baseline solve could not certify an optimal roster. It is not scored as zero or silently discarded.

| Forecast / planner | Own opening: net / hits | Common opening: net / hits |
|---|---:|---:|
| Standing-method HGB, four-year fit | 2088 / 28 | 2134 / 44 |
| Native-window HGB reference | 2041 / 36 | 1971 / 60 |
| Dastan-architecture adaptation | 1989 / 32 | 2035 / 32 |
| OpenFPL cv1 adaptation | 2094 / 24 | 2134 / 8 |
| Conjugate/Poisson component adaptation | **failed** | 2062 / 60 |
| Standing-method HGB, five-prior-season fit | 2156 / 28 | 2125 / 40 |
| Four-year HGB, one-week planner | 2121 / 44 | 2109 / 48 |
| Archived official EP, one-week planner | 1862 / 184 | 1907 / 188 |

A source-only minimum-cost position/club flow fallback now supplies a legal affordable opening squad when that baseline solve fails. It does not fix the main point solver’s choices. Existing held-squad fallbacks remain unchanged. The revised experiment reruns **every arm**, with unchanged frozen forecasts, fitting recipes, search budgets and parameters, in new evidence directories. Initial results remain separate. Changes between tables also reflect short wall-time search variability; they do not isolate a causal point gain from the repair.

## Cost and solution quality

The revised sixteen management jobs took 25.51 measured minutes in serial; the largest sampled worker RSS was 533.3 MiB. Feature preparation and learner fitting are additional. Each optional learner fit took at most 68.03 seconds in this run; the largest sampled fit RSS was about 1.79 GiB. Jobs used two CPU threads with a resource watchdog; no GPU was used. These are measured research jobs, not a promise of future runtime.

Selected fixed-schedule bounds were unavailable at 87 of 608 deadlines; missing bounds remain unknown. The largest known selected relative gap was 0.169990. These bounds cover the retained feasible plan’s restricted pool and heuristic point objective only. The outer chip-search/global season bound is unknown. Time exhaustion and all per-path bound counts are in the aggregate. No near-optimal season claim follows from small conditional gaps.

## Interpretation and remaining work

One reused season cannot establish consistency or future superiority. Training clocks for older statistics are reconstructed; mutable archives and capture/publication claims are not independent historical availability certificates. Missing news stays unknown, and the common official-zero availability interpretation is current-GW-only and experimental. Official EP has complete observed coverage here but unreported publisher training lineage.

Native/common-forecast external-planner comparisons, bounded repeatability and joint-system qualification remain separate stages. These results do not change the approved model, normal weekly defaults or model-promotion gates.

Primary sources: [Dastan](https://github.com/qazybekb/smartplayfpl-dastan), [OpenFPL](https://github.com/daniegr/OpenFPL), [AIrsenal](https://github.com/alan-turing-institute/AIrsenal). [Attribution and adaptation scope](../THIRD_PARTY_NOTICES.md).
