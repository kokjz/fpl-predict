import hashlib
import json
import lzma

import numpy as np
import pandas as pd
import pytest

import phase2_execution as m
from conditional_forecaster import ConditionalForecaster
from test_fplcache_availability import example
from incumbent_availability import augment as incumbent_augment


class Constant:
    def __init__(self, value):
        self.value = value

    def predict(self, x):
        return np.full(len(x), self.value, dtype=float)


def models():
    return Constant(2.), ConditionalForecaster(Constant(3.), Constant(.9), Constant(70.),
        Constant(.8), Constant(.4), 0., 0., {}, {})


def synthetic(tmp_path):
    season = '2026-27'
    clock = {g: pd.Timestamp('2026-08-01T10:00Z')+pd.Timedelta(weeks=g) for g in range(1, 39)}
    played_weeks = [1, 2, 3, 10, *range(12, 21)]
    calendar = [dict(season=season, gameweek=g, deadline=clock[g].isoformat(),
                     status='planned' if g in played_weeks else 'no_fixtures') for g in range(1, 39)]
    rows = []
    for gw in played_weeks:
        for fixture in ([gw*10, gw*10+1] if gw == 12 else [gw*10]):
            for i in range(1, 61):
                rows.append(dict(season=season, GW=gw, element=i, fixture=fixture,
                    position={1:'GK', 2:'DEF', 3:'MID', 4:'FWD'}[1+(i-1)//15],
                    team_id=1+(i-1)%20, opponent_team=1+i%20, value=40,
                    was_home=True, team_gf=1, team_ga=1, kickoff_time=(clock[gw]+pd.Timedelta(hours=2)).isoformat(),
                    minutes=90 if i%7 else 0, total_points=i%9 if i%7 else 0,
                    defensive_contribution=0., goals_scored=0., assists=0., clean_sheets=0.,
                    bonus=0., bps=0., threat=0., creativity=0., saves=0.,
                    expected_goals=.1, expected_assists=.05, expected_goals_conceded=1.))
    frame = pd.DataFrame(rows)
    bridge = pd.DataFrame(dict(id=range(1, 61), code=range(10001, 10061)))
    expected = frame[['season', 'fixture', 'element']].merge(bridge, left_on='element', right_on='id').rename(columns={'code':'fpl_code'})[m.KEYS]
    def bootstrap(gw):
        return dict(events=[dict(id=g, is_next=g==gw, finished=False, deadline_time=clock[g].isoformat()) for g in range(1, 39)],
            teams=[dict(id=i) for i in range(1, 21)],
            elements=[dict(id=i+1000, code=i+10000, team=1+(i-1)%20, element_type=1+(i-1)//15,
                           chance_of_playing_next_round=75) for i in range(1, 61)])
    gw = 10
    columns = ['timestamp','season','gameweek','player_id','opta_code','position','news','chance_of_playing_next_round','return_gameweek']
    content = [','.join(columns)]
    for i in range(1, 61):
        pos = ['GK','DEF','MID','FWD'][(i-1)//15]
        content.append(f'opaque-capture,2627,10,{i+1000},p{i+10000},{pos},,75,')
    raw = ('\n'.join(content)+'\n').encode()
    proof = dict(gameweek=gw, deadline=clock[gw].isoformat(), published_at=(clock[gw]-pd.Timedelta(hours=1)).isoformat(),
                 commit='a'*40, size=len(raw), git_blob_sha1=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
    primary = {(season, gw): [(raw, proof, bootstrap(gw))]}
    gw = 12
    stamp = clock[gw]-pd.Timedelta(hours=1)
    raw = lzma.compress(json.dumps(bootstrap(gw)).encode())
    local = tmp_path/'fallback.json.xz'
    local.write_bytes(raw)
    entry = dict(season=season, gameweek=gw, path=f'cache/{stamp.year}/{stamp.month}/{stamp.day}/{stamp:%H%M}.json.xz',
        commit_time=stamp.isoformat(), deadline=clock[gw].isoformat(), local_path=str(local),
        sha256=hashlib.sha256(raw).hexdigest(), blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
    return frame, {season:bridge}, calendar, expected, primary, [entry]


def test_season_path_refusal_before_io(tmp_path):
    with pytest.raises(ValueError, match='Season'):
        m.scope(['2026-27'])
    with pytest.raises(ValueError, match='path'):
        m.checked_path(tmp_path/'2026-27'/'never-opened', '2025-26')
    with pytest.raises(ValueError, match='Season'):
        m.admit_snapshot(dict(season='2026-27'), None, None)
    with pytest.raises(ValueError, match='Season'):
        m.score(None, None, None, None, None, None, None, None, None, None, None, evidence_root=tmp_path)


def test_historical_signals_and_code_identity():
    d, x, bridge, obs = example()
    got, coverage = m.augment(d, x, {'2025-26':bridge}, obs)
    old, _ = incumbent_augment(d, x, bridge, obs.drop(columns='season'))
    assert got[m.SIGNALS].to_numpy().tobytes() == old[m.SIGNALS].to_numpy().tobytes()
    assert coverage[0]['matched'] == 2
    # Source IDs can drift; the code is the only join key.
    obs['element'] = [900, 901]
    drift, _ = m.augment(d, x, {'2025-26':bridge}, obs)
    assert drift.equals(got)
    obs.loc[0, 'source_position'] = 4
    with pytest.raises(ValueError, match='position'):
        m.augment(d, x, {'2025-26':bridge}, obs)


def test_selection_historical_strict_parity():
    from fplcache_availability import select_snapshot
    entries = [dict(path='cache/2025/9/12/0900.json.xz', commit_time='2025-09-12T09:01Z')]
    assert m.select_snapshot(entries, '2025-09-12T10:00Z') == select_snapshot(entries, '2025-09-12T10:00Z')
    assert m.select_snapshot(entries, '2025-09-12T09:01Z') is None
    with pytest.raises(ValueError, match='Deadline refused'):
        m.select_snapshot([], '2026-08-01T10:00Z')


def test_outcome_calendar_missing_cutoff_and_supplied_mismatch(tmp_path):
    frame, bridges, calendar, expected, _, _ = synthetic(tmp_path)
    assert 'cutoff' not in frame and frame.GW.nunique() > 1
    admitted = m.admit_outcomes(frame, bridges, calendar, expected, phase2_authorised=True)
    clocks = {r['gameweek']:m.utc(r['deadline']) for r in calendar}
    assert admitted.cutoff.tolist() == [clocks[g] for g in admitted.GW]
    supplied = frame.copy()
    supplied['cutoff'] = supplied.GW.map(clocks)
    assert m.admit_outcomes(supplied, bridges, calendar, expected, phase2_authorised=True).cutoff.equals(admitted.cutoff)
    supplied.loc[supplied.index[-1], 'cutoff'] += pd.Timedelta(seconds=1)
    with pytest.raises(ValueError, match='Outcome deadline mismatch'):
        m.admit_outcomes(supplied, bridges, calendar, expected, phase2_authorised=True)


def test_a3_full_forecasts_and_missing_head():
    conditional = pd.DataFrame(dict(core_xp=[2., 4.], expected_points=[3., 6.]))
    core, full = m.forecasts([4., 2.], conditional)
    assert core['blend_equal'].tolist() == [3., 3.]
    assert full['control'].tolist() == [4., 2.]
    assert full['conditional'].tolist() == [3., 6.]
    assert full['blend_equal'].tolist() == [3.5, 4.]
    with pytest.raises(ValueError, match='expected_points'):
        m.forecasts([4., 2.], conditional.drop(columns='expected_points'))


@pytest.mark.parametrize('primary,blend,eligible', [(True,True,'conditional'), (True,False,'conditional'),
                                                  (False,True,'blend_equal'), (False,False,None)])
def test_decision_priority(primary, blend, eligible):
    assert m.decision(dict(conditional=dict(passed=primary), blend_equal=dict(passed=blend))) == eligible


def test_synthetic_end_to_end_and_canary_refusal(tmp_path):
    frame, bridges, calendar, expected, primary, snapshots = synthetic(tmp_path)
    control, conditional = models()
    cr = pd.DataFrame(dict(season=['2025-26'], fixture=[1], fpl_code=[101], pos=[2]))
    cx = pd.DataFrame(1., index=cr.index, columns=list(dict.fromkeys(m.CORE_FEATURES+m.DC_FEATURES+m.SIGNALS)))
    cx[m.SIGNALS] = [0., 1.]
    canary = m.prediction_hashes(cr, cx, control, conditional)
    bad = dict(canary, key_sha256='0'*64)
    with pytest.raises(ValueError, match='Canary'):
        m.score(frame, bridges, calendar, expected, primary, snapshots, control, conditional, cr, cx, bad,
                evidence_root=tmp_path/'refused', phase2_authorised=True)
    assert not (tmp_path/'refused').exists()
    before = {p.resolve() for p in tmp_path.rglob('*') if p.is_file()}
    report = m.score(frame, bridges, calendar, expected, primary, snapshots, control, conditional, cr, cx, canary,
                     evidence_root=tmp_path/'evidence', phase2_authorised=True)
    assert {p.resolve() for p in tmp_path.rglob('*') if p.is_file()}-before == {(tmp_path/'evidence/phase2-report.json').resolve()}
    assert json.loads((tmp_path/'evidence/phase2-report.json').read_text()) == report
    assert set(report['gates']) == {'conditional', 'blend_equal'}
    assert all(set(g['criteria']) == {'2','3','4','6','7'} and g['gate5']['descriptive'] for g in report['gates'].values())
    assert report['candidates_tested'] == 2 and not report['automatic_promotion']
    assert report['fixed_squads']['count'] == 20
    assert len(report['fixed_squads']['totals']['control']) == 20
    sources = {r['gameweek']:r for r in report['sources']}
    assert sources[10]['source'] == 'AIrsenal' and sources[10]['known_rows'] == 60
    assert sources[11]['source'] == 'no_fixtures'
    assert sources[12]['source'] == 'fplcache fallback' and sources[12]['known_rows'] == 120
    assert sources[13]['source'] == 'none' and sources[13]['unmatched_rows'] == 60
    # Position disagreement is a stop, including code matches across ID drift.
    admitted = m.admit_outcomes(frame, bridges, calendar, expected, phase2_authorised=True)
    raw, proof, bootstrap = primary[('2026-27',10)][0]
    bad_bootstrap = json.loads(json.dumps(bootstrap))
    bad_bootstrap['elements'][0]['element_type'] = 4
    with pytest.raises(ValueError, match='position'):
        m.choose_sources(calendar, {('2026-27',10):[(raw,proof,bad_bootstrap)]}, snapshots,
                         bridges, admitted, phase2_authorised=True)
    with pytest.raises(ValueError, match='keys'):
        m.admit_outcomes(frame.iloc[1:], bridges, calendar, expected, phase2_authorised=True)


def test_official_event_live_double_fixture_universe():
    rows = pd.DataFrame(dict(season=['2025-26']*2, GW=[20]*2, element=[1]*2, fixture=[100,101], pos=[2]*2))
    fixture = lambda ident, points: dict(fixture=ident, stats=[dict(identifier='minutes', value=90, points=2),
                                                            dict(identifier='bonus', value=points, points=points)])
    payload = {('2025-26',20):dict(elements=[dict(id=1, stats=dict(total_points=999), explain=[fixture(100,1),fixture(101,3)])])}
    result = m.official_outcomes(payload, rows)
    assert result.total_points.tolist() == [3,5] and result.minutes.tolist() == [90,90]
    with pytest.raises(ValueError, match='coverage'):
        m.official_outcomes(payload, rows.iloc[:1])
