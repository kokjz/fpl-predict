"""Locked unconditional points extension after a qualified availability-head study."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from benchmark_evaluation import paired_block_errors
from benchmark_metrics import point_scores
from experiment_runner import file_hash
from fpl_model import CORE_FEATURES,DC_FEATURES,candidate_mask,fit_estimator,sample_weights
from incumbent_availability import SIGNALS,load
from reference_pilot import split_masks

POLICY=dict(schema_version=1,method='incumbent-availability-unconditional-points-v1',
    arms=['control','structured'],training='identical head study rows/weights, through GW19; no validation refit',
    core='fixed hgb7, clip [0,20], blend1; structured arm adds chance and missingness',
    dc='same fixed hgb7 training on observed DC; each arm caps at its own appearance probability',
    minutes='unchanged; no minutes/p60 refit',
    interpretation='direct unconditional target training including zero outcomes; never multiply core points by p_play',
    qualification=dict(candidate_rmse_relative_improvement=.005,mae_max_relative_worsening=.005,
        candidate_ndcg_no_worse=True,both_windows=True,owned_points_nonnegative_required=True),
    external_replay='Compare both arms and retained external adaptations on identical 2025/26 GW28-38 market and original policy/scenarios',
    no_original_2024_dastan_backcast='News starts2025; no fabricated historical articles/labels',
    promotion=False,limits=['reused historical outcomes','source and schedule limitations inherited from head manifest',
    'single availability season cannot satisfy multi-season promotion gates','adaptations are not original external systems'])


def run(manifest,expected,head_report,head_report_sha256,head_predictions,head_predictions_sha256,output,*,trust_local_cache=False):
    paths=[(manifest,expected),(head_report,head_report_sha256),(head_predictions,head_predictions_sha256)]
    if any(file_hash(p)!=h for p,h in paths):raise ValueError('Input checksum mismatch')
    head=json.loads(Path(head_report).read_text())
    if (head.get('integration_eligible') is not True or head['manifest_sha256']!=expected or
            head['predictions_sha256']!=head_predictions_sha256):raise ValueError('Head study not eligible/matched')
    output=Path(output)
    if output.exists():raise ValueError('Output exists')
    spec=json.loads(Path(manifest).read_text());d,x,bridge=load(spec,trust_local_cache=trust_local_cache)
    masks=split_masks(d);train=masks['train'];evaluation=~train;dc_train=train&d.dc_hit.notna()
    target=d.loc[evaluation,['season','GW','element','fixture','pos','total_points','minutes','played']].copy()
    target['candidate']=candidate_mask(x[evaluation]).to_numpy()
    hp=pd.read_csv(head_predictions);keys=['season','GW','element','fixture']
    checked=target.merge(hp[keys+['played','control','structured']],on=keys,how='outer',
                         validate='one_to_one',indicator=True,suffixes=('','_head'))
    if not checked._merge.eq('both').all() or not np.array_equal(checked.played,checked.played_head):
        raise ValueError('Head forecast target coverage differs')
    times={}; predictions={}
    with threadpool_limits(limits=2):
        weights=sample_weights(d[train]);start=time.monotonic()
        dc=fit_estimator('hgb7',x.loc[dc_train,DC_FEATURES],d.loc[dc_train,'dc_hit'],sample_weights(d[dc_train]))
        dc_probability=np.where(target.pos.eq(1),0,np.clip(dc.predict(x.loc[evaluation,DC_FEATURES]),0,1))
        times['shared_dc_fit_predict_seconds']=time.monotonic()-start
        # Reindex saved head forecasts explicitly; never rely on CSV row order.
        by_key=hp.set_index(keys).loc[pd.MultiIndex.from_frame(target[keys])]
        for arm,columns in [('control',CORE_FEATURES),('structured',CORE_FEATURES+SIGNALS)]:
            start=time.monotonic()
            core=fit_estimator('hgb7',x.loc[train,columns],d.loc[train,'points_core'],weights)
            times[arm+'_core_fit_seconds']=time.monotonic()-start;start=time.monotonic()
            raw=np.clip(core.predict(x.loc[evaluation,columns]),0,20)
            play=by_key[arm].to_numpy(float)
            predictions[arm]=raw+2*np.minimum(play,dc_probability)
            times[arm+'_predict_seconds']=time.monotonic()-start
    out=target.rename(columns={'GW':'gameweek','total_points':'actual','pos':'position'}).copy()
    out['fpl_code']=out.element.map(bridge.set_index('id').code).astype(int)
    for arm,p in predictions.items():out[arm]=p
    grouped=out.groupby(['season','gameweek','fpl_code']).agg(actual=('actual','sum'),candidate=('candidate','first'),
        control=('control','sum'),structured=('structured','sum')).reset_index()
    reports={}
    for name,weeks in [('validation',range(20,28)),('audit',range(28,39))]:
        g=grouped[grouped.gameweek.isin(weeks)];c=g[g.candidate]
        if set(c.gameweek)!=set(weeks):raise ValueError('Incomplete candidate evaluation window')
        metrics={a:dict(candidates=point_scores(c,a),all=point_scores(g,a)) for a in POLICY['arms']}
        base=metrics['control']['candidates'];new=metrics['structured']['candidates']
        checks=dict(rmse_at_least_half_percent=new['rmse']<=base['rmse']*.995,
            mae_within_half_percent=new['mae']<=base['mae']*1.005,
            candidate_ndcg_no_worse=new['mean_within_gw_ndcg10']>=base['mean_within_gw_ndcg10'])
        reports[name]=dict(metrics=metrics,checks=checks,point_error_rank_gate=all(checks.values()),
            paired=paired_block_errors(c,'structured','control'))
    output.mkdir(parents=True)
    out.to_csv(output/'predictions.csv',index=False)
    report=dict(policy=POLICY,evaluation=reports,timing=times,model_promotion=False,
                selection_benchmark_required=True,manifest_sha256=expected,
                head_report_sha256=head_report_sha256,head_predictions_sha256=head_predictions_sha256,
                predictions_sha256=file_hash(output/'predictions.csv'),
                code_sha256=file_hash(Path(__file__)),
                protocol_sha256=file_hash(Path(__file__).parent/'fpl_predict_resources/incumbent_availability_points_protocol.json'))
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['manifest','head-report','head-predictions','output']:p.add_argument('--'+n,type=Path,required=True)
    for n in ['sha256','head-report-sha256','head-predictions-sha256']:p.add_argument('--'+n,required=True)
    p.add_argument('--trust-local-cache',action='store_true');a=p.parse_args()
    run(a.manifest,a.sha256,a.head_report,a.head_report_sha256,a.head_predictions,a.head_predictions_sha256,a.output,trust_local_cache=a.trust_local_cache)


if __name__=='__main__':main()
