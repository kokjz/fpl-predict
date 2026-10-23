# Expected season-points evaluation

A useful FPL management policy can lose an individual gameweek, starting-squad
case or season. Our objective is expected net points across all 38 gameweeks, with
an explicit tolerance for downside, rather than victory in every historical run.
The earlier no-negative-opening consistency gate and all its results remain
unchanged. Failure of that narrow gate is not proof that H6 is inferior.

## Declared new research criteria

The [fixed protocol](season_expected_points_protocol_2026-10-24.json) predates
all twelve new policy scores. H1 and H6 share forecasts, opening membership,
prices, transfer rules, chip resources and canonical XI/captain selection within
each season. The source-pinned Solio core is an adaptation under the same outer
chip planner and forecast inputs; this is not its original complete manager.

The primary comparison is H6 minus H1 net season points after transfer hits. Average
the two opening differences within each season, then weight the two seasons
equally. Declared historical research support requires a strictly positive mean,
no season-average loss greater than 19 points and no single-opening loss greater
than 38 points. Small positive gains can qualify. The downside allowances correspond
to 0.5 and 1 point per gameweek respectively; these are pragmatic operational
allowances, not estimated uncertainty bounds. Report every paired effect,
win/tie/loss, median, worst case and the proportion of opening losses exceeding
19 points. Passing versus H1 does not establish superiority versus Solio.

These are research decision allowances, not universal loss limits: failing them
does not establish negative expected value.

These criteria were chosen after earlier research, and both seasons already
have research exposure. They are prospective for this new matrix, not a fresh
untouched holdout or a retroactive pass for the original gate. Two seasons cannot
support reliable generalisation claims. Openings are nested within seasons;
repeated solver calls measure numerical variability rather than independent
football outcomes. Do not calculate confidence by treating all gameweeks or
opening cases as independent seasons. All legality and data-integrity checks
remain mandatory, and research support does not automatically approve production
policy defaults or forecast weights.

## Historical source admission

The [2024/25 source inventory](season_2024_source_inventory.json) preserves pinned
market/calendar identities and the explicit restricted no-Assistant-Manager
scope. All policies receive two Wildcard windows and one seasonal Free Hit,
Bench Boost and Triple Captain. This is a legal subset of 2024/25 actions, not full
Assistant Manager functionality or current-season rules applied retrospectively.

The offline [preparation tool](../tools/prepare_season_2024.py) verifies a supplied
manifest and trusted local history/feature caches before loading them. It fits
the fixed standing four-head recipe only on 2020/21–2023/24, disables defensive
contribution scoring and projects each origin with that origin's history and
fixture information. The current deployment artifact is never backcast.

Older snapshots lack `can_select`; the explicitly reported fallback excludes
status `u` and `n`, then uses the archived boolean once available. This is a
conservative eligibility proxy, not certification of the original UI. Final
club changes belong only to the outcome evaluator and never rewrite an earlier
market or forecast. A stale merged row for fixture239 is reconciled against the
pinned individual history, with original bytes retained. All 784 footballer season
totals reconcile after that derived correction.

The December derby postponement was published after the chosen GW15 origin.
Its later blank is scored correctly without inserting that later information
into the earlier forecast. Conditional fixture changes remain unresolved until
admissible confirmation. Official article publication dates can conceal later
edits: misleading earlier-dated bodies are excluded, and separate dated sources
are retained. Archive commit/capture and article publication clocks remain
publisher claims rather than independently witnessed historical timestamps.
Calendar replay audits gameweek assignments; cached future kickoff times can lag
announcements and are not predictor features in this origin-frozen reference.

## Reproduction

Use a source checkout and `PYTHONPATH=src`. Historical datasets, executable model
files and raw per-path evidence stay in an explicitly selected private directory.
Nothing downloads or trains merely by importing these tools.

1. Supply a checksummed preparation manifest with trusted history/features,
   historical merged/player/team files, correction evidence, market/calendar
   receipts, dated fixture updates and rule/protocol evidence. Run
   `tools/prepare_season_2024.py --manifest ... --manifest-sha256 ... --output ...
   --trust-local-cache` under the existing bounded process-group watchdog.
2. Create a reference manifest mapping each declared season to checksummed
   `decisions` and `outcomes` bundles. The [study runner](../tools/run_expected_points_study.py)
   accepts `lock` with `--manifest`, `--manifest-sha256`, `--protocol` and a new
   private `--output`. It freezes sources, resource files, runtime, inputs and
   both source-only opening rosters. Never reuse an output destination.
3. Run each `arm` serially with the same arguments plus `--lock`,
   `--lock-sha256`, `--season`, `--seed` and `--policy`. Solio additionally needs
   the explicitly admitted native runtime/source/site-packages paths. The frozen
   matrix is 2 seasons × 2 openings × 3 policies. Use two threads, 4 GiB sampled process-group
   RSS, 900 seconds per path and the declared storage watchdog. Do not overlap
   numerical studies or tune on their observed outcomes.
4. Independently reconcile all settlements and retained provisional plans with
   [audit_season_path](../tools/audit_season_path.py), and every completed native
   reply with [audit_native_trace](../tools/audit_native_trace.py). Retain expected
   failures and unknown selected-plan bounds; no raw attempt gap is a certificate
   for a different retained plan or the global chip/season problem.
5. Feed the complete declared rows to
   [evaluate_season_policies](../tools/evaluate_season_policies.py). Missing,
   failed, duplicate and nonfinite cases cannot silently disappear. Mark
   integrity verified only after the independent audits.

The separate [calendar probe](../tools/probe_chip_calendars.py) follows its
[fixed diagnostic protocol](season_calendar_probe_protocol_2026-10-24.json).
It compares two cores and two same-origin provisional chip schedules from the
same H6 state at eight fixed origins. Incompatible alternative schedules are
reported. Future actual chip dates and evaluator/settlement files are not inputs.
Horizon objectives and remaining-chip reserve assumptions are reported separately;
a better conditional proxy is not a causal or measured season-point improvement.
Supply the opening-lock, source-lock and protocol checksums explicitly, alongside
the decisions/reference paths and admitted native runtime. Run this short probe
after the full season batch is terminal.
