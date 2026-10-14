"""Evaluate a frozen pre-deadline forecast only after a GW is finished/checked."""
import argparse
import datetime as dt
import json
from pathlib import Path
import pandas as pd
import numpy as np
from fpl_model import metrics

from runtime import workspace_root
ROOT = workspace_root()

def optional_metrics(actual, predicted):
    if not len(actual):return {'n':0,'rmse':None,'mae':None,'bias':None}
    return metrics(actual,predicted)

def playing_time_diagnostics(frame):
    result={}
    for label,mask in [('all',pd.Series(True,index=frame.index)),('candidates',frame.candidate_pool)]:
        d=frame.loc[mask]
        minutes=d.expected_minutes.to_numpy(dtype=float)
        probability=d.p_play.to_numpy(dtype=float)
        if not np.isfinite(minutes).all() or not np.isfinite(probability).all() or ((probability<0)|(probability>1)).any():
            raise ValueError('Playing-time predictions must be finite, with probabilities in [0,1]')
        actual=d.actual_appearance.to_numpy(dtype=float)
        buckets=[]
        membership=np.minimum((probability*10).astype(int),9)
        for index in range(10):
            lower=index/10
            keep=membership==index
            if keep.any():buckets.append({'lower':float(lower),'n':int(keep.sum()),'mean_probability':float(probability[keep].mean()),'observed_appearance_rate':float(actual[keep].mean())})
        result[label]={'minutes':optional_metrics(d.actual_minutes,minutes),
                       'appearance_brier':float(np.mean((probability-actual)**2)) if len(d) else None,
                       'n':len(d),'appearance_calibration_bins':buckets}
    return result

def official_comparison(frame):
    result={}
    values=pd.to_numeric(frame.get('official_ep_next',pd.Series(np.nan,index=frame.index)),errors='coerce')
    for label,mask in [('all',pd.Series(True,index=frame.index)),('candidates',frame.candidate_pool)]:
        paired=frame.loc[mask&np.isfinite(values)].copy()
        paired['official']=values.loc[paired.index]
        result[label]={'eligible_rows':int(mask.sum()),'matched_rows':len(paired),
            'metrics':{name:optional_metrics(paired.actual,paired[col]) for name,col in
                       [('model','expected_points'),('official_ep_next','official'),('last5','last5_xp'),('ewm','ewm_xp')]}}
    return result

def validate_forecast_timing(manifest, deadline):
    if not manifest.get('created_at_utc'):
        raise ValueError('Legacy forecast lacks a generation timestamp; use a comparison frozen before the deadline')
    deadline=pd.Timestamp(deadline)
    for key in ['as_of_utc','created_at_utc']:
        if pd.Timestamp(manifest[key])>=deadline:
            raise ValueError('Forecast inputs and generation must both precede the deadline')
    if pd.Timestamp(manifest['as_of_utc'])>pd.Timestamp(manifest['created_at_utc']):
        raise ValueError('Forecast generation cannot precede its inputs')

def run(args):
    forecast=Path(args.forecast)
    manifest=json.loads((forecast/'manifest.json').read_text())
    snapshot=ROOT/'data/current'/(args.outcome_snapshot or (ROOT/'data/current/LATEST').read_text().strip())
    b=json.loads((snapshot/'bootstrap.json').read_text());event=next(e for e in b['events'] if e['id']==args.gw)
    if not event.get('finished') or not event.get('data_checked',False):raise ValueError('Gameweek outcome is not yet finished and checked')
    validate_forecast_timing(manifest,event['deadline_time'])
    predictions=[r for r in json.loads((forecast/'player_gameweek_predictions.json').read_text()) if r['GW']==args.gw]
    if not predictions:raise ValueError('No forecasts for this GW')
    rows=[]
    for r in predictions:
        path=snapshot/f'players/{r["id"]}.json'
        if not path.exists():raise ValueError(f'Missing outcome history for player {r["id"]}; do not silently assume zero')
        h=json.loads(path.read_text())['history']
        week=[v for v in h if v['round']==args.gw]
        actual=sum(v['total_points'] for v in week)
        rows.append({**r,'actual':actual,'actual_minutes':sum(v['minutes'] for v in week),
                     'actual_appearance':any(v['minutes']>0 for v in week)})
    d=pd.DataFrame(rows)
    report={'GW':args.gw,'forecast':str(forecast),'forecast_model_sha256':manifest['model_sha256'],'outcome_snapshot':snapshot.name,'scored_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'metrics':{}}
    for label,mask in [('all',pd.Series(True,index=d.index)),('candidates',d.candidate_pool)]:
        report['metrics'][label]={name:optional_metrics(d.loc[mask,'actual'],d.loc[mask,col]) for name,col in [('model','expected_points'),('last5','last5_xp'),('ewm','ewm_xp')]}
    report['playing_time_diagnostics']=playing_time_diagnostics(d)
    report['official_ep_next_comparison']=official_comparison(d)
    report['diagnostic_notes']=['Points and minutes sum fixtures at player-GW grain; appearance means any minutes in that GW.',
        'Double-GW model appearance probabilities use an approximate independence assumption.',
        'Official baseline covers the frozen next-GW field only; missing values stay missing; all paired methods use identical rows.',
        'Calibration bins/Brier are descriptive diagnostics, not recalibrated predictions or evidence of season-point gain.']
    destination=forecast/f'outcome_GW{args.gw}_{snapshot.name}.json'
    if destination.exists():raise FileExistsError(destination)
    destination.write_text(json.dumps(report,indent=2)+'\n');print(destination)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--forecast',required=True);p.add_argument('--gw',required=True,type=int);p.add_argument('--outcome-snapshot');run(p.parse_args())
