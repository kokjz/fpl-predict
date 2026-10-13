"""One bounded second experiment; no later audit data consulted."""
import argparse,hashlib,json,time
from pathlib import Path
import joblib,numpy as np,pandas as pd
from threadpoolctl import threadpool_limits
from candidate_models import fit_spec
from fpl_model import metrics,candidate_mask

from runtime import workspace_root
ROOT = workspace_root()

def main(destination=None):
    out=Path(destination) if destination else ROOT/'experiments/I2';out.mkdir(parents=True,exist_ok=False);start=time.time()
    d=pd.read_pickle(ROOT/'artifacts/history.pkl');d=d[d.season<='2023-24'];x=pd.read_pickle(ROOT/'artifacts/features.pkl').loc[d.index]
    base=json.loads((ROOT/'experiments/I1/finalist_lock.json').read_text())['incumbent'];trials=[];preds={}
    for alpha,enhanced in [(.25,False),(.5,False),(.75,False),(.5,True)]:
        spec={'kind':'direct','enhanced':enhanced,'target_smoothing':alpha,'leaves':7,'iters':200,'lr':.05,'l2':20.,'min_leaf':60}
        name=f'xg_target_{alpha}_'+('enhanced' if enhanced else 'original');yy=[];pp=[];folds={};preds[name]={}
        for season in ['2022-23','2023-24']:
            train=d.season<season;test=d.season==season;assert d[train].ts.max()<d[test].cutoff.min()
            model=fit_spec(spec,x[train],d[train]);pred=model.predict(x[test]);pool=candidate_mask(x[test]).to_numpy()
            folds[season]=metrics(d.loc[test,'points_core'].to_numpy()[pool],pred[pool]);yy.extend(d.loc[test,'points_core'].to_numpy()[pool]);pp.extend(pred[pool]);preds[name][season]=pred
        r={'name':name,'spec':spec,'pooled':metrics(yy,pp),'folds':folds};trials.append(r);print(name,r['pooled'],flush=True)
        (out/'development_trials.json').write_text(json.dumps(trials,indent=2)+'\n')
    eligible=[r for r in trials if r['pooled']['rmse']<=.995*base['pooled']['rmse'] and all(r['folds'][s]['rmse']<=1.005*base['folds'][s]['rmse'] for s in r['folds'])]
    finalist=min(eligible,key=lambda r:(r['pooled']['rmse'],r['pooled']['mae'])) if eligible else None
    lock={'incumbent':base,'finalist':finalist,'trial_count':len(trials),'seconds':time.time()-start,'protocol_sha256':hashlib.sha256((ROOT/'I2_PROTOCOL.md').read_bytes()).hexdigest(),'audit_results_consulted':False,'current_season_results_scored':False,'stopping_rule':'Last distinct bounded hypothesis after I1; retain v1 if no finalist or if the single locked finalist fails final gates.'}
    (out/'finalist_lock.json').write_text(json.dumps(lock,indent=2)+'\n');joblib.dump({'predictions':preds},out/'development_predictions.joblib');print('LOCK',json.dumps(lock,indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir');args=parser.parse_args()
    with threadpool_limits(limits=4):main(args.output_dir)
