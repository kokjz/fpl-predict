"""Offline bootstrap and feature-lineage audit; never scores, fits or certifies a model."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
from urllib.parse import urlsplit

import numpy as np
import pandas as pd

from experiment_runner import file_hash
from external_benchmark import FIXTURE_KEYS, _identities, _json, _numeric, _required, _timestamp

MAX_COMPRESSED = 2_000_000
MAX_EXPANDED = 16_000_000
FAMILIES = ("player", "team", "opponent")


def read_snapshot(path, expected_sha256):
    """Verify bytes before bounded JSON/XZ parsing; never deserialise pickles."""
    path = Path(path)
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("Expected SHA-256")
    limit = MAX_COMPRESSED if path.suffix == ".xz" else MAX_EXPANDED
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Snapshot size/checksum mismatch")
    if path.suffix == ".xz":
        decoder = lzma.LZMADecompressor(memlimit=64 * 1024**2)
        try:
            raw = decoder.decompress(raw, max_length=MAX_EXPANDED + 1)
        except lzma.LZMAError as exc:
            raise ValueError("Invalid/over-budget XZ snapshot") from exc
        if len(raw) > MAX_EXPANDED or not decoder.eof or decoder.unused_data:
            raise ValueError("Expanded snapshot exceeds budget or has trailing data")
    try:
        payload = _json(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid snapshot JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Snapshot must be a JSON object")
    return payload


def extract_bootstrap(payload, season, gameweek, captured_at):
    """Validate an archive's recorded capture, calendar and identity mapping.

    Filename/capture metadata are publisher claims, not independent timestamp
    certification. Bootstrap has no complete fixture announcement history.
    """
    if not isinstance(season, str) or not re.fullmatch(r"20\d\d-\d\d", season):
        raise ValueError("Invalid season")
    start = int(season[:4])
    if int(season[-2:]) != (start + 1) % 100 or type(gameweek) is not int or not 1 <= gameweek <= 38:
        raise ValueError("Invalid season/gameweek")
    _required(payload, ["events", "elements", "teams"], "bootstrap")
    events = pd.DataFrame(payload["events"])
    _required(events, ["id", "deadline_time", "is_next", "finished"], "events")
    _numeric(events, ["id"], integer=True, minimum=1)
    if events.id.duplicated().any() or set(events.id) != set(range(1, 39)):
        raise ValueError("Incomplete/ambiguous event calendar")
    deadlines = events.deadline_time.map(_timestamp)
    if deadlines.min().year != start:
        raise ValueError("Snapshot belongs to another season")
    target = events.loc[events.id.eq(gameweek)].iloc[0]
    if not events.is_next.map(lambda v: isinstance(v, (bool, np.bool_))).all() or not isinstance(target.finished, (bool, np.bool_)):
        raise ValueError("Invalid event flags")
    if not bool(target.is_next) or bool(target.finished) or int(events.is_next.sum()) != 1:
        raise ValueError("Snapshot does not unambiguously name this unfinished GW next")
    deadline = _timestamp(target.deadline_time); captured = _timestamp(captured_at)
    age = (deadline - captured).total_seconds() / 3600
    if not 0 < age <= 24:
        raise ValueError("Capture must be before deadline and at most24h old")
    players = pd.DataFrame(payload["elements"])
    teams = pd.DataFrame(payload["teams"])
    _required(players, ["id", "code", "team", "element_type"], "elements")
    _required(teams, ["id"], "teams")
    _numeric(players, ["id", "code", "team", "element_type"], integer=True, minimum=1)
    _numeric(teams, ["id"], integer=True, minimum=1)
    if players.empty or players.id.duplicated().any() or players.code.duplicated().any() or teams.id.duplicated().any():
        raise ValueError("Empty/ambiguous seasonal identities")
    if not players.team.isin(teams.id).all() or not players.element_type.between(1, 4).all():
        raise ValueError("Invalid club/position mapping")
    identities = players[["id", "code", "team", "element_type"]].rename(
        columns={"id": "element", "code": "fpl_code", "element_type": "position"})
    identities.insert(0, "gameweek", gameweek); identities.insert(0, "season", season)
    return {"season": season, "gameweek": gameweek, "deadline": deadline.isoformat(),
            "captured_at": captured.isoformat(), "age_hours": age,
            "capture_evidence": "publisher_recorded", "players": len(players)}, identities


def audit_snapshots(spec, root):
    """Admit exact declared snapshot coverage; no silent dropped/missing weeks."""
    _required(spec, ["schema_version", "season", "gameweeks", "snapshots"], "snapshot manifest")
    if spec["schema_version"] != 1:
        raise ValueError("Unsupported snapshot manifest")
    weeks = spec["gameweeks"]
    if not isinstance(weeks, list) or not weeks or any(type(v) is not int or not 1 <= v <= 38 for v in weeks) or len(set(weeks)) != len(weeks):
        raise ValueError("Declare unique gameweeks")
    records = []; identities = []
    root = Path(root).resolve()
    for entry in spec["snapshots"]:
        _required(entry, ["gameweek", "file", "sha256", "captured_at", "source_url", "source_revision"], "snapshot")
        url = urlsplit(entry["source_url"])
        revision = entry["source_revision"]
        if (url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment or
                not re.fullmatch(r"[0-9a-f]{40}", revision) or revision not in url.path.split("/")):
            raise ValueError("Require a pinned, public HTTPS source URL without credentials/query")
        path = (root / entry["file"]).resolve()
        if Path(entry["file"]).is_absolute() or not path.is_relative_to(root):
            raise ValueError("Snapshot file escapes declared root")
        payload = read_snapshot(path, entry["sha256"])
        record, bridge = extract_bootstrap(payload, spec["season"], entry["gameweek"], entry["captured_at"])
        records.append({**record, "sha256": entry["sha256"], "source_revision": revision})
        identities.append(bridge)
    if len(records) != len(weeks) or {r["gameweek"] for r in records} != set(weeks):
        raise ValueError("Missing/duplicate/out-of-scope snapshot coverage")
    return ({"schema_version": 1, "snapshot_checks_passed": True,
             "independent_capture_certified": False, "fixture_knowledge_certified": False,
             "benchmark_eligible": False, "model_promotion": False,
             "snapshots": sorted(records, key=lambda r: r["gameweek"])},
            pd.concat(identities, ignore_index=True))


def audit_history_sources(rows, lineage, deadlines):
    """Check supplied latest-source evidence for every player/team/opponent family.

    No feature values or source times are inferred. Cold-start families require
    an explicit zero source count and missing maximum; absence is not a pass.
    A passing contract is not proof of the truth/completeness of supplied maxima.
    """
    rows = rows.copy(); lineage = lineage.copy(); deadlines = deadlines.copy()
    _required(rows, FIXTURE_KEYS, "rows"); _identities(rows, fixtures=True)
    if rows.duplicated(FIXTURE_KEYS).any(): raise ValueError("Duplicate target row")
    _required(lineage, [*FIXTURE_KEYS, "family", "source_count", "source_max_ts"], "lineage")
    _numeric(lineage, ["gameweek", "fpl_code", "fixture"], integer=True, minimum=0)
    _identities(lineage[FIXTURE_KEYS].drop_duplicates().copy(), fixtures=True)
    _numeric(lineage, ["source_count"], integer=True, minimum=0)
    if not lineage.family.isin(FAMILIES).all() or lineage.duplicated([*FIXTURE_KEYS, "family"]).any():
        raise ValueError("Unknown/duplicate history family")
    expected = rows[FIXTURE_KEYS].merge(pd.DataFrame({"family": FAMILIES}), how="cross")
    joined = expected.merge(lineage, on=[*FIXTURE_KEYS, "family"], how="outer", indicator=True, validate="one_to_one")
    if not joined._merge.eq("both").all(): raise ValueError("Missing/extra history-family coverage")
    _required(deadlines, ["season", "gameweek", "deadline"], "deadlines")
    # Reuse identity validation without manufacturing fixture/player identities.
    _numeric(deadlines, ["gameweek"], integer=True, minimum=1)
    if deadlines.duplicated(["season", "gameweek"]).any(): raise ValueError("Ambiguous deadline")
    deadlines["deadline"] = deadlines.deadline.map(_timestamp)
    joined = joined.merge(deadlines[["season", "gameweek", "deadline"]], on=["season", "gameweek"], how="left", validate="many_to_one")
    if joined.deadline.isna().any(): raise ValueError("Missing deadline evidence")
    missing = joined.source_max_ts.isna()
    if (missing != joined.source_count.eq(0)).any():
        raise ValueError("Missing source evidence is not an explicit cold start")
    joined["source_max_ts"] = joined.source_max_ts.map(lambda t: pd.NaT if pd.isna(t) else _timestamp(t))
    # All are match-history features: allow the same3h completion buffer as pilot.
    late = joined.source_max_ts.notna() & joined.source_max_ts.ge(joined.deadline - pd.Timedelta(hours=3))
    return {"schema_version": 1, "history_contract_passed": not bool(late.any()),
            "target_rows": len(rows), "family_records": len(joined),
            "late_family_records": int(late.sum()),
            "late_by_family": {f: int((late & joined.family.eq(f)).sum()) for f in FAMILIES},
            "independent_lineage_certified": False, "benchmark_eligible": False,
            "remaining_checks": ["truth/completeness of supplied source maxima",
                                 "statistical publication/correction availability times",
                                 "other predictor families and train/selection provenance",
                                 "fixture assignments/opponents known at the deadline"]}


def audit_fixture_snapshot(frame, captured_at):
    """Screen claimed as-of fixture bytes for obvious future-result contamination.

    A pass does not establish that this schedule was still current at a later
    deadline. Unknown event assignments/kickoffs remain unknown, never filled.
    """
    d = frame.copy(); captured = _timestamp(captured_at)
    _required(d, ["id", "event", "kickoff_time", "finished", "started", "team_h_score", "team_a_score"], "fixtures")
    _numeric(d, ["id"], integer=True, minimum=1)
    if d.empty or d.id.duplicated().any(): raise ValueError("Empty/ambiguous fixture IDs")
    assigned = d.event.notna()
    events = d.loc[assigned, ["event"]].copy()
    _numeric(events, ["event"], integer=True, minimum=1)
    if not events.event.le(38).all(): raise ValueError("Invalid fixture GW")
    kickoff = d.kickoff_time.map(lambda t: pd.NaT if pd.isna(t) else _timestamp(t))
    for flag in ("finished", "started"):
        if not d[flag].map(lambda v: pd.isna(v) or isinstance(v, (bool, np.bool_))).all():
            raise ValueError("Fixture flags must be booleans or unknown")
    # A finished fixture without its kickoff cannot establish an as-of history.
    if (kickoff.isna() & d.finished.eq(True)).any(): raise ValueError("Finished fixture has no time")
    future = kickoff.notna() & kickoff.ge(captured)
    contaminated = future & (d.finished.eq(True) | d.started.eq(True) |
                              d.team_h_score.notna() | d.team_a_score.notna())
    return {"fixture_rows": len(d), "asof_result_screen_passed": not bool(contaminated.any()),
            "future_result_conflicts": int(contaminated.sum()),
            "unknown_event_rows": int(d.event.isna().sum()),
            "unknown_kickoff_rows": int(kickoff.isna().sum()),
            "fixture_knowledge_certified": False, "benchmark_eligible": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists(): raise ValueError("Output exists")
        if file_hash(args.manifest) != args.manifest_sha256: raise ValueError("Manifest checksum mismatch")
        with args.manifest.open("rb") as stream: raw = stream.read(MAX_COMPRESSED + 1)
        if len(raw) > MAX_COMPRESSED: raise ValueError("Manifest exceeds size budget")
        result, _ = audit_snapshots(_json(raw), args.snapshot_root)
        result["manifest_sha256"] = args.manifest_sha256
        with args.output.open("x") as stream: json.dump(result, stream, indent=2, allow_nan=False)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"Provenance audit rejected: {exc}\n")
    print("Snapshot audit saved; fixture knowledge and full model provenance remain separate gates.")


if __name__ == "__main__":
    main()
