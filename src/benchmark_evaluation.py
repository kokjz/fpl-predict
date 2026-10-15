"""Bounded shared-row uncertainty and fixed-squad diagnostics; never train."""
import itertools
import math
import re

import numpy as np
import pandas as pd

from benchmark_metrics import point_scores
from forecast import legal_squad, select_xi
from points_replay import realised_points

KEYS = ['season', 'gameweek', 'fpl_code']


def paired_block_errors(frame, left, right, *, samples=1000, block_length=4, seed=20261015):
    """Paired pooled-error intervals using aggregate GW sums, not row resampling."""
    if type(samples) is not int or not 100 <= samples <= 5000 or block_length != 4:
        raise ValueError('Use100–5000 draws and the declared four-GW blocks')
    base = dict(scope='descriptive fixed-prediction uncertainty, not training or selection uncertainty',
                difference='left_minus_right; negative error difference favours left',
                samples=samples, block_length=block_length, seed=seed)
    if frame.empty: return {**base, 'status':'insufficient_contiguous_weeks', 'gameweeks':0}
    if not np.isfinite(frame[['actual',left,right]].to_numpy(dtype=float)).all():
        raise ValueError('Nonfinite error inputs')
    d=frame[['season','gameweek']].copy()
    el=frame[left].to_numpy()-frame.actual.to_numpy(); er=frame[right].to_numpy()-frame.actual.to_numpy()
    d['n']=1; d['sl']=el**2; d['sr']=er**2; d['al']=abs(el); d['ar']=abs(er)
    g=d.groupby(['season','gameweek'],sort=True)[['n','sl','sr','al','ar']].sum()
    segments=[]
    for _, season in g.groupby(level=0,sort=True):
        weeks=season.index.get_level_values('gameweek').to_numpy()
        for indexes in np.split(np.arange(len(weeks)),np.flatnonzero(np.diff(weeks)!=1)+1):
            if len(indexes):segments.append(season.iloc[indexes].to_numpy(dtype=float))
    base.update(gameweeks=len(g), contiguous_segments=[len(s) for s in segments])
    if max(map(len,segments)) < 8:
        return {**base,'status':'insufficient_contiguous_weeks'}
    rng=np.random.default_rng(seed); draws=np.zeros((samples,5))
    for segment in segments:
        n=len(segment); length=min(block_length,n)
        starts=rng.integers(0,n,size=(samples,math.ceil(n/length)))
        indexes=((starts[:,:,None]+np.arange(length))%n).reshape(samples,-1)[:,:n]
        draws+=segment[indexes].sum(axis=1)
    totals=g.sum().to_numpy(dtype=float)
    result={**base,'status':'descriptive_interval','confidence':.95}
    for label,observed,values in (
        ('rmse',np.sqrt(totals[1]/totals[0])-np.sqrt(totals[2]/totals[0]),
         np.sqrt(draws[:,1]/draws[:,0])-np.sqrt(draws[:,2]/draws[:,0])),
        ('mae',(totals[3]-totals[4])/totals[0],(draws[:,3]-draws[:,4])/draws[:,0])):
        result[label]={'delta':float(observed),'lower':float(np.quantile(values,.025)),
                       'upper':float(np.quantile(values,.975))}
    return result


def uncertainty(frame, columns):
    return [{'models':[left,right],**paired_block_errors(frame,columns[left],columns[right])}
            for left,right in itertools.combinations(columns,2)]


def diagnostics(frame, columns):
    """Position/history are declared predeadline; realised-minute slices diagnostic."""
    slices={}
    if 'position' in frame:
        for pos in range(1,5):slices[f'position_{pos}']=frame[frame.position==pos]
    if 'n_history' in frame:
        slices['cold_start_history_under3']=frame[frame.n_history<3]
        slices['history_at_least3']=frame[frame.n_history>=3]
    if 'minutes' in frame:
        slices['actual_zero_minutes_diagnostic']=frame[frame.minutes==0]
        slices['actual_positive_minutes_diagnostic']=frame[frame.minutes>0]
    return {label:{'rows':len(sub),'models':{name:point_scores(sub,col) for name,col in columns.items()}}
            for label,sub in slices.items()}


def fixed_squad_report(joined, truth, columns, spec):
    """Compare the same declared15, legal XI and ordinary captain, with autosubs.

    Panels are supplied, never selected from realised outcomes. This is a replay
    of fixed squads, not a transfer/chip or full-season strategy simulation.
    """
    from external_benchmark import _timestamp
    if spec.get('schema_version')!=1 or not isinstance(spec.get('panels'),list) or not 1<=len(spec['panels'])<=100:
        raise ValueError('Expected1–100 declared squad panels')
    if 'minutes' not in truth:
        raise ValueError('Fixed-squad replay requires verified fixture minutes')
    panels=[]; seen=set()
    for panel in spec['panels']:
        name=panel.get('id')
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',name) or name in seen:
            raise ValueError('Missing/duplicate squad panel id')
        seen.add(name)
        season=panel['season']; gw=panel['gameweek']
        if type(gw) is not int or not 1<=gw<=38:raise ValueError('Invalid panel gameweek')
        week=joined[(joined.season==season)&(joined.gameweek==gw)]
        truth_week=truth[(truth.season==season)&(truth.gameweek==gw)]
        if truth_week.empty:raise ValueError('Panel outside outcome universe')
        deadline=truth_week.deadline.iloc[0]
        if not _timestamp(panel['inputs_as_of']) < deadline:raise ValueError('Panel inputs reach deadline')
        origin=panel['origin'];created=_timestamp(panel['created_at'])
        if origin not in ('retrospective_fixed','archived_predeadline'):raise ValueError('Unknown panel origin')
        if _timestamp(panel['inputs_as_of'])>created:raise ValueError('Panel creation precedes inputs')
        if origin=='archived_predeadline' and created>=deadline:raise ValueError('Panel not frozen before deadline')
        raw=panel['players']; players=[]
        if not isinstance(raw,list) or len(raw)!=15:raise ValueError('Panel needs15players')
        for p in raw:
            if any(type(p.get(k)) is not int for k in ('fpl_code','position','price_tenths')):
                raise ValueError('Panel IDs/positions/prices must be integers')
            if p['fpl_code']<=0 or p['price_tenths']<=0 or not isinstance(p.get('team'),str) or not p['team']:
                raise ValueError('Invalid panel player metadata')
            players.append({'id':p['fpl_code'],'position':p['position'],'team':p['team'],'price_tenths':p['price_tenths']})
        if not legal_squad(players) or sum(p['price_tenths'] for p in players)>1000:
            raise ValueError('Illegal panel composition, club cap or initial100m budget')
        ids={p['id'] for p in players}; sub=week[week.fpl_code.isin(ids)]
        if len(sub)!=15 or sub[list(columns.values())].isna().any().any():
            panels.append({'id':name,'status':'ineligible_missing_predictions_or_outcomes'});continue
        if 'position' in sub and any(int(sub.set_index('fpl_code').loc[p['id'],'position'])!=p['position'] for p in players):
            raise ValueError('Panel positions conflict with declared outcome metadata')
        actual=sub.set_index('fpl_code').actual.to_dict()
        played=truth_week.groupby('fpl_code').minutes.sum().gt(0).to_dict()
        mapping={p['id']:p for p in players}; scores={}
        for model,col in columns.items():
            predicted=sub.set_index('fpl_code')[col].to_dict()
            selection=select_xi([{**p,'expected_points':predicted[p['id']]} for p in players])
            scores[model]=realised_points(selection,mapping,actual,played)
        panels.append({'id':name,'status':'scored','season':season,'gameweek':gw,'origin':origin,
                       'realised_points':scores})
    eligible=[p for p in panels if p['status']=='scored']
    return {'scope':'fixed supplied squads, ordinary captain/autosubs/vice; no transfers, hits or chips',
            'selection_objective':'XI mean points plus captain; expected autosubs not optimised',
            'independence':'panel selection/timestamp provenance declared, not independently certified',
            'eligible_panels':len(eligible),'total_panels':len(panels),'panels':panels,
            'mean_points':{name:float(np.mean([p['realised_points'][name] for p in eligible])) if eligible else None for name in columns}}
