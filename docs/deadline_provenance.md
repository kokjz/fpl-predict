# Historical information-time audits

`fpl-predict audit-deadlines` is an offline, non-scoring audit. It verifies the
declared bytes of timestamped bootstrap archives, requires the requested season
and unique unfinished `is_next` event, checks capture strictly before the deadline
and no more than24hours old, and validates seasonal player-code/position/club IDs.
It does not download data, train, update a registry or create a weekly runtime.

A private manifest declares exact coverage:

```json
{
  "schema_version": 1,
  "season": "2025-26",
  "gameweeks": [28],
  "snapshots": [{
    "gameweek": 28,
    "file": "GW28.json.xz",
    "sha256": "REPLACE_WITH_VERIFIED_SHA256",
    "captured_at": "2026-02-27T13:14:00Z",
    "source_url": "https://raw.githubusercontent.com/OWNER/REPO/COMMIT/cache/FILE.json.xz",
    "source_revision": "REPLACE_WITH_40_CHARACTER_PINNED_COMMIT"
  }]
}
```

Replace placeholders with reviewed values; the exact40-character revision must
be a source URL path component. URLs cannot contain credentials, queries or
fragments. Relative files must stay inside the selected snapshot root.

```sh
fpl-predict audit-deadlines --manifest private/snapshot-manifest.json \
  --manifest-sha256 RECORDED_SHA256 --snapshot-root private/snapshots \
  --output private/new-audit.json
```

The manifest is limited to2MB. Individual XZ files are limited to2MB compressed,
16MB expanded and64MiB decoder memory; plain JSON is limited to16MB. Checksums
precede parsing. Duplicate JSON keys, concatenated XZ streams, oversized content,
missing/extra/duplicate weeks, wrong seasons, ambiguous IDs, naive timestamps and
post-deadline captures fail. Outputs are exclusive/write-once. Real raw snapshots
and private manifests/identity bridges belong outside Git.

## Separate gates

The report deliberately distinguishes these statements:

1. The supplied bytes are internally consistent with a publisher-recorded
   pre-deadline bootstrap capture. Filename timestamps and Git history are useful
   provenance; hashes alone do not independently certify historical capture.
2. The fixture list, opponents and GW assignments were known at decision time.
   Bootstrap events do not supply a complete fixture announcement history. A
   final fixture CSV cannot stand in for an as-of schedule.
3. Every predictor uses information available then. Equal player histories
   across double fixtures do not establish opponent-history safety.

The API `audit_history_sources(rows, lineage, deadlines)` requires every target
fixture/player key to have exactly one `player`, `team` and `opponent` family
record. Each record supplies a nonnegative integer `source_count` and latest
`source_max_ts`. Positive history requires an aware timestamp strictly earlier
than deadline minus the three-hour completion buffer; cold starts require an
explicit zero count and missing maximum. Missing families cannot silently pass.
These are match-history families; snapshot signals need their own capture audit.
The aggregate report counts violations by family without exposing player rows.

Supplied maxima need independent review for truthful, complete lineage. A safe
maximum match timestamp also does not establish when statistics/corrections were
published. Other features, model training/selection, schedule knowledge and
capture evidence remain separate checks. Reports never automatically set full
benchmark eligibility or promote a model.

`audit_fixture_snapshot(frame, captured_at)` additionally screens as-of fixture
exports for results/started flags on matches not yet begun. Unknown GW assignments
and kickoff times stay unknown. A clean but old schedule is not proof it remained
current at a later deadline. This audit is a necessary consistency screen, not
an independent provenance certificate or a complete historical schedule rebuild.
