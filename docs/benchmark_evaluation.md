# Shared-row evaluation extension

The benchmark report schema is now version2. Original coverage, candidate/all-row
metrics and separate all-model/pairwise intersections remain available. The
[admission protocol](BENCHMARK_PROTOCOL.md) is unchanged; evaluation settings are
separately versioned in `fpl_predict_resources/benchmark_evaluation_protocol.json`
and its checksum is recorded in each report. No training or promotion is involved.

## Paired gameweek-block uncertainty

For each intersection's predeadline candidate cohort, report pooled RMSE and MAE
differences for every pair. Negative left-minus-right error favours the left model.
Use1000paired circular block-bootstrap draws with four-GW blocks, fixed seed20261015,
and95% percentile intervals. Aggregate counts, squared errors and absolute errors
per gameweek before resampling; do not materialise resampled player rows.

Blocks stay within a season and contiguous observed-GW segment, so they never
cross missing weeks or season boundaries. Preserve each segment's number of weeks
and recompute pooled errors using sampled row counts. Report segment lengths;
without at least one eight-GW segment, return an explicit insufficient-data status
rather than an interval. Eight weeks is a conservative reporting rule, not proof
of reliable inference; short/small samples still require caution.

These are descriptive intervals for fixed predictions. They do not capture
training-seed uncertainty, correct repeated-test selection bias or adjust for
multiple pairwise comparisons. They are not independent confirmation, a promotion
gate by themselves, or a claim of extra captain/season points. No ranking-metric
confidence intervals are supplied. Do not select a winner retrospectively from
many inspected intervals.

## Optional outcome metadata

In addition to the normal outcome columns, verified exports may contain:

| Column | Validation and use |
|---|---|
| `position` | Integer1–4, identical within player-GW; position error breakdowns |
| `n_history` | Nonnegative predeadline record count, identical within player-GW; under3 cold-start diagnostic |
| `minutes` | Integer0–90 per fixture, zero for explicit blanks; sum doubles for played/not-played diagnostics and squad scoring |

Invalid metadata is rejected before intersections are chosen. A declared candidate
with fewer than3prior records is inconsistent and rejected. These fields' actual
historical provenance still needs manual review. Missing metadata remains absent;
it is not fabricated. Realised-minute slices are diagnostic and never redefine
the primary predeadline candidate pool. Existing errors/ranks are calculated on
identical rows for every model inside each slice.

## Supplied fixed-squad panels

Optionally add `--squads /path/to/private/panels.json` to `fpl-predict benchmark`.
The exact panel file is hashed into the output. It contains:

```json
{
  "schema_version": 1,
  "panels": [
    {
      "id": "panel1",
      "season": "2025-26",
      "gameweek": 28,
      "origin": "retrospective_fixed",
      "inputs_as_of": "<actual timezone-aware predeadline input cutoff>",
      "created_at": "<actual timezone-aware panel creation timestamp>",
      "players": [
        {"fpl_code": 123, "position": 1, "team": "example-club", "price_tenths": 45}
      ]
    }
  ]
}
```

The example shows structure only: supply all15players, with two goalkeepers,
five defenders, five midfielders and three forwards; at most three per club and
an initial total budget of1000tenths (£100m). Supply1–100uniquely named panels.
Prices, positions, club and selection basis must genuinely be available at the
stated cutoff and independently reviewed. The evaluator does not choose panels
from realised returns. A supplied retrospective panel is not an untouched or
prospective selection test. `archived_predeadline` additionally requires actual
creation before the deadline; do not backdate a panel assembled later.

All models must cover all15players and outcomes must include every player,
including explicit verified blanks. Any missing method/player makes the whole
panel ineligible across all methods. There is no zero-fill or favourable model
subset. Supplied positions are checked against outcome metadata when present.

Every model uses the same legal-XI/captain selector and its own forecasts, then
the existing realised scorer applies goalkeeper/outfield autosubs and ordinary
captain/vice fallback. The selection objective does not optimise expected autosub
value. Reports contain aggregate points per method/panel and mean panel points,
not player rows. There are no transfers, hits, chips or evolving squad finances;
this is not a complete season-strategy backtest. Multiple panels/weeks are
correlated and mean points have no implied independent significance test.

Keep all raw exports/panels/generated reports private unless audited for public
release. No forecast or squad action occurs simply by installing these tools.
