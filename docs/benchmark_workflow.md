# Import and compare external forecasts

Read the [locked protocol](BENCHMARK_PROTOCOL.md) and [source readiness
inventory](benchmark_sources.json) first. This workflow validates supplied exports;
it does not reconstruct data, run external models, train, fetch forecasts or
approve a new champion. The actual three-way historical comparison remains
blocked by the readiness items in that inventory.

## 1. Prepare a verified outcome universe

Supply a local CSV or JSONL table with these columns:

| Column | Meaning |
|---|---|
| `season` | `2024-25`, `2025-26` or `2026-27`; other seasons need a protocol update |
| `gameweek` | Integer 1–38 |
| `fpl_code` | Positive stable player code; seasonal element IDs are inadmissible |
| `fixture` | Positive fixture ID; 0 is an explicit verified blank placeholder |
| `actual` | Full points for that fixture, under that season's rules |
| `candidate` | Frozen pre-deadline candidate predicate; JSON boolean or CSV `true`/`false` |
| `deadline` | Timezone-aware gameweek deadline, identical for both fixtures of a double |

Every expected fixture must be present for each declared player-gameweek. A blank
is one row with fixture=0 and actual=0. Confirm schedule/outcome finalisation and
candidate provenance independently before hashing the table. This importer cannot
prove a candidate flag was actually calculated from earlier history or that an
outcome schedule has not omitted a fixture. Fix that universe before evaluating
any system, rather than selecting favourable rows after seeing errors.

## 2. Prepare one local export and manifest per method

Exports need `season`, `gameweek`, `fpl_code`, `prediction` and, for fixture-grain
exports, `fixture`. A complete player-GW export already includes both fixtures.
Fixture exports must include the entire double or omit that player-GW entirely.
An optional `actual` column is checked against the outcome universe. Extra source
columns are ignored; absent predictions are not imputed.

Seasonal ID bridges must be audited and joined upstream; the importer deliberately
does not guess identity mappings. There is no direct raw-parquet reader dependency.
Convert reviewed sources to CSV/JSONL outside the operational environment if
needed; do not execute third-party model binaries.

Example manifest structure (replace every illustrative value with verified ones):

```json
{
  "schema_version": 1,
  "model_id": "reference_method",
  "file": "forecast.csv",
  "grain": "player_gameweek",
  "prediction_kind": "retrospective",
  "horizon_gameweeks": 1,
  "target_by_season": {"2025-26": "fpl-total-2025-26"},
  "source_url": "https://example.org/reference",
  "source_revision": "0000000000000000000000000000000000000000",
  "code_sha256": "<64 lowercase hex characters>",
  "data_sha256": "<64 lowercase hex characters>",
  "input_sha256": "<SHA256 of the exact local forecast CSV bytes>",
  "columns": {"gameweek": "gw", "prediction": "xpts"},
  "timing": {
    "train_cutoff": "2025-05-01T12:00:00Z",
    "selection_cutoff": "2025-06-01T12:00:00Z",
    "features_cutoff": "2026-01-01T09:00:00Z",
    "created_at": "2026-10-15T09:00:00Z"
  }
}
```

Only one-gameweek forecasts are admitted; multi-gameweek totals must not be
relabeled as next-GW forecasts.

The example is structural, not evidence of an admissible real model. Source
revision must be an immutable 40-character commit or 64-character content hash.
Source URLs must use HTTPS without credentials, query strings or fragments. `file` is
resolved relative to its manifest; explicitly supplied absolute paths are also
accepted. `columns` maps canonical names to actual export columns. The mapping
must be one-to-one and cannot alias another implicitly selected canonical column.

`timing` gives explicit per-export defaults; row columns override those defaults
for exports spanning many deadlines/refits. For both modes the training and
selection cutoffs must precede the deadline and be no later than the feature
cutoff; all cutoffs must precede forecast creation. These fields mean the latest
information used, including tuning/calibration, not the wall-clock time a later
retrospective fit ran.

For `archived_predeadline`, additionally supply `captured_at` with independently
reviewed archive evidence. Creation <= capture < deadline is required. A forecast
first frozen after the deadline is inadmissible in this mode. Do not backdate a
retrospective forecast; retain its real later `created_at` and use `retrospective`.

Declared code/training-data hashes and timestamps require source review. The CLI
verifies supplied export bytes and the supplied outcome hash itself; it does not
possess the source training data or prove the declared cutoffs were obeyed.

## 3. Run the comparison

Use at least two distinct manifests and a new output path:

```sh
fpl-predict benchmark \
  --outcomes /path/to/private/outcomes.jsonl \
  --outcomes-sha256 <verified-outcome-SHA256> \
  --manifest /path/to/private/incumbent.json \
  --manifest /path/to/private/reference.json \
  --output /path/to/private/reports/comparison-001.json
```

The result records protocol, outcome, manifest and export checksums, declared
source/timing metadata, total and candidate coverage, and separate all-model and
pairwise intersections. Each intersection contains candidate and all-row metrics.
An empty intersection is explicit: zero rows and null metrics, not a fabricated
winner. Pairwise tables may cover different rows, so their scores cannot be
combined into a universal ranking. Ranking-week counts expose constant/small
cohorts. Reports contain no individual prediction rows or local input paths.

Inputs are bounded to 64MiB/file and one million rows/table, with at most twelve
methods. These are admission bounds, not a promised memory ceiling; use smaller
chunks/exports on constrained machines and profile separately before large runs.
No output file is created on validation failure. Existing reports are never
overwritten. Keep all exports, manifests and generated reports outside Git; review
aggregate/source metadata before choosing to publish any report.

This first package has no confidence intervals, squad replay, historical source
reconstruction or runtime profiler. Those belong to later explicitly scoped
work; none of the current output establishes season-point gain or model promotion.


## Preflight before scoring

`fpl-predict benchmark-preflight` accepts the same input/output arguments as
`benchmark` and records contract failures without calculating accuracy metrics.
`all_contracts_valid` means the declared schema/timing/target contracts passed;
it never certifies the actual training provenance or grants model promotion.
Malformed files/checksums still fail before a report is created.

A library adapter `benchmark_readiness.join_seasonal_bridge` converts an
OpenFPL-labelled element/GW CSV using an explicit one-season fixture/code bridge.
It requires exact key coverage and rejects ambiguous doubles and conflicting IDs.
It adds no dates, model identity or missing predictions. Review and provide those
separately in the manifest before using the generic importer.

On 15 October 2026, an alternative GitHub contents endpoint supplied the complete
pinned OpenFPL-labelled CSV. Its publisher checksum matches; all18,173 rows join
the bridge and the independent historical full-score table without conflicts.
922 rows differ from core points, confirming that target alignment is material.
This closes file retrieval/integrity only. Training/exporter lineage, capture
provenance and a comparable incumbent full-score window remain open. The CSV is
not redistributed and no model scores were calculated by this readiness audit.

The next full-score fit design is specified in [the pilot run plan](BENCHMARK_RUN_PLAN.md).
It resolves the proposed scoring window without claiming new forecasts exist.
