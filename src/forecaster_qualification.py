"""Fixed chronological forecaster qualification; no automatic model promotion."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from conditional_forecaster import fit,missing_availability
from benchmark_metrics import point_scores
from benchmark_evaluation import paired_block_errors
from fpl_model import CORE_FEATURES,candidate_mask,fit_estimator,sample_weights
from incumbent_availability import load
from experiment_runner import file_hash

PROTOCOL=Path(__file__).parent/'fpl_predict_resources/forecaster_qualification_protocol.json'


def join_market(market,conditional):
    """Attach fixed forecasts by stable keys, never by merged positional order."""
    keys=['season','gameweek','fpl_code']
    if market.duplicated(keys).any() or conditional.duplicated(keys).any():raise ValueError('Duplicate market keys')
    left=pd.MultiIndex.from_frame(market[keys]);right=pd.MultiIndex.from_frame(conditional[keys])
    if set(left)!=set(right):raise ValueError('Unequal listed market coverage')
    source=conditional.set_index(keys).loc[left]
    for k in ['actual','minutes','position','price_tenths','prior_minutes','cards','fixture_count','blank_verified']:
        if not np.allclose(market[k].to_numpy(float),source[k].to_numpy(float),rtol=0,atol=1e-10):raise ValueError('Market metadata differs: '+k)
    if not np.array_equal(market.team.to_numpy(),source.team.to_numpy()) or not np.allclose(market.reference.to_numpy(),source.anchor.to_numpy(),rtol=0,atol=1e-10):raise ValueError('Market reference differs')
    result=market.copy();result['conditional_forecaster']=source.new_xp.to_numpy()
    result['quote_as_of']=result.inputs_as_of;result['inputs_as_of']=source.inputs_as_of.to_numpy()
    if not np.isfinite(result.conditional_forecaster).all():raise ValueError('Nonfinite forecasts')
    return result


def development(d,x):
    """Same-train core comparison; no availability observations pre-2025."""
    records=[];folds={}
    for season in ['2022-23','2023-24']:
        train=d.season.lt(season);test=d.season.eq(season)
        if not train.any() or not test.any() or pd.to_datetime(d.loc[train,'ts'],utc=True).max()+pd.Timedelta(hours=3)>=pd.to_datetime(d.loc[test,'cutoff'],utc=True).min():raise ValueError('Invalid chronological development split')
        xx=missing_availability(x);start=time.monotonic();model=fit(d,xx,train)
        with threadpool_limits(limits=2):
            old=fit_estimator('hgb7',x.loc[train,CORE_FEATURES],d.loc[train,'points_core'],sample_weights(d[train]))
            baseline=np.clip(old.predict(x.loc[test,CORE_FEATURES]),0,20)
        out=d.loc[test,['season','GW','element','fixture','points_core']].rename(columns={'GW':'gameweek','points_core':'actual'}).copy()
        out['candidate']=candidate_mask(x[test]).to_numpy();out['standing']=baseline
        out['conditional']=model.predict(xx[test],d.loc[test,'pos']).core_xp.to_numpy()
        z=out.groupby(['season','gameweek','element']).agg(actual=('actual','sum'),candidate=('candidate','first'),standing=('standing','sum'),conditional=('conditional','sum')).reset_index();c=z[z.candidate]
        folds[season]=dict(metrics={m:point_scores(c,m) for m in ['standing','conditional']},paired=paired_block_errors(c,'conditional','standing'),seconds=time.monotonic()-start,
            available_news=False,scope='core-only chronological refits, older availability explicitly missing')
        records.append(out);print('Completed fixed development',season,flush=True)
    frame=pd.concat(records);z=frame.groupby(['season','gameweek','element']).agg(actual=('actual','sum'),candidate=('candidate','first'),standing=('standing','sum'),conditional=('conditional','sum')).reset_index();c=z[z.candidate]
    metrics={m:point_scores(c,m) for m in ['standing','conditional']}
    checks=dict(pooled_core_rmse_half_percent=metrics['conditional']['rmse']<=metrics['standing']['rmse']*.995,
        each_fold_within_half_percent=all(f['metrics']['conditional']['rmse']<=f['metrics']['standing']['rmse']*1.005 for f in folds.values()))
    return frame,dict(folds=folds,pooled=metrics,checks=checks,passed=all(checks.values()),external_scope='No admitted external predictions for these seasons; no fabricated external performance or new external fits')


def run(manifest,sha256,output,*,trust_local_cache=False):
    if file_hash(manifest)!=sha256:raise ValueError('Manifest checksum mismatch')
    output=Path(output)
    if output.exists():raise ValueError('Preserve immutable run; output exists')
    spec=json.loads(Path(manifest).read_text());d,x,_=load(spec,trust_local_cache=trust_local_cache);output.mkdir(parents=True)
    (output/'spec.json').write_text(json.dumps(dict(protocol_sha256=file_hash(PROTOCOL),manifest_sha256=sha256,engine_sha256=file_hash(Path(__file__)),model_sha256=file_hash(Path(__file__).with_name('conditional_forecaster.py'))),indent=2))
    frame,report=development(d,x);frame.to_csv(output/'development.csv',index=False)
    report.update(model_promotion=False,expanded_fits_eligible=report['passed'])
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False));return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['manifest','output']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--sha256',required=True);p.add_argument('--trust-local-cache',action='store_true');a=p.parse_args()
    run(a.manifest,a.sha256,a.output,trust_local_cache=a.trust_local_cache)


if __name__=='__main__':main()
