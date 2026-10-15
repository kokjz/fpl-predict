"""Offline admission of published historical attribute CSV prefixes.

Git metadata must be independently retrieved and reviewed. Git timestamps are
publisher-history evidence, not independent cryptographic time certification.
No news is translated into a learned probability, and no model is fitted.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

from external_benchmark import _timestamp

MAX_BYTES = 25_000_000
REQUIRED = {"timestamp", "season", "gameweek", "player_id", "opta_code", "position",
            "news", "chance_of_playing_next_round", "return_gameweek"}


def read_archive(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES: raise ValueError("Archive size budget")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as f: raw = f.read(MAX_BYTES+1)
    if len(raw) > MAX_BYTES: raise ValueError("Expanded archive size budget")
    return raw


def optional_integer(value, low, high):
    if value in (None, ""): return None
    if not re.fullmatch(r"\d+", str(value)): raise ValueError("Invalid attribute integer")
    result = int(value)
    if not low <= result <= high: raise ValueError("Attribute range")
    return result


def admit_prefix(raw, record, bootstrap):
    """Return aggregate audit and selected raw observations without assumed UTC.

    Use publication of the exact byte prefix as the conservative availability
    time, retaining naive source clocks as opaque capture identifiers. The final
    append group is selected without using player outcomes or a name fallback.
    """
    if len(raw) > MAX_BYTES: raise ValueError("Archive size budget")
    deadline = _timestamp(record["deadline"]); published = _timestamp(record["published_at"])
    if published >= deadline: raise ValueError("Publication is not before deadline")
    if not re.fullmatch(r"[0-9a-f]{40}", record["commit"]): raise ValueError("Invalid commit identity")
    size = record["size"]
    if type(size) is not int or not 0 < size <= len(raw): raise ValueError("Invalid prefix extent")
    prefix = raw[:size]
    blob = hashlib.sha1(b"blob "+str(size).encode()+b"\0"+prefix).hexdigest()
    if blob != record["git_blob_sha1"]: raise ValueError("Published prefix checksum mismatch")
    if not prefix.endswith(b"\n"): raise ValueError("Incomplete CSV record")
    reader = csv.DictReader(io.StringIO(prefix.decode("utf-8"), newline=""))
    if not REQUIRED <= set(reader.fieldnames or []): raise ValueError("Missing source schema")
    if len(reader.fieldnames) != len(set(reader.fieldnames)): raise ValueError("Duplicate source columns")
    # Keep only the last contiguous capture group, not all historical rows.
    capture = None; selected = []; completed = set()
    for row in reader:
        if None in row or any(v is None for v in row.values()): raise ValueError("Malformed CSV row")
        stamp = row["timestamp"]
        if not stamp: raise ValueError("Missing capture identifier")
        if capture != stamp:
            if stamp in completed: raise ValueError("Noncontiguous capture groups")
            if capture is not None: completed.add(capture)
            capture = stamp; selected = []
        selected.append(row)
    if not selected: raise ValueError("Empty published prefix")
    gw = optional_integer(record["gameweek"], 1, 38)
    events = [e for e in bootstrap["events"] if e["id"] == gw]
    if len(events) != 1 or _timestamp(events[0]["deadline_time"]) != deadline:
        raise ValueError("Independent bootstrap deadline differs")
    by_code = {}; by_id = {}
    for player in bootstrap["elements"]:
        if player["code"] in by_code or player["id"] in by_id: raise ValueError("Ambiguous bootstrap identity")
        by_code[player["code"]] = player; by_id[player["id"]] = player
    seen_codes = set(); seen_ids = set(); known = 0; missing = 0; news = 0; chance = 0; return_gw = 0
    observations = []
    for row in selected:
        if row["season"] != "2526" or optional_integer(row["gameweek"], 1, 38) != gw:
            raise ValueError("Capture season/gameweek differs")
        if not re.fullmatch(r"p\d+", row["opta_code"]): raise ValueError("Missing stable source identity")
        code = int(row["opta_code"][1:]); element = optional_integer(row["player_id"], 1, 100000)
        if code <= 0 or code in seen_codes or element in seen_ids: raise ValueError("Duplicate source identity")
        seen_codes.add(code); seen_ids.add(element)
        official = by_code.get(code)
        if official is None:
            if element in by_id: raise ValueError("Source ID maps to another bootstrap code")
            missing += 1
        else:
            if official["id"] != element: raise ValueError("Source code/element conflict")
            position = {"GK": 1, "DEF": 2, "MID": 3, "FWD": 4}.get(row["position"])
            if official["element_type"] != position: raise ValueError("Source position conflict")
            known += 1
        value = optional_integer(row["chance_of_playing_next_round"], 0, 100)
        back = optional_integer(row["return_gameweek"], 1, 38)
        text = row["news"].strip(); news += bool(text); chance += value is not None; return_gw += back is not None
        observations.append(dict(fpl_code=code, element=element, news=text,
                                 chance_label=value, return_gameweek=back,
                                 available_by=published.isoformat(), source_clock=capture))
    report = dict(gameweek=gw, published_at=published.isoformat(), deadline=deadline.isoformat(),
                  publication_lead_hours=(deadline-published).total_seconds()/3600,
                  commit=record["commit"], git_blob_sha1=blob, prefix_bytes=size,
                  prefix_sha256=hashlib.sha256(prefix).hexdigest(), rows=len(selected),
                  bootstrap_known=known, absent_at_other_capture=missing,
                  news_nonempty=news, chance_known=chance, return_gameweek_known=return_gw,
                  source_clock_has_timezone=(bool(re.search(r"(?:Z|[+-]\d\d:\d\d)$", capture))),
                  time_basis="exact-prefix Git publication, not assumed source-clock timezone",
                  model_admitted=False, benchmark_admitted=False)
    return report, observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "proof", "output"): parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists(): raise ValueError("Audit output exists")
        if args.proof.stat().st_size > 1_000_000: raise ValueError("Proof size budget")
        proof = json.loads(args.proof.read_text()); raw = read_archive(args.archive); reports = []
        if not 0 < len(proof["records"]) <= 38: raise ValueError("Proof record budget")
        for record in proof["records"]:
            path = Path(record["bootstrap_path"])
            if path.stat().st_size > 10_000_000: raise ValueError("Bootstrap size budget")
            # Bootstrap files may be xz-compressed; hashes cover exact supplied bytes.
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != record["bootstrap_sha256"]: raise ValueError("Bootstrap checksum mismatch")
            if path.suffix == ".xz":
                import lzma
                with lzma.open(path, "rb") as f: data = f.read(10_000_001)
                if len(data) > 10_000_000: raise ValueError("Expanded bootstrap budget")
            report, _ = admit_prefix(raw, record, json.loads(data)); reports.append(report)
        result = dict(schema_version=1, archive_sha256=hashlib.sha256(raw).hexdigest(),
                      proof_sha256=hashlib.sha256(args.proof.read_bytes()).hexdigest(), reports=reports,
                      scope=proof.get("scope", "supplied sample only"), model_admitted=False,
                      limitations=["Git-history timing is not independent certification", "sample coverage only",
                                   "chance labels are not calibrated probabilities", "no training or accuracy evidence"])
        with args.output.open("x") as f: json.dump(result, f, indent=2, allow_nan=False)
    except (ValueError, KeyError, OSError, TypeError) as exc: parser.exit(2, f"Availability audit rejected: {exc}\n")
    print("Offline source audit saved; no model admission or fitting.")


if __name__ == "__main__": main()
