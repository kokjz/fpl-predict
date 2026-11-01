"""Frozen single-fold rich/market confirmation; no operational promotion."""
import csv
from datetime import datetime, timedelta
import io
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from fpl_model import CORE_FEATURES, candidate_mask, estimator, sample_weights
from benchmark_metrics import evaluate, point_scores
from benchmark_evaluation import paired_block_errors
import rich_market_combination as base
from market_strength import NAME_MAP, market_probabilities, solve_lambdas, fit_ratings, project, timestamp
from market_stage_b import identity, source_clock
from market_stage_c import array_hash, canonical_hash

SEASONS=(*base.SEASONS,'2024-25')
FOLD='2024-25'
# Exact FPL/football-data spelling equivalence only; no fuzzy matching.
NAME_EQUIVALENCES={'Ipswich':'Ipswich'}


def scope(frame):
    return frame.loc[frame.season.isin(SEASONS)].copy()


def read_scoped(path):
    """Filter by season before dtype parsing or feature construction."""
    with Path(path).open(newline='',encoding='utf-8-sig') as f:
        reader=csv.reader(f);header=next(reader);si=header.index('season')
        buffer=io.StringIO();writer=csv.writer(buffer);writer.writerow(header)
        for row in reader:
            if len(row)!=len(header):raise ValueError('Malformed frozen CSV')
            if row[si] in SEASONS:writer.writerow(row)
    buffer.seek(0);return pd.read_csv(buffer)


def select_control(history,features,bridges,directory=None):
    """Same trusted I4 export path, selecting allowed indices before any use."""
    d=scope(history);x=features.loc[d.index].copy()
    if not d.index.equals(x.index):raise ValueError('Cache alignment')
    for season in SEASONS:
        bridge=bridges[season][['id','code']]
        if bridge.id.duplicated().any() or bridge.code.duplicated().any():raise ValueError('Ambiguous stable-code bridge')
        d.loc[d.season.eq(season),'fpl_code']=d.loc[d.season.eq(season),'element'].map(bridge.set_index('id').code)
    if d.fpl_code.isna().any():raise ValueError('Missing stable code')
    d['fpl_code']=d.fpl_code.astype(np.int64)
    meta=['season','GW','element','fixture','pos','team_id','value','ts','cutoff','total_points','points_core','minutes','fpl_code']
    out=pd.concat([d[meta],x[CORE_FEATURES+['source_max_ts']]],axis=1)
    # Original I4 exporter SHA2566438a587dd2fc580ec84aca538fc1a8bfe334d48aed776120c089e962ac34736.
    # No float_format/dtype/precision override: reproduce its complete boundary.
    with tempfile.TemporaryDirectory(prefix='rmc-control-export-',dir=directory) as temporary:
        target=Path(temporary)/'control.csv'
        out.to_csv(target,index=False,mode='x')
        return pd.read_csv(target).rename(columns={'GW':'gameweek'})


def validate_inputs(p,t,c):
    p=scope(p).reset_index(drop=True);t=scope(t).reset_index(drop=True);c=scope(c)
    if set(p.season)!=set(SEASONS) or set(t.season)!=set(SEASONS) or set(c.season)!=set(SEASONS):raise ValueError('Missing confirmation seasons')
    for frame in (p,c):
        if frame[base.i4.KEYS].isna().any().any() or frame.duplicated(base.i4.KEYS).any():raise ValueError('Ambiguous confirmation keys')
    index=pd.MultiIndex.from_frame(p[base.i4.KEYS]);indexed=c.set_index(base.i4.KEYS)
    if len(indexed)!=len(index) or set(indexed.index)!=set(index):raise ValueError('Control coverage differs')
    c=indexed.reindex(index).reset_index()
    for frame,names in [(p,['ts','deadline']),(t,['ts']),(c,['ts','cutoff','source_max_ts'])]:
        for name in names:
            frame.loc[frame[name].notna(),name].map(base.i4._timestamp)
            frame[name]=pd.to_datetime(frame[name],utc=True)
    if not (p.total_points.eq(c.points_core).all() and p.total_points.eq(c.total_points).all() and p.minutes.eq(c.minutes).all() and p.position.eq(c.pos).all() and p.ts.eq(c.ts).all() and p.deadline.eq(c.cutoff).all()):raise ValueError('Control targets/context differ, including confirmation points_core')
    if not np.isfinite(c[[*CORE_FEATURES,'points_core','minutes']].to_numpy(float)).all():raise ValueError('Nonfinite control')
    if (c.source_max_ts.notna() & c.source_max_ts.ge(c.cutoff-pd.Timedelta(hours=3))).any():raise ValueError('Future control source')
    if (c.source_max_ts.isna() & c.n_history.gt(0)).any():raise ValueError('Missing control source')
    us=['us_shots','us_xG','us_xGChain','us_xGBuildup','us_key_passes','us_xA']
    if (p.minutes.gt(0)&p.understat_id.notna()&p[us].isna().any(axis=1)).any():raise ValueError('Mapped source gap')
    base.NativeHistory(p,t)
    if set(p.loc[p.season.eq(FOLD),'gameweek'])!=set(range(1,39)):raise ValueError('Incomplete confirmation gameweeks')
    if p.loc[p.season.lt(FOLD),'ts'].max()+pd.Timedelta(hours=3)>=p.loc[p.season.eq(FOLD),'deadline'].min():raise ValueError('Training labels cross fold')
    if p.deadline.ge(p.ts).any():raise ValueError('Invalid deadline')
    return p,t,c


def admit_market(rows,players):
    p=players.loc[players.season.eq(FOLD)]
    if len(rows)!=380:raise ValueError('Expected380 market rows')
    names=dict(NAME_MAP,**NAME_EQUIVALENCES);fixtures={}
    for r in p.itertuples():
        if not isinstance(r.home,(bool,np.bool_)):raise ValueError('Invalid venue')
        home,away=(r.team_name,r.opponent_name) if r.home else (r.opponent_name,r.team_name)
        key=(timestamp(r.ts).date().isoformat(),home,away);value=(int(r.fixture),timestamp(r.ts).isoformat())
        if key in fixtures and fixtures[key]!=value:raise ValueError('Ambiguous FPL fixture context')
        fixtures[key]=value
    if len(fixtures)!=380:raise ValueError('Expected380 FPL fixtures')
    matched=set();out=[];counts={}
    for i,row in enumerate(rows,1):
        if row['HomeTeam'] not in names or row['AwayTeam'] not in names:raise ValueError('Unmapped exact team name')
        home,away=names[row['HomeTeam']],names[row['AwayTeam']]
        date=datetime.strptime(row['Date'],'%d/%m/%Y').date().isoformat();key=(date,home,away)
        if key not in fixtures:raise ValueError('No exact FPL date/team match')
        fixture,kickoff=fixtures[key]
        if fixture in matched:raise ValueError('Duplicate market fixture')
        matched.add(fixture);probs,columns=market_probabilities(row);fit=solve_lambdas(probs)
        for name,group in columns.items():
            label=name+':'+','.join(group);counts[label]=counts.get(label,0)+1
        clock=datetime.strptime(row['Date']+' '+row['Time'],'%d/%m/%Y %H:%M').replace(tzinfo=ZoneInfo('Europe/London')).isoformat()
        out.append(dict(season=FOLD,source_row=i,fixture=fixture,home=home,away=away,csv_kickoff=clock,canonical_kickoff=kickoff,probability_target=probs.tolist(),columns_used=columns,**fit))
    if len(matched)!=380:raise ValueError('Incomplete380/380 match')
    return out,dict(rows=380,fpl_available=380,fpl_matched=380,complete_odds=380,exceptions=0,name_equivalences=NAME_EQUIVALENCES,name_map=names,selected_columns=counts)


def market_rows(players,lambdas):
    """Same market_stage_c path, extended only to the declared confirmation season."""
    markets=[];targets={};seen=set();known=set(NAME_MAP.values())|set(NAME_EQUIVALENCES.values())
    for raw in lambdas:
        if raw['season'] not in ('2019-20',*SEASONS):raise ValueError('Excluded market season')
        r=dict(raw,date=raw['csv_kickoff'][:10],fpl_kickoff=raw['canonical_kickoff']);key=identity(r)
        if r['home'] not in known or r['away'] not in known or r['home']==r['away']:raise ValueError('Unknown/noncanonical club')
        if key in seen:raise ValueError('Duplicate market identity')
        seen.add(key);markets.append(dict(season=r['season'],fixture=r['fixture'],identity=key,kickoff=source_clock(r),home=r['home'],away=r['away'],lambda_home=r['lambda_home'],lambda_away=r['lambda_away']))
        if r['season']!='2019-20':targets[(r['season'],int(r['fixture']))]=r
    markets.sort(key=lambda r:(r['kickoff'],r['identity']));ratings={};projections={};values=[];evidence=[]
    for r in players.itertuples():
        if r.season not in SEASONS:raise ValueError('Excluded player target')
        target=targets[(r.season,int(r.fixture))]
        if not isinstance(r.home,(bool,np.bool_)):raise ValueError('Invalid venue')
        home=bool(r.home)
        if (r.team_name,r.opponent_name)!=((target['home'],target['away']) if home else (target['away'],target['home'])):raise ValueError('Player fixture/club/venue mismatch')
        if timestamp(r.ts)!=timestamp(target['fpl_kickoff']):raise ValueError('Player fixture clock mismatch')
        cutoff=timestamp(r.deadline)-timedelta(hours=3);key=(r.season,'fpl',int(r.fixture))
        if timestamp(r.ts)<=cutoff:raise ValueError('Invalid origin')
        if cutoff not in ratings:
            eligible=[m for m in markets if m['kickoff']<cutoff]
            ratings[cutoff]=(fit_ratings(eligible,cutoff),{m['identity'] for m in eligible})
        rating,used=ratings[cutoff]
        if key in used:raise ValueError('Target odds entered history')
        cache=(cutoff,r.team_name,r.opponent_name,home)
        if cache not in projections:projections[cache]=project(rating,r.team_name,r.opponent_name,home)
        z=projections[cache];values.append([z[n] for n in base.MARKET_FEATURES])
        evidence.append(dict(season=r.season,fixture=int(r.fixture),team=r.team_name,cutoff=cutoff.isoformat(),source_max=rating.source_max.isoformat(),cold_start_team=z['cold_start_team'],cold_start_opponent=z['cold_start_opponent']))
    result=np.asarray(values,dtype=np.float64)
    if result.shape!=(len(players),3) or not np.isfinite(result).all():raise ValueError('Nonfinite/incomplete market features')
    return result,evidence,len(ratings)


def shared_proof(a):
    n=len(a['y']);x=a['X_control'];z=a['X_combined'];width=len(CORE_FEATURES)
    if x.shape!=(n,width) or z.shape!=(n,len(base.COMBINED)):raise ValueError('Feature shape differs')
    if x.tobytes()!=np.ascontiguousarray(z[:,:width]).tobytes():raise ValueError('Control bytes differ')
    if not np.isfinite(x).all() or np.isinf(z).any() or not np.isfinite(z[:,-3:]).all():raise ValueError('Nonfinite feature contract')
    if set(a['season'])!=set(SEASONS):raise ValueError('Excluded/missing cohort season')
    keys=list(zip(*(a[k].tolist() for k in base.i4.KEYS)))
    if len(set(keys))!=n:raise ValueError('Duplicate cohort keys')
    for k in ['y','minutes','cutoff_ns','ts_ns']:
        if len(a[k])!=n or not np.isfinite(a[k]).all():raise ValueError('Shared targets/clocks differ')
    train,test=base.fold_masks(a['season'],FOLD,confirmation=True)
    if not test.any() or a['ts_ns'][train].max()>=a['cutoff_ns'][test].min() or not (a['cutoff_ns']<a['ts_ns']).all():raise ValueError('Invalid origin')
    if not np.array_equal(a['candidate'],(x[:,CORE_FEATURES.index('n_history')]>=3)&(x[:,CORE_FEATURES.index('last5_minutes')]>=45)):raise ValueError('Candidate differs')
    frame=pd.DataFrame({k:a[k] for k in ['season','gameweek','fpl_code','candidate','cutoff_ns']})
    if (frame.groupby(['season','gameweek','fpl_code'])[['candidate','cutoff_ns']].nunique()!=1).any().any():raise ValueError('DGW cohort differs')
    weights=sample_weights(pd.DataFrame({'ts':pd.to_datetime(a['ts_ns'][train],utc=True)}))
    if weights.tobytes()!=a['weights'].tobytes():raise ValueError('Age weights differ')
    hashes={k:array_hash(v) for k,v in sorted(a.items())}
    return dict(rows=n,core_bytes_identical=True,shared_keys_cohort_cutoffs_weights_evaluation_targets=True,hashes=hashes,proof_sha256=canonical_hash(hashes))


def fit_predict(a,method):
    if method not in base.METHODS:raise ValueError('Undeclared method')
    shared_proof(a);train,test=base.fold_masks(a['season'],FOLD,confirmation=True)
    frame=pd.DataFrame(a['X_'+method],columns=base.FEATURES[method]);cols=base.selected_columns(frame,train,method)
    model=estimator('hgb7');model.fit(frame.loc[train,cols],a['y'][train],sample_weight=a['weights'])
    prediction=np.clip(model.predict(frame.loc[test,cols]),0,20)
    if not np.isfinite(prediction).all():raise ValueError('Nonfinite prediction')
    return prediction,dict(train_rows=int(train.sum()),test_rows=int(test.sum()),selected_feature_count=len(cols),selected_features=cols,omitted_features=[n for n in base.FEATURES[method] if n not in cols],parameters=model.get_params())


def gate(candidate,control,delta):
    rules={}
    for unit in ['player_gw','fixture']:
        for metric,ratio in [('rmse',.995),('mae',1.005)]:
            value=candidate[unit][metric];threshold=ratio*control[unit][metric]
            rules[unit+'_'+metric]=dict(candidate=value,threshold=threshold,passed=bool(value<=threshold))
    rules['ndcg10']=dict(candidate=candidate['ndcg10'],control=control['ndcg10'],passed=bool(candidate['ndcg10']>=control['ndcg10']))
    rules['mean_fixed_squad_delta']=dict(delta=delta,passed=bool(delta>=0))
    return dict(passed=all(x['passed'] for x in rules.values()),criteria=rules)


def analyse(a,predictions,panel):
    shared_proof(a);test=a['season']==FOLD
    z=pd.DataFrame({k:a[k][test] for k in ['season','gameweek','fixture','fpl_code','minutes','candidate','element','pos','n_history']});z['actual']=a['y'][test]
    z['last5_minutes']=a['X_control'][test,CORE_FEATURES.index('last5_minutes')];result=dict(folds={FOLD:{}},metrics={},points={},relative_percent={})
    for method in base.METHODS:
        z[method]=predictions[method];d=z.rename(columns={'gameweek':'GW','actual':'points_core'})
        result['folds'][FOLD][method]=evaluate(d,d,z[method].to_numpy())
    totals={m:[] for m in base.METHODS}
    for squad in panel['squads']:
        one=base.i4.replay(z,dict(first_gw=panel['first_gw'],squads=[squad]),base.METHODS)
        for m in base.METHODS:totals[m].append(one[m]['mean_total'])
    g=z.groupby(['season','gameweek','fpl_code']).agg({**{m:'sum' for m in base.METHODS},'actual':'sum','candidate':'first'}).reset_index()
    for m in base.METHODS:
        delta=np.asarray(totals[m])-totals['control']
        result['points'][m]=dict(totals=totals[m],deltas=delta.tolist(),mean_total=float(np.mean(totals[m])),mean_delta=float(delta.mean()),minimum_delta=float(delta.min()),maximum_delta=float(delta.max()))
        result['metrics'][m]=dict(player_gw=point_scores(g[g.candidate],m),fixture=point_scores(z[z.candidate],m),all_player_gw=point_scores(g,m),all_fixture=point_scores(z,m),ndcg10=point_scores(g[g.candidate],m)['mean_within_gw_ndcg10'],position_candidate_fixture={str(pos):point_scores(z[z.candidate&z.pos.eq(pos)],m) for pos in (1,2,3,4)},actual_minutes_diagnostics={f'{lo}_{hi}':point_scores(z[z.minutes.between(lo,hi)],m) for lo,hi in [(0,0),(1,59),(60,90)]},cold_start=point_scores(z[z.n_history.lt(3)],m))
    result['gate']=gate(result['metrics']['combined'],result['metrics']['control'],result['points']['combined']['mean_delta'])
    for unit in ['player_gw','fixture','all_player_gw','all_fixture']:
        result['relative_percent'][unit]={metric:100*(result['metrics']['combined'][unit][metric]/result['metrics']['control'][unit][metric]-1) for metric in ['rmse','mae']}
    for label,c,v in [('ndcg10',result['metrics']['control']['ndcg10'],result['metrics']['combined']['ndcg10']),('fixed_squad_points',result['points']['control']['mean_total'],result['points']['combined']['mean_total'])]:result['relative_percent'][label]=100*(v/c-1) if c else None
    result['paired']=dict(combined=paired_block_errors(g[g.candidate],'combined','control'))
    return result,z
