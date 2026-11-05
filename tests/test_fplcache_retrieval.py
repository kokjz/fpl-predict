import copy
import hashlib
import json
from pathlib import Path

import pytest
import fplcache_retrieval as m


def partial(tmp_path):
    raw = b'unchanged retained bytes'
    old = tmp_path/'retained.json.xz'
    old.write_bytes(raw)
    row = dict(season='2021-22', gameweek=1, status='selected',
               path='cache/2021/8/13/1200.json.xz', adding_commit='a'*40,
               commit_time='2021-08-13T12:01:00Z', path_time='2021-08-13T12:00:00+00:00',
               deadline='2021-08-13T17:30:00Z', local_path=str(old), bytes=len(raw),
               blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
               sha256=hashlib.sha256(raw).hexdigest())
    ledger = dict(status='running', listing_revision='b'*40, metadata_requests=167, downloads=54,
                  total_bytes=len(raw), retries=0, re_selections=1, selected=[row])
    calendar = [dict(season='2021-22', gameweek=g, status='planned', deadline='2021-08-13T17:30:00Z')
                for g in [1, 2, 3]]
    output = tmp_path/'resume'
    output.mkdir()
    for name in ['retrieval.json', 'network.jsonl']:
        (output/name).touch()
    (output/'snapshots').mkdir()
    (output/'snapshots/054.json.xz').touch()
    evidence = tmp_path/'handover-active'
    evidence.mkdir()
    return ledger, [dict(row, kind='snapshot')], calendar, output, evidence


def test_resume_never_repeats_or_resets_partial_ledger(tmp_path, monkeypatch):
    args = partial(tmp_path)
    ledger, receipts, calendar, output, evidence = args
    before = copy.deepcopy(ledger)
    retained_bytes = Path(ledger['selected'][0]['local_path']).read_bytes()
    driver = m.Continuation(*args)
    visited = []
    def one(planned):
        assert m.key(planned) not in [m.key(r) for r in before['selected']]
        visited.append(m.key(planned))
        driver.state['metadata_requests'] += 3
        driver.state['downloads'] += 1
        driver.state['total_bytes'] += 100
        return dict(planned, status='selected')
    monkeypatch.setattr(driver, 'select_one', one)
    driver.run()
    result = json.loads((output/'retrieval.json').read_text())
    assert visited == [('2021-22', 2), ('2021-22', 3)]
    assert result['metadata_requests'] == 173 and result['downloads'] == 56
    assert result['re_selections'] == 1 and result['total_bytes'] == before['total_bytes']+200
    assert result['selected'][0] == before['selected'][0] and ledger == before
    assert Path(ledger['selected'][0]['local_path']).read_bytes() == retained_bytes
    assert result['after_resume']['metadata_requests'] == 6
    assert (evidence/'resume-retained-verification.json').is_file()
    with pytest.raises(ValueError, match='Fresh'):
        m.Continuation(*args)


def test_corruption_refused_before_any_network(tmp_path, monkeypatch):
    args = partial(tmp_path)
    Path(args[0]['selected'][0]['local_path']).write_bytes(b'corrupt')
    def never(*a, **k):
        raise AssertionError('Network must not run')
    monkeypatch.setattr(m.subprocess, 'run', never)
    with pytest.raises(ValueError, match='size'):
        m.Continuation(*args)


def test_receipt_or_calendar_conflict_refused(tmp_path):
    ledger, receipts, calendar, output, evidence = partial(tmp_path)
    receipts[0]['blob'] = 'wrong'
    with pytest.raises(ValueError, match='receipt differs'):
        m.Continuation(ledger, receipts, calendar, output, evidence)
    receipts[0]['blob'] = ledger['selected'][0]['blob']
    calendar.reverse()
    with pytest.raises(ValueError, match='calendar prefix'):
        m.Continuation(ledger, receipts, calendar, output, evidence)


def test_cumulative_budget_and_existing_slot_are_refused(tmp_path, monkeypatch):
    driver = m.Continuation(*partial(tmp_path))
    driver.state['metadata_requests'] = 600
    def never(*a, **k):
        raise AssertionError('No request beyond budget')
    monkeypatch.setattr(m.subprocess, 'run', never)
    with pytest.raises(ValueError, match='budget'):
        driver.api('never')
    slot = driver.output/'snapshots/054.json.xz'
    slot.write_bytes(b'preserved')
    entry = dict(adding_commit='a'*40, path='cache/2021/8/20/1200.json.xz')
    with pytest.raises(ValueError, match='Fresh'):
        driver.download(entry)
    assert driver.state['downloads'] == 54 and slot.read_bytes() == b'preserved'


def test_future_calendar_refused_before_transport(tmp_path, monkeypatch):
    args = partial(tmp_path)
    args[2][-1]['season'] = '2026-27'
    def never(*a, **k):
        raise AssertionError('Forbidden calendar must not reach transport')
    monkeypatch.setattr(m.subprocess, 'run', never)
    with pytest.raises(ValueError, match='season refused'):
        m.Continuation(*args)
