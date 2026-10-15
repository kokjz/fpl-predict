# Reference source readiness — 15 October 2026

This is a source/data eligibility audit, not an accuracy comparison. Public text
was inspected without executing third-party code or loading third-party model
pickles. Local input records and raw snapshots remain outside the repository.

## Dastan

Pinned source: [`qazybekb/smartplayfpl-dastan`,
`758db9247e8b3a9a870c991064f74d8339d61cd0`](https://github.com/qazybekb/smartplayfpl-dastan/tree/758db9247e8b3a9a870c991064f74d8339d61cd0).
Inspected `dastan/data.py`, `dastan/rebuild/features.py`, the release manifest,
`data/source_pins.json`, `models/feature_cols.json` and `docs/REBUILDING_DATA.md`.
The whitelist contains 286 features. The release declares a 38,697,486-byte,
163,072-row feature parquet with SHA-256
`dcf8411d458e7b99b15472975280cf855e15de22070022fad6fce0f76f3f299c`.
That declaration is not a verified local download: the available text connector
rejects binary data. A full upstream rebuild was not started.

The rebuild calculates shifted player/team rolling histories in kickoff/date
order. The deadline anchoring helper broadcasts the earliest fixture's columns
whose names begin `player_`, `team_`, `ar_`, `cx_`, `p_any_`, `p60_`, or
`e_minutes_`. It deliberately excludes `opp_`. Its equality assertion covers the
same prefixes; it does not verify per-feature source timestamps against an
archived deadline.

**Eligibility question:** a later fixture in a double could use an opponent
history updated by a match after the GW deadline. The anchoring assertion alone
does not rule that out. This is a source-level counterexample to the sufficiency
of that check, **not a demonstrated leakage count in the published parquet**.
Admission needs actual feature bytes plus per-row history/source-date checks,
including opponent features and interleaved/postponed matches. Even the earliest
fixture's shifted history needs comparison to the deadline, not just kickoff.

The pinned raw-source revisions differ from the incumbent's inputs. Equal row
counts do not establish identical data. The upstream rebuild documentation also
distinguishes the published training mappings from later identity corrections.
Preserve those differences in a reproduction; label corrected variants
separately. Source-code licensing does not grant blanket rights to redistribute
FPL/Understat/raw feature data. No such data is added here.

**Status:** no qualified common-window Dastan fit yet. A future download/rebuild,
temporal/identity audit and fixed reference training policy are required. Existing
production weights trained beyond the proposed start cannot be used as a fair
earlier-window reference. This is a provenance/input prerequisite, not evidence
that more hardware is needed.

## OpenFPL-labelled archive and method

The previously verified archive has 18,173 rows covering 2025/26 GW1–24, SHA-256
`8113cb86392d98000e84ae0b383c7871cf35bf74a08cd3042cb5c8d81eab3849`.
Its stable-ID bridge and full-score outcomes reconcile, but exporter/model
lineage, training/selection times and genuine pre-deadline capture still need
independent evidence. A filename does not establish original-system provenance.
It cannot supply the proposed GW28–38 comparison. No predictions are extended,
imputed or backdated. Refer to the [source inventory](benchmark_sources.json)
and [run plan](BENCHMARK_RUN_PLAN.md) for the separate archive route.

## Incumbent-method reference

The local trained deployment binary is not used to score its own training past.
A new, fixed training-only fit is possible with cached, pinned raw data. Its
reconstructed schedule still prevents admission as a fully verified historical
pre-deadline benchmark. The separately declared
[retrospective pilot](reference_pilot.md) measures pipeline cost and full-score
baseline errors without changing that gate or the approved champion.
