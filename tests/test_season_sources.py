import hashlib,lzma
import pytest
from season_sources import calendar,COLUMNS


def source(tmp_path,raw=None):
    raw=raw or b'id,event,team_h,team_a,kickoff_time,total_points\n1,2,1,2,2025-08-20T12:00Z,999\n'
    p=tmp_path/'base.csv.xz';p.write_bytes(lzma.compress(raw))
    return dict(file=p.name,compressed_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),sha256=hashlib.sha256(raw).hexdigest(),publication_claim='2025-08-01T00:00Z',captured_at='2025-08-02T00:00Z')


def test_calendar_whitelist_and_outcome_mutation(tmp_path):
    e=source(tmp_path);a=calendar(e,tmp_path);assert list(a)==COLUMNS
    e=source(tmp_path,b'id,event,team_h,team_a,kickoff_time,total_points\n1,2,1,2,2025-08-20T12:00Z,-999\n')
    assert a.equals(calendar(e,tmp_path))


def test_calendar_cutoff_hash_and_escape_fail(tmp_path):
    e=source(tmp_path);e['publication_claim']=e['captured_at']
    with pytest.raises(ValueError,match='before origin'):calendar(e,tmp_path)
    e=source(tmp_path);e['sha256']='invalid'
    with pytest.raises(ValueError,match='content hash'):calendar(e,tmp_path)
    e['file']='../escape.csv.xz'
    with pytest.raises(ValueError,match='escapes'):calendar(e,tmp_path)


def test_calendar_unknown_event_allowed_duplicate_fixture_rejected(tmp_path):
    e=source(tmp_path,b'id,event,team_h,team_a,kickoff_time\n1,,1,2,\n');assert calendar(e,tmp_path).event.isna().all()
    e=source(tmp_path,b'id,event,team_h,team_a,kickoff_time\n1,2,1,2,\n1,3,1,2,\n')
    with pytest.raises(ValueError,match='identity'):calendar(e,tmp_path)


def test_audit_result_fields_never_enter_default_calendar(tmp_path):
    raw=b'id,event,team_h,team_a,kickoff_time,finished,started,team_h_score,team_a_score\n1,2,1,2,2025-08-20T12:00Z,False,False,,\n'
    e=source(tmp_path,raw);f=calendar(e,tmp_path,audit_only=True)
    assert 'finished' in f and 'finished' not in calendar(e,tmp_path)


def test_future_results_reject_a_calendar_as_historical_evidence(tmp_path):
    from deadline_provenance import replay_event_assignments
    raw=b'id,event,team_h,team_a,kickoff_time,finished,started,team_h_score,team_a_score\n1,2,1,2,2025-08-20T12:00Z,True,True,2,1\n'
    e=source(tmp_path,raw);f=calendar(e,tmp_path,audit_only=True)
    with pytest.raises(ValueError,match='future results'):replay_event_assignments(f,e['publication_claim'],[],e['captured_at'])
