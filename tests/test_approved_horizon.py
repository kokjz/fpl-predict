"""Synthetic approved-artifact/receipt admission; no real squad or model fit."""
import copy
import datetime as dt
import hashlib
import json
from dataclasses import replace
import joblib
import pandas as pd
import pytest
import approved_horizon as bridge
from forecast_sensitivity import apply_sensitivity,sensitivity_factor
from fpl_model import normalise
from season_engine import Market
from test_model import tiny


class Model:
    def __init__(self,version='synthetic-v1'):self.metadata={'version':version}
    def predict(self,x,pos):
        return pd.DataFrame(dict(core_xp=3.,dc_xp=.2,expected_points=3.2,
            expected_minutes=60.,p_play=.8,p60=.7),index=x.index)


def setup(tmp_path,monkeypatch):
    root=tmp_path/'models';root.mkdir();artifact=root/'artifact.joblib';joblib.dump(Model(),artifact)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    registry=dict(champion='synthetic-v1',versions={'synthetic-v1':dict(status='approved',
        artifact='artifact.joblib',sha256=digest(artifact))})
    (root/'model_registry.json').write_text(json.dumps(registry))
    monkeypatch.setattr(bridge,'now_utc',lambda:dt.datetime(2026,1,1,tzinfo=dt.timezone.utc))
    receipt=tmp_path/'observation.json';bridge.observe_approved(root,receipt)
    market=Market.create('2026-27',30,'2027-03-01T12:00Z','2027-03-01T11:00Z',[
        dict(id=1,position=2,team='1',price_tenths=50,can_buy=True),
        dict(id=2,position=4,team='2',price_tenths=50,can_buy=True)])
    fixtures=pd.DataFrame([dict(id=i,event=g,team_h=1,team_a=2,kickoff_time='2027-03-01T13:00Z')
        for i,g in [(1,30),(2,32),(3,32)]])
    history=normalise(tiny())
    kwargs=dict(through=32,receipt_path=receipt,receipt_sha256=digest(receipt),source_as_of=market.as_of)
    return root,history,market,fixtures,kwargs


def review(market):
    document=dict(schema_version=1,GW=30,recorded_at_utc='2027-03-01T10:30Z',players=[dict(
        id=1,minutes=30.,availability=.5,reason='Synthetic sensitivity assumption',source_url='https://example.org/team-news',
        published_at_utc='2027-03-01T09:00Z',checked_at_utc='2027-03-01T10:00Z')])
    bootstrap=dict(events=[dict(id=30,is_next=True,deadline_time=market.deadline)],elements=[dict(id=1),dict(id=2)])
    return dict(review=document,bootstrap=bootstrap,bootstrap_as_of='2027-03-01T10:00Z')


def test_approved_receipt_blank_double_and_current_only_manual_sensitivity(tmp_path,monkeypatch):
    root,history,m,f,k=setup(tmp_path,monkeypatch)
    base,report=bridge.project_approved(root,history,m,f,**k)
    assert report['champion']=='synthetic-v1' and base.values()[30,1]==3.2
    assert base.values()[31,1]==0 and base.values()[32,1]==6.4
    adjusted,r=bridge.project_approved(root,history,m,f,**k,**review(m))
    assert adjusted.values()[30,1]==pytest.approx(.8)
    assert adjusted.values()[32,1]==base.values()[32,1] and adjusted.values()[30,2]==3.2
    assert r['review_gameweek']==30 and r['source_max_ts'] is None
    assert 'availability_review_canonical_json' in adjusted.provenance['source_hashes']
    with pytest.raises(FileExistsError):bridge.observe_approved(root,k['receipt_path'])


@pytest.mark.parametrize('damage',['receipt_hash','artifact_hash','unapproved','late_receipt','late_source','late_bootstrap','late_review','wrong_gw'])
def test_invalid_identity_and_clocks_fail_before_artifact_deserialisation(tmp_path,monkeypatch,damage):
    root,h,m,f,k=setup(tmp_path,monkeypatch);extra={}
    if damage=='receipt_hash':k['receipt_sha256']='0'*64
    elif damage in ('artifact_hash','unapproved'):
        p=root/'model_registry.json';r=json.loads(p.read_text())
        r['versions']['synthetic-v1']['sha256' if damage=='artifact_hash' else 'status']='0'*64 if damage=='artifact_hash' else 'candidate'
        p.write_text(json.dumps(r))
    elif damage=='late_receipt':
        p=k['receipt_path'];r=json.loads(p.read_text());r['observed_at_utc']=m.as_of;p.write_text(json.dumps(r));k['receipt_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    elif damage=='late_source':k['source_as_of']='2027-03-01T11:30Z'
    else:
        extra=review(m)
        if damage=='late_bootstrap':extra['bootstrap_as_of']='2027-03-01T11:30Z'
        elif damage=='late_review':extra['review']['recorded_at_utc']='2027-03-01T11:30Z'
        else:extra['review']['GW']=31
    monkeypatch.setattr(bridge.joblib,'load',lambda *a,**kw:pytest.fail('Invalid source admitted before loading'))
    with pytest.raises(ValueError):bridge.project_approved(root,h,m,f,**k,**extra)


def test_artifact_metadata_version_and_backcast_are_rejected(tmp_path,monkeypatch):
    root,h,m,f,k=setup(tmp_path,monkeypatch);artifact=root/'artifact.joblib'
    joblib.dump(Model('wrong'),artifact);p=root/'model_registry.json';r=json.loads(p.read_text());sha=hashlib.sha256(artifact.read_bytes()).hexdigest();r['versions']['synthetic-v1']['sha256']=sha;p.write_text(json.dumps(r))
    p=k['receipt_path'];receipt=json.loads(p.read_text());receipt['artifact_sha256']=sha;p.write_text(json.dumps(receipt));k['receipt_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='version'):bridge.project_approved(root,h,m,f,**k)
    old=replace(m,as_of='2025-03-01T11:00Z',deadline='2025-03-01T12:00Z')
    with pytest.raises(ValueError,match='Late'):bridge.project_approved(root,h,old,f,**k)


def test_sensitivity_preserves_explicit_scaling_and_probability_caps():
    source=dict(core_xp=3.,dc_xp=.2,expected_points=3.2,expected_minutes=60.,p_play=.8,p60=.7)
    assert apply_sensitivity(source,{})==source  # no automatic p_play multiplier
    assert sensitivity_factor(source,dict(minutes=30.,availability=.5))==.25
    value=apply_sensitivity(source,dict(minutes=30.,availability=.5))
    assert value['expected_points']==pytest.approx(.8) and value['expected_minutes']==15.
    assert source['expected_points']==3.2
    assert apply_sensitivity(source,dict(minutes=0.))['expected_points']==0.
    capped=apply_sensitivity(dict(source,dc_xp=2.,expected_minutes=10.),dict(minutes=90.))
    assert capped['p_play']==capped['p60']==1. and capped['expected_minutes']==90. and capped['dc_xp']==2.
    for change in [dict(minutes=91),dict(availability=float('nan'))]:
        with pytest.raises(ValueError):apply_sensitivity(source,change)
