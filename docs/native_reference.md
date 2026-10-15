# Native-window reference research command

This optional workflow rebuilds286 history/context predictors and conditions one
fixed lightweight learner on four position indicators. It is a named retrospective
feature pilot, not original Dastan/OpenFPL, a production replacement or automatic
promotion. Read the immutable [protocol](NATIVE_REFERENCE_PROTOCOL.md), including
the explicit two-row training gap mask and missing older snapshot history.

## Canonical, private inputs

Provide plain CSVs and a JSON source proof outside Git. No pickle or trained binary
is consumed. The command has no network activity or automatic runtime creation.

| Input | Required contract |
| --- | --- |
| players.csv | `season,gameweek,fixture,fpl_code,position,team_name,opponent_name,home,ts,deadline,understat_id`; all raw columns named in `native_history.PLAYER_STATS`; `defensive_contribution,cbit,recoveries,tackles,starts` |
| teams.csv | `season,fixture,team_name,opponent_name,ts`; raw `TEAM_STATS` columns except the two derived league-rank columns |
| snapshots.csv | `season,gameweek,fpl_code,captured_at` and the seven `SNAPSHOT_FEATURES`; include only actual captured identities |
| reference.csv | Exact frozen fixture export: `season,gameweek,fpl_code,fixture,actual,reference,candidate` |
| provenance.json | Reviewed source proof with `native_inputs_ready: true`, source hashes, coverage gaps, identity corrections and limitations; strict failure retained separately |

Positions are1GK/2DEF/3MID/4FWD; times must be timezone-aware; scores are actual
full seasonal points. Raw unknown statistics remain NaN, not guessed zeros.
Snapshot absence stays explicit and never causes a prediction row to disappear.
Training/validation/test windows and the exact allowed mapped training-gap keys
are enforced independently of the producer's readiness flag. No other mapped
appearance gaps may pass. Input files are capped at200MB; player rows at200,000.

Source preparation can use `native_sources` without importing third-party project
code: `corrected_assignments`, `join_player_statistics`, `join_team_statistics`,
`snapshot_features` and `match_roster_observations` expose the join logic.
Player captures yield `(numeric_understat_id, decoded_player_payload)`; team
captures yield `(start_year, decoded_league_payload)`. FPL rows supply stable codes,
seasonal assignment intervals, unique fixture dates, venues, scores and UTC event
times. Team clock offsets are reported instead of guessing the provider timezone.
Required conflicting match records stop; exact duplicates are counted; unrelated
provider dates/competitions do not enter the FPL population. Match rosters can
provide real missing observations, but absent roster entries never create zeros.

Retrieve/cache provider and archive inputs separately with explicit byte/time
limits, retain request URLs/retrieval times/hashes and verify them before these
functions. Provider responses can change after statistical corrections. No dataset
or opaque local source manifest is an independently certified historic capture.
FPL/Understat data rights are separate from the attributed MIT feature definitions.

## Freeze, then run

```sh
fpl-predict native-reference prepare \
  --players private/players.csv --teams private/teams.csv \
  --snapshots private/snapshots.csv --reference private/reference.csv \
  --provenance private/provenance.json --output private/manifest.json

fpl-predict native-reference run --manifest private/manifest.json \
  --manifest-sha256 RECORDED_SHA256 --directory private/new-job
```

Preparation checks raw schema, splits, source gaps and reference-key coverage
without fitting or scoring. It freezes policy, code/library versions and input
hashes. Run the second command under the [resource/storage watchdog](experiment_runner.md)
with the manifest and all input hashes declared, expected `predictions.csv` and
`results.json`, and the protocol's budgets. Artifacts are write-once. No model
binary is saved and the operational registry is untouched.

The worker separately reports load/audit, feature-build, fit and prediction times.
The watchdog measures whole-process observed memory and project storage growth.
Failed/incomplete jobs never count as scores. Reports preserve both snapshot-known
candidate primary and all-candidate/all-player diagnostics, with identical shared
keys for the frozen reference and no outcome-based row exclusions. Missing-snapshot
codes might have been added later before the deadline; no stronger claim is made.
