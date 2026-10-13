"""Evaluate a frozen pre-deadline forecast only after a GW is finished/checked."""
import argparse
import datetime as dt
import json
from pathlib import Path
import pandas as pd
from fpl_model import metrics

from runtime import workspace_root
ROOT = workspace_root()

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
        actual=sum(v['total_points'] for v in h if v['round']==args.gw)
        rows.append({**r,'actual':actual})
    d=pd.DataFrame(rows)
    report={'GW':args.gw,'forecast':str(forecast),'forecast_model_sha256':manifest['model_sha256'],'outcome_snapshot':snapshot.name,'scored_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'metrics':{}}
    for label,mask in [('all',pd.Series(True,index=d.index)),('candidates',d.candidate_pool)]:
        report['metrics'][label]={name:metrics(d.loc[mask,'actual'],d.loc[mask,col]) for name,col in [('model','expected_points'),('last5','last5_xp'),('ewm','ewm_xp')]}
    destination=forecast/f'outcome_GW{args.gw}_{snapshot.name}.json'
    if destination.exists():raise FileExistsError(destination)
    destination.write_text(json.dumps(report,indent=2)+'\n');print(destination)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--forecast',required=True);p.add_argument('--gw',required=True,type=int);p.add_argument('--outcome-snapshot');run(p.parse_args())
