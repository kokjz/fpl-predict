"""Freeze and score same-squad, no-transfer shadow comparisons before outcomes."""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from forecast import select_xi, legal_squad
from points_replay import formation, realised_points
from model_registry import resolve_champion
from external_benchmark import _timestamp


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_selection(selection, players):
    all_ids=selection['starters']+selection['bench']
    if len(all_ids)!=15 or len(set(all_ids))!=15 or set(all_ids)!=set(players):
        raise ValueError('Selection must contain the same complete 15-player squad')
    if not formation(selection['starters'],players):
        raise ValueError('Starting formation is illegal')
    if selection['captain']==selection['vice'] or any(selection[k] not in selection['starters'] for k in ['captain','vice']):
        raise ValueError('Captain and vice must be distinct starters')


def freeze(root, forecast, state_path, destination, gw, baseline_source):
    root,forecast,state_path,destination=map(Path,[root,forecast,state_path,destination])
    now=dt.datetime.now(dt.timezone.utc)
    model_path,version,record=resolve_champion(root)
    manifest=json.loads((forecast/'manifest.json').read_text())
    if manifest['model_sha256']!=record['sha256']:
        raise ValueError('The chosen forecast does not use the approved champion')
    snapshot=root/'data/current'/manifest['snapshot']
    bootstrap=json.loads((snapshot/'bootstrap.json').read_text())
    event=next(e for e in bootstrap['events'] if e['id']==gw)
    deadline=pd.Timestamp(event['deadline_time'])
    if pd.Timestamp(now)>=deadline:raise ValueError('Cannot freeze a comparison after its deadline')
    if pd.Timestamp(manifest['as_of_utc'])>pd.Timestamp(now):raise ValueError('Inputs are dated in the future')
    if manifest.get('created_at_utc') and pd.Timestamp(manifest['created_at_utc'])>pd.Timestamp(now):
        raise ValueError('Forecast is dated in the future')
    state=json.loads(state_path.read_text());ids=[p['id'] for p in state['players']]
    predictions=[r for r in json.loads((forecast/'player_gameweek_predictions.json').read_text()) if r['GW']==gw]
    if len({r['id'] for r in predictions})!=len(predictions):raise ValueError('Duplicate player forecasts')
    selected=[r for r in predictions if r['id'] in ids];players={r['id']:r for r in selected}
    if set(players)!=set(ids) or not legal_squad(selected):raise ValueError('Incomplete or illegal squad')
    selections={}
    for label,col in [('model','expected_points'),('last5','last5_xp'),('ewm','ewm_xp')]:
        if not all(math.isfinite(r[col]) for r in selected):raise ValueError('Non-finite prediction')
        selections[label]=select_xi([{**r,'expected_points':r[col]} for r in selected])
    previous=state['screenshot_selection']
    selections['preserved_pre_model_selection']={
        'starters':previous['starters'],'bench':previous['bench_outfield']+[previous['bench_goalkeeper']],
        'captain':previous['captain'],'vice':previous['vice_captain']}
    for selection in selections.values():validate_selection(selection,players)
    trial={'schema_version':1,'created_at_utc':now.isoformat(),'deadline_utc':deadline.isoformat(),
        'GW':gw,'season':state['season'],'status':'provisional_shadow_comparison',
        'model_version':version,'model_sha256':record['sha256'],
        'input_as_of_utc':manifest['as_of_utc'],'forecast_path':str(forecast),
        'players':selected,'selections':selections,'transfer_cost':0,'chip':None,
        'baseline_provenance':{'source':str(baseline_source),
            'scope':'Previously documented unchanged selection, not the conditional manual transfer/chip policy.',
            'independence':'Preserved from before model fitting; not a newly blinded manual recommendation.'},
        'limitations':['Same fixed squad, no transfers/hits/chips; this is not a full strategy test.',
            'Provisional record; final near-deadline trial must be designated before results.',
            'Current injuries are unadjusted unless a documented forecast scenario was supplied.']}
    destination.mkdir(parents=True,exist_ok=False)
    sources={'forecast_manifest.json':forecast/'manifest.json',
        'frozen_predictions.json':forecast/'player_gameweek_predictions.json',
        'team_state.json':state_path,'pre_model_source.md':Path(baseline_source),
        'bootstrap_at_forecast.json':snapshot/'bootstrap.json',
        'fixtures_at_forecast.json':snapshot/'fixtures.json'}
    for name,path in sources.items():(destination/name).write_bytes(path.read_bytes())
    (destination/'trial.json').write_text(json.dumps(trial,indent=2)+'\n')
    hashes={name:digest(destination/name) for name in [*sources,'trial.json']}
    (destination/'integrity.json').write_text(json.dumps(hashes,indent=2)+'\n')
    return trial


def load_trial(destination):
    destination=Path(destination)
    for name,expected in json.loads((destination/'integrity.json').read_text()).items():
        path=(destination/name).resolve()
        if not path.is_relative_to(destination.resolve()) or digest(path)!=expected:
            raise ValueError('Frozen comparison integrity check failed')
    trial=json.loads((destination/'trial.json').read_text())
    if pd.Timestamp(trial['created_at_utc'])>=pd.Timestamp(trial['deadline_utc']):
        raise ValueError('Comparison was not frozen before its deadline')
    players={r['id']:r for r in trial['players']}
    for selection in trial['selections'].values():validate_selection(selection,players)
    return trial


def designate_primary(root, destination, baseline=None):
    """Choose the evaluation record before outcomes, never the best run afterwards."""
    root,destination=Path(root).resolve(),Path(destination).resolve()
    if baseline not in (None,'ewm','last5'):raise ValueError('Unknown primary baseline')
    if not destination.is_relative_to(root):raise ValueError('Primary trial must be inside the model project')
    trial=load_trial(destination);now=dt.datetime.now(dt.timezone.utc)
    if pd.Timestamp(now)>=pd.Timestamp(trial['deadline_utc']):raise ValueError('Primary selection is after the deadline')
    target=root/'decision_trials'/f'PRIMARY_{trial["season"].replace("/","-")}_GW{trial["GW"]}.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    record={'trial':str(destination.relative_to(root)),'trial_sha256':digest(destination/'trial.json'),
            'designated_at_utc':now.isoformat(),'scope':'Primary same-squad shadow comparison; no account action'}
    if baseline is not None:record['primary_baseline']=baseline
    with target.open('x') as file:file.write(json.dumps(record,indent=2)+'\n')
    return record


def _score_result(destination, outcome):
    destination,outcome=Path(destination),Path(outcome);trial=load_trial(destination)
    b=json.loads((outcome/'bootstrap.json').read_text())
    season_tag=trial['season'].replace('/','_')
    config=b.get('game_config',{}).get('settings',{}).get('static_content_url','')
    if season_tag not in config:raise ValueError('Outcome season does not match the frozen trial')
    event=next(e for e in b['events'] if e['id']==trial['GW'])
    if not event.get('finished') or not event.get('data_checked'):
        raise ValueError('Gameweek outcome is not yet finished and checked')
    if pd.Timestamp(event['deadline_time'])!=pd.Timestamp(trial['deadline_utc']):
        raise ValueError('Deadline changed; explicit schedule review is required')
    players={r['id']:r for r in trial['players']};actual={};played={};hashes={}
    for pid in players:
        path=outcome/f'players/{pid}.json'
        if not path.exists():raise ValueError('Missing outcome history; never infer zero from missing data')
        history=json.loads(path.read_text())['history'];rows=[h for h in history if h['round']==trial['GW']]
        actual[pid]=sum(r['total_points'] for r in rows);played[pid]=any(r['minutes']>0 for r in rows)
        hashes[str(pid)]=digest(path)
    points={name:realised_points(selection,players,actual,played) for name,selection in trial['selections'].items()}
    result={'GW':trial['GW'],'trial_sha256':digest(destination/'trial.json'),
        'scored_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'outcome_snapshot':str(outcome),
        'outcome_hashes':hashes,'bootstrap_sha256':digest(outcome/'bootstrap.json'),
        'realised_points':points,'model_minus_baseline':{name:points['model']-p for name,p in points.items() if name!='model'},
        'scope':'Same owned squad, legal autosubs and captain fallback; no transfers or chips.'}
    return result


def score(destination, outcome):
    destination,outcome=Path(destination),Path(outcome)
    result=_score_result(destination,outcome)
    target=destination/f'outcome_{outcome.name}.json'
    with target.open('x') as file:file.write(json.dumps(result,indent=2)+'\n')
    return result


def point_uncertainty(records):
    """Descriptive four-GW blocks; never turn a short run into approval."""
    weeks=np.asarray([r['gameweek'] for r in records]);values=np.asarray([r['delta'] for r in records],dtype=float)
    segments=[values[idx] for idx in np.split(np.arange(len(values)),np.flatnonzero(np.diff(weeks)!=1)+1) if len(idx)]
    result=dict(scope='fixed frozen decisions only; not selection uncertainty or full strategy',block_length=4,samples=1000,seed=20261015)
    if not segments or max(map(len,segments))<8:return {**result,'status':'insufficient_contiguous_weeks'}
    rng=np.random.default_rng(20261015);totals=np.zeros(1000)
    for segment in segments:
        n=len(segment);starts=rng.integers(0,n,size=(1000,math.ceil(n/4)))
        indexes=((starts[:,:,None]+np.arange(min(4,n)))%n).reshape(1000,-1)[:,:n]
        # When n<4 only one block is needed; retain exact sample length.
        totals+=segment[indexes].sum(axis=1)
    means=totals/len(values)
    return {**result,'status':'descriptive_interval','mean_point_delta':float(values.mean()),
            'lower':float(np.quantile(means,.025)),'upper':float(np.quantile(means,.975))}


def review_primaries(root):
    """Read-only aggregation of explicitly designated, independently re-scored trials.

    Never choose among multiple outcome corrections, invent a baseline for legacy
    records, mix model versions/seasons/baselines, or use undeclared trial runs.
    """
    root=Path(root).resolve();now=pd.Timestamp(dt.datetime.now(dt.timezone.utc))
    groups={};pending=[];seen=set();evidence=[]
    for primary_path in sorted((root/'decision_trials').glob('PRIMARY_*.json')):
        primary=json.loads(primary_path.read_text());trial_path=(root/primary['trial']).resolve()
        if not trial_path.is_relative_to(root):raise ValueError('Primary path escapes workspace')
        trial=load_trial(trial_path);deadline=_timestamp(trial['deadline_utc'])
        if primary['trial_sha256']!=digest(trial_path/'trial.json'):raise ValueError('Primary trial hash differs')
        if _timestamp(primary['designated_at_utc'])>=deadline:raise ValueError('Primary designation is after deadline')
        key=(trial['season'],trial['GW'])
        if key in seen:raise ValueError('Duplicate primary gameweek')
        seen.add(key);baseline=primary.get('primary_baseline')
        reason=None
        if baseline not in ('ewm','last5'):reason='legacy_or_unknown_primary_baseline'
        elif now<deadline:reason='deadline_not_passed'
        outcomes=sorted(trial_path.glob('outcome_*.json'))
        if reason is None and len(outcomes)!=1:reason='outcome_absent_or_multiple_revisions_require_review'
        if reason:
            pending.append(dict(season=trial['season'],gameweek=trial['GW'],reason=reason));continue
        saved=json.loads(outcomes[0].read_text())
        if _timestamp(saved['scored_at_utc'])<deadline:raise ValueError('Outcome score predates deadline')
        fresh=_score_result(trial_path,saved['outcome_snapshot'])
        for field in ('GW','trial_sha256','outcome_hashes','bootstrap_sha256','realised_points','model_minus_baseline'):
            if saved[field]!=fresh[field]:raise ValueError('Saved outcome differs from verified source re-score')
        group=(trial['season'],trial['model_version'],trial['model_sha256'],baseline)
        groups.setdefault(group,[]).append(dict(gameweek=trial['GW'],delta=float(saved['model_minus_baseline'][baseline])))
        evidence.append(dict(primary_sha256=digest(primary_path),trial_sha256=primary['trial_sha256'],outcome_sha256=digest(outcomes[0])))
    reports=[]
    for (season,version,model_sha,baseline),records in sorted(groups.items()):
        records=sorted(records,key=lambda r:r['gameweek']);uncertainty=point_uncertainty(records)
        reports.append(dict(season=season,model_version=version,model_sha256=model_sha,baseline=baseline,
                            gameweeks=[r['gameweek'] for r in records],n=len(records),
                            total_point_delta=sum(r['delta'] for r in records),uncertainty=uncertainty,
                            initial_review_ready=uncertainty['status']=='descriptive_interval'))
    return dict(schema_version=1,created_at_utc=now.isoformat(),groups=reports,pending=pending,
                evidence=evidence,model_promotion=False,
                limitations=['Same observed squad each week; not transfer/chip/financial policy gains',
                             'Eight contiguous weeks is an initial review, not proof of superiority',
                             'Historical or postdeadline forecasts cannot be made prospective by this review'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('freeze')
    for flag in ['root','forecast','state','destination','baseline-source']:p.add_argument('--'+flag,required=True)
    p.add_argument('--gw',type=int,required=True)
    p=sub.add_parser('score');p.add_argument('--trial',required=True);p.add_argument('--outcome',required=True)
    p=sub.add_parser('designate');p.add_argument('--root',required=True);p.add_argument('--trial',required=True)
    p.add_argument('--baseline',choices=['ewm','last5'],help='Freeze the primary comparison before outcomes; omitted legacy records remain unlabelled')
    p=sub.add_parser('review');p.add_argument('--root',required=True);p.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command=='freeze':
        result=freeze(args.root,args.forecast,args.state,args.destination,args.gw,args.baseline_source)
        print('Frozen',args.destination,'at',result['created_at_utc'])
    elif args.command=='designate':print(json.dumps(designate_primary(args.root,args.trial,args.baseline),indent=2))
    elif args.command=='review':
        result=review_primaries(args.root)
        with Path(args.output).open('x') as file:json.dump(result,file,indent=2,allow_nan=False)
        print('Primary review saved; no model promotion or account action.')
    else:print(json.dumps(score(args.trial,args.outcome),indent=2))
