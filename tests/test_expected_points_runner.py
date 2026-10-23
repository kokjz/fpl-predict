import copy,gzip,hashlib,importlib.util,json
from pathlib import Path
import pytest
from test_season_benchmark import bundle


def module():
    s=importlib.util.spec_from_file_location('expected_runner',Path(__file__).parents[1]/'tools/run_expected_points_study.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def setup(tmp_path):
    m=module();refs={}
    for season in ['2024-25','2025-26']:
        d,o=bundle();year=int(season[:4]);players=[]
        for i,p in enumerate(d[0]['market']['rows']*2):players.append(dict(p,id=i+1,price_tenths=60,team=str(i%20+1)))
        for w in d:
            w['market']['season']=season;w['market']['rows']=players
            for k in ['as_of','deadline']:w['market'][k]=w['market'][k].replace('2025',str(year)).replace('2026',str(year+1))
            f=w['forecast'];f['trained_through']=f'{year}-05-01T00:00Z';f['feature_cutoff']=f['source_as_of']=w['market']['as_of']
            f['rows']=[dict(gameweek=g,id=p['id'],expected_points=2.) for g in range(w['market']['gameweek'],min(38,w['market']['gameweek']+5)+1) for p in players]
        refs[season]={}
        for name,value in [('decisions',dict(schema_version=1,weeks=d)),('outcomes',dict(schema_version=1,weeks=o))]:
            path=tmp_path/f'{season}-{name}.json.gz';path.write_bytes(gzip.compress(json.dumps(value).encode()));refs[season][name]=dict(path=str(path),sha256=m.digest(path))
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(refs));p=Path(__file__).parents[1]/'docs/season_expected_points_protocol_2026-10-24.json'
    return m,manifest,p


def test_lock_binds_both_seasons_source_only_openings_and_existing_destinations(tmp_path):
    m,f,p=setup(tmp_path);lock=tmp_path/'lock.json';v=m.create_lock(f,m.digest(f),p,lock)
    assert set(v['openings'])=={'2024-25','2025-26'}
    assert all(len(set(o['ids']))==15 and o['cost_tenths']==900 for s in v['openings'].values() for o in s.values())
    with pytest.raises(ValueError,match='new output'):m.create_lock(f,m.digest(f),p,lock)
    assert m.sampler.__name__=='sampler'


def test_changed_inputs_cannot_be_used_with_frozen_lock(tmp_path):
    m,f,p=setup(tmp_path);lock=tmp_path/'lock.json';v=m.create_lock(f,m.digest(f),p,lock);path=Path(v['fingerprint']['inputs']['2024-25']['decisions']['path']);path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='checksum'):m.run_arm(f,m.digest(f),p,lock,m.digest(lock),'2024-25',20261070,'standingH1_adaptive',tmp_path/'result')
    assert not (tmp_path/'result').exists()


def test_undeclared_matrix_budget_and_public_destination_rejected(tmp_path):
    m,f,p=setup(tmp_path);q=json.loads(p.read_text());q['resources']['threads']=4;bad=tmp_path/'bad.json';bad.write_text(json.dumps(q))
    with pytest.raises(ValueError,match='Resource'):m.protocol(bad)
    with pytest.raises(ValueError,match='public'):m.private_destination(Path(__file__).parents[1]/'forbidden-output')
