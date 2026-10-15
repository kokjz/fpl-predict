import copy
import hashlib
import json
import lzma

import pandas as pd
import pytest

import deadline_provenance as audit


def bootstrap():
    return {"events": [{"id": gw, "deadline_time": f"2025-08-{gw:02d}T10:00:00Z" if gw <= 28 else f"2025-09-{gw-28:02d}T10:00:00Z",
                        "is_next": gw == 28, "finished": False} for gw in range(1, 39)],
            "elements": [{"id": 1, "code": 101, "team": 1, "element_type": 2}],
            "teams": [{"id": 1}]}


def spec(tmp_path):
    raw = lzma.compress(json.dumps(bootstrap()).encode())
    (tmp_path / "snapshot.json.xz").write_bytes(raw)
    return {"schema_version": 1, "season": "2025-26", "gameweeks": [28],
            "snapshots": [{"gameweek": 28, "file": "snapshot.json.xz", "sha256": hashlib.sha256(raw).hexdigest(),
                           "captured_at": "2025-08-28T09:00:00Z", "source_revision": "a"*40,
                           "source_url": "https://example.org/" + "a"*40 + "/snapshot.json.xz"}]}


def test_snapshot_hash_calendar_and_identity_checks(tmp_path):
    result, bridge = audit.audit_snapshots(spec(tmp_path), tmp_path)
    assert result["snapshot_checks_passed"]
    assert not result["independent_capture_certified"] and not result["benchmark_eligible"]
    assert not result["fixture_knowledge_certified"]
    assert bridge.fpl_code.tolist() == [101] and bridge.position.tolist() == [2]


@pytest.mark.parametrize("bad", ["late", "naive", "old", "next", "duplicate_id", "duplicate_code", "season", "club", "position", "event", "flags"])
def test_bad_bootstrap_is_not_admitted(bad):
    payload = bootstrap(); capture = "2025-08-28T09:00:00Z"
    if bad == "late": capture = "2025-08-28T10:00:00Z"
    if bad == "naive": capture = "2025-08-28T09:00:00"
    if bad == "old": capture = "2025-08-26T10:00:00Z"
    if bad == "next": payload["events"][27]["is_next"] = False
    if bad in ("duplicate_id", "duplicate_code"): payload["elements"].append(copy.deepcopy(payload["elements"][0]))
    if bad == "season": payload["events"][0]["deadline_time"] = "2024-08-01T10:00:00Z"
    if bad == "club": payload["elements"][0]["team"] = 99
    if bad == "position": payload["elements"][0]["element_type"] = 5
    if bad == "event": payload["events"][0]["id"] = 28
    if bad == "flags": payload["events"][27]["is_next"] = "true"
    with pytest.raises(ValueError): audit.extract_bootstrap(payload, "2025-26", 28, capture)


@pytest.mark.parametrize("bad", ["hash", "escape", "coverage", "secret_url", "revision"])
def test_bad_manifest_fails_closed(tmp_path, bad):
    manifest = spec(tmp_path); entry = manifest["snapshots"][0]
    if bad == "hash": entry["sha256"] = "b"*64
    if bad == "escape": entry["file"] = "../snapshot.json.xz"
    if bad == "coverage": manifest["gameweeks"] = [28, 29]
    if bad == "secret_url": entry["source_url"] += "?token=private"
    if bad == "revision": entry["source_revision"] = "b"*40
    with pytest.raises(ValueError): audit.audit_snapshots(manifest, tmp_path)


def test_expansion_and_trailing_streams_are_bounded(tmp_path, monkeypatch):
    manifest = spec(tmp_path); entry = manifest["snapshots"][0]
    monkeypatch.setattr(audit, "MAX_EXPANDED", 100)
    with pytest.raises(ValueError, match="Expanded"): audit.read_snapshot(tmp_path / entry["file"], entry["sha256"])
    monkeypatch.setattr(audit, "MAX_EXPANDED", 16000000)
    path = tmp_path / entry["file"]; raw = path.read_bytes() + lzma.compress(b"{}")
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="trailing"): audit.read_snapshot(path, hashlib.sha256(raw).hexdigest())


def history_frames():
    rows = pd.DataFrame([{"season": "2025-26", "gameweek": 28, "fpl_code": 101, "fixture": 1}])
    lineage = pd.concat([rows.assign(family=f, source_count=3, source_max_ts="2026-02-21T15:00:00Z")
                         for f in audit.FAMILIES], ignore_index=True)
    deadlines = pd.DataFrame([{"season": "2025-26", "gameweek": 28, "deadline": "2026-02-27T18:30:00Z"}])
    return rows, lineage, deadlines


def test_opponent_is_checked_even_when_player_history_is_anchored():
    rows, lineage, deadlines = history_frames()
    assert audit.audit_history_sources(rows, lineage, deadlines)["history_contract_passed"]
    lineage.loc[lineage.family.eq("opponent"), "source_max_ts"] = "2026-02-28T15:00:00Z"
    result = audit.audit_history_sources(rows, lineage, deadlines)
    assert not result["history_contract_passed"]
    assert result["late_by_family"] == {"player": 0, "team": 0, "opponent": 1}
    assert not result["benchmark_eligible"]


@pytest.mark.parametrize("bad", ["missing", "duplicate", "unknown", "missing_time", "naive", "deadline"])
def test_incomplete_lineage_cannot_pass(bad):
    rows, lineage, deadlines = history_frames()
    if bad == "missing": lineage = lineage.iloc[:2]
    if bad == "duplicate": lineage = pd.concat([lineage, lineage.iloc[[0]]])
    if bad == "unknown": lineage.loc[2, "family"] = "unreviewed"
    if bad == "missing_time": lineage.loc[0, "source_max_ts"] = None
    if bad == "naive": lineage.loc[0, "source_max_ts"] = "2026-02-21T15:00:00"
    if bad == "deadline": deadlines = deadlines.iloc[:0]
    with pytest.raises(ValueError): audit.audit_history_sources(rows, lineage, deadlines)


def test_explicit_zero_history_is_distinct_from_missing_provenance():
    rows, lineage, deadlines = history_frames()
    lineage.loc[0, ["source_count", "source_max_ts"]] = [0, None]
    result = audit.audit_history_sources(rows, lineage, deadlines)
    assert result["history_contract_passed"] and not result["independent_lineage_certified"]
    lineage.loc[1, "source_max_ts"] = "2026-02-27T15:30:00Z"
    assert not audit.audit_history_sources(rows, lineage, deadlines)["history_contract_passed"]


def test_fixture_capture_rejects_future_results_and_preserves_unknown_schedule():
    frame = pd.DataFrame([dict(id=1, event=28, kickoff_time="2026-02-28T15:00:00Z",
                               finished=False, started=False, team_h_score=None, team_a_score=None),
                          dict(id=2, event=None, kickoff_time=None, finished=False,
                               started=None, team_h_score=None, team_a_score=None)])
    result = audit.audit_fixture_snapshot(frame, "2026-02-27T13:00:00Z")
    assert result["asof_result_screen_passed"] and result["unknown_event_rows"] == 1
    assert not result["fixture_knowledge_certified"]
    frame.loc[0, "team_h_score"] = 2
    assert audit.audit_fixture_snapshot(frame, "2026-02-27T13:00:00Z")["future_result_conflicts"] == 1
