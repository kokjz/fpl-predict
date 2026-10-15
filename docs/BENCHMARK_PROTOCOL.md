# Matched external benchmark protocol — version 1

Specification frozen 15 October 2026. This package establishes source readiness,
import safeguards and repeatable scoring. It does not fit models, establish a new
accuracy ranking, or change the approved model. The machine-readable contract is
[`benchmark_protocol.json`](../src/fpl_predict_resources/benchmark_protocol.json).

## Questions and scope

Start with the incumbent, Dastan and original OpenFPL. Treat OpenFPL Scout AI as a
separate project. Add other systems only when their inputs and evaluation
provenance meet this protocol. Keep two tracks separate:

- Archived forecasts describe the documented historical system and its native
  inputs. Only independently evidenced capture before a deadline qualifies as an
  archived pre-deadline forecast.
- Retrospective refits reproduce a method using historical cutoffs. Their actual
  creation date remains the later date. Matching training/selection windows and
  update cadence is required for a controlled method comparison. Native-feature
  comparisons measure systems; common-feature ablations measure learners.

All current historical windows have already been inspected during research.
They must be labelled retrospective evidence, never newly untouched tests. Source
metadata is an audit assertion, not proof that a model really obeyed it.

## Locked definitions

- Horizon: next gameweek. Grain: stable FPL player code plus season and gameweek.
- Target: full FPL points under the rules for that particular season, including
  applicable defensive-contribution awards. Do not equate core and full points
  unless their equivalence is verified for that season.
- Primary cohort: pre-deadline candidates using >=3 prior match records and a
  last-five mean of >=45 minutes, frozen once per player-gameweek. Candidate
  membership must not use realised minutes or points. All-player scores are
  secondary; realised-starter/return-band analyses are diagnostic only.
- Primary metric: pooled candidate player-gameweek RMSE. Also report MAE, bias,
  mean within-GW Spearman and NDCG@10 (negative actual gains clipped to zero).
  Constant-outcome weeks cannot support rank discrimination and are excluded
  from ranking averages with the usable-week count reported.
- Every comparison uses exactly the same rows for every method in that table.
  Report all-model intersection and each larger pairwise intersection separately,
  with total and candidate coverage. Do not combine different intersections into
  a single leaderboard. Missing predictions remain missing, never zero-filled.
- Both fixtures of a double share the same pre-deadline information. Fixture
  predictions are summed only when every expected fixture is present. Incomplete
  doubles fail; entirely absent player-gameweeks reduce reported coverage.
  A blank player-gameweek may be represented explicitly by fixture=0 and actual=0
  in a verified schedule; do not fabricate a played fixture for a blank.
- Reject conflicting IDs, duplicate keys, inconsistent deadlines/candidates,
  nonfinite values, unsupported targets, overlapping column mappings, unrecognised
  records and conflicting source outcomes before choosing matched subsets.
- Require timezone-aware feature, training and selection cutoffs before the
  deadline. For historical forecasts also require creation <= capture < deadline.
  Retrospective generation after the deadline is allowed and labelled accordingly.

## Data readiness and the historical window

The [source inventory](benchmark_sources.json) records eligibility and unresolved
items. The existing 2024/25 Dastan comparison remains a separate reference.
2025/26 GW1–24 is a **provisional** OpenFPL comparison window, not an executable
training specification. Original incumbent OOF predictions exclude defensive
contribution; the separate full-score evaluation covers GW28–38. Until full-score
forecasts with valid historical cutoffs are available, a three-way ranking is
blocked. Do not attach a future-trained component or silently remove awards.

Any changed cold-start/DC method is a separately named benchmark variant, not
unmodified v1. Before fitting, lock training/validation/test windows, feature
provenance, refit schedule, seeds and selection rules in a separate run manifest.
External shipped weights may have seen the proposed test season. Never use those
weights to manufacture historical forecasts.

## Implementation and admission checks

`fpl-predict benchmark` reads explicitly supplied local CSV/JSONL exports and
manifests. No external model code, serialised model weights, downloads or training
are executed. A column-mapping adapter accepts player-GW or fixture predictions;
season-specific element-to-code bridges must be joined and audited upstream.
The tool does not guess player identities or infer missing timestamps.

Reports retain source/protocol/outcome/input checksums, origin, cutoff ranges,
coverage and separate intersection metrics, but no individual rows or local
paths. These reports still require manual source and licence review before public
release. SHA fields for code/training data are declarations unless those assets
have also been independently audited; export and supplied outcome bytes are
verified directly by the CLI.

The [evaluation extension](benchmark_evaluation.md) adds descriptive paired
four-GW-block RMSE/MAE intervals, optional position/history/minute diagnostics and
supplied fixed-squad replays. Its settings are separately versioned and hashed;
the original admission protocol remains unchanged. Resource supervision is an
explicit separate [runner](experiment_runner.md), never automatic training.
Promotion/season-gain claims still require valid provenance and independent
validation; these tools do not supply that evidence by themselves.

## Later pilot and promotion

A later explicitly authorised pilot should profile one fit before expanding
folds/seeds, initially two CPU threads, one fit at a time, no paid services, a
proposed 30-minute/method and two-hour total computation cap, and a memory limit
chosen against free RAM. Enforce caps with an external supervisor; this import
command is not a training/resource supervisor. No reference runtime is promised.

Future improvements must pass the existing development screen and independent
error, point-relevance and integrity gates. Retrospective analysis cannot replace
prospective validation: freeze future forecasts at the same deadlines in normal
user-triggered planning cycles. Six to eight weeks is an initial review interval,
not proof or automatic promotion. No scheduled collection is enabled here.

## Sources

- [Dastan data and archived exports](https://github.com/qazybekb/smartplayfpl-dastan/blob/758db9247e8b3a9a870c991064f74d8339d61cd0/docs/DATA.md)
- [Dastan/OpenFPL benchmark implementation](https://github.com/qazybekb/smartplayfpl-dastan/blob/758db9247e8b3a9a870c991064f74d8339d61cd0/dastan/benchmark_openfpl.py)
- [Chronological validation and selection leakage](https://scikit-learn.org/stable/modules/cross_validation.html)
