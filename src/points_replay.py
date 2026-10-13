"""Point-relevant fixed-squad historical comparisons with realised autosubs."""
from collections import Counter
from itertools import combinations
import numpy as np
import pandas as pd
from fpl_model import candidate_mask
from forecast import select_xi,legal_squad

def formation(ids,players):
    count=Counter(players[i]['position'] for i in ids)
    return len(ids)==11 and count[1]==1 and count[2]>=3 and count[3]>=2 and count[4]>=1

def realised_points(selection,players,actual,played):
    ids=list(selection['starters']);keeper=[i for i in ids if players[i]['position']==1][0]
    if not played.get(keeper,False):
        substitutes=[i for i in selection['bench'] if players[i]['position']==1 and played.get(i,False)]
        if substitutes:ids[ids.index(keeper)]=substitutes[0]
    missing=[i for i in ids if players[i]['position']!=1 and not played.get(i,False)]
    bench=[i for i in selection['bench'] if players[i]['position']!=1]
    # Lexicographic priority of eligible bench positions, subject to a legal final XI.
    best=(tuple(0 for _ in bench),ids)
    for n in range(1,min(len(missing),len(bench))+1):
        for incoming in combinations(bench,n):
            if not all(played.get(i,False) for i in incoming):continue
            priority=tuple(int(i in incoming) for i in bench)
            for outgoing in combinations(missing,n):
                candidate=[i for i in ids if i not in outgoing]+list(incoming)
                if formation(candidate,players) and priority>best[0]:best=(priority,candidate)
    cap=selection['captain'] if played.get(selection['captain'],False) else selection['vice'] if played.get(selection['vice'],False) else None
    return float(sum(actual.get(i,0) for i in best[1])+(actual.get(cap,0) if cap is not None else 0))

def make_squads(d,x,season,count=20):
    year=d[d.season==season];first=next(gw for gw in sorted(year.GW.unique()) if candidate_mask(x.loc[year[year.GW==gw].index]).any())
    opening=year[year.GW==first];cutoff=opening.cutoff.iloc[0]
    opening=opening[candidate_mask(x.loc[opening.index])].drop_duplicates('element')
    history=year[year.ts<cutoff-pd.Timedelta(hours=3)].sort_values('ts').groupby('element').tail(1).set_index('element')
    candidates=[]
    for r in opening.itertuples():
        if r.element not in history.index:continue
        price=float(history.loc[r.element,'value'])
        if not np.isfinite(price) or price<=0:continue
        candidates.append({'id':int(r.element),'position':int(r.pos),'team':int(r.team_id),'price_tenths':price,'weight':max(float(x.loc[r.Index,'ew4_points_core']),.1)})
    rng=np.random.default_rng(20260921);squads=[];seen=set()
    for attempt in range(10000):
        selected=[]
        for pos,n in [(1,2),(2,5),(3,5),(4,3)]:
            pool=[p for p in candidates if p['position']==pos]
            weights=np.array([p['weight'] for p in pool]);idx=rng.choice(len(pool),size=n,replace=False,p=weights/weights.sum());selected.extend(pool[i] for i in idx)
        key=tuple(sorted(p['id'] for p in selected))
        if key not in seen and legal_squad(selected) and sum(p['price_tenths'] for p in selected)<=1000:
            squads.append(selected);seen.add(key)
            if len(squads)==count:break
    if len(squads)!=count:raise ValueError('Could not construct the predeclared number of squads')
    return squads,int(first)

def compare(d,x,season,incumbent,challenger):
    year=d[d.season==season].copy();assert len(incumbent)==len(year)==len(challenger)
    year['v1']=np.asarray(incumbent);year['candidate']=np.asarray(challenger)
    # Same strictly lagged DC estimate for both methods; no future-trained DC model here.
    dc=np.where((year.pos!=1)&(season>='2025-26'),2*x.loc[year.index,'dc_rate4'].to_numpy(),0.)
    year['v1']+=dc;year['candidate']+=dc
    grouped=year.groupby(['GW','element']).agg({'v1':'sum','candidate':'sum','total_points':'sum','minutes':'sum'})
    squads,first=make_squads(d,x,season);rows=[]
    for sid,squad in enumerate(squads):
        players={p['id']:p for p in squad}
        for gw in range(first,39):
            sub=grouped.loc[gw] if gw in grouped.index.levels[0] else pd.DataFrame()
            actual={i:float(sub.loc[i,'total_points']) if i in sub.index else 0. for i in players}
            played={i:bool(sub.loc[i,'minutes']>0) if i in sub.index else False for i in players}
            row={'season':season,'squad':sid,'GW':gw}
            for model in ['v1','candidate']:
                choices=[{**p,'expected_points':float(sub.loc[p['id'],model]) if p['id'] in sub.index else 0.} for p in squad]
                row[model]=realised_points(select_xi(choices),players,actual,played)
            row['difference']=row['candidate']-row['v1'];rows.append(row)
    return pd.DataFrame(rows),squads
