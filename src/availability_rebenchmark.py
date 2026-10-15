"""Matched historical error and selection rebenchmark for availability research."""
import numpy as np
import pandas as pd
from benchmark_metrics import point_scores

MODELS=['reference','availability_reference','native_reference','conditional_reference','openfpl_cv1_refit','conjugate_poisson']
KEYS=['season','gameweek','fixture','fpl_code']


def align(points,external,market,source_audits):
    """Preserve every forecast/market row; validate the reproduced old control.

    Source audits must come from the hash-verified head manifest. News can be
    newer than a price snapshot while still predeadline: retain quote time and
    move inputs_as_of to the latest admitted source. Never call this equal feeds.
    """
    for f in [points,external]:
        if f.duplicated(KEYS).any():raise ValueError('Duplicate fixture predictions')
    if market.duplicated(['season','gameweek','fpl_code']).any():raise ValueError('Duplicate market')
    p=points[points.gameweek.between(28,38)].copy()
    if set(p.gameweek)!=set(range(28,39)):raise ValueError('Missing point weeks')
    e=external.copy()
    joined=e.merge(p[KEYS+['actual','minutes','position','candidate','control','structured']],on=KEYS,
        how='outer',indicator=True,validate='one_to_one',suffixes=('','_new'))
    if not joined._merge.eq('both').all():raise ValueError('Unequal fixture forecast coverage')
    for old,new in [('actual','actual_new'),('minutes','minutes_new'),('reference','control'),('position','position_new')]:
        if not np.allclose(joined[old],joined[new],rtol=0,atol=1e-10):
            raise ValueError('Control/outcome mismatch')
    if not joined.candidate.eq(joined.candidate_new).all():raise ValueError('Candidate cohort mismatch')
    joined['availability_reference']=joined.structured
    output=joined[KEYS+['actual','minutes','candidate',*MODELS]].copy()
    if not np.isfinite(output[['actual','minutes',*MODELS]]).all().all():raise ValueError('Nonfinite predictions')
    grouped=output.groupby(['season','gameweek','fpl_code']).agg(
        actual=('actual','sum'),candidate=('candidate','first'),**{m:(m,'sum') for m in MODELS}).reset_index()
    m=market.copy();keys=['season','gameweek','fpl_code']
    update=grouped[keys+['availability_reference']]
    old_models=[n for n in MODELS if n!='availability_reference']
    check=m.merge(grouped[keys+['actual',*old_models]],on=keys,validate='one_to_one',suffixes=('','_sum'))
    for name in ['actual',*old_models]:
        if not np.allclose(check[name],check[name+'_sum'],rtol=0,atol=1e-10):
            raise ValueError('Retained market/fixture totals conflict')
    result=m.merge(update,on=keys,how='outer',indicator=True,validate='one_to_one')
    if result._merge.eq('right_only').any():raise ValueError('Forecast absent from retained market')
    missing=result._merge.eq('left_only')
    if not {'blank_verified','fixture_count'}<=set(result):raise ValueError('Missing blank proof')
    if not (result.loc[missing,'blank_verified'].eq(1)&result.loc[missing,'fixture_count'].eq(0)).all():
        raise ValueError('Unexplained missing market forecast')
    if not result.loc[missing,['actual',*old_models]].eq(0).all().all():raise ValueError('Nonzero blank')
    result.loc[missing,'availability_reference']=0.
    result=result.drop(columns='_merge');result['quote_as_of']=result.inputs_as_of
    if len({r['gameweek'] for r in source_audits})!=len(source_audits):raise ValueError('Duplicate source weeks')
    times={r['gameweek']:pd.Timestamp(r['published_at']) for r in source_audits}
    if not set(range(28,39))<=set(times):raise ValueError('Missing news publication times')
    updates=[]
    for gw,week in result.groupby('gameweek'):
        quote=pd.Timestamp(week.inputs_as_of.iloc[0]);news=times[int(gw)];cutoff=max(quote,news)
        if cutoff>=pd.Timestamp(week.deadline.iloc[0]):raise ValueError('New source after market deadline')
        result.loc[week.index,'inputs_as_of']=cutoff.isoformat()
        updates.append(dict(gameweek=int(gw),quote_as_of=quote.isoformat(),news_published_at=news.isoformat(),
                            comparison_as_of=cutoff.isoformat(),quote_earlier_than_news=quote<news))
    metrics={m:dict(candidates=point_scores(grouped[grouped.candidate],m),all=point_scores(grouped,m)) for m in MODELS}
    return result,dict(metrics=metrics,fixture_rows=len(output),player_gw_rows=len(grouped),
        candidate_player_gws=int(grouped.candidate.sum()),market_rows=len(result),verified_blanks_filled=int(missing.sum()),
        control_max_absolute_difference=float(np.max(np.abs(joined.reference-joined.control))),
        source_times=updates,scope='same deadline and retained quote-market; unequal source feeds; named external adaptations, not originals')


def main():
    import argparse,json
    from pathlib import Path
    from experiment_runner import file_hash
    from selection_benchmark import run
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['points','points-report','external','market','head-manifest']:
        parser.add_argument('--'+name,type=Path,required=True)
        parser.add_argument('--'+name+'-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    entries={n:dict(path=getattr(args,n),sha256=getattr(args,n+'_sha256'))
             for n in ['points','points_report','external','market','head_manifest']}
    if args.output.exists():parser.error('Output exists; preserve evidence')
    if any(file_hash(e['path'])!=e['sha256'] for e in entries.values()):parser.error('Input checksum mismatch')
    report=json.loads(args.points_report.read_text());head=json.loads(args.head_manifest.read_text())
    if report['predictions_sha256']!=args.points_sha256 or report['manifest_sha256']!=args.head_manifest_sha256:
        parser.error('Points report/manifest mismatch')
    market,audit=align(pd.read_csv(args.points),pd.read_csv(args.external),pd.read_csv(args.market),head['source_audits'])
    args.output.mkdir(parents=True)
    spec=dict(inputs={n:e['sha256'] for n,e in entries.items()},models=MODELS,
        reference='availability_reference',panels=12,rolling=6,reset=True,
        engine_sha256=file_hash(Path(__file__)),
        selection_sha256=file_hash(Path(__file__).with_name('selection_benchmark.py')),
        selector_sha256=file_hash(Path(__file__).with_name('forecast.py')),
        protocol_sha256=file_hash(Path(__file__).parent/'fpl_predict_resources/selection_protocol.json'))
    (args.output/'spec.json').write_text(json.dumps(spec,indent=2))
    (args.output/'input_audit.json').write_text(json.dumps(audit,indent=2,allow_nan=False))
    market.to_csv(args.output/'market.csv',index=False)
    scores,actions,result=run(market,MODELS,reference='availability_reference',panels=12,rolling=6,reset=True)
    scores.to_csv(args.output/'scores.csv',index=False)
    (args.output/'actions.json').write_text(json.dumps(actions,indent=2,allow_nan=False))
    (args.output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
