"""Audit pinned deadline-calendar sources separately from forecasts and outcomes."""
import argparse
import io
import json
import lzma
from pathlib import Path
import pandas as pd
from availability_evidence import utc
from deadline_provenance import read_snapshot,extract_bootstrap,replay_event_assignments
from experiment_runner import file_hash
from season_engine import audit_bootstrap

COLUMNS=['id','event','team_h','team_a','kickoff_time']


def calendar(entry,root,*,audit_only=False):
    root=Path(root).resolve();p=(root/entry['file']).resolve()
    if not p.is_relative_to(root):raise ValueError('Calendar escapes source root')
    if file_hash(p)!=entry['compressed_sha256']:raise ValueError('Compressed calendar hash mismatch')
    if utc(entry['publication_claim'])>=utc(entry['captured_at']):raise ValueError('Calendar revision not before origin')
    # Bounded lossless decode; never load nested historical match-result columns.
    dec=lzma.LZMADecompressor();raw=dec.decompress(p.read_bytes(),max_length=4*1024**2+1)
    if len(raw)>4*1024**2 or not dec.eof or dec.unused_data:raise ValueError('Oversized/incomplete calendar')
    import hashlib
    if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Calendar content hash mismatch')
    columns=COLUMNS+['finished','started','team_h_score','team_a_score'] if audit_only else COLUMNS
    f=pd.read_csv(io.BytesIO(raw),usecols=columns)
    if f.empty or f.id.duplicated().any() or f[COLUMNS[:4]].drop(columns='event').isna().any().any():raise ValueError('Invalid calendar identity')
    for k in ('id','team_h','team_a'):
        if not f[k].gt(0).all() or not f[k].eq(f[k].round()).all():raise ValueError('Invalid calendar integer')
    event=f.event.dropna()
    if not event.between(1,38).all() or not event.eq(event.round()).all() or f.team_h.eq(f.team_a).any():raise ValueError('Invalid calendar assignment')
    return f.loc[:,columns]


def audit(manifest,snapshots,calendar_root,snapshot_root,actual_fixtures,updates=()):
    if manifest['season']!=snapshots['season']:raise ValueError('Season mismatch')
    entries=manifest['entries'];boots=snapshots['snapshots']
    if len(entries)!=38 or {e['gameweek'] for e in entries}!=set(range(1,39)):raise ValueError('Need all38calendar origins')
    if len(boots)!=38 or {e['gameweek'] for e in boots}!=set(range(1,39)):raise ValueError('Need all38bootstrap origins')
    reports=[]
    for entry in sorted(entries,key=lambda e:e['gameweek']):
        gw=entry['gameweek'];s=next(e for e in boots if e['gameweek']==gw)
        if utc(s['captured_at'])!=utc(entry['captured_at']):raise ValueError('Market/calendar origin differs')
        root=Path(snapshot_root).resolve();p=(root/s['file']).resolve()
        if not p.is_relative_to(root):raise ValueError('Bootstrap escapes root')
        b=read_snapshot(p,s['sha256']);info,_=extract_bootstrap(b,manifest['season'],gw,s['captured_at'])
        f=calendar(entry,calendar_root,audit_only=True)
        later=[u for u in updates if utc(u['available_at'])>utc(entry['publication_claim'])]
        assignments=replay_event_assignments(f,entry['publication_claim'],later,s['captured_at'])
        selected=set(assignments.loc[assignments.event.eq(gw),'id'].astype(int))
        actual=set(actual_fixtures.loc[actual_fixtures.gameweek.eq(gw),'fixture'].astype(int))
        rules=audit_bootstrap(b,manifest['season'],gw)
        reports.append(dict(gameweek=gw,deadline=info['deadline'],origin=s['captured_at'],calendar_revision=entry['revision'],
            calendar_sha256=entry['sha256'],bootstrap_sha256=s['sha256'],forecast_calendar_fixtures=len(selected),
            actual_fixtures=len(actual),membership_matches=selected==actual,only_calendar=sorted(selected-actual),only_outcome=sorted(actual-selected),rules=rules))
    return dict(season=manifest['season'],weeks=reports,all38_memberships_match=all(r['membership_matches'] for r in reports),
        all_active_rules_compatible=all(r['rules']['active_rules_compatible'] for r in reports),
        provenance='Pinned historical commit timestamps and cached capture claims; not independently witnessed publication',
        limitations=['Future provisional chip overrides must be excluded from planning until supported','This audit does not fit or admit any forecast, prove a policy causal or establish season-points performance'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('calendars','bootstraps','outcome-fixtures'):
        p.add_argument('--'+name,type=Path,required=True);p.add_argument('--'+name+'-sha256',required=True)
    for name in ('calendar-root','bootstrap-root','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--updates',type=Path);p.add_argument('--updates-sha256');a=p.parse_args()
    paths={n:getattr(a,n) for n in ('calendars','bootstraps','outcome_fixtures')}
    if a.output.exists():p.error('Output exists; retain evidence')
    if any(file_hash(v)!=getattr(a,k+'_sha256') for k,v in paths.items()):p.error('Input checksum mismatch')
    if bool(a.updates)!=bool(a.updates_sha256):p.error('Updates require path and checksum')
    if a.updates and file_hash(a.updates)!=a.updates_sha256:p.error('Update checksum mismatch')
    manifest=json.loads(a.calendars.read_text());snapshots=json.loads(a.bootstraps.read_text())
    f=pd.read_csv(a.outcome_fixtures,usecols=['season','gameweek','fixture']);f=f[f.season.eq(manifest['season'])]
    result=audit(manifest,snapshots,a.calendar_root,a.bootstrap_root,f,json.loads(a.updates.read_text()) if a.updates else [])
    result['inputs_sha256']={n:file_hash(v) for n,v in paths.items()}
    if a.updates:result['inputs_sha256']['updates']=file_hash(a.updates)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)


if __name__=='__main__':main()
