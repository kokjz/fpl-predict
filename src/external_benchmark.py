"""Local-only, provenance-declared comparison of identical player-gameweek rows.

This module never imports external model code, fits estimators or fetches URLs.
Declared source provenance still requires independent human review.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
from urllib.parse import urlsplit
from importlib.resources import files
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark_metrics import point_scores

KEYS = ["season", "gameweek", "fpl_code"]
FIXTURE_KEYS = [*KEYS, "fixture"]
TIMES = ["features_cutoff", "train_cutoff", "selection_cutoff", "created_at"]
SHA = re.compile(r"[0-9a-f]{64}")
MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}")


def protocol():
    return json.loads(files("fpl_predict_resources").joinpath("benchmark_protocol.json").read_text())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _required(obj, fields, label):
    missing = set(fields) - set(obj)
    if missing:
        raise ValueError(f"{label}: missing fields {sorted(missing)}")


def _timestamp(value):
    try:
        stamp = pd.Timestamp(value)
        if pd.isna(stamp) or stamp.tzinfo is None:
            raise ValueError
        return stamp.tz_convert("UTC")
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Expected a timezone-aware timestamp") from exc


def _numeric(frame, columns, *, integer=False, minimum=None):
    for col in columns:
        if frame[col].map(lambda v: isinstance(v, (bool, np.bool_))).any():
            raise ValueError(f"{col}: booleans are not numeric IDs/scores")
        try:
            values = pd.to_numeric(frame[col], errors="raise")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{col}: invalid numeric value") from exc
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"{col}: nonfinite value")
        if integer and ((values.abs() > 2**53).any() or not (values == np.floor(values)).all()):
            raise ValueError(f"{col}: IDs must be integers")
        if minimum is not None and not values.ge(minimum).all():
            raise ValueError(f"{col}: out-of-range value")
        frame[col] = values.astype("int64") if integer else values.astype(float)


def _identities(frame, *, fixtures=False):
    if frame.empty or len(frame) > protocol()["max_rows"]:
        raise ValueError("Empty input or row limit exceeded")
    if not frame.season.map(lambda s: isinstance(s, str)).all():
        raise ValueError("season must be a string")
    if not set(frame.season).issubset(protocol()["target_by_season"]):
        raise ValueError("Unsupported season: extend and review protocol first")
    _numeric(frame, ["gameweek", "fpl_code"], integer=True, minimum=1)
    if not frame.gameweek.le(38).all():
        raise ValueError("gameweek out of range")
    if fixtures:
        _numeric(frame, ["fixture"], integer=True, minimum=0)
    keys = FIXTURE_KEYS if fixtures else KEYS
    if frame.duplicated(keys).any():
        raise ValueError("Duplicate input keys")


def prepare_outcomes(frame):
    """Validate authoritative fixture outcomes and a frozen candidate predicate."""
    _required(frame, [*FIXTURE_KEYS, "actual", "candidate", "deadline"], "outcomes")
    d = frame.copy()
    _identities(d, fixtures=True)
    _numeric(d, ["actual"], integer=True)
    if not d.candidate.map(lambda v: isinstance(v, (bool, np.bool_))).all():
        raise ValueError("candidate must contain explicit booleans")
    d["deadline"] = d.deadline.map(_timestamp)
    # Every player's fixtures in a GW share one candidate decision and deadline.
    groups = d.groupby(KEYS, sort=True)
    for col in ("candidate", "deadline"):
        if not groups[col].nunique().eq(1).all():
            raise ValueError(f"Conflicting {col} within player-gameweek")
    if not d.groupby(["season", "gameweek"]).deadline.nunique().eq(1).all():
        raise ValueError("Conflicting gameweek deadlines")
    blanks = d.fixture.eq(0)
    if not d.loc[blanks, "actual"].eq(0).all():
        raise ValueError("Blank placeholder must have zero points")
    if any(0 in set(g.fixture) and len(g) != 1 for _, g in groups):
        raise ValueError("Blank placeholder mixed with played fixtures")
    # A fixture belongs to one GW in this declared schedule.
    played = d.loc[~blanks]
    if not played.groupby(["season", "fixture"]).gameweek.nunique().le(1).all():
        raise ValueError("Fixture assigned to multiple gameweeks")
    return d


def _mapped(frame, manifest):
    mapping = manifest.get("columns", {})
    if not isinstance(mapping, dict) or len(set(mapping.values())) != len(mapping):
        raise ValueError("Column mapping must be one-to-one")
    allowed = set(FIXTURE_KEYS + TIMES + ["prediction", "actual", "captured_at"])
    if not set(mapping).issubset(allowed):
        raise ValueError("Unknown canonical column mapping")
    selected = {}
    for col in allowed:
        source = mapping.get(col, col)
        if source in frame.columns:
            selected[col] = frame[source]
        elif col in mapping:
            raise ValueError(f"Mapped column absent: {col}")
    # Implicit canonical names must not alias an explicitly mapped source.
    used = [mapping.get(col, col) for col in selected]
    if len(used) != len(set(used)):
        raise ValueError("Overlapping canonical and mapped columns")
    return pd.DataFrame(selected, index=frame.index)


def validate_manifest(manifest):
    _required(manifest, ["schema_version", "model_id", "grain", "prediction_kind",
                        "horizon_gameweeks", "target_by_season", "source_url", "source_revision",
                        "code_sha256", "data_sha256", "input_sha256"], "manifest")
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported manifest version")
    if not isinstance(manifest["model_id"], str) or not MODEL_ID.fullmatch(manifest["model_id"]):
        raise ValueError("Invalid model_id")
    if type(manifest["horizon_gameweeks"]) is not int or manifest["horizon_gameweeks"] != 1:
        raise ValueError("Only one-gameweek forecast horizons are supported")
    if manifest["grain"] not in ("fixture", "player_gameweek"):
        raise ValueError("Unknown prediction grain")
    if manifest["prediction_kind"] not in ("archived_predeadline", "retrospective"):
        raise ValueError("Unknown prediction origin")
    if not isinstance(manifest["target_by_season"], dict):
        raise ValueError("target_by_season must be a mapping")
    for name in ("code_sha256", "data_sha256", "input_sha256"):
        if not isinstance(manifest[name], str) or not SHA.fullmatch(manifest[name]):
            raise ValueError(f"Invalid {name}")
    if not isinstance(manifest["source_url"], str):
        raise ValueError("Expected public HTTPS source URL")
    url = urlsplit(manifest["source_url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("Source URL must be HTTPS without credentials, query or fragment")
    revision = manifest["source_revision"]
    if not isinstance(revision, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", revision):
        raise ValueError("Expected immutable source commit or content hash")


def normalise_forecast(frame, manifest, outcomes):
    """Adapt a declared export, rejecting every invalid row before intersection."""
    validate_manifest(manifest)
    d = _mapped(frame, manifest)
    fixture_grain = manifest["grain"] == "fixture"
    _required(d, [*(FIXTURE_KEYS if fixture_grain else KEYS), "prediction"], "predictions")
    _identities(d, fixtures=fixture_grain)
    _numeric(d, ["prediction"])
    if "actual" in d:
        _numeric(d, ["actual"])
    targets = protocol()["target_by_season"]
    for season in set(d.season):
        if manifest["target_by_season"].get(season) != targets[season]:
            raise ValueError("Scoring target mismatch")
    defaults = manifest.get("timing", {})
    if not isinstance(defaults, dict):
        raise ValueError("timing must be a mapping")
    for col in TIMES + (["captured_at"] if manifest["prediction_kind"] == "archived_predeadline" else []):
        if col not in d:
            if col not in defaults:
                raise ValueError(f"Missing timing evidence: {col}")
            d[col] = defaults[col]
        d[col] = d[col].map(_timestamp)
    if "captured_at" in d:
        d["captured_at"] = d.captured_at.map(_timestamp)
    baseline = outcomes.groupby(KEYS, as_index=False).agg(
        expected_actual=("actual", "sum"), deadline=("deadline", "first"))
    keys = FIXTURE_KEYS if fixture_grain else KEYS
    expected = outcomes[[*FIXTURE_KEYS, "actual", "deadline"]].rename(columns={"actual": "expected_actual"}) if fixture_grain else baseline
    d = d.merge(expected, on=keys, how="left", validate="one_to_one", indicator=True)
    if not d._merge.eq("both").all():
        raise ValueError("Prediction keys outside declared outcome universe")
    if "actual" in d and not np.allclose(d.actual, d.expected_actual, atol=1e-9, rtol=0):
        raise ValueError("Conflicting source outcomes")
    for col in ("features_cutoff", "train_cutoff", "selection_cutoff"):
        if not d[col].lt(d.deadline).all():
            raise ValueError(f"{col} reaches or follows deadline")
        if not d[col].le(d.created_at).all():
            raise ValueError(f"{col} follows prediction creation")
    for col in ("train_cutoff", "selection_cutoff"):
        if not d[col].le(d.features_cutoff).all():
            raise ValueError(f"{col} follows available feature cutoff")
    if manifest["prediction_kind"] == "archived_predeadline":
        if not (d.created_at.le(d.captured_at) & d.captured_at.lt(d.deadline)).all():
            raise ValueError("Archived forecast not captured before deadline")
    if fixture_grain:
        # Entirely absent GWs are coverage gaps. Partial doubles cannot be scored.
        actual_sets = d.groupby(KEYS).fixture.agg(lambda s: frozenset(s))
        expected_sets = outcomes.groupby(KEYS).fixture.agg(lambda s: frozenset(s))
        if any(fixtures != expected_sets.loc[key] for key, fixtures in actual_sets.items()):
            raise ValueError("Incomplete fixture coverage within player-gameweek")
        for col in TIMES + (["captured_at"] if "captured_at" in d else []):
            if not d.groupby(KEYS)[col].nunique().eq(1).all():
                raise ValueError("Double fixtures have differing timing evidence")
    result = d.groupby(KEYS, as_index=False).prediction.sum()
    if not np.isfinite(result.prediction).all():
        raise ValueError("Nonfinite aggregate forecast")
    timing = {col: {"min": d[col].min().isoformat(), "max": d[col].max().isoformat()}
              for col in TIMES + (["captured_at"] if "captured_at" in d else [])}
    return result, timing


def compare(outcomes, exports):
    """Return aggregate reports; `exports` is [(raw_frame, manifest), ...]."""
    truth = prepare_outcomes(outcomes)
    if len(exports) < 2 or len(exports) > 12:
        raise ValueError("Supply between two and twelve models")
    base = truth.groupby(KEYS, as_index=False).agg(
        actual=("actual", "sum"), candidate=("candidate", "first"))
    if not np.isfinite(base.actual).all():
        raise ValueError("Nonfinite aggregate outcomes")
    joined = base.copy()
    provenance = {}
    prediction_columns = {}
    for i, (frame, manifest) in enumerate(exports):
        normal, timing = normalise_forecast(frame, manifest, truth)
        name = manifest["model_id"]
        if name in provenance:
            raise ValueError("Duplicate model IDs")
        column = f"prediction_{i}"
        prediction_columns[name] = column
        provenance[name] = {k: manifest[k] for k in (
            "grain", "prediction_kind", "horizon_gameweeks", "target_by_season", "source_url", "source_revision",
            "code_sha256", "data_sha256", "input_sha256")}
        provenance[name]["declared_timing_ranges"] = timing
        joined = joined.merge(normal.rename(columns={"prediction": column}), on=KEYS,
                              how="left", validate="one_to_one")
    names = list(provenance)

    def section(selected):
        cols = [prediction_columns[n] for n in selected]
        matched = joined.loc[joined[cols].notna().all(axis=1)]
        return {
            "rows": len(matched),
            "coverage": len(matched) / len(base),
            "candidate_coverage": float(matched.candidate.sum() / base.candidate.sum()) if base.candidate.any() else None,
            "cohorts": {
                label: {"rows": len(subset), "models": {
                    name: point_scores(subset, prediction_columns[name]) for name in selected}}
                for label, subset in (("predeadline_candidates", matched.loc[matched.candidate]),
                                      ("all_matched", matched))}}

    return {
        "schema_version": 1,
        "protocol_id": protocol()["protocol_id"],
        "protocol_sha256": digest(files("fpl_predict_resources").joinpath("benchmark_protocol.json").read_bytes()),
        "scope": "retrospective comparison; provenance declared, not independently certified",
        "promotion": False,
        "outcome_player_gameweeks": len(base),
        "outcome_candidate_player_gameweeks": int(base.candidate.sum()),
        "sources": provenance,
        "coverage_by_model": {name: {
            "rows": int(joined[col].notna().sum()),
            "coverage": float(joined[col].notna().mean()),
            "candidate_rows": int((joined[col].notna() & joined.candidate).sum()),
            "candidate_coverage": float(joined.loc[joined.candidate, col].notna().mean()) if base.candidate.any() else None}
            for name, col in prediction_columns.items()},
        "all_model_intersection": section(names),
        "pairwise_intersections": [{"models": list(pair), **section(pair)}
                                   for pair in itertools.combinations(names, 2)],
    }


def _json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON object key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def _read(path):
    # Bounded read even if a file grows after stat; reject oversized inputs.
    with Path(path).open("rb") as stream:
        raw = stream.read(protocol()["max_file_bytes"] + 1)
    if len(raw) > protocol()["max_file_bytes"]:
        raise ValueError("File size limit exceeded")
    return raw


def load_table(path):
    raw = _read(path)
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        import csv
        import io
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Missing or duplicate CSV columns")
        rows = []
        for row in reader:
            if None in row or None in row.values():
                raise ValueError("Malformed CSV row")
            rows.append(row)
            if len(rows) > protocol()["max_rows"]:
                raise ValueError("Row limit exceeded")
        frame = pd.DataFrame(rows)
        # Explicit CSV true/false only; never bool('False') or fill missingness.
        if "candidate" in frame:
            if not frame.candidate.isin(["true", "false"]).all():
                raise ValueError("CSV candidate requires lowercase true/false")
            frame["candidate"] = frame.candidate.eq("true")
    elif suffix == ".jsonl":
        rows = [_json(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        if len(rows) > protocol()["max_rows"] or not all(isinstance(r, dict) for r in rows):
            raise ValueError("Invalid JSONL rows or row limit exceeded")
        frame = pd.DataFrame(rows)
    else:
        raise ValueError("Only CSV and JSONL tables are supported")
    return frame, digest(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outcomes", required=True, type=Path)
    parser.add_argument("--outcomes-sha256", required=True)
    parser.add_argument("--manifest", required=True, action="append", type=Path,
                        help="Repeat per model; local export path relative to each manifest")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if not 2 <= len(args.manifest) <= 12:
            raise ValueError("Supply between two and twelve model manifests")
        if args.output.exists():
            raise ValueError("Output already exists; use a new report filename")
        outcomes, outcome_hash = load_table(args.outcomes)
        if outcome_hash != args.outcomes_sha256:
            raise ValueError("Outcome checksum mismatch")
        exports = []
        manifest_hashes = {}
        for path in args.manifest:
            raw = _read(path)
            manifest = _json(raw)
            validate_manifest(manifest)
            _required(manifest, ["file"], "manifest")
            if not isinstance(manifest["file"], str) or not manifest["file"]:
                raise ValueError("Missing local export path")
            table, export_hash = load_table(path.parent / manifest["file"])
            if export_hash != manifest["input_sha256"]:
                raise ValueError("Forecast checksum mismatch")
            exports.append((table, manifest))
            manifest_hashes[manifest["model_id"]] = digest(raw)
        result = compare(outcomes, exports)
        result["outcomes_sha256"] = outcome_hash
        result["manifest_sha256"] = manifest_hashes
        serialised = json.dumps(result, indent=2, allow_nan=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            stream.write(serialised)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"Benchmark rejected: {exc}\n")
    print("Aggregate comparison saved. No training, provenance certification or promotion performed.")


if __name__ == "__main__":
    main()
