"""Locked temporal experiment, held-out metrics and final local model artifact."""
import hashlib
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import time
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from fpl_model import *

from runtime import workspace_root
ROOT = workspace_root()
ART=ROOT/"artifacts"

def save(name,obj):
    (ART/name).write_text(json.dumps(obj,indent=2,default=str)+"\n")

def summary(d,x,p):
    out={}
    for label,mask in [("all",np.ones(len(d),dtype=bool)),("candidates",candidate_mask(x))]+[(f"position_{v}",candidate_mask(x)&(d.pos==v)) for v in range(1,5)]:
        out[label]={name:metrics(d.points_core[mask],values[mask]) for name,values in p.items()}
    return out

def captain_replay(d,x,p):
    z=d[["season","GW","element","name","points_core"]].copy()
    z["eligible"]=candidate_mask(x).to_numpy()
    for name,values in p.items(): z[name]=np.asarray(values)
    # All fixtures in a double count together; every fixture has the same cutoff.
    g=z.groupby(["season","GW","element","name"],as_index=False).agg({"points_core":"sum","eligible":"max",**{name:"sum" for name in p}})
    g=g[g.eligible].copy();rows=[]
    for (season,gw),v in g.groupby(["season","GW"]):
        row={"season":season,"GW":int(gw)}
        for name in p:
            chosen=v.sort_values([name,"element"],ascending=[False,True]).iloc[0]
            row[name+"_player"]=chosen["name"];row[name+"_points"]=float(chosen.points_core)
        rows.append(row)
    return pd.DataFrame(rows)

def block_ci(values,seed=31):
    # Contiguous 4-GW moving blocks, sampled within each season independently.
    rng=np.random.default_rng(seed);boot=[]
    arrays=[np.asarray(v) for v in values]
    for _ in range(2000):
        allv=[]
        for a in arrays:
            starts=rng.integers(0,len(a),size=int(np.ceil(len(a)/4)))
            allv.extend(np.concatenate([a[(s+np.arange(4))%len(a)] for s in starts])[:len(a)])
        boot.append(float(np.mean(allv)))
    return {"mean":float(np.mean(np.concatenate(arrays))),"ci95":np.quantile(boot,[.025,.975]).tolist(),"block_gameweeks":4}

def run():
    ART.mkdir(exist_ok=True);start=time.time()
    d=pd.read_pickle(ROOT/"artifacts/history.pkl");x=pd.read_pickle(ROOT/"artifacts/features.pkl")
    tr=d.season.isin(["2020-21","2021-22","2022-23"]);va=d.season=="2023-24"
    assert d[tr].ts.max()<d[va].cutoff.min()
    assert not d.duplicated(["season","element","fixture"]).any()
    assert set(CORE_FEATURES).isdisjoint({"xP","total_points","minutes","value","element","name","selected","team_h_score","team_a_score"})
    scores=[];fitted={};pool=candidate_mask(x[va]).to_numpy()
    for name in ["ridge","hgb7","hgb15","hgb31"]:
        m=fit_estimator(name,x.loc[tr,CORE_FEATURES],d.loc[tr,"points_core"],sample_weights(d[tr]));fitted[name]=m
        raw=np.clip(m.predict(x.loc[va,CORE_FEATURES]),0,20)
        for blend in [.5,.75,1.]:
            pred=blend*raw+(1-blend)*x.loc[va,"ew4_points_core"].to_numpy()
            scores.append({"name":name,"blend":blend,**metrics(d.loc[va,"points_core"].to_numpy()[pool],pred[pool])})
        print('validation fitted',name,flush=True)
    choice=min(scores,key=lambda z:(z['rmse'],z['mae']))
    validation_base={name:metrics(d.loc[va,"points_core"].to_numpy()[pool],x.loc[va,col].to_numpy()[pool]) for name,col in [('last5','last5_points'),('ewm','ew4_points_core')]}
    lock={"choice":choice,"candidates":scores,"baselines":validation_base,"train_seasons":sorted(d[tr].season.unique()),"validation_season":"2023-24","locked_before_holdout_evaluation":True,"protocol_sha256":hashlib.sha256((ROOT/'EXPERIMENT_PROTOCOL.md').read_bytes()).hexdigest()}
    save('selection_lock.json',lock)
    coreval=choice['blend']*np.clip(fitted[choice['name']].predict(x.loc[va,CORE_FEATURES]),0,20)+(1-choice['blend'])*x.loc[va,'ew4_points_core'].to_numpy()
    intervals={str(pos):np.quantile((d.loc[va,'points_core'].to_numpy()-coreval)[d.loc[va,'pos'].to_numpy()==pos],[.1,.9]).tolist() for pos in range(1,5)}
    results={};oof=[];captains=[]
    for season in ['2024-25','2025-26']:
        train=d.season<season;test=d.season==season
        assert d.loc[train,'ts'].max()<d.loc[test,'cutoff'].min()
        m=fit_estimator(choice['name'],x.loc[train,CORE_FEATURES],d.loc[train,'points_core'],sample_weights(d[train]))
        pred=choice['blend']*np.clip(m.predict(x.loc[test,CORE_FEATURES]),0,20)+(1-choice['blend'])*x.loc[test,'ew4_points_core'].to_numpy()
        p={'model':pd.Series(pred,index=d[test].index),'last5':x.loc[test,'last5_points'],'ewm':x.loc[test,'ew4_points_core']}
        results[season]=summary(d[test],x[test],p)
        out=d.loc[test,['season','GW','element','fixture','name','pos','points_core','total_points','cutoff']].copy()
        for k,v in p.items():out[k]=v
        out['candidate']=candidate_mask(x[test]);out['interval_lower']=[max(-3,v+intervals[str(int(pos))][0]) for v,pos in zip(pred,d.loc[test,'pos'])];out['interval_upper']=[v+intervals[str(int(pos))][1] for v,pos in zip(pred,d.loc[test,'pos'])]
        results[season]['interval80_coverage']=float(((out.points_core>=out.interval_lower)&(out.points_core<=out.interval_upper)).mean())
        oof.append(out);captains.append(captain_replay(d[test],x[test],p))
        print('held-out complete',season,flush=True)
    out=pd.concat(oof);out.to_json(ART/'heldout_predictions.jsonl',orient='records',lines=True,date_format='iso')
    cap=pd.concat(captains);cap.to_json(ART/'captain_replay.jsonl',orient='records',lines=True)
    pooled={k:metrics(out.loc[out.candidate,'points_core'],out.loc[out.candidate,k]) for k in ['model','last5','ewm']}
    gains={}
    for base in ['last5','ewm']:
        gains[base]=block_ci([g.model_points.to_numpy()-g[base+'_points'].to_numpy() for _,g in cap.groupby('season')])
        gains[base]['total_captain_bonus_point_difference']=float((cap.model_points-cap[base+'_points']).sum())
    # Minutes/event learners: no model selection on final test outcomes.
    aux={};aux_metrics={};aux_test={}
    for target,baseline in [('minutes','ew4_minutes'),('played','ew4_played'),('sixty','ew4_sixty')]:
        model=fit_estimator('hgb7',x.loc[tr,CORE_FEATURES],d.loc[tr,target],sample_weights(d[tr]))
        pv=np.clip(model.predict(x.loc[va,CORE_FEATURES]),0,90 if target=='minutes' else 1)
        aux_metrics[target]={'validation':metrics(d.loc[va,target],pv),'validation_baseline':metrics(d.loc[va,target],x.loc[va,baseline])}
        # Fixed hgb7 auxiliary architecture, reported independently from core acceptance.
        train=d.season<'2025-26';test=d.season=='2025-26'
        model=fit_estimator('hgb7',x.loc[train,CORE_FEATURES],d.loc[train,target],sample_weights(d[train]))
        pt=np.clip(model.predict(x.loc[test,CORE_FEATURES]),0,90 if target=='minutes' else 1)
        aux_test[target]=pd.Series(pt,index=d[test].index)
        aux_metrics[target]['test_2025_26']=metrics(d.loc[test,target],pt)
        aux_metrics[target]['test_baseline']=metrics(d.loc[test,target],x.loc[test,baseline])
        cand=candidate_mask(x[test])
        aux_metrics[target]['test_candidates']=metrics(d.loc[test,target][cand],pt[cand])
        aux_metrics[target]['test_candidates_baseline']=metrics(d.loc[test,target][cand],x.loc[test,baseline][cand])
        if target!='minutes':
            aux_metrics[target]['brier']=float(np.mean((pt-d.loc[test,target].to_numpy())**2))
            bins=[]
            for lo in np.arange(0,1,.1):
                sel=(pt>=lo)&(pt<(lo+.1) if lo<.9 else pt<=1)
                if sel.any():bins.append({'lo':float(lo),'n':int(sel.sum()),'predicted':float(pt[sel].mean()),'observed':float(d.loc[test,target].to_numpy()[sel].mean())})
            aux_metrics[target]['calibration_bins']=bins
        aux[target]=fit_estimator('hgb7',x[CORE_FEATURES],d[target],sample_weights(d))
    # DC development has distinct temporal boundaries; do not claim full-season held-out DC.
    year=d.season=='2025-26';dc_tr=year&(d.GW<=19);dc_va=year&(d.GW.between(20,27));dc_te=year&(d.GW>=28)
    assert d.loc[dc_tr,'ts'].max()<d.loc[dc_va,'cutoff'].min()
    assert d.loc[dc_va,'ts'].max()<d.loc[dc_te,'cutoff'].min()
    dm=fit_estimator('hgb7',x.loc[dc_tr,DC_FEATURES],d.loc[dc_tr,'dc_hit'],sample_weights(d[dc_tr]))
    vpred=np.where(d.loc[dc_va,'pos']==1,0,np.clip(dm.predict(x.loc[dc_va,DC_FEATURES]),0,1))
    vbase=np.where(d.loc[dc_va,'pos']==1,0,x.loc[dc_va,'dc_rate4'])
    dcval={'hgb7':metrics(d.loc[dc_va,'dc_hit'],vpred),'ewm':metrics(d.loc[dc_va,'dc_hit'],vbase)}
    dcname=min(dcval,key=lambda k:dcval[k]['rmse'])
    save('dc_selection_lock.json',{'choice':dcname,'validation':dcval,'train':'2025-26 GW1-19','validation_gws':'20-27','test_gws':'28-38'})
    dm=fit_estimator('hgb7',x.loc[dc_tr|dc_va,DC_FEATURES],d.loc[dc_tr|dc_va,'dc_hit'],sample_weights(d[dc_tr|dc_va]))
    dpred=np.where(d.loc[dc_te,'pos']==1,0,np.clip(dm.predict(x.loc[dc_te,DC_FEATURES]),0,1) if dcname=='hgb7' else x.loc[dc_te,'dc_rate4'])
    # Match production coherence rule: earning the award requires appearing.
    dpred=np.minimum(dpred,aux_test['played'].loc[d[dc_te].index].to_numpy())
    dcbase=np.where(d.loc[dc_te,'pos']==1,0,x.loc[dc_te,'dc_rate4'])
    dctest=metrics(d.loc[dc_te,'dc_hit'],dpred);dctest['brier']=dctest['rmse']**2
    common=out[(out.season=='2025-26')&(out.GW>=28)].copy()
    assert common.index.equals(d[dc_te].index)
    common['full_model']=common.model+2*dpred
    common['full_last5']=common.last5+2*dcbase
    common['full_ewm']=common['ewm']+2*dcbase
    full={k:metrics(common.loc[common.candidate,'total_points'],common.loc[common.candidate,k]) for k in ['full_model','full_last5','full_ewm']}
    improve=1-pooled['model']['rmse']/pooled['last5']['rmse']
    gates={'pooled_core_rmse_improvement_at_least_1pct':improve>=.01,'each_test_season_within_2pct_of_ewm':all(results[s]['candidates']['model']['rmse']<=1.02*results[s]['candidates']['ewm']['rmse'] for s in results)}
    finalcore=fit_estimator(choice['name'],x[CORE_FEATURES],d.points_core,sample_weights(d))
    finaldc=fit_estimator('hgb7',x.loc[year,DC_FEATURES],d.loc[year,'dc_hit'],sample_weights(d[year])) if dcname=='hgb7' else None
    meta={'version':'1.0.0','core_choice':choice,'training_seasons':sorted(d.season.unique()),'trained_rows':len(d),'feature_columns':CORE_FEATURES,'dc_feature_columns':DC_FEATURES,'protocol_sha256':lock['protocol_sha256'],'source_commit':json.loads((ROOT/'data/historical/manifest.json').read_text())['commit'],'point_gates_passed':all(gates.values()),'seconds':round(time.time()-start,2)}
    model=ForecastModel(finalcore,choice['name'],choice['blend'],aux['minutes'],aux['played'],aux['sixty'],finaldc,dcname,intervals,meta)
    joblib.dump(model,ART/'model.joblib')
    reloaded=joblib.load(ART/'model.joblib')
    assert np.allclose(model.predict(x.head(50),d.pos.head(50)).expected_points,reloaded.predict(x.head(50),d.pos.head(50)).expected_points)
    report={'metadata':meta,'selection':lock,'heldout_by_season':results,'pooled_candidates':pooled,'captain_bonus_comparison':gains,'auxiliary':aux_metrics,'dc':{'selected':dcname,'validation':dcval,'test':dctest,'test_baseline':metrics(d.loc[dc_te,'dc_hit'],dcbase),'full_score_candidate_test':full},'numeric_acceptance':gates,'core_rmse_improvement':improve,'remaining_acceptance':['adversarial leakage and planning tests','current forecast smoke test','documentation and workflow integration']}
    save('evaluation.json',report)
    print(json.dumps({'choice':choice,'pooled':pooled,'gates':gates,'captain':gains,'dc':report['dc'],'seconds':meta['seconds']},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--reproduce',action='store_true');args=parser.parse_args()
    if (ART/'evaluation.json').exists():
        if not args.reproduce:raise SystemExit('An evaluated model already exists. Use --reproduce to write a separate experiment without overwriting it.')
        ART=ART/'reproductions'/dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')
    with threadpool_limits(limits=4): run()
