# Reproducing the coherence study

This is an offline research workflow. It does not modify a runtime registry or
operate an FPL account. Keep downloaded data, trusted executable caches, model
binaries and generated results outside the source checkout. Use new output
folders for every run; preserve source bytes, checksums and failed attempts.

Start with the [diagnostic protocol](coherence_protocol_2026-10-26.json),
[calibration protocol](appearance_calibration_protocol_2026-10-26.json),
[historical source inventory](historical_2023_admission.json) and
[component results](COHERENCE_CALIBRATION_RESULTS_2026-10-26.md).
The code is included; historical archives and trained binaries are not bundled.

## Prepare the historical reference

Obtain the pinned bootstrap snapshots and Git-versioned fixture sources in the
source inventory. Calendar forecast views contain exactly `id`, `event`,
`team_h`, `team_a`, `kickoff_time`; raw result/stat columns remain audit-only.
Select the latest admitted calendar strictly before each bootstrap capture.
Never replace an earlier fixture schedule with its final season assignment.

`tools/prepare_season_2023.py` takes a JSON manifest with:

- `season`: `2023-24`; `training_seasons`: `2020-21`, `2021-22`, `2022-23`.
- `source_root`: the private archive directory.
- `inputs`: entries named `history`, `features`, `merged`, `players`, `teams`,
  `markets`, `calendars`, each with its `path` and SHA-256 `sha256`.
- The referenced markets document has `market_origins`: all 38 gameweeks,
  capture/deadline clocks, archive file names and compressed hashes, using the
  published inventory schema.
- The referenced calendars document has `entries`: all 38 matching origins
  with `as_of`, `source_clock`,
  whitelisted view file name and SHA-256, also as in the inventory.

The history/features are aligned trusted caches from the ordinary feature
pipeline. The tool checks the fixed prior-year mask and feature clocks. Pickle
and model loading require the explicit trust flag. Its initial pass audits all
origins and final listed-player outcome coverage before any estimator fits.

```sh
python tools/prepare_season_2023.py --manifest "$MANIFEST" \
  --manifest-sha256 "$MANIFEST_SHA256" --trust-local-cache \
  --output "$FPL_PREDICT_HOME/research/admission"

python tools/prepare_season_2023.py --manifest "$MANIFEST" \
  --manifest-sha256 "$MANIFEST_SHA256" --trust-local-cache --fit \
  --output "$FPL_PREDICT_HOME/research/prior-reference"
```

This fixed recipe saves a prior-only reference, a decision bundle, an evaluator
bundle and an audit report. It is not an approved deployment artifact. The
Bournemouth–Luton abandonment remains an unexpected GW17 event; later voided
points are used only for evaluation, with normal autosub/vice rules.

## Prepare and calibrate appearance sidecars

`tools/prepare_decision_availability.py` accepts a nonempty subset of the admitted
2023/24, 2024/25 and 2025/26 research profiles. Its manifest specifies, per season,
checksummed `history`, `model`, `decisions` and 38 `origins`. Each origin supplies
its calendar view, official-zero IDs derived from the frozen bootstrap and
source hashes. `receipts` lists additional checksummed admission documents.
The tool reproduces the point means before emitting a sidecar. It does not fit.

`tools/calibrate_appearance.py` then takes:

- `protocol` and `protocol_sha256` for the frozen calibration specification.
- `training`, keyed by year, with checksummed `markets` and `availability`
  entries plus `source_root` for the archived snapshots.
- `targets`, keyed by test year, with `training_season` and a checksummed base
  `availability` entry.

The declared pairs are 2023/24→2024/25 and 2024/25→2025/26. All prior training
labels must be available before every target origin. Only GW1–37 minute
increments observed in the next confirmed snapshot are eligible. This noisy
proxy has documented exclusions; do not use later corrected match outcomes to
choose training rows. The output contains the frozen cohorts, two JSON
calibrations, mapped sidecars and receipts. Unconditional point means, explicit
zero-support flags and raw pre-mixture probabilities remain unchanged.

## Evaluate decisions and continuous seasons

The optional `FirstActionSelection` API isolates the immediate XI/bench/captain
change while preserving a mean manager's transfers, chips and later proposals.
Freeze selections before loading evaluator outcomes. This conditional overlay
is distinct from an adaptive season replay.

The source-only `tools/run_repeatability_study.py` exposes `run_case` for an
entire 38-GW replay. Supply the admitted decision/evaluator bundles, frozen
appearance sidecar, one common opening roster, the named policy and a new
private output directory. Use the declared fixed-node/probe/seed settings and
run the full matrix serially under `experiment_runner` resource guards. Commit
only the first action and replan each deadline. Do not substitute different
budgets or combine partial failed paths into a successful season.

The adapted Solio comparison additionally requires the separately installed,
source-pinned [native runtime](native_planner_comparison.md). Its 2023/24 FT adapter is
separate from the newer-season AST. No external manager implementation or
third-party runtime is bundled here.

`tools/audit_season_path.py`, `tools/audit_native_trace.py` and
`tools/audit_decision_objective.py` provide separate financial, scoring, native
proposal and expected-objective checks. Compare complete repeated decision
fingerprints, not just totals. Aggregate every declared starting case with equal
season weighting. Keep the previous gates/results, unknown conditional bounds,
all failed attempts and source limitations. Neither a code merge nor a positive
historical comparison changes production approval.
