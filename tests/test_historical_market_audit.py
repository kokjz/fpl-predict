from datetime import datetime,timedelta,timezone
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import pytest


def module():
    spec=importlib.util.spec_from_file_location('markets',Path(__file__).parents[1]/'tools/audit_historical_markets.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def setup(tmp_path):
    entries=[]
    for gw in range(1,39):
        cutoff=datetime(2024,8,16,17,30,tzinfo=timezone.utc)+timedelta(days=7*(gw-1))
        capture=cutoff-timedelta(hours=5.5)
        d=dict(events=[dict(id=gw,deadline_time=cutoff.isoformat())],elements=[dict(id=1,element_type=1,team=1,now_cost=45)],chips=[])
        raw=json.dumps(d).encode();packed=lzma.compress(raw);p=tmp_path/f'{gw}.xz';p.write_bytes(packed)
        entries.append(dict(gameweek=gw,file=p.name,compressed_sha256=hashlib.sha256(packed).hexdigest(),sha256=hashlib.sha256(raw).hexdigest(),captured_at=capture.isoformat(),deadline=cutoff.isoformat(),players=1,source_url='https://example.invalid/pinned',source_revision='abc'))
    return dict(season='2024-25',market_origins=entries)


def test_known_capture_receipts_do_not_admit_whole_replay(tmp_path):
    m=module();d=setup(tmp_path);out=m.audit(d,tmp_path)
    assert out['complete'] and out['market_origins_verified']==38 and not out['full_season_replay_admitted']
    assert out['rows'][0]['capture_age_hours']==5.5


@pytest.mark.parametrize('kind',['late','missing','duplicate','escape','hash','price','deadline','oversized','position'])
def test_historical_admission_rejects_tamper(tmp_path,kind):
    m=module();d=setup(tmp_path);e=d['market_origins'][0]
    if kind=='late':e['captured_at']=e['deadline']
    elif kind=='missing':d['market_origins'].pop()
    elif kind=='duplicate':d['market_origins'][1]['gameweek']=1
    elif kind=='escape':e['file']='../outside.xz'
    elif kind=='hash':e['sha256']='0'*64
    elif kind=='oversized':(tmp_path/e['file']).write_bytes(b'X'*(512*1024+1))
    else:
        p=tmp_path/e['file'];raw=json.loads(lzma.decompress(p.read_bytes()))
        if kind=='price':raw['elements'][0]['now_cost']=True
        elif kind=='position':raw['elements'][0]['element_type']=True
        else:raw['events'][0]['deadline_time']='2024-08-17T17:30Z'
        data=json.dumps(raw).encode();packed=lzma.compress(data);p.write_bytes(packed);e['sha256']=hashlib.sha256(data).hexdigest();e['compressed_sha256']=hashlib.sha256(packed).hexdigest()
    with pytest.raises((ValueError,FileNotFoundError)):m.audit(d,tmp_path)


def test_receipts_must_have_increasing_gameweek_deadlines(tmp_path):
    m=module();d=setup(tmp_path);e=d['market_origins'][1];first=d['market_origins'][0]
    e['captured_at']=first['captured_at'];e['deadline']=first['deadline']
    p=tmp_path/e['file'];data=json.loads(lzma.decompress(p.read_bytes()));data['events'][0]['deadline_time']=e['deadline']
    raw=json.dumps(data).encode();packed=lzma.compress(raw);p.write_bytes(packed)
    e['sha256']=hashlib.sha256(raw).hexdigest();e['compressed_sha256']=hashlib.sha256(packed).hexdigest()
    with pytest.raises(ValueError,match='Nonchronological'):m.audit(d,tmp_path)
