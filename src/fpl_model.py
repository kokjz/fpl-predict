"""Time-safe, identity-free FPL features and pooled supervised forecasting.

Only this module constructs model features, for both training and live inference.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

POSITIONS = {"GK":1,"GKP":1,"DEF":2,"MID":3,"FWD":4}
STATS = ["minutes","points_core","goals_scored","assists","clean_sheets","bonus","bps","threat","creativity","saves","expected_goals","expected_assists","expected_goals_conceded","played","sixty"]
PRIORS = dict(zip(STATS,[30,1.6,.07,.05,.18,.2,7,8,5,.2,.09,.06,.6,.5,.3]))
CORE_FEATURES = ["home","n_history","days_since_last","last_minutes","last_points","last5_minutes","last5_points"] + [f"pos_{p}" for p in range(1,5)] + [f"ew{h}_{s}" for h in (4,12) for s in STATS] + [f"{side}_ew{h}_{s}" for side in ("team","opp") for h in (4,12) for s in ("gf","ga")]
DC_FEATURES = [f for f in CORE_FEATURES if "points" not in f]+["dc_rate4","dc_rate12","dc_actions4","dc_records"]

def normalise(df):
    d=df.copy()
    if "pos" not in d: d["pos"]=d.position.map(POSITIONS)
    d=d[d.pos.isin([1,2,3,4])].copy()
    d["ts"]=pd.to_datetime(d.kickoff_time,utc=True)
    d["played"]=(d.minutes>0).astype(float)
    d["sixty"]=(d.minutes>=60).astype(float)
    if "defensive_contribution" not in d: d["defensive_contribution"]=np.nan
    d["dc_hit"]=np.where(d.defensive_contribution.isna(),np.nan,np.where(d.pos==1,0,(d.defensive_contribution>=np.where(d.pos==2,10,12)).astype(float)))
    d["points_core"]=d.total_points-2*d.dc_hit.fillna(0)
    for col in STATS:
        if col not in d: d[col]=np.nan
        d[col]=pd.to_numeric(d[col],errors="coerce")
    if "team_gf" not in d:
        d["team_gf"]=np.where(d.was_home,d.team_h_score,d.team_a_score)
        d["team_ga"]=np.where(d.was_home,d.team_a_score,d.team_h_score)
    if "cutoff" not in d:
        d["cutoff"]=d.groupby(["season","GW"]).ts.transform("min")-pd.Timedelta(minutes=90)
    else: d["cutoff"]=pd.to_datetime(d.cutoff,utc=True)
    return d.sort_values(["ts","element","fixture"]).reset_index(drop=True)

def load_history(root):
    frames=[];audit=[]
    for path in sorted(Path(root).glob("*/gws/merged_gw.csv")):
        raw=pd.read_csv(path);d=raw.drop_duplicates().copy()
        d=d[d.position.isin(POSITIONS)]
        assert not d.duplicated(["element","fixture"]).any(),f"Conflicting duplicates: {path}"
        teams=pd.read_csv(path.parents[1]/"teams.csv")
        d["team_id"]=d.team.map(dict(zip(teams.name,teams.id)))
        assert d.team_id.notna().all()
        d["season"]=path.parts[-3]
        audit.append({"season":d.season.iloc[0],"raw_rows":len(raw),"exact_duplicates_removed":int(raw.duplicated().sum()),"retained_player_rows":len(d),"fixtures":int(d.fixture.nunique()),"gameweeks":int(d.GW.nunique())})
        frames.append(d)
    return normalise(pd.concat(frames,ignore_index=True)),audit

def ew(values,half,prior,prior_mass=2.):
    a=np.asarray(values,dtype=float)
    w=2.**(-np.arange(len(a)-1,-1,-1)/half)
    keep=np.isfinite(a)
    return float((np.dot(a[keep],w[keep])+prior*prior_mass)/(w[keep].sum()+prior_mass))

class FeatureStore:
    def __init__(self,history):
        self.players={k:g.sort_values("ts") for k,g in history.groupby(["season","element"],sort=False)}
        team=history.drop_duplicates(["season","team_id","fixture"])
        self.teams={k:g.sort_values("ts") for k,g in team.groupby(["season","team_id"],sort=False)}
        self.cache={}

    def player(self,season,element,cutoff):
        key=(season,element,cutoff.value)
        if key in self.cache: return self.cache[key]
        g=self.players.get((season,element))
        # Conservative 3h completion buffer. Same-GW matches always lie after its cutoff.
        h=g[g.ts < cutoff-pd.Timedelta(hours=3)] if g is not None else pd.DataFrame()
        n=len(h)
        z={"n_history":min(n,38),"days_since_last":min((cutoff-h.ts.iloc[-1]).total_seconds()/86400,180) if n else 60.,"last_minutes":float(h.minutes.iloc[-1]) if n else 30.,"last_points":float(h.points_core.iloc[-1]) if n else 1.6,"last5_minutes":float(h.minutes.tail(5).mean()) if n else 30.,"last5_points":float(h.points_core.tail(5).mean()) if n else 1.6}
        for half in (4,12):
            for stat in STATS:
                z[f"ew{half}_{stat}"]=ew(h[stat] if n else [],half,PRIORS[stat])
        dh=h[h.dc_hit.notna()] if n else pd.DataFrame()
        z["dc_records"]=len(dh)
        z["dc_rate4"]=ew(dh.dc_hit if len(dh) else [],4,.12,3.)
        z["dc_rate12"]=ew(dh.dc_hit if len(dh) else [],12,.12,3.)
        z["dc_actions4"]=ew(dh.defensive_contribution if len(dh) else [],4,3.,3.)
        z["source_max_ts"]=h.ts.max() if n else pd.NaT
        self.cache[key]=z
        return z

    def team(self,season,team,cutoff):
        key=("team",season,team,cutoff.value)
        if key in self.cache: return self.cache[key]
        g=self.teams.get((season,team))
        h=g[g.ts < cutoff-pd.Timedelta(hours=3)] if g is not None else pd.DataFrame()
        z={f"ew{half}_{s}":ew(h[f"team_{s}"] if len(h) else [],half,1.35,4.) for half in (4,12) for s in ("gf","ga")}
        z["source_max_ts"]=h.ts.max() if len(h) else pd.NaT
        self.cache[key]=z
        return z

    def transform(self,targets):
        output=[]
        for r in targets.itertuples():
            z=dict(self.player(r.season,r.element,r.cutoff))
            sources=[z.pop("source_max_ts")]
            z["home"]=float(r.was_home)
            for p in range(1,5): z[f"pos_{p}"]=float(r.pos==p)
            for side,ident in [("team",r.team_id),("opp",r.opponent_team)]:
                t=self.team(r.season,ident,r.cutoff)
                sources.append(t["source_max_ts"])
                z.update({f"{side}_{k}":v for k,v in t.items() if k!="source_max_ts"})
            z["source_max_ts"]=max((x for x in sources if not pd.isna(x)),default=pd.NaT)
            output.append(z)
        return pd.DataFrame(output,index=targets.index)

def sample_weights(rows):
    age=(rows.ts.max()-rows.ts).dt.total_seconds()/86400
    return np.power(.5,age.to_numpy()/730.5)

def estimator(name):
    if name=="ridge": return make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=100.))
    specs={"hgb7":(7,200,20.),"hgb15":(15,180,30.),"hgb31":(31,150,50.)}
    leaves,iters,l2=specs[name]
    return HistGradientBoostingRegressor(max_leaf_nodes=leaves,max_iter=iters,learning_rate=.05,l2_regularization=l2,min_samples_leaf=60,early_stopping=False,random_state=20260921)

def fit_estimator(name,x,y,weights):
    m=estimator(name)
    if name=="ridge": m.fit(x,y,ridge__sample_weight=weights)
    else: m.fit(x,y,sample_weight=weights)
    return m

@dataclass
class ForecastModel:
    core: object
    core_name: str
    blend: float
    minutes: object
    played: object
    sixty: object
    dc: object
    dc_name: str
    residual_intervals: dict
    metadata: dict

    def predict(self,x,pos):
        raw=np.clip(self.core.predict(x[CORE_FEATURES]),0,20)
        core=self.blend*raw+(1-self.blend)*x.ew4_points_core.to_numpy()
        mins=np.clip(self.minutes.predict(x[CORE_FEATURES]),0,90)
        play=np.clip(self.played.predict(x[CORE_FEATURES]),0,1)
        sixty=np.minimum(play,np.clip(self.sixty.predict(x[CORE_FEATURES]),0,1))
        if self.dc_name=="ewm": dc=x.dc_rate4.to_numpy().copy()
        else: dc=np.clip(self.dc.predict(x[DC_FEATURES]),0,1)
        dc=np.where(np.asarray(pos)==1,0,np.minimum(dc,play))
        return pd.DataFrame({"core_xp":core,"dc_xp":2*dc,"expected_points":core+2*dc,"expected_minutes":mins,"p_play":play,"p60":sixty},index=x.index)

def metrics(y,p):
    e=np.asarray(p)-np.asarray(y)
    return {"n":len(e),"rmse":float(np.sqrt(np.mean(e*e))),"mae":float(np.mean(np.abs(e))),"bias":float(e.mean())}

def candidate_mask(x):
    return (x.n_history>=3)&(x.last5_minutes>=45)
