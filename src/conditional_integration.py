"""Fixed historical conditional-return fit with frozen old/new appearance heads."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from benchmark_metrics import point_scores
from benchmark_evaluation import paired_block_errors
from experiment_runner import file_hash
from fpl_model import CORE_FEATURES,DC_FEATURES,candidate_mask,fit_estimator,sample_weights
from incumbent_availability import load
from reference_pilot import split_masks

POLICY=dict(schema_version=1,method='conditional-availability-selection-v1',
    training='2020-21 through 2024-25 plus 2025-26 GW1-19, only appearing rows for conditional targets',
    learner='fixed hgb7,49CORE features,no availability covariates in shared return model',
    core_clip=[0,20],conditional_dc='fixed hgb7 on earlier appearing observed-DC rows,clip[0,1],GK0',
    conditional_minutes='fixed hgb7 on same appearing rows,clip[1,90];diagnostic only',
    probabilities='reuse exact frozen control/structured appearance forecasts from previous admitted study',
    formula='p_play*(conditional_core+2*conditional_DC)+p_card_only*conditional_card; shared training-only zero-minute card rate/return',
    validation=[20,27],audit=[28,38],refit_validation=False,parameter_or_seed_search=False,
    arms=['anchor','old_mean','new_mean','old_expected','new_expected'],
    fixed_squads=12,squad_source='neutral panels frozen separately at GW20 and GW28; no future roster used in development',
    primary='new_expected minus old_mean mean realised owned points/GW; scenarios averaged inside GW',
    factorial=['new_mean-old_mean','old_expected-old_mean','new_expected-new_mean','new_expected-old_expected'],
    expected_selector='exact exhaustive legal-XI/bench/captain/vice optimum under independent player-GW appearances',
    dgw_primary='independent fixture appearances: p_any=1-product(1-p_fixture); means sum fixture expectations',
    sensitivity='shared fixture threshold p_any=max(p_fixture), primary chosen-plan .25 common-uniform mixture expectation',
    sensitivity_squads=[0,4,8],sensitivity_reoptimisation='persistent-fixture assumption, allGWs in both windows; never selected by outcomes',
    promotion=False,
    progression=dict(development_candidate_rmse_improvement=.005,mae_max_worsening=.005,ndcg_no_worse=True,
       development_owned_vs_anchor_nonnegative=True,development_combined_vs_old_mean_nonnegative=True,
       frozen_finalist='new_expected only; no best-arm selection',
       historical_extension='only if development forecast/owned gates pass; always report all existing-window scores',
       full_promotion='unchanged existing multi-season/current/integrity gates, not waived by this pilot'),
    limits=['inspected/reused historical outcomes,not untouched','conditional means average cameo/long appearances',
      'independent availability is assumed,not learnt; correlation stress is not empirical injury modelling',
      'rare zero-minute card prior is pooled/training-only,not player-specific',
      'source publication/roster/cached schedule/statistical correction limits inherited','no direct club news or future data',
      'exact optimum applies only to fixed owned15 and specified distribution; not full transfer/chip optimisation'])


def fit_returns(d,x,head):
    train=split_masks(d)['train'];appearing=train&d.played.eq(1);dc_train=appearing&d.dc_hit.notna()
    if not appearing.any() or not dc_train.any():raise ValueError('No conditional training rows')
    target=d.loc[~train,['season','GW','element','fixture','pos','total_points','minutes','played']].copy()
    target['candidate']=candidate_mask(x[~train]).to_numpy()
    keys=['season','GW','element','fixture']
    merged=target.merge(head[keys+['played','control','structured']],on=keys,how='outer',validate='one_to_one',indicator=True,suffixes=('','_head'))
    if not merged._merge.eq('both').all() or not np.array_equal(merged.played,merged.played_head):raise ValueError('Head target coverage differs')
    bykey=head.set_index(keys).loc[pd.MultiIndex.from_frame(target[keys])]
    if not np.isfinite(bykey[['control','structured']]).all().all() or not bykey[['control','structured']].ge(0).all().all() or not bykey[['control','structured']].le(1).all().all():raise ValueError('Invalid frozen probabilities')
    cards=d.yellow_cards+d.red_cards
    if not np.isfinite(cards).all() or cards.lt(0).any():raise ValueError('Invalid card event data')
    if ((~train)&d.played.eq(0)&d.total_points.ne(0)&cards.eq(0)).any():raise ValueError('Unexplained zero-minute points require a separate event model')
    weights=pd.Series(sample_weights(d[train]),index=d[train].index);timing={};pred={}
    zero=train&d.played.eq(0);card=zero&cards.gt(0)
    if not zero.any():raise ValueError('No nonappearance prior training rows')
    card_rate=float(weights.loc[d[card].index].sum()/weights.loc[d[zero].index].sum())
    card_return=float(np.average(d.loc[card,'points_core'],weights=weights.loc[d[card].index])) if card.any() else 0.
    with threadpool_limits(limits=2):
        for name,rows,columns,label,limits in [('core',appearing,CORE_FEATURES,'points_core',(0,20)),
             ('dc',dc_train,DC_FEATURES,'dc_hit',(0,1)),('minutes',appearing,CORE_FEATURES,'minutes',(1,90))]:
            start=time.monotonic();m=fit_estimator('hgb7',x.loc[rows,columns],d.loc[rows,label],weights.loc[d[rows].index])
            timing[name+'_fit_seconds']=time.monotonic()-start;start=time.monotonic()
            pred[name]=np.clip(m.predict(x.loc[~train,columns]),*limits)
            timing[name+'_predict_seconds']=time.monotonic()-start
    pred['dc']=np.where(target.pos.eq(1),0,pred['dc'])
    out=target.rename(columns={'GW':'gameweek','pos':'position','total_points':'actual'})
    for n,v in pred.items():out['conditional_'+n]=v
    out['conditional_card']=card_return
    for arm,source in [('old','control'),('new','structured')]:
        p=bykey[source].to_numpy(float);out[arm+'_p']=p
        out[arm+'_p_card']=(1-p)*card_rate
        out[arm+'_xp']=p*(pred['core']+2*pred['dc'])+(1-p)*card_rate*card_return;out[arm+'_minutes']=p*pred['minutes']
    return out,dict(training_rows=int(train.sum()),appearing_training_rows=int(appearing.sum()),conditional_dc_rows=int(dc_train.sum()),card_prior=dict(training_only=True,nonappearance_rows=int(zero.sum()),card_only_rows=int(card.sum()),conditional_card_rate=card_rate,conditional_card_return=card_return),timing=timing)


def metrics(frame):
    groups=frame.groupby(['season','gameweek','fpl_code'])
    if groups.candidate.nunique().ne(1).any():raise ValueError('DGW candidate inconsistency')
    g=groups.agg(actual=('actual','sum'),candidate=('candidate','first'),old=('old_xp','sum'),new=('new_xp','sum')).reset_index()
    result={}
    for name,lo,hi in [('validation',20,27),('audit',28,38)]:
        z=g[g.gameweek.between(lo,hi)];c=z[z.candidate]
        if set(c.gameweek)!=set(range(lo,hi+1)):raise ValueError('Incomplete candidate window')
        m={a:dict(candidates=point_scores(c,a),all=point_scores(z,a)) for a in ['old','new']}
        result[name]=dict(metrics=m,paired=paired_block_errors(c,'new','old'))
    return result


def run(manifest,manifest_hash,head_path,head_hash,output,*,trust_local_cache=False):
    if file_hash(manifest)!=manifest_hash or file_hash(head_path)!=head_hash:raise ValueError('Input checksum mismatch')
    output=Path(output)
    if output.exists():raise ValueError('Output exists')
    spec=json.loads(Path(manifest).read_text());d,x,bridge=load(spec,trust_local_cache=trust_local_cache)
    frame,report=fit_returns(d,x,pd.read_csv(head_path))
    frame['fpl_code']=frame.element.map(bridge.set_index('id').code).astype(int)
    report.update(policy=POLICY,environment=spec['environment'],metrics=metrics(frame),model_promotion=False,
        manifest_sha256=manifest_hash,head_sha256=head_hash,code_sha256=file_hash(Path(__file__)),
        protocol_sha256=file_hash(Path(__file__).parent/'fpl_predict_resources/conditional_selection_protocol.json'))
    output.mkdir(parents=True);frame.to_csv(output/'predictions.csv',index=False)
    report['predictions_sha256']=file_hash(output/'predictions.csv')
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['manifest','head','output']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--manifest-sha256',required=True);p.add_argument('--head-sha256',required=True)
    p.add_argument('--trust-local-cache',action='store_true');a=p.parse_args()
    run(a.manifest,a.manifest_sha256,a.head,a.head_sha256,a.output,trust_local_cache=a.trust_local_cache)


if __name__=='__main__':main()
