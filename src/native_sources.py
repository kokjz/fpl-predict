"""Auditable numeric source joins for the native-window research variant.

No network, pickle loading or automatic substitution of released rolling values.
All target rows survive; unavailable mapped appearances fail readiness.
"""
import numpy as np
import pandas as pd

from deadline_provenance import extract_bootstrap

ALIASES={"Man City":"Manchester City","Man Utd":"Manchester United","Newcastle":"Newcastle United",
         "Nott'm Forest":"Nottingham Forest","Sheffield Utd":"Sheffield United","Spurs":"Tottenham",
         "West Brom":"West Bromwich Albion","Wolves":"Wolverhampton Wanderers"}
IDENTITY_CORRECTIONS={437688:9216,515501:10576}
FIELDS={"us_shots":"shots","us_xG":"xG","us_xGChain":"xGChain","us_xGBuildup":"xGBuildup",
        "us_key_passes":"key_passes","us_xA":"xA"}


def provider_name(name):return ALIASES.get(name,name)


def corrected_assignments(frame):
    """Apply the two published evidence-backed historical identity corrections."""
    result=frame.copy()
    for code,identity in IDENTITY_CORRECTIONS.items():result.loc[result.fpl_code.eq(code),"understat_id"]=identity
    return result


def match_roster_observations(metadata,payload):
    """Read actual match-roster records for profile-omitted appearances.

    Metadata comes from the provider's league match list; callers retain its
    source hash and the match-response hash. No synthetic zero statistics.
    """
    rosters=payload["rosters"];seen=set();result=[];goals={"h":0,"a":0};own={"h":0,"a":0}
    for side in ("h","a"):
        if not rosters.get(side):raise ValueError("Incomplete match roster")
        for row in rosters[side].values():
            identity=int(row["player_id"])
            if identity in seen or str(row["team_id"])!=str(metadata[side+"_team_id"]) or row["h_a"]!=side:
                raise ValueError("Ambiguous match-roster identity")
            seen.add(identity);goals[side]+=float(row["goals"]);own[side]+=float(row["own_goals"])
            record={**row,"date":metadata["date"],"h_team":metadata["h_team"],"a_team":metadata["a_team"]}
            for field in FIELDS.values():
                if not np.isfinite(float(record[field])):raise ValueError("Invalid match-roster statistic")
            result.append((identity,record))
    if goals["h"]+own["a"]!=float(metadata["h_goals"]) or goals["a"]+own["h"]!=float(metadata["a_goals"]):
        raise ValueError("Incomplete match-roster goals")
    return result


def _key(row):
    if pd.isna(row.understat_id):return None
    home=provider_name(row.team_name if row.home else row.opponent_name)
    away=provider_name(row.opponent_name if row.home else row.team_name)
    return (int(row.understat_id),row.ts.date().isoformat(),home,away)


def join_player_statistics(players,captures):
    """Join by reviewed ID/date/home/away, never names guessed from outcomes.

    `captures` yields (numeric Understat ID, decoded public player payload).
    Exact duplicate required records are counted; conflicts stop. Provider
    matches outside the required FPL date/team scope are not training records.
    """
    required={_key(r) for r in players.itertuples()}-{None}
    lookup={};duplicates=0
    for identity,payload in captures:
        if not isinstance(payload.get("matches"),list):raise ValueError("Missing provider match list")
        for row in payload["matches"]:
            key=(int(identity),str(row["date"])[:10],row["h_team"],row["a_team"])
            if key not in required:continue
            if key in lookup:
                if row!=lookup[key]:raise ValueError("Conflicting provider match identity")
                duplicates+=1;continue
            lookup[key]=row
    values={name:[] for name in FIELDS};missing=[];unmapped=0
    for r in players.itertuples():
        key=_key(r);row=lookup.get(key)
        if r.minutes>0 and key is not None and row is None:
            missing.append(dict(season=r.season,gameweek=int(r.gameweek) if hasattr(r,"gameweek") else None,
                                fixture=int(r.fixture),code=int(r.fpl_code),understat_id=int(r.understat_id),date=r.ts.date().isoformat()))
        if r.minutes>0 and key is None:unmapped+=1
        for name,field in FIELDS.items():
            # Observed0-minute events differ from unmapped played observations.
            value=float(row[field]) if row is not None else 0. if r.minutes==0 else np.nan
            if np.isinf(value):raise ValueError("Infinite provider statistic")
            values[name].append(value)
    result=players.copy()
    for name,array in values.items():result[name]=array
    return result,dict(mapped_appearance_missing=len(missing),missing=missing,
                       unmapped_appearance_rows=unmapped,exact_provider_duplicates_removed=duplicates)


def join_team_statistics(fixtures,captures):
    """Resolve EPL club/date/venue/score, assigning authoritative FPL event times.

    Provider clock offsets are reported, not guessed into UTC. A club has at most
    one required league fixture on a date; missing/conflicting joins fail readiness.
    """
    lookup={}
    for year,payload in captures:
        for team in payload["teams"].values():
            for row in team["history"]:
                key=(str(year),team["title"],str(row["date"])[:10])
                if key in lookup:raise ValueError("Duplicate provider team/date")
                lookup[key]=row
    rows=[];missing=[];offsets={}
    if fixtures.assign(day=fixtures.ts.dt.date).duplicated(["season","team_name","day"]).any():
        raise ValueError("Ambiguous FPL club/date")
    for r in fixtures.itertuples():
        row=lookup.get((r.season[:4],provider_name(r.team_name),r.ts.date().isoformat()))
        if row is None:
            missing.append(dict(season=r.season,fixture=int(r.fixture),team=r.team_name));continue
        gf=r.team_h_score if r.home else r.team_a_score;ga=r.team_a_score if r.home else r.team_h_score
        if float(row["scored"])!=gf or float(row["missed"])!=ga or row["h_a"]!=("h" if r.home else "a"):
            raise ValueError("Team fixture venue/score disagreement")
        offset=int((pd.Timestamp(row["date"],tz="UTC")-r.ts).total_seconds())
        offsets[str(offset)]=offsets.get(str(offset),0)+1
        out=dict(season=r.season,fixture=r.fixture,team_name=r.team_name,opponent_name=r.opponent_name,
                 ts=r.ts,goals_scored=gf,goals_conceded=ga,xg=float(row["xG"]),xga=float(row["xGA"]),
                 deep=float(row["deep"]),deep_allowed=float(row["deep_allowed"]))
        for name in ("ppda","ppda_allowed"):
            out[name+"_att"]=float(row[name]["att"]);out[name+"_def"]=float(row[name]["def"])
        rows.append(out)
    return pd.DataFrame(rows),dict(team_conflicts=missing,provider_team_time_offsets_seconds=offsets)


def snapshot_features(payload,season,gameweek,captured_at):
    """Use captured fields, never post-match `xP`/selection/value substitutes."""
    _,bridge=extract_bootstrap(payload,season,gameweek,captured_at)
    if not np.isfinite(float(payload["total_players"])) or float(payload["total_players"])<=0:
        raise ValueError("Invalid snapshot manager count")
    records=[]
    for r in payload["elements"]:
        records.append(dict(season=season,gameweek=gameweek,fpl_code=r["code"],captured_at=captured_at,
            value=float(r["now_cost"]),selected=float(r["selected_by_percent"])*float(payload["total_players"])/100,
            transfers_balance=float(r["transfers_in_event"])-float(r["transfers_out_event"]),
            ar_ep_next=float(r["ep_next"]) if r.get("ep_next") not in (None,"") else -1.,
            sig_status_risk={"a":0,"d":1,"s":2,"i":3,"u":4,"n":4}.get(r.get("status","a"),0),
            sig_chance_playing=float(r["chance_of_playing_next_round"]) if r.get("chance_of_playing_next_round") is not None else -1.,
            sig_has_news=float(bool((r.get("news") or "").strip()))))
    return pd.DataFrame(records)
