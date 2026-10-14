"""Timestamped observations and explicit GW-scoped sensitivity assumptions.

Official chance labels remain evidence, never calibrated start probabilities.
"""
import math
from urllib.parse import urlparse
import pandas as pd


def utc(value):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError("An explicit timezone-aware timestamp is required")
    return stamp.tz_convert("UTC")


def observations(bootstrap, source):
    upcoming = [e for e in bootstrap["events"] if e.get("is_next")]
    if len(upcoming) > 1:
        raise ValueError("Multiple next gameweeks cannot label observations")
    event = upcoming[0] if upcoming else None
    utc(source["retrieved_utc"])
    if event:utc(event["deadline_time"])
    rows = []
    for player in bootstrap["elements"]:
        if player["element_type"] not in (1, 2, 3, 4): continue
        value = player.get("ep_next")
        try:
            value = float(value)
            if not math.isfinite(value): value = None
        except (TypeError, ValueError): value = None
        if not event:value=None
        rows.append({"id": player["id"], "GW": event["id"] if event else None,
            "status": player.get("status"), "news": player.get("news", ""),
            "news_added": player.get("news_added"),
            "official_chance_label": player.get("chance_of_playing_next_round"),
            "official_ep_next": value,
            "expected_minutes_override": None,
            "reason": None, "source_url": None, "published_at_utc": None})
    return {"schema_version": 1, "source": source,
            "GW": event["id"] if event else None, "deadline_time": event["deadline_time"] if event else None,
            "note": "Official chance labels are not model probabilities; blank overrides are unknown.",
            "players": rows}


def scoped_overrides(document, bootstrap, generated_at):
    if document.get("schema_version") != 1:
        raise ValueError("Unsupported availability review schema")
    gw = document["GW"]
    event = next(e for e in bootstrap["events"] if e["id"] == gw)
    deadline = utc(event["deadline_time"])
    recorded = utc(document["recorded_at_utc"])
    if recorded >= deadline or recorded > utc(generated_at):
        raise ValueError("Review must be recorded before the deadline and forecast generation")
    known = {p["id"] for p in bootstrap["elements"]}
    result = {}
    for entry in document["players"]:
        ident = entry["id"]
        if ident not in known or ident in result:
            raise ValueError("Unknown or duplicate reviewed football player ID")
        if not str(entry.get("reason") or "").strip():
            raise ValueError("Each applied assumption requires a reason")
        parsed = urlparse(entry.get("source_url") or "")
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Each applied assumption requires a public source URL")
        published = utc(entry["published_at_utc"])
        checked = utc(entry["checked_at_utc"])
        if not published <= checked <= recorded:
            raise ValueError("Source publication/check times must precede review recording")
        if checked >= deadline:
            raise ValueError("Post-deadline evidence cannot adjust a frozen forecast")
        assumption = {"reason": entry["reason"], "source_url": entry["source_url"],
                      "published_at_utc": published.isoformat(), "checked_at_utc": checked.isoformat()}
        for key, upper in (("minutes", 90), ("availability", 1)):
            if key in entry:
                value = float(entry[key])
                if not math.isfinite(value) or not 0 <= value <= upper:
                    raise ValueError(f"{key} must be finite in [0,{upper}]")
                assumption[key] = value
        if not any(key in assumption for key in ("minutes", "availability")):
            raise ValueError("Review entry must state a sensitivity assumption")
        result[ident] = assumption
    return gw, recorded, result


def official_baselines(bootstrap):
    upcoming = [e for e in bootstrap["events"] if e.get("is_next")]
    if len(upcoming) != 1: return {}
    result = {}
    for player in bootstrap["elements"]:
        try:
            value = float(player.get("ep_next"))
            if math.isfinite(value): result[(player["id"], upcoming[0]["id"])] = value
        except (TypeError, ValueError): pass
    return result
