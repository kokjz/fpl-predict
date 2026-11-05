import hashlib
import json
import lzma
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import fplcache_availability as m
from incumbent_availability import augment as old_augment
from availability_prospective import fixed_squad as old_squads


def entry(path='cache/2025/9/12/0900.json.xz', commit='2025-09-12T09:01Z'):
    return dict(path=path, commit_time=commit)


@pytest.mark.parametrize('path,commit', [
    ('cache/2025/9/12/1000.json.xz', '2025-09-12T10:00Z'),
    ('cache/2025/9/12/0900.json.xz', '2025-09-12T10:00:01Z'),
    ('cache/2025/9/11/0959.json.xz', '2025-09-11T10:00Z'),
])
def test_selection_strict_boundaries(path, commit):
    assert m.select_snapshot([entry(path, commit)], '2025-09-12T10:00Z') is None


def test_selection_latest_clock_and_scope():
    a = entry()
    b = entry('cache/2025/9/12/0930.json.xz', '2025-09-12T09:31Z')
    assert m.select_snapshot([b, a], '2025-09-12T10:00Z') == b
    assert m.select_snapshot([entry('cache/2025/9/11/1000.json.xz', '2025-09-11T10:00Z')], '2025-09-12T10:00Z')
    with pytest.raises(ValueError, match='clock'):
        m.select_snapshot([entry(commit='2025-09-12T08:54Z')], '2025-09-12T10:00Z')
    with pytest.raises(ValueError, match='final'):
        m.path_time('cache/2026/8/1/0900.json.xz')
    with pytest.raises(ValueError, match='season'):
        m.scope(['2026-27'])


def example():
    d = pd.DataFrame(dict(season=['2025-26']*3, GW=[4]*3, element=[1, 2, 3], fixture=[1]*3,
                          fpl_code=[101, 102, 103], pos=[2]*3,
                          cutoff=pd.to_datetime(['2025-09-12T10:00Z']*3)))
    x = pd.DataFrame(1., index=d.index, columns=m.CORE_FEATURES+m.EXTRA)
    b = pd.DataFrame(dict(id=[1, 2, 3], code=[101, 102, 103]))
    o = pd.DataFrame(dict(season=['2025-26']*2, gameweek=[4]*2, fpl_code=[101, 102],
                          source_position=[2]*2, published_at=['2025-09-12T09:00Z']*2,
                          source_deadline=['2025-09-12T10:00Z']*2, chance_label=[0, None]))
    return d, x, b, o


def test_byte_parity_zero_unknown_and_key_joins():
    d, x, b, o = example()
    got, _ = m.augment(d, x, {'2025-26': b}, o)
    ref, _ = old_augment(d, x, b, o.drop(columns='season'))
    assert got[m.SIGNALS].to_numpy().tobytes() == ref[m.SIGNALS].to_numpy().tobytes()
    assert got[m.SIGNALS].to_numpy().tolist() == [[0, 0], [0, 1], [0, 1]]
    o.loc[1, 'chance_label'] = 75
    a, _ = m.augment(d, x, {'2025-26': b}, o.iloc[::-1])
    assert a.availability_chance.tolist() == [0, .75, 0]
    block = d[m.KEYS].assign(signal=[3, 4, 5])
    with pytest.raises(ValueError, match='order'):
        m.keyed_block(d, block.iloc[::-1], ['signal'])
    o.loc[0, 'source_position'] = 4
    with pytest.raises(ValueError, match='position'):
        m.augment(d, x, {'2025-26': b}, o)


@pytest.mark.parametrize('clock', ['2025-09-12T10:00Z', '2025-09-12T10:01Z'])
def test_publication_both_cutoffs(clock):
    d, x, b, o = example()
    o['published_at'] = clock
    with pytest.raises(ValueError, match='both cutoffs'):
        m.augment(d, x, {'2025-26': b}, o)


def bootstrap():
    return dict(events=[dict(id=g, is_next=g == 4, finished=False,
                             deadline_time='2025-09-12T10:00Z') for g in range(1, 39)],
                teams=[dict(id=1)], elements=[dict(id=i, code=100+i, team=1, element_type=2,
                                                  chance_of_playing_next_round=0 if i == 1 else None) for i in (1, 2)])


def test_admission_am_identity_and_hash(tmp_path):
    d, x, b, o = example()
    payload = bootstrap()
    payload['elements'].append(dict(id=99, code=999, team=1, element_type=5))
    trimmed, excluded = m.player_payload(payload)
    assert excluded == 1 and len(trimmed['elements']) == 2 and len(payload['elements']) == 3
    raw = lzma.compress(json.dumps(payload).encode())
    local = tmp_path/'snapshot.json.xz'
    local.write_bytes(raw)
    e = dict(entry(), local_path=str(local), season='2025-26', gameweek=4,
             deadline='2025-09-12T10:00Z', sha256=hashlib.sha256(raw).hexdigest(),
             blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
    report, obs = m.admit_snapshot(e, b, d)
    assert report['assistant_managers_excluded'] == 1 and report['unmatched_history_rows'] == 1
    got, _ = m.augment(d, x, {'2025-26': b}, obs)
    assert got.availability_missing.tolist() == [0, 1, 1]
    b.loc[0, 'code'] = 1000
    report, _ = m.admit_snapshot(e, b, d)
    assert report['unmatched_history_rows'] == 2  # absent stable code stays unknown
    payload['elements'][0]['element_type'] = 6
    with pytest.raises(ValueError, match='element type'):
        m.player_payload(payload)


@pytest.mark.parametrize('kind', ['drift', 'duplicate', 'position'])
def test_code_keyed_identity_remedy(tmp_path, kind):
    d, x, b, o = example()
    payload = bootstrap()
    if kind == 'drift':
        payload['elements'][0]['id'] = 91
        payload['elements'][1]['id'] = 92
    elif kind == 'duplicate':
        payload['elements'][1]['code'] = payload['elements'][0]['code']
    else:
        payload['elements'][0]['element_type'] = 4
    raw = lzma.compress(json.dumps(payload).encode())
    local = tmp_path/'remedy.json.xz'
    local.write_bytes(raw)
    e = dict(entry(), local_path=str(local), season='2025-26', gameweek=4,
             deadline='2025-09-12T10:00Z', sha256=hashlib.sha256(raw).hexdigest(),
             blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
    if kind == 'duplicate':
        with pytest.raises(ValueError):
            m.admit_snapshot(e, b, d)
    elif kind == 'position':
        with pytest.raises(ValueError, match='position mismatch'):
            m.admit_snapshot(e, b, d)
    else:
        report, obs = m.admit_snapshot(e, b, d)
        assert report['id_drift_rows'] == 2 and report['unmatched_history_rows'] == 1
        got, _ = m.augment(d, x, {'2025-26': b}, obs)
        assert got.availability_missing.tolist() == [0, 1, 1]
        assert got.availability_chance.tolist() == [0, 0, 0]


@pytest.mark.parametrize('value', [None, 1.5, np.inf, True, '1.5'])
def test_noninteger_codes_refused(value):
    with pytest.raises(ValueError):
        m.integer_codes([value])


def test_calendar_no_fixtures_and_other_missing():
    rows = pd.DataFrame([dict(season=s, GW=g, cutoff=f'{s[:4]}-08-01T10:00Z')
                         for s in m.SOURCE_SEASONS for g in range(1, 39) if (s, g) != ('2022-23', 7)])
    calendar = m.planning_calendar(rows)
    assert len(calendar) == 190
    assert [r for r in calendar if r['status'] == 'no_fixtures'] == [
        dict(season='2022-23', gameweek=7, status='no_fixtures', deadline=None)]
    with pytest.raises(ValueError, match='calendar'):
        m.planning_calendar(rows.iloc[1:])


def test_fold_masks_and_time_order():
    rows = pd.DataFrame(dict(season=['2021-22', '2022-23'],
                             ts=pd.to_datetime(['2022-05-01T12:00Z', '2022-08-01T12:00Z']),
                             cutoff=pd.to_datetime(['2022-05-01T10:00Z', '2022-08-01T10:00Z'])))
    train, test = m.fold_masks(rows, '2022-23')
    assert train.tolist() == [True, False] and test.tolist() == [False, True]
    rows.loc[0, 'ts'] = rows.loc[1, 'cutoff']-pd.Timedelta(hours=3)
    with pytest.raises(ValueError, match='cross'):
        m.fold_masks(rows, '2022-23')


def test_gate_boundaries_and_stability():
    control = {'candidate_'+u: dict(rmse=2., mae=1.) for u in ['player_gw', 'fixture']}
    candidate = {'candidate_'+u: dict(rmse=1.99, mae=1.005) for u in ['player_gw', 'fixture']}
    folds = {s: dict(control=control, conditional=candidate) for s in m.FOLDS}
    r = m.gate_table(candidate, control, folds, 0., 2.01, 2., [-.1, .1])
    assert r['passed'] and r['gate5']['descriptive']
    folds[m.FOLDS[0]] = dict(control=control, conditional={k: dict(rmse=2.01001, mae=1.) for k in candidate})
    assert not m.gate_table(candidate, control, folds, 0., 2., 2., [0., 0.])['passed']


def squad_frames():
    rows = []
    # Enough low-cost players, distinct legal teams, varying outcomes/forecasts.
    for gw in [1, 20, 21]:
        for i in range(1, 61):
            pos = 1+(i-1)//15
            rows.append(dict(season='2025-26', GW=gw, element=i, fixture=gw, fpl_code=100+i,
                             pos=pos, team_id=1+(i-1)%20, value=40., minutes=90. if i%7 else 0.,
                             total_points=float(i%9), points_core=float(i%9),
                             ts=pd.Timestamp(f'2026-01-{gw:02d}T12:00Z'),
                             cutoff=pd.Timestamp(f'2026-01-{gw:02d}T10:00Z')))
    d = pd.DataFrame(rows)
    x = pd.DataFrame(1., index=d.index, columns=m.CORE_FEATURES)
    x['n_history'], x['last5_minutes'] = 5., 90.
    mask = d.GW.ge(20)
    pred = dict(control=(d.loc[mask, 'element']%11).to_numpy(float),
                availability=(d.loc[mask, 'element']%13).to_numpy(float))
    return d, x, pred


def test_fixed_squad_replica():
    d, x, pred = squad_frames()
    old = old_squads(d, x, pred, count=3)
    new = m.fixed_squad(d, x, pred, '2025-26', 20, count=3)
    assert new['totals'] == old['totals'] and new['squad_sha256'] == old['squad_sha256']


def test_private_path_synthetic_csv_fit_ledger_aggregate_export(tmp_path):
    rng = np.random.default_rng(33)
    rows = []
    for y in range(2020, 2025):
        for i in range(64):
            playing = i%3 != 0
            rows.append(dict(season=f'{y}-{str(y+1)[-2:]}', GW=10+i%2, element=i+1, fixture=i+1,
                             fpl_code=i+101, pos=1+i%4, ts=f'{y+1}-01-01T12:00Z',
                             cutoff=f'{y+1}-01-01T10:00Z', played=float(playing), minutes=90. if playing else 0.,
                             sixty=float(playing), dc_hit=np.nan, yellow_cards=0., red_cards=0.,
                             points_core=float(i%7) if playing else 0., total_points=float(i%7) if playing else 0.))
    d = pd.DataFrame(rows)
    x = pd.DataFrame(rng.random((len(d), len(m.CORE_FEATURES+m.EXTRA))), columns=m.CORE_FEATURES+m.EXTRA)
    x['n_history'], x['last5_minutes'] = 5., 90.
    control = pd.concat([d, x[m.CORE_FEATURES]], axis=1)
    path = tmp_path/'control.csv'
    control.to_csv(path, index=False)
    control = pd.read_csv(path)
    for frame in [d, control]:
        for n in ['ts', 'cutoff']:
            frame[n] = frame[n].map(m.utc)
    bridges = {s: pd.DataFrame(dict(id=range(1, 65), code=range(101, 165))) for s in d.season.unique()}
    attached, features = m.attach_loader(control.drop(columns=['played', 'sixty', 'dc_hit', 'yellow_cards', 'red_cards']), d, x, bridges)
    o = pd.DataFrame([dict(season=s, gameweek=g, fpl_code=i+101, source_position=1+i%4,
                           published_at=f'{int(s[:4])+1}-01-01T09:00Z', source_deadline=f'{int(s[:4])+1}-01-01T10:00Z',
                           chance_label=0. if i%3 == 0 else 75.)
                      for s in m.SOURCE_SEASONS[:-1] for g in [10, 11] for i in range(64)])
    augmented, _ = m.augment(attached, features, bridges, o)
    assert augmented[m.CORE_FEATURES].to_numpy().tobytes() == control[m.CORE_FEATURES].to_numpy().tobytes()
    parts = []
    for season in m.FOLDS:
        _, test = m.fold_masks(attached, season)
        block = attached.loc[test, m.KEYS].copy()
        for arm in m.ARMS:
            token = m.ledger_attempt(tmp_path/'ledger', season, arm)
            pred, receipt = m.fit(attached, augmented, season, arm)
            assert receipt['test_rows'] == 64 and pred.dc_xp.eq(0).all()
            block[arm] = pred.core_xp.to_numpy()
            token.write_text(json.dumps(dict(status='completed')))
        parts.append(block)
    test = attached.season.isin(m.FOLDS)
    report = m.aggregate(attached.loc[test], augmented.loc[test], pd.concat(parts))
    target = tmp_path/'aggregate.json'
    target.write_text(json.dumps(report, allow_nan=False))
    assert json.loads(target.read_text())['pooled']['conditional']['candidate_fixture']['n'] == 192
    with pytest.raises(FileExistsError):
        m.ledger_attempt(tmp_path/'ledger', m.FOLDS[-1], m.ARMS[-1])
