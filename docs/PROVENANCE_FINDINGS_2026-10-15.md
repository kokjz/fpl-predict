# Historical provenance findings — 15 October 2026

This package audits inputs and source knowledge. It does **not** train, compare
model errors, promote weights, or retroactively upgrade the earlier pilot.
Raw snapshots, feature tables, row-level diagnostics and local paths are not
distributed. The [audit tools](deadline_provenance.md) use synthetic test data.

## Verified native artifacts

Direct bounded HTTPS retrieval succeeded where the text connector could not
read binary data. Files at Dastan revision
[`758db9247e8b3a9a870c991064f74d8339d61cd0`](https://github.com/qazybekb/smartplayfpl-dastan/tree/758db9247e8b3a9a870c991064f74d8339d61cd0)
matched the published release SHA-256s:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| features.parquet | 38,697,486 | `dcf8411d458e7b99b15472975280cf855e15de22070022fad6fce0f76f3f299c` |
| pre_deadline_ep_next.parquet | 371,135 | `f0087b83c279ab9655751b78f2a2fbac492d41e434346ba447e145cf1917fb4b` |
| pre_deadline_signals.parquet | 448,316 | `1a0b4f4565f6097f6efb0c03a6e351742d88cd71671c5d900adcd28bc7436a54` |

The native feature file has163,072rows/304columns. No third-party project code
or model pickle was executed. A temporary isolated Parquet reader parsed data;
the operational dependency environment was not modified.

## Deadline, projection and identity evidence

Retrieved38 compressed2025/26 bootstrap snapshots (5,386,308bytes total) named by
the release provenance tables from
[`Randdalf/fplcache` revision6c364bf](https://github.com/Randdalf/fplcache/tree/6c364bfbd9914649dc5dec016e544be3ae4fe767).
Each names the requested unfinished GW as uniquely next and records capture
before its deadline, within24hours. All38 deadlines match the incumbent's
reconstructed cutoff values. That agreement improves deadline evidence without
establishing every historical input's availability.

All29,645 released2025/26 `ep_next` rows match their raw source value and seasonal
element-ID/stable-code mapping. All eight documented signal transformations also
reproduce across29,645rows. These checks validate those **input artifacts**, not
the original OpenFPL forecast archive's exporter/training/capture lineage.

For GW28, the compressed bytes additionally match Git blob
`335c6be16ab9af49a9d67c74da5ca4c623ae8a2e`. The archive's
[commit30e210e](https://github.com/Randdalf/fplcache/commit/30e210e40673777f83fb7ab5488380875e1e40f3)
records13:14:45UTC on27February, before the18:30deadline. The upstream fetch
script and scheduled Linux workflow support interpretation of filename times
as UTC. These are publisher/Git-history records, not an independent cryptographic
capture certificate; current retrieval alone does not prove historical freezing.

Of29,747 native feature rows,103 codes are absent from the selected per-GW
snapshots. Among rows actually present, there are zero element-ID or position
conflicts. Nine absent-code rows have nonzero minutes/points. Absence from an
earlier snapshot does **not** prove absence at the deadline: players can be added
later. Preserve coverage explicitly; seek closer snapshots or classify unknown,
rather than drop rows after seeing outcomes or use final IDs as silent evidence.

## Opponent-history screen: the source concern occurs in actual bytes

In the2025/26 release,409fixture-player rows have a previous opponent match
after the recorded GW deadline, and both `opp_goals_scored_1` and
`opp_goals_conceded_1` exactly match that match's score. Counts are79inGW26,
248inGW33 and82inGW36. Thus330rows occur within the proposedGW28–38 window.

One concrete example is a Chelsea row facing Brighton on21April19:00UTC:
the GW33 deadline was18April10:00UTC, yet opponent last-match goals are2–2,
matching Brighton's18April16:30UTC match. Both its kickoff and result postdate
the deadline. The inspected rebuild shifts opponent histories at kickoff/date
and its deadline anchoring excludes `opp_`, consistent with these observed values.

This is a reproducible counterexample to relying on that anchoring assertion
alone. The screen uses pinned FPL results/final match times plus inspected source;
it is **not** an independent reconstruction of all Understat features, a count
of every affected predictor, or an estimate of accuracy inflation. Do not infer
intent or rank models from it. The native release is not admitted as a clean
deadline-safe reference. Corrected variants must be named separately.

## Schedule membership reconstruction

Inspected upstream fixture history and retrieved two380-fixture as-of exports:

- [5February commit2c43a95](https://github.com/vaastav/Fantasy-Premier-League/blob/2c43a95002e0a3ec0700b725da76fdd5fefcd1a6/data/2025-26/fixtures.csv), SHA-256 `6312c629796f176868d13f481e61b5578cb9491953e541fc8cdc47403facc170`.
- [13March commit77ab482](https://github.com/vaastav/Fantasy-Premier-League/blob/77ab48216404b0f49f55fa724c520af25b32ddae/data/2025-26/fixtures.csv), SHA-256 `0e594a9423cfb3e001e0f3f4172629c42d44fed59463cef1de0bf7b635077298`.

Neither contains scores/started/finished flags on future matches at its recorded
commit time. The March export leaves one postponed fixture's event/time unknown.
It differs from the final table in four GW assignments and29kickoff times, so
copying the final schedule as if it were this snapshot would be incorrect.

The [official5April announcement](https://www.premierleague.com/en/news/4624106)
places Bournemouth–Leeds, Brighton–Chelsea and Burnley–Man City inGW33 rather
thanGW34. The [official28April announcement](https://www.premierleague.com/en/news/4637009)
places Man City–Crystal Palace inGW36. Because these pages give dates rather
than exact publication times, the manual update log conservatively permits use
only from00:00UTC the following day. No update is applied before that bound.

Selecting the latest inspected base available before each deadline and replaying
those four sourced event changes reproduces **all109evaluation fixture
memberships acrossGW28–38**, with zero missing/extra fixtures. The unknown
postponement stays unknown until its qualifying announcement. This is targeted,
manually sourced event-assignment evidence, not proof of a complete kickoff-time
history, every publication's historical contents or all fixture inputs. Sparse
archive updates cannot by themselves certify a later schedule remained current.

## Consequence and next implementation package

The deadline/season-ID/projection transport gaps are substantially reduced and
target-window membership now has a documented reconstruction. The unchanged
native Dastan release still fails temporal admission; further unchanged-model
training would not produce a fair clean comparison. The existing OpenFPL-labelled
GW1–24 archive still lacks complete forecast lineage and cannot coverGW28–38.

Next implement a **separately named deadline-safe native-feature variant**:
rebuild affected history families using explicit cutoff/source maxima (including
opponents and league-table context), resolve snapshot coverage without
outcome-based exclusions, and audit all additional predictors. Freeze a new
protocol before a bounded reference fit. Do not silently patch the release and
call it the original system, substitute incumbent features, or tune on this
published panel and call it independent. Broader folds/seeds and challenger
selection remain conditional; model-promotion gates are unchanged.

This package required small public downloads and data audits, no model training
or external compute. Data licensing/terms still apply; no raw data or binaries
are published here. The temporary reader/build caches are expendable; unique
compressed snapshots, source evidence and approved weights are retained.
