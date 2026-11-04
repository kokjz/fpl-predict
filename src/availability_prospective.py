"""Frozen availability covariates for a prospective experiment; research only."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from fpl_model import CORE_FEATURES, estimator, sample_weights
from incumbent_availability import SIGNALS, augment, source_observations
from market_stage_c import canonical_hash, array_hash
from benchmark_metrics import evaluate

SEASONS=tuple(f'{y}-{str(y+1)[-2:]}' for y in range(2020,2026))
FEATURES={'control':CORE_FEATURES,'availability':CORE_FEATURES+SIGNALS}
FEATURE_HASHES={k:canonical_hash(v) for k,v in FEATURES.items()}
KEYS=['season','fixture','fpl_code']

def phase1_scope(seasons,operation='historical'):
    if operation not in ('historical','admission','fit','score','freeze'):
        raise ValueError('Phase1 operation refused')
    if not set(seasons)<=set(SEASONS):raise ValueError('Phase1 season refused')

def keyed_block(control,block,names):
    for f in (control,block):
        if f[KEYS].isna().any().any() or f.duplicated(KEYS).any():raise ValueError('Ambiguous keys')
    if not pd.MultiIndex.from_frame(control[KEYS]).equals(pd.MultiIndex.from_frame(block[KEYS])):
        raise ValueError('Block key order or coverage differs')
    z=control[KEYS].merge(block[KEYS+names],on=KEYS,validate='one_to_one',sort=False)
    return pd.DataFrame(z[names].to_numpy(),index=control.index,columns=names)

def augment_control(rows,control,bridge,observations):
    phase1_scope(rows.season,'admission')
    if list(control)!=CORE_FEATURES or not control.index.equals(rows.index):raise ValueError('Control alignment')
    result,coverage=augment(rows,control,bridge,observations)
    if list(result)!=FEATURES['availability']:raise ValueError('Feature order')
    if np.ascontiguousarray(result[CORE_FEATURES].to_numpy(float)).tobytes()!=np.ascontiguousarray(control.to_numpy(float)).tobytes():
        raise ValueError('Control prefix bytes differ')
    if rows.loc[rows.season.eq('2025-26')&rows.GW.le(3)].index.intersection(result.index[result.availability_missing.ne(1)]).size:
        raise ValueError('GW1-3 must be unknown')
    return result,coverage

def census(reports):
    if len(reports)!=35 or {r['gameweek'] for r in reports}!=set(range(4,39)):raise ValueError('Census shape')
    return [dict(gameweek=g,status='no_source',prefix_pass=None,identity_pass=None,chance_known=0) for g in range(1,4)]+[
        dict(r,status='admitted',prefix_pass=True,identity_pass=True) for r in sorted(reports,key=lambda r:r['gameweek'])]

def masks(rows,stage):
    phase1_scope(rows.season,'fit')
    if stage=='B':
        train=rows.season.lt('2025-26')|(rows.season.eq('2025-26')&rows.GW.le(19))
        test=rows.season.eq('2025-26')&rows.GW.between(20,38)
    elif stage=='F':train=pd.Series(True,index=rows.index);test=~train
    else:raise ValueError('Undeclared stage')
    if not train.any():raise ValueError('Empty training set')
    if test.any() and pd.to_datetime(rows.loc[train,'ts'],utc=True).max()>=pd.to_datetime(rows.loc[test,'cutoff'],utc=True).min():
        raise ValueError('Training labels cross test origin')
    return train,test

def fit(rows,features,method,stage):
    phase1_scope(rows.season,'fit')
    if method not in FEATURES or list(features)!=FEATURES[method] or not rows.index.equals(features.index):raise ValueError('Fit feature contract')
    train,test=masks(rows,stage)
    names=[n for n in FEATURES[method] if not features.loc[train,n].isna().all()]
    weights=sample_weights(rows.loc[train])
    model=estimator('hgb7');model.fit(features.loc[train,names],rows.loc[train,'points_core'],sample_weight=weights)
    pred=np.clip(model.predict(features.loc[test,names]),0,20) if test.any() else None
    receipt=dict(train_rows=int(train.sum()),test_rows=int(test.sum()),features=names,feature_sha256=canonical_hash(names),ordered_feature_sha256=FEATURE_HASHES[method],training_row_sha256=canonical_hash(rows.loc[train,KEYS].to_dict('records')),training_feature_sha256=array_hash(features.loc[train].to_numpy(float)),weights_sha256=array_hash(weights),parameters=model.get_params())
    return model,pred,receipt

def gate_b(candidate,control):
    values=[('player_gw_rmse',candidate['candidate_player_gw']['rmse'],control['candidate_player_gw']['rmse'],False),('player_gw_mae',candidate['candidate_player_gw']['mae'],1.005*control['candidate_player_gw']['mae'],False),('ndcg10',candidate['mean_within_gw_ndcg10'],.99*control['mean_within_gw_ndcg10'],True)]
    checks={n:dict(candidate=float(v),threshold=float(t),passed=bool(v>=t if higher else v<=t)) for n,v,t,higher in values}
    return dict(passed=all(v['passed'] for v in checks.values()),criteria=checks)

def phase2_gates(candidate,control,fixed_squad_delta,full_candidate,full_control,block_interval):
    checks={}
    for gate,metric,ratio in [('2','rmse',.995),('3','rmse',1.005),('4','mae',1.005)]:
        checks[gate]=all(candidate[u][metric]<=ratio*control[u][metric] for u in ('player_gw','fixture'))
    checks['6']=bool(fixed_squad_delta>=0)
    checks['7']=bool(full_candidate<=1.005*full_control)
    return dict(passed=all(checks.values()),criteria=checks,gate5=dict(descriptive=True,block_interval=list(block_interval)))

def first_prospective_gameweek(events,pushed_at):
    stamp=pd.Timestamp(pushed_at)
    if stamp.tzinfo is None:raise ValueError('Timezone required')
    eligible=[]
    for e in events:
        deadline=pd.Timestamp(e['deadline_time'])
        if deadline.tzinfo is None:raise ValueError('Timezone required')
        if deadline>stamp:eligible.append((deadline,int(e['id'])))
    if not eligible:raise ValueError('No future deadline')
    deadline,gw=min(eligible)
    return dict(gameweek=gw,deadline=deadline.isoformat(),freeze_push_time=stamp.isoformat())

def score(rows,features,predictions):
    phase1_scope(rows.season,'score')
    _,test=masks(rows,'B');d=rows.loc[test]
    reports={m:evaluate(d,features.loc[test,CORE_FEATURES],predictions[m]) for m in FEATURES}
    return dict(metrics=reports,gate=gate_b(reports['availability'],reports['control']))

def fixed_squad(rows,features,predictions,count=20):
    """Unchanged common selector/autosubs; opening squads fixed at GW20."""
    from forecast import legal_squad,select_xi
    from points_replay import realised_points
    phase1_scope(rows.season,'score')
    year=rows[rows.season.eq('2025-26')];opening=year[year.GW.eq(20)]
    cutoff=opening.cutoff.iloc[0]
    opening=opening.loc[(features.loc[opening.index,'n_history']>=3)&(features.loc[opening.index,'last5_minutes']>=45)].drop_duplicates('element')
    history=year[year.ts<cutoff-pd.Timedelta(hours=3)].sort_values('ts').groupby('element').tail(1).set_index('element')
    pool=[]
    for r in opening.itertuples():
        if r.element not in history.index:continue
        price=float(history.loc[r.element,'value'])
        if not np.isfinite(price) or price<=0:continue
        pool.append(dict(id=int(r.element),position=int(r.pos),team=int(r.team_id),price_tenths=price,weight=max(float(features.loc[r.Index,'ew4_points_core']),.1)))
    rng=np.random.default_rng(20260921);squads=[];seen=set()
    for _ in range(10000):
        selected=[]
        for pos,n in [(1,2),(2,5),(3,5),(4,3)]:
            candidates=[p for p in pool if p['position']==pos]
            weights=np.array([p['weight'] for p in candidates]);ids=rng.choice(len(candidates),size=n,replace=False,p=weights/weights.sum())
            selected.extend(candidates[i] for i in ids)
        key=tuple(sorted(p['id'] for p in selected))
        if key not in seen and legal_squad(selected) and sum(p['price_tenths'] for p in selected)<=1000:
            squads.append(selected);seen.add(key)
            if len(squads)==count:break
    if len(squads)!=count:raise ValueError('Fixed squad count')
    _,test=masks(rows,'B');z=rows.loc[test,['GW','element','minutes','total_points']].copy()
    for m,p in predictions.items():z[m]=p
    grouped=z.groupby(['GW','element']).agg({m:'sum' for m in predictions}|{'minutes':'sum','total_points':'sum'})
    totals={m:[] for m in predictions}
    for squad in squads:
        players={p['id']:p for p in squad};one={m:0. for m in predictions}
        for gw in range(20,39):
            sub=grouped.loc[gw] if gw in grouped.index.get_level_values(0) else pd.DataFrame()
            actual={i:float(sub.loc[i,'total_points']) if i in sub.index else 0. for i in players}
            played={i:bool(sub.loc[i,'minutes']>0) if i in sub.index else False for i in players}
            for m in predictions:
                choices=[dict(p,expected_points=float(sub.loc[p['id'],m]) if p['id'] in sub.index else 0.) for p in squad]
                one[m]+=realised_points(select_xi(choices),players,actual,played)
        for m in predictions:totals[m].append(one[m])
    delta=np.array(totals['availability'])-totals['control']
    return dict(totals=totals,mean_delta=float(delta.mean()),minimum_delta=float(delta.min()),maximum_delta=float(delta.max()),squad_sha256=canonical_hash(squads),count=count,first_gw=20,descriptive=True)
