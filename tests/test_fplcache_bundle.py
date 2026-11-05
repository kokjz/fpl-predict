import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import fplcache_availability as study
import fplcache_bundle as io


def provenance(root, season, arm, rows):
    root.mkdir(parents=True, exist_ok=True)
    result = root/'result.json'
    result.write_text(json.dumps(dict(status='completed', season=season, arm=arm, test_rows=len(rows))))
    ordinal = [(s, a) for s in study.FOLDS for a in study.ARMS].index((season, arm))
    ledger = root/f'{ordinal:02d}.json'
    ledger.write_text(json.dumps(dict(status='completed', receipt_sha256=io.file_sha256(result))))
    return result, ledger


def small():
    rows = pd.DataFrame(dict(season=['2022-23']*2, fixture=[1, 2], fpl_code=[101, 102]), index=[10, 20])
    pred = pd.DataFrame(dict(core_xp=[2., 3.], expected_points=[2., 3.]), index=rows.index)
    return rows, pred


def test_future_fit_writer_roundtrip_without_pickle(tmp_path):
    rows, pred = small()
    path = tmp_path/'future.npz'
    io.write_fit_bundle(path, rows, pred)
    with np.load(path, allow_pickle=False) as z:
        assert z['season'].dtype.kind == 'U' and z['season'].tolist() == rows.season.tolist()
        for name in z.files:
            assert not z[name].dtype.hasobject
    result, ledger = provenance(tmp_path, '2022-23', 'control', rows)
    got, proof = io.read_aggregate_bundle(path, io.file_sha256(path), '2022-23', 'control', result, ledger, rows)
    np.testing.assert_array_equal(got['core_xp'], pred.core_xp)
    assert proof['ordered_keys_validated'] and not proof['season_array_loaded']
    with pytest.raises(FileExistsError):
        io.write_fit_bundle(path, rows, pred)


def test_legacy_object_season_is_never_loaded(tmp_path, monkeypatch):
    rows, pred = small()
    path = tmp_path/'legacy.npz'
    np.savez_compressed(path, season=np.array(rows.season, dtype=object), fixture=rows.fixture.to_numpy(),
                        fpl_code=rows.fpl_code.to_numpy(), core_xp=pred.core_xp.to_numpy(), expected_points=pred.expected_points.to_numpy())
    result, ledger = provenance(tmp_path, '2022-23', 'control', rows)
    original = np.load
    class NumericOnly:
        def __init__(self, actual):
            self.actual = actual
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.actual.close()
        def __getitem__(self, key):
            assert key != 'season', 'Historical season payload must not be decoded'
            return self.actual[key]
    def safe(path, **kwargs):
        assert kwargs == dict(allow_pickle=False)
        return NumericOnly(original(path, **kwargs))
    monkeypatch.setattr(io.np, 'load', safe)
    got, proof = io.read_aggregate_bundle(path, io.file_sha256(path), '2022-23', 'control', result, ledger, rows)
    assert got['core_xp'].tolist() == [2., 3.] and proof['season_from_ledger'] == '2022-23'
    assert 'authenticated' in proof['ledger_season_source']


@pytest.mark.parametrize('bad', ['hash', 'result_season', 'ledger_season', 'binding', 'keys'])
def test_provenance_and_key_failures_stop(tmp_path, bad):
    rows, pred = small()
    path = tmp_path/'data.npz'
    io.write_fit_bundle(path, rows.iloc[::-1] if bad == 'keys' else rows, pred.iloc[::-1] if bad == 'keys' else pred)
    result, ledger = provenance(tmp_path, '2022-23', 'control', rows)
    digest = io.file_sha256(path)
    if bad == 'hash':
        digest = '0'*64
    if bad == 'result_season':
        data = json.loads(result.read_text());data['season'] = '2023-24';result.write_text(json.dumps(data))
        ledger.write_text(json.dumps(dict(status='completed', receipt_sha256=io.file_sha256(result))))
    if bad == 'ledger_season':
        data = json.loads(ledger.read_text());data['season'] = '2023-24';ledger.write_text(json.dumps(data))
    if bad == 'binding':
        data = json.loads(ledger.read_text());data['receipt_sha256'] = '0'*64;ledger.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        io.read_aggregate_bundle(path, digest, '2022-23', 'control', result, ledger, rows)


def test_real_fit_writer_to_aggregate_reader_integration(tmp_path):
    rng = np.random.default_rng(11)
    rows = []
    for year in range(2020, 2025):
        for i in range(32):
            playing = i%3 != 0
            rows.append(dict(season=f'{year}-{str(year+1)[-2:]}', GW=10+i%2, fixture=i+1,
                             fpl_code=101+i, element=i+1, pos=1+i%4, played=float(playing),
                             minutes=90. if playing else 0., sixty=float(playing), dc_hit=np.nan,
                             yellow_cards=0., red_cards=0., points_core=float(i%7) if playing else 0.,
                             ts=pd.Timestamp(f'{year+1}-01-01T12:00Z'), cutoff=pd.Timestamp(f'{year+1}-01-01T10:00Z')))
    d = pd.DataFrame(rows)
    x = pd.DataFrame(rng.random((len(d), len(study.FEATURES))), columns=study.FEATURES)
    x['n_history'], x['last5_minutes'] = 5., 90.
    x['availability_chance'], x['availability_missing'] = 0., 1.
    blocks = []
    for season in study.FOLDS:
        _, mask = study.fold_masks(d, season)
        keys = d.loc[mask, study.KEYS]
        block = keys.copy()
        for arm in study.ARMS:
            prediction, receipt = study.fit(d, x, season, arm)
            root = tmp_path/f'{season}_{arm}'
            root.mkdir()
            path = root/'forecast.npz'
            io.write_fit_bundle(path, keys, prediction)
            result, ledger = provenance(root, season, arm, keys)
            result.write_text(json.dumps(dict(receipt, status='completed')))
            ledger.write_text(json.dumps(dict(status='completed', receipt_sha256=io.file_sha256(result))))
            got, proof = io.read_aggregate_bundle(path, io.file_sha256(path), season, arm, result, ledger, keys)
            block[arm] = got['core_xp']
            assert proof['rows'] == 32
        blocks.append(block)
    mask = d.season.isin(study.FOLDS)
    report = study.aggregate(d.loc[mask], x.loc[mask], pd.concat(blocks))
    assert report['pooled']['conditional']['candidate_fixture']['n'] == 96
