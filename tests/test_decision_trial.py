import datetime as dt
import hashlib
import json
from pathlib import Path

import pytest
from decision_trial import freeze, load_trial, score, designate_primary
from score_forecast import validate_forecast_timing


def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj))


def setup(tmp_path, deadline=None):
    root=tmp_path/'model';root.mkdir();forecast=root/'forecast';forecast.mkdir()
    now=dt.datetime.now(dt.timezone.utc);deadline=deadline or now+dt.timedelta(days=2)
    model=root/'approved.joblib';model.write_bytes(b'approved')
    sha=hashlib.sha256(model.read_bytes()).hexdigest()
    write(root/'model_registry.json',{'champion':'1.0.0','versions':{'1.0.0':{'status':'approved','artifact':'approved.joblib','sha256':sha}}})
    write(forecast/'manifest.json',{'snapshot':'input','model_sha256':sha,'as_of_utc':(now-dt.timedelta(hours=1)).isoformat()})
    positions=[1,1]+[2]*5+[3]*5+[4]*3
    players=[{'id':i+1,'position':pos,'team':i%5+1,'GW':6,'expected_points':float(20-i),'last5_xp':float(i),'ewm_xp':float(i+2)} for i,pos in enumerate(positions)]
    write(forecast/'player_gameweek_predictions.json',players)
    selection={'starters':[1,3,4,5,8,9,10,11,13,14,15], 'bench_goalkeeper':2,
        'bench_outfield':[12,6,7],'captain':13,'vice_captain':8}
    state=root/'team.json';write(state,{'season':'2026/27','players':players,'screenshot_selection':selection})
    b={'events':[{'id':6,'deadline_time':deadline.isoformat(),'finished':False,'data_checked':False}],
       'game_config':{'settings':{'static_content_url':'2026_27'}}}
    write(root/'data/current/input/bootstrap.json',b);write(root/'data/current/input/fixtures.json',[])
    source=root/'prior.md';source.write_text('Previously recorded selection')
    return root,forecast,state,tmp_path/'trial',source,b,players


def make_trial(data):
    root,forecast,state,destination,source,_,_=data
    return freeze(root,forecast,state,destination,6,source)


def test_snapshot_date_does_not_prove_early_generation():
    deadline='2026-10-10T10:00:00Z'
    with pytest.raises(ValueError,match='generation must'):
        validate_forecast_timing({'as_of_utc':'2026-09-21T12:00:00Z','created_at_utc':'2026-10-11T12:00:00Z'},deadline)
    with pytest.raises(ValueError,match='Legacy'):
        validate_forecast_timing({'as_of_utc':'2026-09-21T12:00:00Z'},deadline)
    validate_forecast_timing({'as_of_utc':'2026-09-21T12:00:00Z','created_at_utc':'2026-09-21T13:00:00Z'},deadline)


def test_cannot_freeze_after_deadline(tmp_path):
    data=setup(tmp_path,dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=1))
    with pytest.raises(ValueError,match='after its deadline'):make_trial(data)
    assert not data[3].exists()


def test_freeze_verifies_default_model_and_refuses_overwrite(tmp_path):
    data=setup(tmp_path);trial=make_trial(data)
    assert trial['status']=='provisional_shadow_comparison'
    assert set(trial['selections'])=={'model','last5','ewm','preserved_pre_model_selection'}
    assert load_trial(data[3])==trial
    with pytest.raises(FileExistsError):make_trial(data)


def test_modified_frozen_selection_is_rejected(tmp_path):
    data=setup(tmp_path);make_trial(data)
    path=data[3]/'trial.json';obj=json.loads(path.read_text());obj['selections']['model']['captain']=999;write(path,obj)
    with pytest.raises(ValueError,match='integrity'):load_trial(data[3])


def test_forecast_must_match_champion(tmp_path):
    data=setup(tmp_path);path=data[1]/'manifest.json';m=json.loads(path.read_text());m['model_sha256']='different';write(path,m)
    with pytest.raises(ValueError,match='approved champion'):make_trial(data)


def test_finalised_scoring_requires_complete_matching_outcomes(tmp_path):
    data=setup(tmp_path);make_trial(data);outcome=tmp_path/'outcomes';b=data[5]
    write(outcome/'bootstrap.json',b)
    with pytest.raises(ValueError,match='not yet finished'):score(data[3],outcome)
    b['events'][0].update(finished=True,data_checked=True);write(outcome/'bootstrap.json',b)
    with pytest.raises(ValueError,match='Missing outcome'):score(data[3],outcome)
    for player in data[6]:write(outcome/f'players/{player["id"]}.json',{'history':[{'round':6,'minutes':90,'total_points':2}]})
    result=score(data[3],outcome)
    assert set(result['realised_points'].values())=={24.0}
    with pytest.raises(FileExistsError):score(data[3],outcome)


def test_wrong_season_is_rejected(tmp_path):
    data=setup(tmp_path);make_trial(data);outcome=tmp_path/'outcomes';b=data[5]
    b['game_config']['settings']['static_content_url']='2025_26';write(outcome/'bootstrap.json',b)
    with pytest.raises(ValueError,match='season'):score(data[3],outcome)


def test_primary_cannot_be_changed_to_another_run(tmp_path):
    data=setup(tmp_path);make_trial(data)
    record=designate_primary(tmp_path,data[3])
    assert record['trial']=='trial'
    with pytest.raises(FileExistsError):designate_primary(tmp_path,data[3])
