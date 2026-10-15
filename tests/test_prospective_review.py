import datetime as dt
import json

import pytest

import decision_trial as trials
from test_decision_trial import setup,make_trial,write


def finalised(tmp_path,monkeypatch,baseline='ewm'):
    data=setup(tmp_path);make_trial(data)
    trials.designate_primary(tmp_path,data[3],baseline)
    advanced=dt.datetime.fromisoformat(data[5]['events'][0]['deadline_time'])+dt.timedelta(days=2)
    class FutureClock(dt.datetime):
        @classmethod
        def now(cls,tz=None):return advanced
    monkeypatch.setattr(trials.dt,'datetime',FutureClock)
    outcome=tmp_path/'final-outcome';b=data[5];b['events'][0].update(finished=True,data_checked=True)
    write(outcome/'bootstrap.json',b)
    for p in data[6]:write(outcome/f'players/{p["id"]}.json',{'history':[{'round':6,'minutes':90,'total_points':2}]})
    trials.score(data[3],outcome)
    return data,outcome


def test_primary_pair_is_fixed_and_cannot_be_replaced(tmp_path):
    data=setup(tmp_path);make_trial(data)
    record=trials.designate_primary(tmp_path,data[3],'ewm')
    assert record['primary_baseline']=='ewm'
    with pytest.raises(FileExistsError):trials.designate_primary(tmp_path,data[3],'last5')


def test_review_recomputes_from_frozen_sources_without_writes(tmp_path,monkeypatch):
    data,_=finalised(tmp_path,monkeypatch)
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*.json')}
    report=trials.review_primaries(tmp_path)
    assert report['groups'][0]['n']==1 and report['groups'][0]['baseline']=='ewm'
    assert report['groups'][0]['total_point_delta']==0
    assert not report['groups'][0]['initial_review_ready'] and not report['model_promotion']
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*.json')}


def test_legacy_primary_never_gets_a_retrospective_baseline(tmp_path,monkeypatch):
    finalised(tmp_path,monkeypatch,baseline=None)
    report=trials.review_primaries(tmp_path)
    assert not report['groups'] and report['pending'][0]['reason']=='legacy_or_unknown_primary_baseline'


def test_tampered_saved_points_are_not_trusted(tmp_path,monkeypatch):
    data,_=finalised(tmp_path,monkeypatch)
    path=next(data[3].glob('outcome_*.json'));d=json.loads(path.read_text());d['realised_points']['model']+=100
    write(path,d)
    with pytest.raises(ValueError,match='re-score'):trials.review_primaries(tmp_path)


def test_multiple_corrections_are_not_selected_by_the_best_score(tmp_path,monkeypatch):
    data,_=finalised(tmp_path,monkeypatch)
    path=next(data[3].glob('outcome_*.json'));(data[3]/'outcome_correction.json').write_bytes(path.read_bytes())
    report=trials.review_primaries(tmp_path)
    assert not report['groups'] and 'multiple_revisions' in report['pending'][0]['reason']


def test_eight_contiguous_weeks_is_only_descriptive_and_gaps_stay_missing():
    records=[dict(gameweek=i,delta=2.) for i in range(1,9)]
    report=trials.point_uncertainty(records)
    assert report['status']=='descriptive_interval' and report['lower']==report['upper']==2.
    assert trials.point_uncertainty(records[:7])['status']=='insufficient_contiguous_weeks'
    gapped=[dict(gameweek=i,delta=2.) for i in [1,2,3,4,6,7,8,9]]
    assert trials.point_uncertainty(gapped)['status']=='insufficient_contiguous_weeks'
