"""Fixed mits-r2 team-goal experiment; no player fit or registry writes.

Target labels and identifiers are kept outside predictor columns. Past matches
from a held-out season may enter a later origin's histories; that season never
fits the fold's learner or scaler. Every source must strictly precede its origin.
"""
from collections import Counter
from datetime import timedelta
import math

import numpy as np
from scipy.special import xlogy
from sklearn.metrics import mean_poisson_deviance

from fpl_model import ew
from market_strength import NAME_MAP, fit_ratings, project, timestamp

SEASONS=('2020-21','2021-22','2022-23','2023-24')
FOLDS=('2022-23','2023-24')
ARMS=('C','U','M')
C_FEATURES=['home']+[f'{side}_ew{half}_{stat}' for side in ('team','opp') for half in (4,12) for stat in ('gf','ga')]
FEATURES={'C':C_FEATURES,'U':C_FEATURES+[f'{side}_ew{half}_{stat}' for side in ('team','opp') for half in (4,12) for stat in ('xgf','xga')],
          'M':C_FEATURES+['log_mkt_lambda_for','log_mkt_lambda_against']}


def source_clock(row):
    csv=timestamp(row['csv_kickoff'])
    return csv if row['season']=='2019-20' else max(csv,timestamp(row['fpl_kickoff']))


def identity(row):
    if row['season']=='2019-20':
        return ('2019-20','fd',row['date'],row['home'],row['away'])
    return (row['season'],'fpl',int(row['fixture']))


def check_clubs(row):
    known=set(NAME_MAP.values())
    if row['home'] not in known or row['away'] not in known or row['home']==row['away']:
        raise ValueError('Unknown/noncanonical/same club; record aliases explicitly')


def finite_shared(features,targets):
    sizes={len(x) for x in features.values()}|{len(targets)}
    if len(sizes)!=1 or set(features)!=set(ARMS):raise ValueError('Arm/cohort mismatch')
    for arm,array in features.items():
        if np.asarray(array).ndim!=2 or not np.isfinite(array).all():
            raise ValueError('Non-finite feature in '+arm+'; fail closed, no imputation or drop')
    if not np.isfinite(targets).all() or (np.asarray(targets)<0).any():raise ValueError('Invalid shared targets')


def features(fixtures,markets):
    """Build one chronological numeric cohort; never reads target-match odds."""
    prepared=[];seen=set();history={};previous_clubs={}
    for raw in markets:
        if raw['season'] not in ('2019-20',*SEASONS):raise ValueError('Later market season prohibited')
        check_clubs(raw);key=identity(raw)
        if key in seen:raise ValueError('Duplicate market identity')
        seen.add(key);when=source_clock(raw)
        prepared.append(dict(season=raw['season'],fixture=raw.get('fixture'),identity=key,
                             kickoff=when,home=raw['home'],away=raw['away'],
                             lambda_home=raw['lambda_home'],lambda_away=raw['lambda_away']))
        previous_clubs.setdefault(raw['season'],set()).update([raw['home'],raw['away']])
    prepared.sort(key=lambda r:(r['kickoff'],r['identity']))
    fixture_keys=set()
    for row in fixtures:
        if row['season'] not in SEASONS:raise ValueError('Warmup/later targets prohibited')
        check_clubs(row);key=identity(row)
        if key in fixture_keys:raise ValueError('Duplicate target fixture')
        fixture_keys.add(key);clock=source_clock(row)
        if timestamp(row['deadline'])>=timestamp(row['fpl_kickoff']):raise ValueError('Invalid target origin')
        for home,team,opp in [(True,row['home'],row['away']),(False,row['away'],row['home'])]:
            vals=dict(gf=row['goals_home'] if home else row['goals_away'],ga=row['goals_away'] if home else row['goals_home'],
                      xgf=row['xg_home'] if home else row['xg_away'],xga=row['xg_away'] if home else row['xg_home'])
            history.setdefault((row['season'],team),[]).append((clock,key,vals))
    for records in history.values():records.sort(key=lambda r:(r[0],r[1]))
    matrices={a:[] for a in ARMS};targets=[];keys=[];metadata=[];ratings={};hist_cache={}
    for row in sorted(fixtures,key=lambda r:(timestamp(r['deadline']),r['season'],r['fixture'])):
        cutoff=timestamp(row['deadline'])-timedelta(hours=3);key=identity(row)
        if cutoff not in ratings:
            eligible=[r for r in prepared if r['kickoff']<cutoff]
            ratings[cutoff]=(fit_ratings(eligible,cutoff),{tuple(r['identity']) for r in eligible})
        rating,used=ratings[cutoff]
        if key in used:raise ValueError('Target-match odds entered source window')
        for home,team,opponent in [(True,row['home'],row['away']),(False,row['away'],row['home'])]:
            values={'home':float(home)};counts={};maxima={}
            for side,club in [('team',team),('opp',opponent)]:
                cache=(row['season'],club,cutoff)
                if cache not in hist_cache:
                    prior=[r for r in history.get((row['season'],club),[]) if r[0]<cutoff]
                    if any(r[1]==key for r in prior):raise ValueError('Target outcome entered feature history')
                    if any(not all(math.isfinite(v) for v in r[2].values()) for r in prior):
                        raise ValueError('Non-finite prior observation; fail closed')
                    z={f'ew{half}_{stat}':ew([r[2][stat] for r in prior],half,1.35,4.) for half in (4,12) for stat in ('gf','ga','xgf','xga')}
                    hist_cache[cache]=(z,len(prior),max((r[0] for r in prior),default=None))
                z,count,maximum=hist_cache[cache];values.update({side+'_'+k:v for k,v in z.items()})
                counts[side]=count;maxima[side]=maximum.isoformat() if maximum else None
                if maximum is not None and maximum>=cutoff:raise ValueError('Future goal/xG source')
            projected=project(rating,team,opponent,home)
            values.update(log_mkt_lambda_for=math.log(projected['mkt_lambda_for']),
                          log_mkt_lambda_against=math.log(projected['mkt_lambda_against']))
            for arm in ARMS:matrices[arm].append([values[k] for k in FEATURES[arm]])
            targets.append(row['goals_home'] if home else row['goals_away'])
            keys.append((row['season'],row['fixture'],team))
            prev=str(int(row['season'][:4])-1)+'-'+row['season'][:4][-2:]
            metadata.append(dict(season=row['season'],fixture=row['fixture'],team=team,opponent=opponent,home=home,
                gameweek=row['gameweek'],cutoff=cutoff.isoformat(),source_max={**maxima,'market':rating.source_max.isoformat()},
                history_counts=counts,cold_start_C=counts['team']==0,cold_start_U=counts['team']==0,
                cold_start_M=projected['cold_start_team'],cold_start_M_opponent=projected['cold_start_opponent'],
                promoted_team=team not in previous_clubs.get(prev,set()),market_matches=rating.matches))
    matrices={a:np.asarray(x,dtype=float) for a,x in matrices.items()};targets=np.asarray(targets,dtype=float)
    finite_shared(matrices,targets)
    return matrices,targets,keys,metadata


def fold_masks(seasons,fold):
    if fold not in FOLDS:raise ValueError('Undeclared fold')
    seasons=np.asarray(seasons);train=(seasons<fold)&np.isin(seasons,SEASONS);test=seasons==fold
    if not train.any() or not test.any():raise ValueError('Empty fold')
    if set(seasons[train])!=set(SEASONS[:SEASONS.index(fold)]):raise ValueError('Missing/extra training seasons')
    return train,test


def unit_deviance(y,pred):
    y=np.asarray(y,dtype=float);pred=np.asarray(pred,dtype=float)
    if y.shape!=pred.shape or not np.isfinite(y).all() or (y<0).any() or not np.isfinite(pred).all() or (pred<=0).any():
        raise ValueError('Invalid Poisson evaluation inputs')
    return 2*(xlogy(y,y/pred)-y+pred)


def scores(y,pred):
    dev=unit_deviance(y,pred);y=np.asarray(y);pred=np.asarray(pred);delta=pred-pred.mean();den=float(delta@delta)
    slope=float(delta@(y-y.mean())/den) if den>0 else None
    return dict(mean_poisson_deviance=float(mean_poisson_deviance(y,pred)),clean_sheet_Brier=float(np.mean((np.exp(-pred)-(y==0))**2)),
                calibration_rate_slope=slope,calibration_rate_intercept=float(y.mean()-slope*pred.mean()) if slope is not None else None,
                rows=len(y),actual_mean=float(y.mean()),prediction_mean=float(pred.mean()))


def paired_blocks(y,first,second,gameweeks):
    delta=unit_deviance(y,first)-unit_deviance(y,second);blocks=(np.asarray(gameweeks)-1)//4
    groups=sorted(set(blocks));mean=float(delta.mean());leave=[];table=[]
    for b in groups:
        selected=blocks==b;other=delta[~selected]
        if not len(other):raise ValueError('Need multiple calendar blocks')
        leave.append(float(other.mean()));table.append(dict(first_gw=int(b*4+1),last_gw=int(min(b*4+4,38)),rows=int(selected.sum()),mean_delta=float(delta[selected].mean())))
    v=np.asarray(leave);se=float(np.sqrt((len(v)-1)/len(v)*np.sum((v-v.mean())**2)))
    return dict(mean_delta=mean,jackknife_se=se,descriptive_95_interval=[mean-1.96*se,mean+1.96*se],blocks=table,
                scope='Fixed paired four-GW delete-one-block interval, unequal block lengths; descriptive, not independent-season significance or a gate')
