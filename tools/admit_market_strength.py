"""Offline admission of the five authorised market seasons, without scoring.

Data paths/checksums are supplied privately. No network, player fit, GLM or
evaluation metric is executed here. Output destinations must be new.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from market_strength import NAME_MAP, match_fixture, market_probabilities, solve_lambdas

SEASONS=('2019-20','2020-21','2021-22','2022-23','2023-24')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified(entry):
    p=Path(entry['path'])
    if digest(p)!=entry['sha256']:raise ValueError('Input checksum mismatch: '+str(p))
    return p


def read_csv(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f);return reader.fieldnames,list(reader)


def run(manifest,output):
    start=time.monotonic();output=Path(output)
    if output.exists():raise ValueError('Require a new admission output directory')
    if tuple(x['season'] for x in manifest['markets'])!=SEASONS:
        raise ValueError('Only the five authorised seasons in chronological order')
    output.mkdir(parents=True)
    i4= json.loads(verified(manifest['i4_manifest']).read_text())
    teams_path=verified(manifest['teams'])
    if digest(teams_path)!=i4['inputs']['teams']['sha256']:raise ValueError('Not the frozen I4 team source')
    _,raw=read_csv(teams_path)
    # Later-season rows are never admitted as features, targets or scored data.
    teams=[r for r in raw if r['season'] in SEASONS]
    home_rows=[r for r in teams if r['team_name']<r['opponent_name']]
    # Native canonical teams lack venue. Recover fixture home/away metadata only
    # from the already-held FPL historical source, through an explicit name map.
    fixtures={};source_counts={};fpl_team_ids={}
    for season,entries in manifest['fpl'].items():
        if season not in SEASONS:raise ValueError('Later FPL season prohibited')
        _,clubs=read_csv(verified(entries['teams']))
        ids={r['name']:int(r['id']) for r in clubs};fpl_team_ids[season]=ids
        _,history=read_csv(verified(entries['history']))
        seen={}
        for r in history:
            fixture=int(r['fixture']);team=r['team'];opp_id=int(r['opponent_team'])
            if team not in ids:raise ValueError('FPL team absent from own season map')
            inverse={v:k for k,v in ids.items()};opponent=inverse[opp_id]
            home=r['was_home'].lower()=='true'
            date=r['kickoff_time'][:10];key=(season,date,team if home else opponent,opponent if home else team)
            value=dict(fixture=fixture,home_id=ids[key[2]],away_id=ids[key[3]],kickoff=r['kickoff_time'])
            if fixture in seen and seen[fixture]!=(key,value):raise ValueError('Conflicting FPL fixture metadata')
            seen[fixture]=(key,value)
        for key,value in seen.values():
            if key in fixtures:raise ValueError('Duplicate date/team fixture')
            fixtures[key]=value
        source_counts[season]=len(seen)
    report=dict(status='admitted_with_explicit_exceptions',seasons=[],name_map=NAME_MAP,
                i4_team_source_sha256=digest(teams_path),i4_manifest_sha256=manifest['i4_manifest']['sha256'],
                source_fixture_counts=source_counts,scope='Stage A only; no outcome scoring or Stage-B/C fit')
    lambdas=[];exceptions=[]
    for entry in manifest['markets']:
        season=entry['season'];path=verified(entry);columns,rows=read_csv(path)
        if len(rows)!=380:raise ValueError('Expected 380 EPL rows; report new source before proceeding')
        matched=set();used=Counter();missing=[];residuals=[];row_ids=set()
        available={k:sum(bool(r.get(k,'')) for r in rows) for k in columns if k.startswith('Avg')}
        for i,row in enumerate(rows,1):
            date=datetime.strptime(row['Date'],'%d/%m/%Y').date().isoformat()
            home=NAME_MAP.get(row['HomeTeam']);away=NAME_MAP.get(row['AwayTeam'])
            if home is None or away is None:raise ValueError('Unmapped team; update admission map explicitly')
            key=(date,home,away)
            if key in row_ids:raise ValueError('Duplicate source fixture')
            row_ids.add(key)
            try:
                mapped=match_fixture(season,date,row['HomeTeam'],row['AwayTeam'],fixtures)
                if mapped['fixture'] in matched:raise ValueError('Duplicate fixture match')
                matched.add(mapped['fixture'])
            except ValueError as error:
                mapped=None;exceptions.append(dict(season=season,row=i,date=date,home=home,away=away,reason=str(error)))
            try:probs,groups=market_probabilities(row)
            except ValueError as error:
                missing.append(dict(row=i,reason=str(error)));continue
            fit=solve_lambdas(probs);residuals.append(fit['squared_error'])
            for label,group in groups.items():used[label+':'+','.join(group)]+=1
            kickoff=datetime.strptime(row['Date']+' '+row['Time'],'%d/%m/%Y %H:%M').replace(tzinfo=ZoneInfo('Europe/London')).isoformat()
            lambdas.append(dict(season=season,source_row=i,fixture=mapped['fixture'] if mapped else None,
                                home=home,away=away,csv_kickoff=kickoff,
                                canonical_kickoff=mapped['kickoff'] if mapped else None,
                                probability_target=probs.tolist(),columns_used=groups,**fit))
        own_exceptions=[r for r in exceptions if r['season']==season]
        report['seasons'].append(dict(season=season,market_sha256=entry['sha256'],rows=len(rows),columns=columns,
             fpl_matched=len(matched),fpl_available=source_counts.get(season,0),exceptions=len(own_exceptions),
             complete_odds=len(residuals),missing_odds=missing,column_nonempty_counts=available,
             selected_columns=dict(used),squared_error_max=max(residuals,default=None),
             squared_error_mean=sum(residuals)/len(residuals) if residuals else None))
        print(json.dumps({k:report['seasons'][-1][k] for k in ['season','fpl_matched','exceptions','complete_odds','squared_error_max']}),flush=True)
    report['understat_coverage']={s:dict(team_rows=sum(r['season']==s for r in teams),missing_xg=sum(r['season']==s and (not r['xg'] or not r['xga']) for r in teams)) for s in SEASONS}
    report['seconds']=time.monotonic()-start
    for name,data in [('admission.json',report),('lambdas.json',lambdas),('fixture_exceptions.json',exceptions),('fpl_team_ids.json',fpl_team_ids)]:
        (output/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(json.loads(args.manifest.read_text(encoding='utf-8-sig')),args.output)
