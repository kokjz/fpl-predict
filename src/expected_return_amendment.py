"""ert-r2 amendment1: fixture-level clean sheets and exact points reconciliation."""
import csv
import io
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype,is_string_dtype

import expected_return_targets as base
from market_stage_c import array_hash

SEASONS=base.SEASONS
FOLDS=base.FOLDS
METHODS=base.METHODS
shared_proof=base.shared_proof
fit_predict=base.fit_predict
analyse=base.analyse
opponent_xg=base.opponent_xg

RECONCILIATION=('goals_conceded','saves','penalties_saved','penalties_missed','yellow_cards','red_cards','own_goals','bonus')
PLAYER_NUMERIC=('fixture','gameweek','fpl_code','position','minutes','total_points','goals_scored','assists','us_xG','us_xA',*RECONCILIATION)
PLAYER_TEXT=('season','team_name','opponent_name','ts','deadline')
TEAM_NUMERIC=('fixture','xg')
TEAM_TEXT=('season','team_name','opponent_name','ts')


def schema_preflight(players,teams):
    """Schema and key validity only; no label, coverage, fit or return statistics."""
    report={'scope':'names, dtypes and key uniqueness only; no statistics','tables':{},'gaps':[]}
    for name,frame,numeric,strings,keys in [('players',players,PLAYER_NUMERIC,PLAYER_TEXT,['season','fixture','fpl_code']),('teams',teams,TEAM_NUMERIC,TEAM_TEXT,['season','fixture','team_name'])]:
        missing=sorted(set(numeric+strings)-set(frame))
        dtypes={k:str(frame[k].dtype) for k in numeric+strings if k in frame}
        issues=[{'table':name,'kind':'missing_column','column':k} for k in missing]
        for k in numeric:
            if k in frame and not is_numeric_dtype(frame[k].dtype):issues.append({'table':name,'kind':'numeric_dtype_required','column':k,'dtype':str(frame[k].dtype)})
        for k in strings:
            if k in frame and not is_string_dtype(frame[k].dtype):issues.append({'table':name,'kind':'text_dtype_required','column':k,'dtype':str(frame[k].dtype)})
        unique=None
        if set(keys)<=set(frame):
            unique=not frame.duplicated(keys).any() and not frame[keys].isna().any().any()
            if not unique:issues.append({'table':name,'kind':'nonunique_or_null_fixture_key','columns':keys})
        if name=='players' and set(['season','fixture','ts','gameweek'])<=set(frame):
            contexts=frame[['season','fixture','ts','gameweek']].drop_duplicates()
            if contexts.duplicated(['season','fixture']).any():issues.append({'table':name,'kind':'ambiguous_fixture_context','columns':['season','fixture','ts','gameweek']})
        report['tables'][name]=dict(dtypes=dtypes,missing_columns=missing,key=keys,key_unique=bool(unique) if unique is not None else None)
        report['gaps'].extend(issues)
    report['passed']=not report['gaps']
    return report


def preflight_files(players,teams):
    """Filter later-season records before dtype parsing, then report all gaps."""
    frames={};header_gaps=[]
    for name,path in [('players',players),('teams',teams)]:
        with Path(path).open(newline='',encoding='utf-8-sig') as f:
            reader=csv.reader(f);header=next(reader)
            if len(set(header))!=len(header):header_gaps.append(dict(table=name,kind='duplicate_column_names'))
            if 'season' not in header:
                frames[name]=pd.DataFrame(columns=header)
                header_gaps.append(dict(table=name,kind='cannot_check_fixture_keys_without_season'));continue
            season=header.index('season');buffer=io.StringIO();writer=csv.writer(buffer);writer.writerow(header)
            for row in reader:
                if len(row)!=len(header):
                    header_gaps.append(dict(table=name,kind='malformed_csv_row'));continue
                if row[season] in SEASONS:writer.writerow(row)
            buffer.seek(0);frames[name]=pd.read_csv(buffer)
    report=schema_preflight(frames['players'],frames['teams'])
    report['gaps'].extend(header_gaps);report['passed']=not report['gaps']
    return report


def reconcile(p):
    """No control-file clean sheets or aliases. All operations are per fixture."""
    missing=set(['season','fixture','fpl_code',*RECONCILIATION,*base.REQUIRED])-{'clean_sheets'}-set(p)
    if missing:raise ValueError('Amended schema gaps: '+','.join(sorted(missing)))
    if p.duplicated(['season','fixture','fpl_code']).any():raise ValueError('Not one row per player-fixture; do not adapt')
    q=p.copy();q['clean_sheets']=(q.minutes.ge(60)&q.goals_conceded.eq(0)).astype(float)
    gp=q.position.map({1:6,2:6,3:5,4:4}).to_numpy(float);cs=q.position.map({1:4,2:4,3:1,4:0}).to_numpy(float)
    appearance=np.where(q.minutes.ge(60),2.,np.where(q.minutes.gt(0),1.,0.))
    points=appearance+gp*q.goals_scored.to_numpy(float)+3*q.assists.to_numpy(float)+cs*q.clean_sheets.to_numpy(float)+np.floor(q.saves.to_numpy(float)/3)+5*q.penalties_saved.to_numpy(float)-2*q.penalties_missed.to_numpy(float)-np.where(q.position.isin([1,2]),np.floor(q.goals_conceded.to_numpy(float)/2),0.)-q.yellow_cards.to_numpy(float)-3*q.red_cards.to_numpy(float)-2*q.own_goals.to_numpy(float)+q.bonus.to_numpy(float)
    q['_recomputed_points']=points
    q['_reconciled']=q.minutes.gt(0).to_numpy()&(points==q.total_points.to_numpy(float))
    return q


def constants(p,xga):
    q=reconcile(p);keep=q['_reconciled'].to_numpy();xga=np.asarray(xga,float)
    # Every numerator AND denominator excludes the unreconciled rows.
    return base.constants(q.loc[keep],xga[keep])


def training_target(p,xga,k):
    q=reconcile(p);keep=q['_reconciled'].to_numpy();xga=np.asarray(xga,float)
    result=q.total_points.to_numpy(float).copy();fallback=np.ones(len(q),bool)
    if keep.any():
        target,local_fallback=base.training_target(q.loc[keep],xga[keep],k)
        result[keep]=target;fallback[keep]=local_fallback
    return result,fallback


def fold_labels(p,t,fold):
    if fold not in FOLDS:raise ValueError('Undeclared fold')
    train=p.season.lt(fold).to_numpy()&p.season.isin(SEASONS).to_numpy()
    q=p.loc[train];xga=opponent_xg(q,t[t.season.lt(fold)&t.season.isin(SEASONS)])
    k,sums=constants(q,xga);target,fallback=training_target(q,xga,k)
    result=p.total_points.to_numpy(float).copy();result[train]=target
    return result,dict(k=k,sums=sums,training_rows=int(train.sum()),fallback_rows=int(fallback.sum()),training_label_sha256=array_hash(target),actual_training_label_sha256=array_hash(q.total_points.to_numpy(float))),train


def admission(p,t):
    seasons={};folds={};passed=True
    for season in SEASONS[:3]:
        q=reconcile(p[p.season.eq(season)]);played=q.minutes.gt(0).to_numpy();rec=q['_reconciled'].to_numpy()
        finite=np.isfinite(q[['us_xG','us_xA']].to_numpy(float)).all(axis=1)
        xga=opponent_xg(q,t[t.season.eq(season)])
        fixture=q[['season','fixture','team_name']].copy();fixture['finite']=np.isfinite(xga)
        fixture=fixture.groupby(['season','fixture','team_name'],sort=True).finite.all()
        coverage=float(finite[played].mean()) if played.any() else 0.
        share=float(rec[played].mean()) if played.any() else 0.
        positions={}
        for pos in [1,2,3,4]:
            mask=q.position.eq(pos).to_numpy();active=mask&played
            positions[str(pos)]=dict(rows=int(mask.sum()),minutes_positive=int(active.sum()),finite_return_rows=int((active&finite).sum()),finite_return_share=float(finite[active].mean()) if active.any() else None,reconciled_rows=int((mask&rec).sum()),unreconciled_played_rows=int((active&~rec).sum()),reconciled_share=float(rec[active].mean()) if active.any() else None,fallback_rows=int((mask&(~played|~finite|~rec)).sum()))
        criteria=dict(coverage_at_least_97_percent=coverage>=.97,all_team_fixture_xga_finite=bool(fixture.all() and len(fixture)>0),reconciled_at_least_99_5_percent=share>=.995)
        ok=all(criteria.values());passed &= ok
        seasons[season]=dict(rows=len(q),minutes_positive=int(played.sum()),coverage=coverage,team_fixtures=len(fixture),nonfinite_team_fixtures=int((~fixture).sum()),reconciled_rows=int(rec.sum()),unreconciled_played_rows=int((played&~rec).sum()),reconciled_share=share,fallback_rows=int((~played|~finite|~rec).sum()),positions=positions,criteria=criteria,passed=bool(ok))
    for fold in FOLDS:
        try:labels,info,train=fold_labels(p,t,fold)
        except ValueError as e:
            # These are explicit admission failures, never alternative constants.
            if str(e) not in ['Undefined training-only k','Nonfinite training team-fixture xGA']:raise
            folds[fold]=dict(k=None,label_variance=None,undefined_reason=str(e),k_gate_passed=False);passed=False;continue
        q=p.loc[train];y=q.total_points.to_numpy(float);target=labels[train]
        info['variance_definition']='population variance (ddof=0), descriptive only'
        info['label_variance']=dict(overall=dict(actual=float(np.var(y)),expected_return=float(np.var(target))),by_position={str(pos):dict(actual=float(np.var(y[q.position.eq(pos)])),expected_return=float(np.var(target[q.position.eq(pos)]))) for pos in [1,2,3,4]})
        info['k_gate_passed']=all(.6<=v<=1.6 for v in info['k'].values());passed &= info['k_gate_passed'];folds[fold]=info
    return dict(gate_A_pass=bool(passed),seasons=seasons,folds=folds,stage_A_fits=0,amendment='ert-r2 clean sheets and reconciliation')
