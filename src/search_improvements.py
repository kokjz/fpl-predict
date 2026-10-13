"""Bounded development-only iteration; final audit outcomes are never loaded here."""
import argparse,hashlib,json,time
from pathlib import Path
import joblib,numpy as np,pandas as pd
from threadpoolctl import threadpool_limits
from fpl_model import candidate_mask,metrics
from candidate_models import fit_spec

from runtime import workspace_root
ROOT = workspace_root()
OUT=ROOT/'experiments/I1'
FOLDS=['2022-23','2023-24']

def main():
    if (OUT/'finalist_lock.json').exists():raise FileExistsError('Completed experiment is immutable; choose a new --output-dir')
    OUT.mkdir(parents=True,exist_ok=True)
    start=time.time();all_d=pd.read_pickle(ROOT/'artifacts/history.pkl');all_x=pd.read_pickle(ROOT/'artifacts/features.pkl')
    # Drop later rows before any development operation, even aggregate summaries.
    d=all_d[all_d.season<='2023-24'];x=all_x.loc[d.index];del all_d,all_x
    records=[];preds={};models={};specs={}
    def trial(name,spec,stage):
        if name in specs:return
        specs[name]=spec;foldscores={};preds[name]={};models[name]={}
        yy=[];pp=[]
        for fold in FOLDS:
            tr=d.season<fold;va=d.season==fold
            assert d[tr].ts.max()<d[va].cutoff.min()
            m=fit_spec(spec,x[tr],d[tr]);p=m.predict(x[va]);pool=candidate_mask(x[va]).to_numpy()
            preds[name][fold]=p;models[name][fold]=m;foldscores[fold]=metrics(d.loc[va,'points_core'].to_numpy()[pool],p[pool])
            yy.extend(d.loc[va,'points_core'].to_numpy()[pool]);pp.extend(p[pool])
        rec={'name':name,'stage':stage,'spec':spec,'pooled':metrics(yy,pp),'folds':foldscores};records.append(rec)
        (OUT/'development_trials.json').write_text(json.dumps(records,indent=2)+'\n')
        print(name,round(rec['pooled']['rmse'],6),round(rec['pooled']['mae'],6),flush=True)
    trial('v1',{'kind':'incumbent'},'baseline')
    stage_a={
      'rates_shallow':{'kind':'direct'},
      'rates_deeper':{'kind':'direct','leaves':15,'l2':50.,'min_leaf':100},
      'rates_regularised':{'kind':'direct','l2':100.,'min_leaf':160},
      'minutes_hurdle':{'kind':'hurdle','leaves':7,'l2':50.},
      'candidate_weighted':{'kind':'direct','candidate_weight':2.},
      'recent_weighted':{'kind':'direct','half_days':365.25},
      'raw_deeper':{'kind':'direct','enhanced':False,'leaves':15,'l2':50.}
    }
    for name,spec in stage_a.items():trial(name,spec,'A_structure')
    best_a=min((r for r in records if r['name']!='v1'),key=lambda r:(r['pooled']['rmse'],r['pooled']['mae']))
    base=best_a['spec']
    refinements=[{'iters':450,'lr':.03},{'l2':200.,'min_leaf':160},{'half_days':365.25},{'candidate_weight':2.}]
    for i,change in enumerate(refinements,1):
        s={**base,**change}
        if any(s==other for other in specs.values()):continue
        trial(f'refine_{i}',s,'B_refine')
    ranked=sorted((r for r in records if r['name']!='v1'),key=lambda r:(r['pooled']['rmse'],r['pooled']['mae']))
    best,second=ranked[:2];best_before=best['pooled']['rmse']
    def blend(name,left,right,w):
        # Use cached out-of-fold predictions, not refitting or selecting on audits.
        spec={'kind':'blend','members':[specs[left],specs[right] if right!='ewm' else {'kind':'ewm'}],'weights':[w,1-w]};specs[name]=spec;preds[name]={}
        yy=[];pp=[];foldscores={}
        for fold in FOLDS:
            va=d.season==fold;pool=candidate_mask(x[va]).to_numpy()
            p=w*preds[left][fold]+(1-w)*(preds[right][fold] if right!='ewm' else x.loc[va,'ew4_points_core'].to_numpy())
            preds[name][fold]=p;foldscores[fold]=metrics(d.loc[va,'points_core'].to_numpy()[pool],p[pool]);yy.extend(d.loc[va,'points_core'].to_numpy()[pool]);pp.extend(p[pool])
        rec={'name':name,'stage':'C_ensemble','spec':spec,'pooled':metrics(yy,pp),'folds':foldscores};records.append(rec)
        print(name,round(rec['pooled']['rmse'],6),flush=True)
    for other in [second['name'],'v1','ewm']:
        for w in [.5,.75]:blend(f'blend_{other}_{w}',best['name'],other,w)
    best_c=min(records,key=lambda r:(r['pooled']['rmse'],r['pooled']['mae']))
    stage_c_gain=1-best_c['pooled']['rmse']/best_before
    if stage_c_gain>=.0015 and best_c['spec']['kind']=='blend':
        # The predeclared final refinement keeps the same members and changes 75/25 to 25/75.
        spec=best_c['spec'];w=.25
        left=next(k for k,v in specs.items() if v==spec['members'][0]);right=next((k for k,v in specs.items() if v==spec['members'][1]),'ewm')
        blend('blend_final_25_75',left,right,w)
    champion=records[0]
    eligible=[r for r in records if r['name']!='v1' and r['pooled']['rmse']<=.995*champion['pooled']['rmse'] and all(r['folds'][s]['rmse']<=1.005*champion['folds'][s]['rmse'] for s in FOLDS)]
    finalist=min(eligible,key=lambda r:(r['pooled']['rmse'],r['pooled']['mae'])) if eligible else None
    lock={'incumbent':champion,'finalist':finalist,'trial_count':len(records)-1,'stage_c_gain':stage_c_gain,'seconds':time.time()-start,'protocol_sha256':hashlib.sha256((ROOT/'IMPROVEMENT_PROTOCOL.md').read_bytes()).hexdigest(),'audit_results_consulted':False,'current_season_results_scored':False,'stopping_rule':'Three predeclared families completed; at most one extra blend refinement; next stage is a single locked audit, no adaptive retries.'}
    (OUT/'development_trials.json').write_text(json.dumps(records,indent=2)+'\n');(OUT/'finalist_lock.json').write_text(json.dumps(lock,indent=2)+'\n')
    joblib.dump({'predictions':preds,'specifications':specs},OUT/'development_predictions.joblib')
    print('LOCK',json.dumps(lock,indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir');args=parser.parse_args()
    if args.output_dir:OUT=Path(args.output_dir)
    with threadpool_limits(limits=4):main()
