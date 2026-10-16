"""Same-origin fixture targets and full-season forecast adaptation contracts."""
import numpy as np
import pandas as pd
from availability_evidence import utc
from horizon_forecast import Horizon


def origin_features(history,targets,snapshots):
    x,evidence=history.transform_at_origins(targets,snapshots)
    # These fields describe the next GW, not every later target in the horizon.
    future=targets.target_gameweek.ne(targets.gameweek)
    x.loc[future,['ar_ep_next','sig_chance_playing','sig_status_risk','sig_has_news']]=-1.
    return x,evidence


def fixture_targets(market,bootstrap,fixtures,through):
    if not market.gameweek<=through<=min(38,market.gameweek+7):raise ValueError('Invalid target horizon')
    if {'id','event','team_h','team_a','kickoff_time'}-set(fixtures) or fixtures.id.duplicated().any():raise ValueError('Invalid calendar')
    roster={r['id']:r for r in bootstrap['elements']};clubs={r['id']:r['name'] for r in bootstrap['teams']}
    if len(roster)!=len(bootstrap['elements']) or len(clubs)!=len(bootstrap['teams']):raise ValueError('Duplicate snapshot identity')
    records=[];codes=[]
    for p in market.players:
        if p['id'] not in roster:raise ValueError('Market missing from snapshot')
        r=roster[p['id']];club=int(p['team'])
        if r['element_type']!=p['position'] or r['team']!=club or r['now_cost']!=p['price_tenths']:raise ValueError('Snapshot/market differs')
        codes.append(r['code'])
        for f in fixtures.itertuples():
            if pd.isna(f.event) or not market.gameweek<=f.event<=through or club not in (f.team_h,f.team_a):continue
            home=club==f.team_h;opp=int(f.team_a if home else f.team_h)
            records.append(dict(season=market.season,gameweek=market.gameweek,target_gameweek=int(f.event),fixture=int(f.id),
                fpl_code=int(r['code']),element=p['id'],position=p['position'],team_name=clubs[club],opponent_name=clubs[opp],home=home,
                deadline=market.deadline,inputs_as_of=market.as_of,pos=p['position'],team_id=club,opponent_team=opp,was_home=home,
                cutoff=utc(market.as_of),GW=int(f.event),kickoff_time=f.kickoff_time))
    if len(codes)!=len(set(codes)):raise ValueError('Ambiguous stable code')
    q=pd.DataFrame(records)
    if q.empty:raise ValueError('No admitted fixtures; handle all-player blank explicitly')
    return q


def scoring_core(players):
    """Remove only identifiable DC awards; preserve other scoring limitations."""
    p=players.copy();threshold=np.where(p.position.eq(2),10,12)
    awards=np.where(p.defensive_contribution.isna(),0.,np.where(p.position.eq(1),0.,p.defensive_contribution.ge(threshold).astype(float)))
    p['total_points']=p.total_points-2*awards
    return p


def aggregate(market,targets,core,dc,*,through,trained_through,model_id,source_hashes):
    if len(core)!=len(targets) or len(dc)!=len(targets) or not np.isfinite(core).all() or not np.isfinite(dc).all():raise ValueError('Incomplete forecast rows')
    if targets.duplicated(['season','gameweek','fixture','fpl_code']).any():raise ValueError('Duplicate fixture targets')
    if not targets.season.eq(market.season).all() or not targets.gameweek.eq(market.gameweek).all() or not pd.to_datetime(targets.inputs_as_of,utc=True).eq(utc(market.as_of)).all():raise ValueError('Target origin differs')
    if not targets.target_gameweek.between(market.gameweek,through).all():raise ValueError('Target beyond horizon')
    xp={(g,p['id']):0. for g in range(market.gameweek,through+1) for p in market.players}
    for r,value in zip(targets.itertuples(),np.asarray(core)+np.asarray(dc)):
        key=(int(r.target_gameweek),int(r.element))
        if key not in xp:raise ValueError('Unlisted target')
        xp[key]+=float(value)
    return Horizon.create(market,[dict(gameweek=g,id=i,expected_points=v) for (g,i),v in xp.items()],trained_through=trained_through,
        feature_cutoff=market.as_of,source_as_of=market.as_of,model_id=model_id,source_hashes=source_hashes)


def fit_reference(method,training,validation,xt,xv,query,xq,progress):
    """Fixed prior-only learners; output core points, add common DC separately.

    Matrices use the existing native feature contract. XGBoost remains optional
    and lazily loaded; no saved released weights are backcast. This is a named
    reconstruction/adaptation, not an original system reproduction.
    """
    from threadpoolctl import threadpool_limits
    allowed={'2020-21','2021-22','2022-23','2023-24'}
    if set(training.season)!=allowed or not validation.season.eq('2024-25').all() or not query.season.eq('2025-26').all():raise ValueError('Unexpected chronological split')
    if {'total_points','actual','minutes'}&set(query):raise ValueError('Outcome fields in forecast query')
    if pd.to_datetime(training.ts,utc=True).max()+pd.Timedelta(hours=3)>=pd.to_datetime(validation.deadline,utc=True).min():raise ValueError('Training labels reach validation')
    if pd.to_datetime(validation.ts,utc=True).max()+pd.Timedelta(hours=3)>=pd.to_datetime(query.inputs_as_of,utc=True).min():raise ValueError('Validation labels reach prediction')
    if not training.index.equals(xt.index) or not validation.index.equals(xv.index) or not query.index.equals(xq.index):raise ValueError('Feature alignment differs')
    prediction=np.full(len(query),np.nan)
    with threadpool_limits(limits=2):
        if method=='native_hgb':
            from sklearn.ensemble import HistGradientBoostingRegressor
            from native_reference import POLICY
            a,b=xt.copy(),xq.copy()
            for pos in range(1,5):
                a[f'position_{pos}']=training.position.eq(pos).astype(float);b[f'position_{pos}']=query.position.eq(pos).astype(float)
            # Some supported numerical versions cannot bin all-NaN columns.
            # They contain no training information; do not use future query
            # values to decide retention or invent observations to fill them.
            retained=a.columns[a.notna().any(axis=0)]
            progress(dict(method=method,training_features=len(retained),dropped_all_training_missing=sorted(set(a)-set(retained))))
            a,b=a.loc[:,retained],b.loc[:,retained]
            weights=np.power(.5,(pd.to_datetime(training.ts,utc=True).max()-pd.to_datetime(training.ts,utc=True)).dt.total_seconds().to_numpy()/86400/730.5)
            model=HistGradientBoostingRegressor(**POLICY['parameters']);model.fit(a,training.total_points,sample_weight=weights)
            prediction=np.clip(model.predict(b),0,22)
        elif method in ('dastan_adaptation','openfpl_cv1_adaptation'):
            from conditional_reference import environment,fit_position,check_populations
            from historical_references import fit_openfpl,openfpl_matrix,recipe
            from native_history import FEATURES
            environment() #Explicit pinned optional runtime, before training.
            if method=='dastan_adaptation':
                both=pd.concat([training,validation])
                check_populations(both,dict(train=both.season.isin(allowed),validation=both.season.eq('2024-25')))
            for pos in range(1,5):
                t=training.position.eq(pos);v=validation.position.eq(pos);q=query.position.eq(pos)
                if not t.any() or not v.any() or not q.any():raise ValueError('Missing position population')
                if method=='dastan_adaptation':
                    values,meta=fit_position(training[t],validation[v],xt.loc[t,FEATURES].fillna(0).to_numpy(np.float32),xv.loc[v,FEATURES].fillna(0).to_numpy(np.float32),xq.loc[q,FEATURES].fillna(0).to_numpy(np.float32),lambda r:progress(dict(position=pos,**r)))
                    progress(dict(position=pos,calibration=meta))
                else:
                    names=recipe()['feature_schema'][str(pos)]
                    values=fit_openfpl(training[t],validation[v],openfpl_matrix(xt.loc[t],names),openfpl_matrix(xv.loc[v],names),openfpl_matrix(xq.loc[q],names),pos,progress)
                prediction[q.to_numpy()]=values
        else:raise ValueError('Unknown reference learner')
    if not np.isfinite(prediction).all():raise ValueError('Incomplete native forecast coverage')
    return prediction
