"""Replay trusted prior-only appearance heads against unchanged historical means.

Manifest inputs include the exact source-admitted calendar views and source
receipts. This tool neither downloads sources nor certifies their original dates.
Executable local caches/model files require an explicit trust flag and hashes.
"""
import argparse
import gzip
import json
from pathlib import Path
import time
import joblib
import pandas as pd
from threadpoolctl import threadpool_limits
from decision_availability import project_probabilities
from experiment_runner import file_hash
from fpl_model import STATS
from season_benchmark import read_bundle
from season_engine import Market
from horizon_forecast import Horizon

ROOT = Path(__file__).resolve().parents[1]


def checked(entry):
    path = Path(entry['path'])
    if file_hash(path) != entry['sha256']:
        raise ValueError('Input checksum differs')
    return path


def corrected_history(history, correction):
    """Match the admitted origin recipe, including derived appearance labels."""
    result = history.copy()
    for r in correction.to_dict('records'):
        mask = result.element.eq(r['element']) & result.fixture.eq(r['fixture'])
        if mask.sum() != 1:
            raise ValueError('Ambiguous derived history correction')
        for field in STATS:
            if field in r:
                result.loc[mask, field] = r[field]
        result.loc[mask, 'points_core'] = r['total_points']
        result.loc[mask, 'played'] = float(r['minutes'] > 0)
        result.loc[mask, 'sixty'] = float(r['minutes'] >= 60)
    return result


def prepare(manifest, expected, output, *, trust_local_cache=False):
    if not trust_local_cache:
        raise ValueError('Explicit cache/model trust required')
    if file_hash(manifest) != expected:
        raise ValueError('Manifest checksum differs')
    out = Path(output).resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise ValueError('Require new private output directory')
    spec = json.loads(Path(manifest).read_text())
    if spec['schema_version'] != 1 or set(spec['seasons']) != {'2024-25', '2025-26'}:
        raise ValueError('Undeclared season coverage')
    for entry in spec['receipts']:
        checked(entry)
    for source in spec['seasons'].values():
        for key in ('history', 'model', 'decisions'):
            checked(source[key])
        if source.get('correction'):
            checked(source['correction'])
        for origin in source['origins']:
            checked(origin['calendar'])
    start = time.monotonic()
    out.mkdir(parents=True)
    summaries = []
    with threadpool_limits(limits=2):
        for season, source in spec['seasons'].items():
            model = joblib.load(checked(source['model']))
            history = pd.read_pickle(checked(source['history']))
            history = history[history.season.eq(season)].copy()
            if source.get('correction'):
                history = corrected_history(history, pd.read_csv(checked(source['correction'])))
            decisions = read_bundle(checked(source['decisions']))['weeks']
            origins = source['origins']
            if [x['gameweek'] for x in origins] != list(range(1, 39)) or len(decisions) != 38:
                raise ValueError('Require 38 complete origins')
            weeks = []
            for entry, decision in zip(origins, decisions):
                market = Market.create(**decision['market'])
                if (market.season, market.gameweek, market.as_of) != (season, entry['gameweek'], entry['as_of']):
                    raise ValueError('Source/decision origin differs')
                horizon = Horizon.create(market, **decision['forecast'])
                rows, report = project_probabilities(model, history, market,
                    pd.read_csv(checked(entry['calendar'])), horizon,
                    official_zero_ids=entry['official_zero_ids'])
                weeks.append(dict(gameweek=market.gameweek, as_of=market.as_of,
                    model_sha256=source['model']['sha256'], decision_sha256=source['decisions']['sha256'],
                    source_hashes=entry['source_hashes'], calendar_sha256=entry['calendar']['sha256'],
                    trained_through=report['trained_through'], rows=rows, report=report))
                print('Replayed', season, market.gameweek, flush=True)
            name = season + '.json.gz'
            with gzip.open(out / name, 'xt') as stream:
                json.dump(dict(schema_version=1, season=season, weeks=weeks), stream, separators=(',', ':'), allow_nan=False)
            summaries.append(dict(season=season, origins=38, rows=sum(len(w['rows']) for w in weeks),
                maximum_mean_reproduction_error=max(w['report']['mean_reproduction_max_abs_error'] for w in weeks),
                file=name, sha256=file_hash(out / name), model_sha256=source['model']['sha256']))
    result = dict(complete=True, seasons=summaries, seconds=time.monotonic()-start,
        manifest_sha256=expected, new_fit=False, model_promotion=False,
        scope='Origin-only appearance sidecar; same unconditional means; probability decomposition assumptions are experimental')
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--trust-local-cache', action='store_true')
    a = p.parse_args()
    prepare(a.manifest, a.manifest_sha256, a.output, trust_local_cache=a.trust_local_cache)


if __name__ == '__main__':
    main()
