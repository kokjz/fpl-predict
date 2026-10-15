"""Fixed source-value ablation of the incumbent participation method.

Research only. Never loads the trained champion, changes a registry, or produces
live forecasts. Historical news must first pass the exact-prefix admission audit.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from availability_history import admit_prefix, read_archive
from deadline_provenance import read_snapshot
from experiment_runner import file_hash
from fpl_model import CORE_FEATURES, candidate_mask, fit_estimator, sample_weights
from native_reference import environment
from reference_pilot import audit as audit_caches, load_caches, split_masks

SIGNALS = ['availability_chance', 'availability_missing']
ARMS = ('control', 'structured')
POLICY = {
    'schema_version': 1, 'method': 'incumbent-availability-ablation-v1',
    'training': '2020-21 through 2024-25 plus 2025-26 GW1-19',
    'validation': [20, 27], 'audit': [28, 38], 'news_scope': [4, 38],
    'estimator': 'fixed incumbent hgb7 squared-error regressor, clipped [0,1]',
    'features': CORE_FEATURES, 'augmentation': SIGNALS,
    'weights': 'identical incumbent 730.5-day recency weights',
    'refit_after_validation': False, 'text_or_return_gw_used': False,
    'primary': 'candidate fixture-level mean per-GW Brier, structured minus control',
    'block': 4, 'bootstrap_draws': 4000, 'bootstrap_seed': 20261016,
    'head_gate': {'candidate_brier_relative_improvement': .005,
                  'all_brier_no_worse': True, 'block4_difference_upper_below_zero': True,
                  'both_validation_and_reused_audit': True},
    'follow_up': 'only if head gate passes: fixed unconditional core feature augmentation; no probability multiplication',
    'promotion': False,
    'limits': ['already inspected retrospective windows, not untouched',
               'same architecture and training schedule, not the saved champion predictions',
               'older feature-cache cutoffs/schedules reconstructed; upstream statistics mutable',
               'official FPL syndicated availability, not independent club NLP',
               'fixture-level probabilities; no independent-fixture assumption for DGW any-appearance',
               'one season of news cannot satisfy existing multi-season promotion gates']}


def hashes():
    names = ['incumbent_availability.py', 'fpl_model.py', 'availability_history.py',
             'reference_pilot.py', 'native_reference.py', 'deadline_provenance.py',
             'fpl_predict_resources/incumbent_availability_protocol.json']
    return {n: file_hash(Path(__file__).parent / n) for n in names}


def source_observations(archive, proof_path):
    proof = json.loads(Path(proof_path).read_text())
    records = proof['records']
    if len(records) != 35 or {r['gameweek'] for r in records} != set(range(4, 39)):
        raise ValueError('Require exactly one source prefix for every GW4-38')
    raw = read_archive(archive); observations = []; reports = []
    for record in sorted(records, key=lambda r: r['gameweek']):
        bootstrap = read_snapshot(record['bootstrap_path'], record['bootstrap_sha256'])
        report, rows = admit_prefix(raw, record, bootstrap)
        reports.append(report)
        official = {p['code']: p for p in bootstrap['elements']}
        for row in rows:
            if row['fpl_code'] not in official:
                continue  # audited explicitly in report; never join by display name
            observations.append(dict(gameweek=record['gameweek'], fpl_code=row['fpl_code'],
                source_position=official[row['fpl_code']]['element_type'],
                published_at=row['available_by'], source_deadline=record['deadline'],
                chance_label=row['chance_label']))
    return pd.DataFrame(observations), reports


def augment(d, x, bridge, observations):
    """Preserve all fixture rows. Unknown history/labels stay explicitly unknown."""
    if not d.index.equals(x.index):
        raise ValueError('Unaligned features')
    if observations.duplicated(['gameweek', 'fpl_code']).any():
        raise ValueError('Duplicate source observations')
    z = d[['season', 'GW', 'element', 'fixture', 'pos', 'cutoff']].copy()
    z['row'] = np.arange(len(z))
    z['fpl_code'] = z.element.map(bridge.set_index('id').code).where(z.season.eq('2025-26'))
    if z.loc[z.season.eq('2025-26'), 'fpl_code'].isna().any():
        raise ValueError('Missing current-season stable bridge')
    obs = observations.copy(); obs['season'] = '2025-26'
    z = z.merge(obs, left_on=['season', 'GW', 'fpl_code'],
                right_on=['season', 'gameweek', 'fpl_code'], how='left', validate='many_to_one').sort_values('row')
    matched = z.published_at.notna()
    if (z.loc[matched, 'pos'].to_numpy() != z.loc[matched, 'source_position'].to_numpy()).any():
        raise ValueError('Source position differs')
    publication = pd.to_datetime(z.loc[matched, 'published_at'], utc=True)
    deadline = pd.to_datetime(z.loc[matched, 'source_deadline'], utc=True)
    cutoff = pd.to_datetime(z.loc[matched, 'cutoff'], utc=True)
    if publication.ge(deadline).any() or publication.ge(cutoff).any():
        raise ValueError('Source is not before both recorded cutoffs')
    chance = pd.to_numeric(z.chance_label, errors='raise').to_numpy(float)
    if np.isinf(chance).any() or ((chance[np.isfinite(chance)] < 0) | (chance[np.isfinite(chance)] > 100)).any():
        raise ValueError('Invalid chance covariate')
    result = x.copy()
    result[SIGNALS[0]] = np.where(np.isnan(chance), 0., chance / 100.)
    result[SIGNALS[1]] = np.isnan(chance).astype(float)
    coverage = z.assign(matched=matched.to_numpy(), known=np.isfinite(chance)).groupby(['season', 'GW']).agg(
        rows=('row', 'size'), matched=('matched', 'sum'), known=('known', 'sum')).reset_index()
    return result, coverage.to_dict('records')


def prepare(paths, output, *, trust_local_cache=False):
    if Path(output).exists():
        raise ValueError('Manifest already exists')
    entries = {n: dict(path=str(Path(p).resolve()), sha256=file_hash(p)) for n, p in paths.items()}
    d, x, bridge = load_caches(entries, trust_local_cache)
    splits = audit_caches(d, x, bridge)
    obs, sources = source_observations(paths['archive'], paths['proof'])
    _, coverage = augment(d, x, bridge, obs)
    spec = dict(policy=POLICY, inputs=entries, code=hashes(), environment=environment(),
                splits=splits, source_audits=sources, coverage=coverage,
                created_at=dt.datetime.now(dt.timezone.utc).isoformat())
    Path(output).write_text(json.dumps(spec, indent=2, allow_nan=False))
    return spec


def load(spec, *, trust_local_cache=False):
    if spec['policy'] != POLICY or spec['code'] != hashes() or spec['environment'] != environment():
        raise ValueError('Frozen policy/code/environment changed')
    for entry in spec['inputs'].values():
        if file_hash(entry['path']) != entry['sha256']:
            raise ValueError('Input checksum mismatch')
    d, x, bridge = load_caches(spec['inputs'], trust_local_cache)
    if audit_caches(d, x, bridge) != spec['splits']:
        raise ValueError('Cache split audit changed')
    obs, sources = source_observations(spec['inputs']['archive']['path'], spec['inputs']['proof']['path'])
    x, coverage = augment(d, x, bridge, obs)
    if sources != spec['source_audits'] or coverage != spec['coverage']:
        raise ValueError('Source coverage audit changed')
    return d, x, bridge


def block_difference(frame):
    c = frame[frame.candidate]
    y = c.played.to_numpy(float)
    weekly = c.assign(gap=(c.structured - y)**2 - (c.control - y)**2).groupby('GW').gap.mean()
    weeks = weekly.index.to_numpy()
    if len(weeks) < 4 or not np.all(np.diff(weeks) == 1):
        raise ValueError('Need contiguous candidate GWs')
    n = len(weekly); length = POLICY['block']
    rng = np.random.default_rng(POLICY['bootstrap_seed'])
    starts = rng.integers(0, n, size=(POLICY['bootstrap_draws'], int(np.ceil(n/length))))
    ii = ((starts[:, :, None] + np.arange(length)) % n).reshape(POLICY['bootstrap_draws'], -1)[:, :n]
    return dict(difference=float(weekly.mean()), block4_interval=np.quantile(
        weekly.to_numpy()[ii].mean(axis=1), [.025, .975]).tolist(), gameweeks=n)


def scores(frame, arm):
    result = {}
    for name, mask in [('all', np.ones(len(frame), bool)), ('candidates', frame.candidate.to_numpy(bool))]:
        f = frame[mask]; p = f[arm].to_numpy(float); y = f.played.to_numpy(float)
        if not len(f):
            raise ValueError('Empty score cohort')
        bins = []
        for lo, hi in [(0, .5), (.5, .8), (.8, .95), (.95, 1.0000001)]:
            ix = (p >= lo) & (p < hi)
            bins.append(dict(lower=lo, upper=min(hi, 1), n=int(ix.sum()),
                mean_probability=float(p[ix].mean()) if ix.any() else None,
                actual_rate=float(y[ix].mean()) if ix.any() else None))
        result[name] = dict(n=len(f), brier=float(np.mean((p-y)**2)), reliability=bins,
                           high_probability_n=int((p >= .8).sum()),
                           high_probability_misses=int(((p >= .8) & (y == 0)).sum()))
    return result


def equal_coverage(frame):
    # Per GW, choose the same number as control's >=.8 band. No outcome selection.
    records = []
    for gw, f in frame[frame.candidate].groupby('GW'):
        n = int(f.control.ge(.8).sum()); row = dict(gameweek=int(gw), n=n)
        for arm in ARMS:
            top = f.sort_values([arm, 'element', 'fixture'], ascending=[False, True, True]).head(n)
            row[arm + '_misses'] = int(top.played.eq(0).sum())
        records.append(row)
    return dict(weeks=records, n=sum(r['n'] for r in records),
                **{arm + '_misses': sum(r[arm + '_misses'] for r in records) for arm in ARMS})


def gate(metrics, contrast):
    reduction = 1 - metrics['structured']['candidates']['brier'] / metrics['control']['candidates']['brier']
    checks = dict(candidate_relative_reduction_at_least_half_percent=reduction >= .005,
                  all_brier_no_worse=metrics['structured']['all']['brier'] <= metrics['control']['all']['brier'],
                  descriptive_block4_upper_below_zero=contrast['block4_interval'][1] < 0)
    return dict(passed=all(checks.values()), relative_candidate_reduction=reduction, checks=checks)


def fit_head(d, x):
    masks = split_masks(d); train = masks['train']; predictions = d.loc[~train,
        ['season', 'GW', 'element', 'fixture', 'pos', 'minutes', 'played']].copy()
    predictions['candidate'] = candidate_mask(x[~train]).to_numpy()
    times = {}
    with threadpool_limits(limits=2):
        weights = sample_weights(d[train])
        for arm, columns in [('control', CORE_FEATURES), ('structured', CORE_FEATURES + SIGNALS)]:
            start = time.monotonic()
            model = fit_estimator('hgb7', x.loc[train, columns], d.loc[train, 'played'], weights)
            times[arm + '_fit_seconds'] = time.monotonic() - start
            start = time.monotonic()
            predictions[arm] = np.clip(model.predict(x.loc[~train, columns]), 0, 1)
            times[arm + '_predict_seconds'] = time.monotonic() - start
    reports = {}
    for label, weeks in [('validation', range(20, 28)), ('audit', range(28, 39))]:
        f = predictions[predictions.GW.isin(weeks)]
        if set(f.GW) != set(weeks):
            raise ValueError('Incomplete evaluation window')
        metrics = {arm: scores(f, arm) for arm in ARMS}; contrast = block_difference(f)
        reports[label] = dict(metrics=metrics, primary=contrast, equal_coverage=equal_coverage(f),
                              gate=gate(metrics, contrast))
    report = dict(policy=POLICY, training_rows=int(train.sum()), evaluation=reports, timing=times,
                  integration_eligible=all(v['gate']['passed'] for v in reports.values()),
                  model_promotion=False, points_gain_measured=False,
                  minutes_change='None: minutes and p60 learners unchanged in this ablation')
    return report, predictions


def run(manifest, expected, output, *, trust_local_cache=False):
    if file_hash(manifest) != expected:
        raise ValueError('Manifest checksum mismatch')
    output = Path(output)
    if output.exists():
        raise ValueError('Output exists; preserve previous evidence')
    spec = json.loads(Path(manifest).read_text())
    d, x, _ = load(spec, trust_local_cache=trust_local_cache)
    report, predictions = fit_head(d, x)
    output.mkdir(parents=True)
    predictions.to_csv(output / 'predictions.csv', index=False)
    report['manifest_sha256'] = expected
    report['predictions_sha256'] = file_hash(output / 'predictions.csv')
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('prepare')
    for name in ['history', 'features', 'players', 'archive', 'proof', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--trust-local-cache', action='store_true')
    p = sub.add_parser('run')
    for name in ['manifest', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--sha256', required=True); p.add_argument('--trust-local-cache', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        paths = {n: getattr(args, n) for n in ['history', 'features', 'players', 'archive', 'proof']}
        prepare(paths, args.output, trust_local_cache=args.trust_local_cache)
    else:
        run(args.manifest, args.sha256, args.output, trust_local_cache=args.trust_local_cache)


if __name__ == '__main__':
    main()
