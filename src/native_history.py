"""Cutoff-based native-window research features, independent of deployment caches.

Definitions informed by OpenFPL/Dastan (see THIRD_PARTY_NOTICES.md). Every history
is queried strictly before the common deadline minus a3h completion buffer.
This is a named reconstruction variant, not the released system's feature file.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from external_benchmark import _timestamp

WINDOWS = (1, 3, 5, 10, 38)
PLAYER_STATS = {
    "total_points": "fpl_points", "minutes": "minutes_played",
    "influence": "influence", "creativity": "creativity", "threat": "threat",
    "goals_scored": "goals_scored", "penalties_missed": "penalties_missed",
    "assists": "assists", "goals_conceded": "goals_conceded", "own_goals": "own_goals",
    "saves": "saves", "penalties_saved": "penalties_saved", "yellow_cards": "yellow_cards",
    "red_cards": "red_cards", "bps": "bps", "bonus": "fpl_bonus_points",
    "us_shots": "shots", "us_xG": "xg", "us_xGChain": "xgchain",
    "us_xGBuildup": "xgbuildup", "us_key_passes": "key_passes", "us_xA": "xa",
}
TEAM_STATS = ("goals_scored", "goals_conceded", "league_rank", "opponent_league_rank",
              "xg", "deep_allowed", "ppda_allowed_att", "ppda_allowed_def", "xga",
              "deep", "ppda_att", "ppda_def")
DEFENSIVE = ("defensive_contribution", "cbit", "recoveries", "tackles")
SNAPSHOT_FEATURES = ("value", "selected", "transfers_balance", "ar_ep_next",
                     "sig_status_risk", "sig_chance_playing", "sig_has_news")
FEATURES = ([f"player_{name}_{w}" for name in [*PLAYER_STATS.values(), "relevant_fpl_points"] for w in WINDOWS] +
            [f"{side}_{name}_{w}" for side in ("team", "opp") for name in TEAM_STATS for w in WINDOWS] +
            ["is_home_num", "status_league_rank", "opp_status_league_rank"] + list(SNAPSHOT_FEATURES) +
            [f"{prefix}_{w}" for prefix in ("p_any", "p60", "e_minutes") for w in (3, 5, 10)] +
            [f"ar_{name}_{w}" for name in DEFENSIVE for w in (3, 5, 10, 38)] +
            [f"ar_{name}_{w}" for name in ("dc_hit_rate", "dc_near_rate", "starts") for w in (3, 5, 10)] +
            ["ar_dc_ppg_5", "ar_rest_days", "ar_team_matches_14d"] +
            [f"ar_opp_dc_allowed_{w}" for w in (3, 5, 10)] + ["ar_opp_tackles_allowed_5"])
FAMILIES = ("player", "team", "opponent", "league")


class WindowIndex:
    """NaN-aware prefix sums and strict time queries; no zero-filled unknowns."""
    def __init__(self, frame, columns):
        d = frame.sort_values("ts", kind="stable")
        self.times = pd.to_datetime(d.ts, utc=True).astype("datetime64[ns, UTC]").astype("int64").to_numpy()
        values = d[list(columns)].to_numpy(dtype=float)
        if np.isinf(values).any(): raise ValueError("Infinite raw statistics")
        valid = np.isfinite(values)
        self.sums = np.vstack([np.zeros(len(columns)), np.cumsum(np.where(valid, values, 0), axis=0)])
        self.counts = np.vstack([np.zeros(len(columns)), np.cumsum(valid, axis=0)])
        self.columns = list(columns)

    def end(self, cutoff):
        return int(np.searchsorted(self.times, cutoff.value, side="left"))

    def means(self, cutoff, windows=WINDOWS):
        end = self.end(cutoff); result = {}
        for w in windows:
            begin = max(0, end - w)
            count = self.counts[end] - self.counts[begin]
            result[w] = np.divide(self.sums[end] - self.sums[begin], count,
                                  out=np.full(len(self.columns), np.nan), where=count > 0)
        latest = pd.Timestamp(self.times[end-1], tz="UTC") if end else pd.NaT
        return result, end, latest


def _times(frame):
    d = frame.copy()
    d["ts"] = pd.to_datetime(d.ts.map(_timestamp), utc=True)
    if d.ts.isna().any(): raise ValueError("Missing raw match timestamp")
    return d


def league_tables(teams, queries):
    """Completed-results table at requested times; deterministic GF/GD/name ties.

    Returns global source maxima as well as ranks. This is a reconstructed table,
    not a claim to reproduce every official historical tie-break rule.
    """
    result = {}; history_ranks = {}
    for season, d in teams.groupby("season", sort=True):
        clubs = sorted(d.team_name.unique())
        totals = {c: [0., 0., 0.] for c in clubs}
        matches = d.sort_values("ts", kind="stable")
        records = list(matches.itertuples()); cursor = 0; latest = pd.NaT
        wanted = sorted(set(queries.get(season, [])) | {t - pd.Timedelta(hours=3) for t in d.ts})
        for time in wanted:
            while cursor < len(records) and records[cursor].ts < time:
                r = records[cursor]; gf = float(r.goals_scored); ga = float(r.goals_conceded)
                v = totals[r.team_name]; v[0] += 3 if gf > ga else 1 if gf == ga else 0
                v[1] += gf-ga; v[2] += gf; latest = r.ts; cursor += 1
            ordered = sorted(clubs, key=lambda c: (-totals[c][0], -totals[c][1], -totals[c][2], c))
            ranks = {c: i+1 for i, c in enumerate(ordered)}
            result[(season, time.value)] = (ranks, cursor, latest)
        for r in d.itertuples():
            ranks = result[(season, (r.ts-pd.Timedelta(hours=3)).value)][0]
            history_ranks[(season, r.fixture, r.team_name)] = (ranks[r.team_name], ranks[r.opponent_name])
    return result, history_ranks


class NativeHistory:
    """Canonical numeric match histories only; never consumes released rolling columns."""
    def __init__(self, players, teams):
        p = _times(players); t = _times(teams)
        needed_p = {"season", "fixture", "fpl_code", "position", "team_name", "opponent_name", "home", "starts", *PLAYER_STATS, *DEFENSIVE}
        needed_t = {"season", "fixture", "team_name", "opponent_name", *[c for c in TEAM_STATS if "league_rank" not in c]}
        if needed_p-set(p) or needed_t-set(t): raise ValueError("Missing required native raw columns")
        if p.duplicated(["season", "fixture", "fpl_code"]).any() or t.duplicated(["season", "fixture", "team_name"]).any():
            raise ValueError("Duplicate raw identity")
        if p.duplicated(["fpl_code","ts"]).any() or t.duplicated(["team_name","ts"]).any():
            raise ValueError("Ambiguous simultaneous history records")
        if not p.position.isin([1, 2, 3, 4]).all() or not p.home.isin([True, False]).all():
            raise ValueError("Invalid position/venue")
        if not np.isfinite(p[["minutes", "total_points"]]).all().all() or not p.minutes.between(0, 90).all():
            raise ValueError("Invalid player targets")
        if not np.isfinite(t[["goals_scored", "goals_conceded"]]).all().all():
            raise ValueError("Missing team results")
        known = set(zip(t.season, t.fixture, t.team_name))
        if not all((r.season, r.fixture, r.team_name) in known and (r.season, r.fixture, r.opponent_name) in known for r in p.itertuples()):
            raise ValueError("Player/team/opponent match coverage differs")
        self.players = p; self.teams = t; self.cache = {}; self.snapshot_cache = {}

    def prepare(self, targets):
        queries = {s: list(g.deadline-pd.Timedelta(hours=3)) for s,g in targets.groupby("season")}
        self.leagues, historical = league_tables(self.teams, queries)
        t = self.teams.copy()
        ranks = [historical[(r.season, r.fixture, r.team_name)] for r in t.itertuples()]
        t["league_rank"] = [r[0] for r in ranks]; t["opponent_league_rank"] = [r[1] for r in ranks]
        self.team_index = {key: WindowIndex(g, TEAM_STATS) for key,g in t.groupby("team_name", sort=False)}
        p = self.players.copy()
        p["_any"] = p.minutes.gt(0).astype(float); p["_sixty"] = p.minutes.ge(60).astype(float)
        threshold = np.where(p.position.eq(2),10,12)
        p["_hit"] = np.where(p.defensive_contribution.isna(),np.nan,
                              np.where(p.position.eq(1),0,p.defensive_contribution.ge(threshold).astype(float)))
        p["_near"] = np.where(p.defensive_contribution.isna(),np.nan,
                               np.where(p.position.eq(1),0,(p.defensive_contribution.ge(threshold-3)&p.defensive_contribution.lt(threshold)).astype(float)))
        player_cols = [*PLAYER_STATS, *DEFENSIVE, "_hit", "_near", "starts"]
        self.player_index = {key: WindowIndex(g, player_cols) for key,g in p.groupby("fpl_code", sort=False)}
        self.venue_index = {key: WindowIndex(g,["total_points"]) for key,g in p.groupby(["fpl_code","home"], sort=False)}
        self.availability_index = {key: WindowIndex(g,["_any","_sixty","minutes"]) for key,g in p.groupby(["season","fpl_code"], sort=False)}
        allowed = p.groupby(["season","fixture","opponent_name"],as_index=False).agg(
            ts=("ts","first"),dc=("defensive_contribution",lambda a:a.sum(min_count=1)),
            tackles=("tackles",lambda a:a.sum(min_count=1)))
        self.allowed_index = {key: WindowIndex(g,["dc","tackles"]) for key,g in allowed.groupby("opponent_name",sort=False)}

    def transform_at_origins(self, targets, snapshots):
        """Query history at inputs_as_of, not the later actual deadline.

        A snapshot may equal its own observed origin, but must still precede the
        physical FPL deadline. Preserve the legacy strict deadline API below.
        """
        if 'inputs_as_of' not in targets:raise ValueError('Missing information origin')
        t=targets.copy()
        origin=pd.to_datetime(t.inputs_as_of.map(_timestamp),utc=True)
        deadline=pd.to_datetime(t.deadline.map(_timestamp),utc=True)
        if origin.ge(deadline).any():raise ValueError('Origin must precede actual deadline')
        t['deadline']=origin
        return self.transform(t,snapshots,_snapshot_at_origin=True)

    def transform(self, targets, snapshots, *, _snapshot_at_origin=False):
        targets = targets.copy(); snapshots = snapshots.copy()
        required = {"season","gameweek","fixture","fpl_code","position","team_name","opponent_name","home","deadline"}
        if required-set(targets): raise ValueError("Missing target context")
        if not targets.index.is_unique or targets.duplicated(["season","gameweek","fixture","fpl_code"]).any():
            raise ValueError("Ambiguous targets")
        targets["deadline"] = pd.to_datetime(targets.deadline.map(_timestamp),utc=True)
        if targets.groupby(["season","gameweek"]).deadline.nunique().ne(1).any():
            raise ValueError("One shared deadline per GW required")
        if not targets.position.isin([1,2,3,4]).all() or not targets.home.isin([True,False]).all():
            raise ValueError("Invalid target position/venue")
        snapshot_keys = ["season","gameweek","fpl_code"]
        if set([*snapshot_keys,"captured_at",*SNAPSHOT_FEATURES])-set(snapshots): raise ValueError("Missing snapshot schema")
        if snapshots.duplicated(snapshot_keys).any(): raise ValueError("Duplicate snapshot identity")
        if len(snapshots):
            snapshots["captured_at"] = pd.to_datetime(snapshots.captured_at.map(_timestamp),utc=True)
        snap = snapshots.set_index(snapshot_keys)
        self.prepare(targets)
        # Do not retain one286-key Python dict per row or all player/GW query
        # results: those structures dwarf the numeric matrix on local hardware.
        output = np.empty((len(targets),len(FEATURES)),dtype=np.float32)
        evidence = {"snapshot_present":np.zeros(len(targets),dtype=bool),
                    "candidate":np.zeros(len(targets),dtype=bool),
                    "snapshot_at":np.full(len(targets),pd.NaT.value,dtype=np.int64)}
        for family in FAMILIES:
            evidence[family+"_source_count"]=np.zeros(len(targets),dtype=np.int32)
            evidence[family+"_source_max_ts"]=np.full(len(targets),pd.NaT.value,dtype=np.int64)
        for i,r in enumerate(targets.itertuples()):
            cutoff = r.deadline-pd.Timedelta(hours=3)
            source = {}; z = {}
            index = self.player_index.get(r.fpl_code)
            if index is None: raise ValueError("Target player missing from raw histories")
            values,count,latest = index.means(cutoff); source["player"]=(count,latest)
            for w, array in values.items():
                for name,value in zip(self.player_index[r.fpl_code].columns,array):
                    if name in PLAYER_STATS: z[f"player_{PLAYER_STATS[name]}_{w}"]=value
                    elif w in (3,5,10,38) and name in DEFENSIVE: z[f"ar_{name}_{w}"]=value
                    elif w in (3,5,10) and name in ("_hit","_near","starts"):
                        suffix={"_hit":"dc_hit_rate","_near":"dc_near_rate","starts":"starts"}[name]
                        z[f"ar_{suffix}_{w}"]=value
            venue = self.venue_index.get((r.fpl_code,r.home))
            vv = venue.means(cutoff)[0] if venue else {w:[np.nan] for w in WINDOWS}
            for w in WINDOWS: z[f"player_relevant_fpl_points_{w}"]=vv[w][0]
            for family,club,prefix in (("team",r.team_name,"team"),("opponent",r.opponent_name,"opp")):
                if club not in self.team_index: raise ValueError("Unknown team/opponent")
                cache_key=(family,club,cutoff.value)
                if cache_key not in self.cache: self.cache[cache_key]=self.team_index[club].means(cutoff)
                tv,number,last=self.cache[cache_key]; source[family]=(number,last)
                for w,array in tv.items():
                    for name,value in zip(TEAM_STATS,array): z[f"{prefix}_{name}_{w}"]=value
            ranks,number,last=self.leagues[(r.season,cutoff.value)]
            if r.team_name not in ranks or r.opponent_name not in ranks: raise ValueError("Unknown current league club")
            source["league"]=(number,last)
            z.update(is_home_num=float(r.home),status_league_rank=ranks[r.team_name],opp_status_league_rank=ranks[r.opponent_name])
            ai=self.availability_index.get((r.season,r.fpl_code))
            availability=ai.means(cutoff,(3,5,10)) if ai else ({w:[np.nan]*3 for w in (3,5,10)},0,pd.NaT)
            av=availability[0]
            evidence["candidate"][i]=availability[1]>=3 and np.isfinite(av[5][2]) and av[5][2]>=45
            # Explicit cold-start priors, fixed before experiments.
            priors={1:(.50,.48,45.),2:(.55,.42,42.),3:(.52,.38,38.),4:(.50,.35,35.)}[r.position]
            for w,array in av.items():
                for j,prefix in enumerate(("p_any","p60","e_minutes")):
                    z[f"{prefix}_{w}"]=float(array[j]) if np.isfinite(array[j]) else priors[j]
            z["ar_dc_ppg_5"]=2*z["ar_dc_hit_rate_5"]
            z["ar_rest_days"]=float(np.clip((r.deadline-latest).total_seconds()/86400,1,14)) if count else 14.
            ti=self.team_index[r.team_name]
            z["ar_team_matches_14d"]=int(((ti.times>= (r.deadline-pd.Timedelta(days=14)).value)&(ti.times<cutoff.value)).sum())
            allowed=self.allowed_index.get(r.opponent_name)
            av=allowed.means(cutoff,(3,5,10))[0] if allowed else {w:[np.nan,np.nan] for w in (3,5,10)}
            for w,array in av.items(): z[f"ar_opp_dc_allowed_{w}"]=array[0]
            z["ar_opp_tackles_allowed_5"]=av[5][1]
            snapshot_key=(r.season,r.gameweek,r.fpl_code)
            present=snapshot_key in snap.index
            captured=pd.NaT
            if present:
                row=snap.loc[snapshot_key]; captured=row.captured_at
                if (captured>r.deadline if _snapshot_at_origin else captured>=r.deadline) or captured<r.deadline-pd.Timedelta(hours=24):
                    raise ValueError("Late/stale snapshot")
                for name in SNAPSHOT_FEATURES: z[name]=row[name]
            else:
                for name in SNAPSHOT_FEATURES: z[name]=-1.
            if set(z)!=set(FEATURES): raise ValueError("Native feature contract changed")
            output[i]=[z[name] for name in FEATURES]
            evidence["snapshot_present"][i]=present
            evidence["snapshot_at"][i]=captured.value
            for family,(number,last) in source.items():
                if number and (pd.isna(last) or last>=cutoff): raise ValueError("Future history source")
                evidence[family+"_source_count"][i]=number
                evidence[family+"_source_max_ts"][i]=last.value
        evidence=pd.DataFrame(evidence,index=targets.index)
        for name in ["snapshot_at",*[f+"_source_max_ts" for f in FAMILIES]]:
            evidence[name]=pd.to_datetime(evidence[name],utc=True)
        return pd.DataFrame(output,index=targets.index,columns=FEATURES),evidence
