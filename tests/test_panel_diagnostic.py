import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from panel_diagnostic import canonical_bytes,compare_panels,panel_hash


def panels():
    return {fold:dict(first_gw=4,squads=[[
        dict(id=offset+i,position=2,team=i,price_tenths=45.,weight=1.+i)
        for i in range(1,4)] for offset in [0,10]]) for fold in ['2022-23','2023-24']}


def test_exact_and_small_weight_repr_differences():
    original=panels();same=compare_panels(original,copy.deepcopy(original))
    assert same['classification']=='A' and same['canonical_hash_equal'] and same['first_difference'] is None
    new=copy.deepcopy(original);new['2022-23']['squads'][0][0]['weight']=np.nextafter(2.,3.)
    report=compare_panels(original,new)
    assert report['classification']=='A' and report['weight']['unequal_count']==1
    assert report['weight']['compared']==12 and not report['canonical_hash_equal']
    first=report['first_difference']
    assert (first['fold'],first['squad'],first['member'],first['field'])==('2022-23',0,0,'weight')
    assert first['original']['repr']=='2.0' and '2.0000000000000004' in first['regenerated']['repr']


@pytest.mark.parametrize('change',['id','position','team','price','first_gw','squad_count','member_count','fold','member_order','squad_order','large_weight','missing_field'])
def test_every_structural_difference_is_b(change):
    original=panels();new=copy.deepcopy(original);fold=new['2022-23'];member=fold['squads'][0][0]
    if change in ['id','position','team']:member[change]+=1
    elif change=='price':member['price_tenths']=np.nextafter(45.,46.)  # Any price difference is B.
    elif change=='first_gw':fold['first_gw']=5
    elif change=='squad_count':fold['squads'].pop()
    elif change=='member_count':fold['squads'][0].pop()
    elif change=='fold':new.pop('2022-23')
    elif change=='member_order':fold['squads'][0].reverse()
    elif change=='squad_order':fold['squads'].reverse()
    elif change=='large_weight':member['weight']*=1+2e-9
    else:member.pop('price_tenths')
    report=compare_panels(original,new)
    assert report['classification']=='B'
    if change in ['member_order','squad_order']:
        assert report['folds']['2022-23']['squad_id_set_ignoring_order_equal']
    json.dumps(report,allow_nan=False)


def test_relative_boundary_zero_and_type_only():
    original=panels();original['2022-23']['squads'][0][0]['weight']=1e9
    new=copy.deepcopy(original);new['2022-23']['squads'][0][0]['weight']+=1
    assert compare_panels(original,new)['classification']=='A'  # Exactly1e-9 relative.
    new['2022-23']['squads'][0][0]['weight']+=1
    assert compare_panels(original,new)['classification']=='B'
    original['2022-23']['squads'][0][0]['weight']=0.;new=copy.deepcopy(original)
    assert compare_panels(original,new)['weight']['maximum_relative_difference']==0
    new['2022-23']['squads'][0][0]['weight']=1e-16
    report=compare_panels(original,new)
    assert report['classification']=='B' and report['weight']['maximum_relative_difference']=='Infinity'
    new=copy.deepcopy(original);new['2022-23']['squads'][0][0]['id']=1.
    report=compare_panels(original,new)
    assert report['classification']=='A' and report['type_difference_count']==1
    assert report['first_difference']['kind']=='type_only' and not report['canonical_hash_equal']


def test_nonfinite_weight_is_b_and_json_safe():
    original=panels();new=copy.deepcopy(original);new['2022-23']['squads'][0][0]['weight']=float('nan')
    report=compare_panels(original,new)
    assert report['classification']=='B' and report['weight']['invalid_count']==1
    json.dumps(report,allow_nan=False)


def worker():
    path=Path(__file__).resolve().parents[1]/'tools/diagnose_market_stage_c_panels.py'
    spec=importlib.util.spec_from_file_location('panel_diagnostic_worker',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod


def test_same_verified_i4_load_and_panels_once_no_model_or_market(tmp_path,monkeypatch):
    m=worker();original=panels();entries={};hashes={}
    for name in ['players','teams','control','provenance']:
        logical=(name+' synthetic input').encode();p=tmp_path/(name+'.gz' if name=='control' else name+'.csv')
        p.write_bytes(gzip.compress(logical) if name=='control' else logical)
        hashes[name]=hashlib.sha256(logical).hexdigest();entries[name]=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    policy={'synthetic':True};manifest=dict(panels=original,policy=policy,inputs={k:dict(sha256=v) for k,v in hashes.items()},code={},environment={'synthetic':True})
    p=tmp_path/'manifest.json';p.write_bytes(canonical_bytes(manifest))
    cfg=dict(references=dict(original_i4_panels_canonical_sha256=panel_hash(original)))
    stage_c=dict(input_panel_policy_sha256=panel_hash(policy),input_manifest_original_inputs={k:dict(sha256=v) for k,v in hashes.items()})
    calls=[];frames=[pd.DataFrame(index=range(n)) for n in [3,2,3]]
    monkeypatch.setattr(m,'qualify_i4_sources',lambda x:calls.append('qualify') or {})
    monkeypatch.setattr(m.i4,'load',lambda e:calls.append('load') or tuple(frames))
    monkeypatch.setattr(m.i4,'panels',lambda c:calls.append('panels') or original)
    import market_stage_c
    from sklearn.ensemble import HistGradientBoostingRegressor
    monkeypatch.setattr(market_stage_c,'market_rows',lambda *a,**kw:pytest.fail('No market rows authorised'))
    monkeypatch.setattr(HistGradientBoostingRegressor,'fit',lambda *a,**kw:pytest.fail('No fit authorised'))
    old,new,receipt=m.load_and_regenerate(dict(i4_manifest=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()),inputs=entries),cfg,stage_c)
    assert calls==['qualify','load','panels'] and old==new==original
    assert receipt['admitted_input_rows']==dict(players=3,teams=2,control=3)


def test_panels_persist_before_comparison_and_existing_output_never_reloads(tmp_path,monkeypatch):
    m=worker();cfg,stage_c=m.protocol();original=panels();calls=[]
    monkeypatch.setattr(m,'versions',lambda:cfg['runs'][0]['expected'])
    monkeypatch.setattr(m,'load_and_regenerate',lambda *a:calls.append('load') or (original,copy.deepcopy(original),{}))
    def compare(left,right,tolerance):
        assert (tmp_path/'panels.canonical.json').read_bytes()==canonical_bytes(right)
        return compare_panels(left,right,tolerance)
    monkeypatch.setattr(m,'compare_panels',compare)
    assert m.diagnose({},'D1',tmp_path)
    assert calls==['load'] and hashlib.sha256((tmp_path/'panels.canonical.json').read_bytes()).hexdigest()==panel_hash(original)
    assert json.loads((tmp_path/'diagnostic.json').read_text())['classification']=='A'
    with pytest.raises(ValueError,match='no retry'):m.diagnose({},'D1',tmp_path)
    assert calls==['load']


def test_cannot_load_is_class_c_and_does_not_continue(tmp_path,monkeypatch):
    m=worker();cfg,_=m.protocol();calls=[]
    monkeypatch.setattr(m,'versions',lambda:cfg['runs'][0]['expected'])
    def fail(*args):calls.append('load');raise ValueError('synthetic qualification failure')
    monkeypatch.setattr(m,'load_and_regenerate',fail)
    assert not m.diagnose({},'D1',tmp_path)
    record=json.loads((tmp_path/'diagnostic.json').read_text())
    assert calls==['load'] and record['classification']=='C' and record['phase']=='load_and_panels'
    assert not (tmp_path/'panels.canonical.json').exists()
