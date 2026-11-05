"""Safe forecast-bundle IO; historical object season payloads stay unopened."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from fplcache_availability import FOLDS, ARMS, KEYS, keyed_block


def file_sha256(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError('Bundle/provenance file absent')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_fit_bundle(path, keys, prediction):
    """Future fit writer: explicit Unicode season and numeric-only other arrays."""
    if not keys.index.equals(prediction.index) or not keys.index.is_unique:
        raise ValueError('Fit bundle alignment')
    seasons = set(keys.season)
    if len(seasons) != 1 or not seasons <= set(FOLDS):
        raise ValueError('Fit season refused')
    if set(KEYS) & set(prediction):
        raise ValueError('Prediction/key collision')
    arrays = dict(season=keys.season.to_numpy(dtype='U7'))
    for name in ['fixture', 'fpl_code']:
        values = keys[name].to_numpy()
        if values.dtype.kind not in 'iu':
            raise ValueError('Integer fit keys required')
        arrays[name] = values.astype('int64', copy=False)
    for name in prediction:
        values = prediction[name].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError('Nonfinite fit forecast')
        arrays[name] = values
    with Path(path).open('xb') as stream:
        np.savez_compressed(stream, **arrays)


def read_aggregate_bundle(path, expected_sha256, season, arm, result_path, ledger_path, rows):
    """Authenticate bytes and season provenance before opening numeric arrays."""
    if season not in FOLDS or arm not in ARMS:
        raise ValueError('Fold or arm refused')
    actual_sha256 = file_sha256(path)
    if actual_sha256 != expected_sha256:
        raise ValueError('Forecast bundle SHA256 mismatch')
    result_sha256 = file_sha256(result_path)
    ledger_sha256 = file_sha256(ledger_path)
    result = json.loads(Path(result_path).read_text(encoding='utf-8'))
    ledger = json.loads(Path(ledger_path).read_text(encoding='utf-8'))
    ordinal = [(s, a) for s in FOLDS for a in ARMS].index((season, arm))
    if Path(ledger_path).name != f'{ordinal:02d}.json':
        raise ValueError('Fit ledger ordinal mismatch')
    if ledger.get('status') != 'completed' or result.get('status') != 'completed':
        raise ValueError('Fit not completed')
    if ledger.get('receipt_sha256') != result_sha256:
        raise ValueError('Fit ledger receipt binding mismatch')
    if result.get('season') != season or result.get('arm') != arm:
        raise ValueError('Result season/arm mismatch')
    # Completed original entries contain the result hash, rather than repeating
    # its season/arm. That verified hash authenticates the season recorded there.
    ledger_season = ledger.get('season', result['season'])
    ledger_arm = ledger.get('arm', result['arm'])
    if ledger_season != season or ledger_arm != arm:
        raise ValueError('Ledger season/arm mismatch')
    if not rows.season.eq(season).all() or len(rows) != result.get('test_rows'):
        raise ValueError('Admitted fold row coverage mismatch')
    names = ['fixture', 'fpl_code', 'core_xp', 'expected_points']
    with np.load(path, allow_pickle=False) as bundle:
        arrays = {name: bundle[name] for name in names}
    for name, values in arrays.items():
        if values.ndim != 1 or len(values) != len(rows) or values.dtype.kind not in 'iuf':
            raise ValueError('Numeric forecast array contract')
        if not np.isfinite(values).all():
            raise ValueError('Nonfinite forecast bundle array')
    if any(arrays[name].dtype.kind not in 'iu' for name in ['fixture', 'fpl_code']):
        raise ValueError('Integer aggregate keys required')
    saved = pd.DataFrame(dict(season=[season]*len(rows), fixture=arrays['fixture'],
                              fpl_code=arrays['fpl_code']), index=rows.index)
    keyed_block(rows, saved, [])
    proof = dict(path=str(Path(path).resolve()), expected_sha256=expected_sha256, actual_sha256=actual_sha256,
                 season_from_loop=season, season_from_result=result['season'], season_from_ledger=ledger_season,
                 ledger_season_source='explicit field' if 'season' in ledger else 'result.json authenticated by receipt_sha256',
                 result_sha256=result_sha256, ledger_sha256=ledger_sha256, arm=arm, rows=len(rows),
                 loaded_arrays=names, season_array_loaded=False, allow_pickle=False, ordered_keys_validated=True)
    return {name: arrays[name] for name in ['core_xp', 'expected_points']}, proof
