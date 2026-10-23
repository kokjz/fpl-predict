"""Bounded read-only historical market receipt audit; never admits a replay.

Capture/publication clocks in an archive are claims, not independent proof.
Market receipts do not establish fixture-as-known, outcome or forecast coverage.
"""
import argparse
from datetime import datetime
import hashlib
import json
import lzma
from pathlib import Path


def stamp(value):
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None:raise ValueError('Timestamp needs timezone')
    return t


def audit(manifest,root):
    root=Path(root).resolve();entries=manifest['market_origins']
    if len(entries)!=38 or {p['gameweek'] for p in entries}!=set(range(1,39)):
        raise ValueError('Need one market receipt for each of38origins')
    rows=[]
    for e in sorted(entries,key=lambda p:p['gameweek']):
        path=(root/e['file']).resolve()
        if not path.is_relative_to(root):raise ValueError('Receipt path escapes root')
        packed=path.read_bytes()
        if len(packed)>512*1024 or hashlib.sha256(packed).hexdigest()!=e['compressed_sha256']:
            raise ValueError('Compressed source mismatch or oversized')
        decoder=lzma.LZMADecompressor();raw=decoder.decompress(packed,max_length=4*1024**2+1)
        if len(raw)>4*1024**2 or not decoder.eof or decoder.unused_data or hashlib.sha256(raw).hexdigest()!=e['sha256']:
            raise ValueError('Decoded source mismatch or oversized')
        def invalid(value):raise ValueError('Nonfinite source JSON')
        data=json.loads(raw,parse_constant=invalid);g=e['gameweek']
        if stamp(e['captured_at'])>=stamp(e['deadline']):raise ValueError('Capture not before deadline')
        events=[x for x in data['events'] if x['id']==g]
        if len(events)!=1 or stamp(events[0]['deadline_time'])!=stamp(e['deadline']):raise ValueError('Deadline differs')
        players=[p for p in data['elements'] if p['element_type'] in [1,2,3,4]]
        if not players or len({p['id'] for p in players})!=len(players):raise ValueError('Empty or duplicate market')
        if any(type(p[k]) is not int or p[k]<1 for p in players for k in ['id','now_cost','team']):raise ValueError('Invalid player/club/price integer')
        if e.get('players')!=len(players):raise ValueError('Listed count differs')
        rows.append(dict(gameweek=g,listed_players=len(players),listed_managers=sum(p['element_type']==5 for p in data['elements']),
                         capture_age_hours=(stamp(e['deadline'])-stamp(e['captured_at'])).total_seconds()/3600,
                         chip_names=sorted({c['name'] for c in data.get('chips',[])}),
                         market_sha256=e['sha256'],source_url=e['source_url'],source_revision=e['source_revision']))
    return dict(complete=True,season=manifest['season'],market_origins_verified=38,rows=rows,
                full_season_replay_admitted=False,
                scope='Byte/schema/deadline verification of38historical market receipts only; archive publication/capture claims are not independent certification. No fixture/calendar/outcome/forecast/rule compatibility admission is implied.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Output exists')
    if hashlib.sha256(a.manifest.read_bytes()).hexdigest()!=a.manifest_sha256:p.error('Manifest checksum differs')
    if a.output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):p.error('Keep detailed receipts outside public checkout')
    result=audit(json.loads(a.manifest.read_text()),a.source_root)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)


if __name__=='__main__':main()
