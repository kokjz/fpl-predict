"""Read-only point-risk attribution and predeadline availability-evidence triage."""
import argparse
import datetime as dt
import json
from urllib.parse import urlsplit
from pathlib import Path

import numpy as np
import pandas as pd

from availability_evidence import scoped_overrides, utc
from experiment_runner import file_hash
from score_forecast import playing_time_diagnostics

POLICY = dict(version=1, snapshot_max_hours=6, forecast_max_hours=24, review_max_hours=24,
              high_probability=.8, probability_edges=[0,.5,.8,.95,1], predicted_minutes_edges=[0,30,60],
              interpretation='Fixed review heuristics, not learned cutoffs or calibrated start probabilities')


def read_json(path):
    return json.loads(Path(path).read_text())


def event_for(bootstrap, gw):
    events = [e for e in bootstrap['events'] if e['id'] == gw]
    if len(events) != 1: raise ValueError('Unknown/duplicate gameweek')
    utc(events[0]['deadline_time'])
    return events[0]


def identities(bootstrap):
    players = bootstrap['elements']
    ids = [p['id'] for p in players]; codes = [p['code'] for p in players]
    if len(set(ids)) != len(ids) or len(set(codes)) != len(codes): raise ValueError('Duplicate identity')
    return {p['id']:p for p in players}


def frozen_rows(forecast, gw, deadline):
    forecast = Path(forecast); manifest = read_json(forecast/'manifest.json')
    created = utc(manifest['created_at_utc']); inputs = utc(manifest['as_of_utc'])
    if not inputs <= created < utc(deadline): raise ValueError('Forecast not frozen before deadline')
    rows = [r for r in read_json(forecast/'player_gameweek_predictions.json') if r['GW'] == gw]
    if not rows or len({r['id'] for r in rows}) != len(rows): raise ValueError('Empty/duplicate forecasts')
    for r in rows:
        if type(r['id']) is not int or r['id'] <= 0 or type(r['candidate_pool']) is not bool:
            raise ValueError('Invalid forecast identity/cohort')
        for name in ('expected_points','expected_minutes','p_play'):
            if not np.isfinite(float(r[name])): raise ValueError('Nonfinite forecast')
        if not 0 <= r['p_play'] <= 1 or r['expected_minutes'] < 0: raise ValueError('Invalid forecast probability/minutes')
        fixtures = r['fixtures']
        if (not isinstance(fixtures,list) or any(type(f) is not int or f <= 0 for f in fixtures) or
                len(set(fixtures)) != len(fixtures) or r['expected_minutes'] > 90*len(fixtures)):
            raise ValueError('Invalid fixture/minutes forecast')
        if not fixtures and any(r[k] != 0 for k in ('expected_points','expected_minutes','p_play')):
            raise ValueError('Blank forecast must be zero')
    return manifest, rows


def risk_summary(frame):
    """No fitting: actual-minute bins explain errors, predicted bins audit risk."""
    result = {}
    for name, mask in [('all',pd.Series(True,index=frame.index)),('candidates',frame.candidate_pool)]:
        d = frame.loc[mask]; n = len(d)
        error2 = (d.expected_points-d.actual)**2
        def group(keep):
            sub = d[keep]; e = error2[keep]
            zero = sub.actual_minutes.eq(0)
            return dict(n=len(sub),nonappearances=int(zero.sum()),
                mean_probability=float(sub.p_play.mean()) if len(sub) else None,
                observed_appearance_rate=float(sub.actual_appearance.mean()) if len(sub) else None,
                points_rmse=float(np.sqrt(e.mean())) if len(sub) else None,
                contribution_to_total_mse=float(e.sum()/n) if n else None,
                nonappearance_contribution_to_total_mse=float(e[zero].sum()/n) if n else None)
        by_actual = {key:group(keep) for key,keep in [
            ('zero',d.actual_minutes.eq(0)),('one_to_59',d.actual_minutes.gt(0)&d.actual_minutes.lt(60)),
            ('60plus',d.actual_minutes.ge(60))]}
        bands = np.minimum(np.searchsorted([.5,.8,.95],d.p_play,side='right'),3)
        probability = {key:group(bands == i) for i,key in enumerate(['below_.5','.5_to_.8','.8_to_.95','.95_to_1'])}
        minutes = {key:group(keep) for key,keep in [
            ('below_30',d.expected_minutes.lt(30)),('30_to_60',d.expected_minutes.ge(30)&d.expected_minutes.lt(60)),
            ('60plus',d.expected_minutes.ge(60))]}
        result[name] = dict(n=n,points_mse=float(error2.mean()) if n else None,
            by_actual_minutes_diagnostic_only=by_actual,by_predicted_probability=probability,
            by_predicted_minutes=minutes,high_probability_nonappearance=group(d.p_play.ge(.8)))
    return result


def history(forecast, origin, outcome, gw):
    forecast=Path(forecast); outcome=Path(outcome); original=read_json(origin)
    final=read_json(outcome/'bootstrap.json'); event=event_for(final,gw)
    if not event.get('finished') or not event.get('data_checked'): raise ValueError('Outcomes not finalised')
    if utc(event_for(original,gw)['deadline_time']) != utc(event['deadline_time']):raise ValueError('Origin/outcome season or deadline differs')
    manifest, rows = frozen_rows(forecast,gw,event['deadline_time'])
    before=identities(original); after=identities(final); records=[]; histories={}; empty=0
    for row in rows:
        ident=row['id']
        if (ident not in before or ident not in after or before[ident]['code'] != after[ident]['code'] or
                row['position'] != before[ident]['element_type'] or row['position'] != after[ident]['element_type']): raise ValueError('Identity/position conflict')
        path=outcome/'players'/f'{ident}.json'; payload=read_json(path)
        all_history=payload['history']
        if len({r['fixture'] for r in all_history}) != len(all_history): raise ValueError('Duplicate outcome fixture')
        week=[r for r in all_history if r['round'] == gw]
        minutes=np.asarray([r['minutes'] for r in week],float); points=np.asarray([r['total_points'] for r in week],float)
        if not np.isfinite(minutes).all() or not np.isfinite(points).all() or ((minutes<0)|(minutes>90)).any():
            raise ValueError('Invalid final history')
        empty += int(not week); histories[str(ident)]=file_hash(path)
        records.append({**row,'actual':float(points.sum()),'actual_minutes':float(minutes.sum()),
                        'actual_appearance':bool((minutes>0).any())})
    frame=pd.DataFrame(records)
    return dict(schema_version=1,GW=gw,scope='Retained frozen all-player forecast; no manager-squad analysis',policy=POLICY,
        model_sha256=manifest['model_sha256'],playing_time=playing_time_diagnostics(frame),point_risk=risk_summary(frame),
        empty_retained_histories=empty,empty_history_convention='Retained official histories sum GW rows, including zero for no rows; missing files fail',
        hashes=dict(forecast_manifest=file_hash(forecast/'manifest.json'),forecasts=file_hash(forecast/'player_gameweek_predictions.json'),
            origin=file_hash(origin),outcome_bootstrap=file_hash(outcome/'bootstrap.json'),histories=histories),
        caveats=['Descriptive reused outcomes; no calibration, model promotion or realised season gain',
                 'Actual-minute bands never determine predeadline eligibility','p_play is any minutes, not starts/p60',
                 'Doubles retain existing approximate appearance aggregation'])


def external_evidence(document, bootstrap, gw, now):
    """Caller-researched club/league/press observations, never instructions."""
    if document.get('schema_version')!=1 or document['GW']!=gw:raise ValueError('External evidence scope')
    recorded=utc(document['recorded_at_utc']);deadline=utc(event_for(bootstrap,gw)['deadline_time'])
    if not recorded<=now<deadline:raise ValueError('External evidence recorded in future/after deadline')
    known=identities(bootstrap);result={}
    for entry in document['players']:
        ident=entry['id'];url=urlsplit(entry['source_url'])
        if type(ident) is not int or ident<=0 or ident not in known or ident in result:raise ValueError('Unknown/duplicate external player ID')
        if (url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment or
                not str(entry['summary']).strip()):raise ValueError('External evidence requires public source and summary')
        if entry['source_kind'] not in ('club','league','press'):raise ValueError('Unknown external source kind')
        if entry['reported_availability'] not in ('out','doubtful','available','unknown'):raise ValueError('Unknown reported availability')
        if not utc(entry['published_at_utc'])<=utc(entry['checked_at_utc'])<=recorded:
            raise ValueError('External publication/check order')
        result[ident]=entry
    return result


def preflight(forecast, snapshot, gw, as_of, review=None, include_ids=(), evidence=None, origin=None):
    """Triage uses no outcomes; no flag is a football fitness clearance."""
    forecast=Path(forecast); snapshot=Path(snapshot); now=utc(as_of)
    bootstrap=read_json(snapshot/'bootstrap.json'); event=event_for(bootstrap,gw)
    if not event.get('is_next') or event.get('finished') or sum(bool(e.get('is_next')) for e in bootstrap['events']) != 1:
        raise ValueError('Snapshot must name this unfinished GW next')
    deadline=utc(event['deadline_time'])
    if now >= deadline: raise ValueError('Preflight must be before deadline')
    manifest, rows = frozen_rows(forecast,gw,deadline)
    snapshot_manifest=read_json(snapshot/'manifest.json')
    sources=[s for s in snapshot_manifest['files'] if s['file']=='bootstrap.json']
    if len(sources) != 1: raise ValueError('Missing/duplicate bootstrap provenance')
    source=sources[0]
    if (source['url'] != 'https://fantasy.premierleague.com/api/bootstrap-static/' or
            file_hash(snapshot/'bootstrap.json') != source['sha256']): raise ValueError('Unverified official bootstrap bytes/source')
    captured=utc(source['retrieved_utc']); completed=utc(snapshot_manifest['retrieved_utc'])
    generated=utc(manifest['created_at_utc'])
    input_time=utc(manifest.get('snapshot_as_of_utc',manifest['as_of_utc']))
    same_inputs=manifest.get('inputs_manifest_sha256') == file_hash(snapshot/'manifest.json')
    if (captured>completed or completed>now or generated>now or
            (completed<input_time and not same_inputs)): raise ValueError('Future or older snapshot/forecast evidence')
    players=identities(bootstrap); forecast_ids={r['id'] for r in rows}
    include_ids=set(include_ids)
    if not include_ids <= forecast_ids: raise ValueError('Unknown requested forecast ID')
    if not forecast_ids <= set(players): raise ValueError('Missing current player identity')
    if origin:
        original=read_json(origin);old=identities(original)
        if utc(event_for(original,gw)['deadline_time']) != deadline:raise ValueError('Origin/current season or deadline differs')
        if any(i not in old or old[i]['code'] != players[i]['code'] for i in forecast_ids):
            raise ValueError('Origin/current stable identity conflict')
    scoped={}; review_doc=None
    if review:
        review_doc=read_json(review)
        if review_doc['GW'] != gw: raise ValueError('Review names another GW')
        _,_,scoped=scoped_overrides(review_doc,bootstrap,now)
    external=external_evidence(read_json(evidence),bootstrap,gw,now) if evidence else {}
    issues=[]
    if (now-captured).total_seconds()>6*3600: issues.append('bootstrap_older_than_6h')
    if (now-generated).total_seconds()>24*3600: issues.append('forecast_older_than_24h')
    queue=[]; checked=0
    for row in rows:
        ident=row['id']; current=players[ident]
        if row['position'] != current['element_type']: raise ValueError('Forecast/current position conflict')
        if not row['candidate_pool'] and ident not in include_ids: continue
        checked+=1; reasons=[]
        status=current.get('status'); chance=current.get('chance_of_playing_next_round'); news=current.get('news')
        if status is None or not str(status).strip(): reasons.append('status_unknown')
        elif status != 'a': reasons.append('flagged_status')
        if chance is not None:
            if isinstance(chance,bool) or not np.isfinite(float(chance)) or not 0<=float(chance)<=100:
                raise ValueError('Invalid official chance label')
            if float(chance)<100: reasons.append('official_chance_below_100')
        if str(news or '').strip(): reasons.append('news_requires_interpretation')
        if 'status' in row and row['status'] != status: reasons.append('status_changed_since_forecast')
        if 'news' in row and row['news'] != news: reasons.append('news_changed_since_forecast')
        supplied=external.get(ident)
        if supplied is not None:
            reasons.append('external_evidence_requires_interpretation')
            if supplied['reported_availability'] in ('out','doubtful'):
                reasons.append('external_reported_'+supplied['reported_availability'])
            if (now-utc(supplied['checked_at_utc'])).total_seconds()>24*3600:
                reasons.append('external_check_older_than_24h')
        entry=scoped.get(ident)
        if reasons and entry is None: reasons.append('no_sourced_sensitivity_review')
        if entry is not None and (now-utc(entry['checked_at_utc'])).total_seconds()>24*3600:
            reasons.append('review_check_older_than_24h')
        if reasons:
            queue.append(dict(id=ident,reasons=reasons,p_play=row['p_play'],expected_minutes=row['expected_minutes'],
                expected_points=row['expected_points'],high_model_probability=row['p_play']>=.8,
                sourced_assumption_present=entry is not None,external_evidence_present=supplied is not None))
    return dict(schema_version=1,GW=gw,as_of_utc=now.isoformat(),deadline_utc=deadline.isoformat(),policy=POLICY,
        status='review_required' if issues or queue else 'no_machine_detected_issues',
        global_issues=issues,identity_bridge_verified=origin is not None,checked_players=checked,review_queue=queue,fitness_clearance=False,
        hashes=dict(forecast_manifest=file_hash(forecast/'manifest.json'),forecasts=file_hash(forecast/'player_gameweek_predictions.json'),
            bootstrap=file_hash(snapshot/'bootstrap.json'),snapshot_manifest=file_hash(snapshot/'manifest.json'),
            origin=file_hash(origin) if origin else None,review=file_hash(review) if review else None,external_evidence=file_hash(evidence) if evidence else None),
        notes=['No news fetch, forecasts, squad choices or overrides applied',
            'Status a/blank news is not proof of health; official chance is not calibrated p_play',
            'A sourced sensitivity assumption never clears a flag or certifies a start',
            'Review remaining owned players and captain candidates in the authorised weekly workflow',
            'Supply origin bootstrap to verify stable football identities across refreshed snapshots',
            'External source labels/publication/check times are supplied claims, not independently authenticated',
            'Fixture/press-conference completeness is not certified'])


def main():
    p=argparse.ArgumentParser(description=__doc__); commands=p.add_subparsers(dest='command',required=True)
    h=commands.add_parser('history'); f=commands.add_parser('preflight')
    for parser in (h,f):
        parser.add_argument('--forecast',type=Path,required=True);parser.add_argument('--gw',type=int,required=True)
        parser.add_argument('--output',type=Path,required=True)
    h.add_argument('--origin',type=Path,required=True);h.add_argument('--outcome',type=Path,required=True)
    f.add_argument('--snapshot',type=Path,required=True);f.add_argument('--as-of',required=True)
    f.add_argument('--origin',type=Path);f.add_argument('--evidence',type=Path);f.add_argument('--review',type=Path);f.add_argument('--include-id',type=int,action='append',default=[])
    args=p.parse_args()
    try:
        if args.output.exists(): raise ValueError('Output exists; evidence is immutable')
        result=(history(args.forecast,args.origin,args.outcome,args.gw) if args.command=='history' else
                preflight(args.forecast,args.snapshot,args.gw,args.as_of,args.review,args.include_id,args.evidence,args.origin))
        result['engine_sha256']=file_hash(Path(__file__))
        result['created_at_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
        with args.output.open('x') as stream: json.dump(result,stream,indent=2,allow_nan=False)
    except (KeyError,ValueError,TypeError,OSError) as exc:p.exit(2,f'Participation audit rejected: {exc}\n')
    print('Read-only participation audit saved; no fitness clearance or model change.')


if __name__ == '__main__':main()
