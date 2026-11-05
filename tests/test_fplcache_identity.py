import hashlib
import json
import lzma
import numpy as np
import pandas as pd
import pytest
import fplcache_identity as m


def frames():
    h = pd.DataFrame(dict(season=['2021-22']*2, GW=[1, 1], element=[1, 2], pos=[2, 3]))
    b = pd.DataFrame(dict(id=[1, 2], code=[101, 102]))
    s = pd.DataFrame(dict(id=[1, 2], code=[101, 102], element_type=[2, 3]))
    return h, b, s


def test_representation_and_id_drift_cases():
    h, b, s = frames()
    s['code'] = s.code.astype(str)
    report = m.diagnostic(h, b, s)
    assert report['id_code_mismatch_rows'] == 2 and report['int64_code_mismatch_rows'] == 0
    assert report['snapshot_code_dtype'] == 'object' and m.classify([report]) == 1
    s['code'] = [102, 101]
    s['element_type'] = [3, 2]
    report = m.diagnostic(h, b, s)
    assert report['id_code_mismatch_rows'] == 2 and report['int64_code_mismatch_rows'] == 2
    assert report['code_position_mismatch_rows'] == 0 and report['id_drift_rows'] == 2
    assert report['examples'][0] == [1, 101, 2, 101, [2, 2]] or report['examples'][0] == [1, 101, 1, 102, [2, 3]]
    assert m.classify([report]) == 2


@pytest.mark.parametrize('bad', ['duplicate', 'position', 'missing', 'fractional'])
def test_case3_records_failures_without_raising(bad):
    h, b, s = frames()
    if bad == 'duplicate':
        s.loc[1, 'code'] = 101
    if bad == 'position':
        s.loc[0, 'element_type'] = 4
    if bad == 'missing':
        b.loc[0, 'code'] = np.nan
    if bad == 'fractional':
        s['code'] = [101.5, 102.]
    report = m.diagnostic(h, b, s)
    assert m.classify([report]) == 3
    assert len(report['examples']) <= 5


def entry(tmp_path):
    payload = dict(events=[dict(total_points='NEVER_DECODE_THIS_TARGET')],
                   elements=[dict(id=1, code=101, element_type=2,
                                  chance_of_playing_next_round='NEVER_DECODE_THIS_LABEL',
                                  news='NEVER_DECODE_THIS_NEWS', nested=[dict(value='NEVER_DECODE_THIS_NESTED')])])
    raw = lzma.compress(json.dumps(payload).encode())
    p = tmp_path/'snapshot.json.xz'
    p.write_bytes(raw)
    return dict(season='2021-22', gameweek=1, status='selected', path='cache/2021/8/13/1200.json.xz',
                local_path=str(p), sha256=hashlib.sha256(raw).hexdigest(),
                blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())


def test_selective_parser_never_decodes_unselected_values(tmp_path, monkeypatch):
    e = entry(tmp_path)
    original = json.loads
    def watched(raw, *a, **kw):
        assert b'NEVER_DECODE_THIS' not in (raw.encode() if isinstance(raw, str) else raw)
        return original(raw, *a, **kw)
    monkeypatch.setattr(m.json, 'loads', watched)
    got = m.read_identities(e)
    assert got.to_dict('records') == [dict(id=1, code=101, element_type=2)]
    e['blob'] = 'wrong'
    with pytest.raises(ValueError, match='Git blob'):
        m.read_identities(e)


def test_progress_token_precedes_processing_and_totals(tmp_path, monkeypatch):
    e = entry(tmp_path)
    evidence = tmp_path/'evidence'
    evidence.mkdir()
    h, b, s = frames()
    h['points_core'] = 'NOT_SELECTED_OR_USED'
    def read(row):
        p = evidence/'diagnostic-progress/000.json'
        assert p.is_file() and json.loads(p.read_text())['path'] == e['path']
        return s
    monkeypatch.setattr(m, 'read_identities', read)
    report = m.diagnostic_loop([e], h, {'2021-22': b}, evidence)
    assert report['snapshots'] == 1 and report['case'] == 1
    assert report['overall']['history_rows'] == 2
    assert report['per_season']['2021-22']['history_rows'] == 2
    assert not report['target_columns_selected'] and not report['availability_values_decoded']


def test_integer_validation_and_forbidden_path(tmp_path):
    values, valid = m.finite_int64(['101', 102., None, 1.5, np.inf, True, 2**70])
    assert values[:2].tolist() == [101, 102] and valid.tolist() == [True, True, False, False, False, False, False]
    e = entry(tmp_path)
    e['path'] = 'cache/2026/8/1/1200.json.xz'
    with pytest.raises(ValueError, match='final'):
        m.read_identities(e)
