# Benchmarks and other options

## Performance and other options

The published v1 historical evaluation used 163,072 player-match records from 2020/21–2025/26. On 15,308 eligible candidate records across the 2024/25 and 2025/26 expanding-window tests:

| Method | Core-points RMSE ↓ | Core-points MAE ↓ |
|---|---:|---:|
| fpl-predict v1 | **2.900** | **2.101** |
| Last-five average | 3.175 | 2.365 |
| Recency average | 2.982 | 2.108 |

Eligibility uses prior history and lagged minutes, rather than selecting players by their eventual performance. Core points exclude the separately modelled defensive-contribution award. These results do not establish a captaincy or full-season points advantage. [Validation details and limitations](validation.md).

Related open-source projects take different approaches:

| Project | Approach | Relationship to fpl-predict |
|---|---|---|
| [OpenFPL](https://github.com/daniegr/OpenFPL) | Position-specific tree ensembles using FPL and Understat features | A broader ensemble approach; its published test window and cohorts differ, so headline errors are not directly comparable. |
| [Dastan](https://github.com/qazybekb/smartplayfpl-dastan) | Participation and conditional-return models blended with direct point predictions | A richer forecasting benchmark with retained historical predictions. |
| [AIrsenal](https://github.com/alan-turing-institute/AIrsenal) | Team-scoreline and player-involvement models connected to squad/transfer optimisation | A broader team-management framework using event-based forecasting. |

A separate matched retrospective comparison against Dastan covers 17,622 player-gameweeks in 2024/25 GW15–38. On the 5,145 players/gameweeks meeting fpl-predict's pre-deadline candidate criteria:

| Method | Full-points RMSE ↓ | Full-points MAE ↓ |
|---|---:|---:|
| fpl-predict v1 | 2.9765 | 2.1354 |
| Dastan | **2.8910** | **2.0204** |

On that same candidate cohort, v1 achieved higher **top-10 ranking quality**
(mean NDCG@10 **0.4937 versus 0.4878**, leading in 13 of 24 GWs). This is a
planning-relevant historical strength: it rewards putting high-return options
near the top, although it does not enforce squad constraints. The small lead has
an exploratory uncertainty interval spanning zero.

About **55% of Dastan's MSE advantage** comes from candidates who subsequently
recorded zero minutes. Known unavailable players can be excluded using predeadline
evidence, but unexpected non-appearances remain important selection errors and
must stay in the comparison. Dastan also has lower error among 60+ minute players.
The [decision-relevance explanation](comparison_interpretation.md) gives the
full decomposition, source limitations and distinction between measured wins and
unproved general superiority.

Dastan had about 2.9% lower RMSE on those matched records. Training policies and feature sets differ, and this is an archived retrospective comparison, not a prospective competition. Do not compare this table directly with the core-points table above: the periods and targets differ. [Comparison methods, provenance and aggregate results](open_source_comparison_2026-10-14.md).

A [practical selection benchmark](SELECTION_BENCHMARK_RESULTS_2026-10-15.md)
compares realised lineup points, budgeted squad construction and rolling transfers
under one shared policy. In the 2025/26 GW28–38 window the incumbent leads the
measured squad-reset and rolling totals against named-method adaptations; the
primary owned-squad comparisons remain inconclusive. A separate replay of original
Dastan forecasts shows a small, inconclusive +0.198 points/GW lead for Dastan.
These retrospective results do not establish parity or superiority over the
original external systems, and no model was promoted. The report includes
coverage, uncertainty, source distinctions and measured execution cost; the
[workflow](selection_benchmark.md) explains how to test your own forecasts.

The [availability follow-up and six-method rebenchmark](INCUMBENT_AVAILABILITY_RESULTS_2026-10-16.md)
adds a tested research challenger on the same historical market and policy. It
improves weekly reset scores but slightly loses owned-squad and rolling-transfer
scores against the incumbent control; it is not promoted. Original Dastan results
above remain separate from this 2025/26 Dastan-architecture adaptation.

The [conditional-integration follow-up](CONDITIONAL_SELECTION_RESULTS_2026-10-16.md)
adds another fixed historical comparison. Its unapproved challenger has observed
RMSE 2.94125 versus 2.95404 for the Dastan adaptation, but higher MAE; the paired
RMSE interval crosses zero. This is not an original-Dastan or general superiority
claim. The report also separates mean-policy forecast value from the new selector.

For shared-row comparisons against other systems, see the [external benchmark
protocol](BENCHMARK_PROTOCOL.md), [source readiness inventory](benchmark_sources.json)
and [local import workflow](benchmark_workflow.md). The optional
`fpl-predict benchmark` command validates local exports and produces aggregate
coverage/error/ranking reports and [bounded evaluation diagnostics](benchmark_evaluation.md).
An explicit [resource-controlled runner](experiment_runner.md) is available
for separately authorised experiments. These tools do not promote models.
The [reference source audit](REFERENCE_SOURCE_AUDIT.md) distinguishes verified
inputs from unresolved provenance. An explicit [retrospective reference pilot](reference_pilot.md)
can measure full-score baseline errors and fitting cost without changing the approved model.
The optional [deadline/provenance audit](deadline_provenance.md) checks
historical bootstrap captures and player/team/opponent source-time contracts
separately from accuracy scoring.
See the [dated provenance findings](PROVENANCE_FINDINGS_2026-10-15.md) for
verified inputs, observed temporal concerns and remaining reference-fit gates.
A separately named [native-window reference pilot](native_reference.md)
rebuilds histories at common deadlines under a [pre-fit protocol](NATIVE_REFERENCE_PROTOCOL.md).
It is research tooling; merged code does not replace approved forecasting weights.
The optional [native development study](native_development.md) tests a fixed
set of richer-history challengers with chronological error and decision gates.
An offline [availability source audit](AVAILABILITY_SOURCE_AUDIT_2026-10-15.md)
checks exact historical CSV prefixes against pre-deadline Git publication records.
The optional [conditional architecture reference](conditional_reference.md)
uses an explicitly installed research dependency and a separately frozen protocol.
The [prospective validation handoff](PROSPECTIVE_VALIDATION_HANDOFF.md)
describes pre-deadline comparison locks and read-only reviews of finalised trials.


Back to the [project overview](../README.md).
