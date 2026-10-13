"""I1 candidates: deterministic transformations of already time-safe features."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from fpl_model import CORE_FEATURES,fit_estimator,candidate_mask

def enhance(x):
    z=x[CORE_FEATURES].copy()
    score_goal=10*z.pos_1+6*z.pos_2+5*z.pos_3+4*z.pos_4
    for half in (4,12):
        minutes=z[f'ew{half}_minutes'].clip(lower=15)
        play=z[f'ew{half}_played'].clip(lower=.15)
        for stat in ['goals_scored','assists','expected_goals','expected_assists','threat','creativity','bonus','saves','points_core']:
            z[f'per90_{half}_{stat}']=90*z[f'ew{half}_{stat}']/minutes
        z[f'conditional_points_{half}']=z[f'ew{half}_points_core']/play
        z[f'conditional_minutes_{half}']=z[f'ew{half}_minutes']/play
        z[f'attack_matchup_{half}']=z[f'team_ew{half}_gf']*z[f'opp_ew{half}_ga']/1.35
        z[f'defence_matchup_{half}']=z[f'team_ew{half}_ga']*z[f'opp_ew{half}_gf']/1.35
        z[f'xgi_points_{half}']=score_goal*z[f'per90_{half}_expected_goals']+3*z[f'per90_{half}_expected_assists']
        z[f'finishing_gap_{half}']=z[f'per90_{half}_goals_scored']-z[f'per90_{half}_expected_goals']
    for stat in ['minutes','points_core','played','sixty','expected_goals','expected_assists','threat']:
        z['trend_'+stat]=z['ew4_'+stat]-z['ew12_'+stat]
    z['last_minutes_vs_form']=z.last_minutes-z.ew4_minutes
    z['recent_minutes_vs_form']=z.last5_minutes-z.ew12_minutes
    z['role_stability']=z.ew4_sixty/z.ew4_played.clip(lower=.15)
    z['history_reliability']=z.n_history/(z.n_history+6.)
    return z

class CandidateCore:
    def __init__(self,spec):self.spec=spec

    def fit(self,x,rows):
        if self.spec['kind']=='incumbent':
            age=(rows.ts.max()-rows.ts).dt.total_seconds().to_numpy()/86400
            self.model=fit_estimator('hgb7',x[CORE_FEATURES],rows.points_core,np.power(.5,age/730.5));return self
        self.enhanced=self.spec.get('enhanced',True)
        xx=enhance(x) if self.enhanced else x[CORE_FEATURES]
        age=(rows.ts.max()-rows.ts).dt.total_seconds().to_numpy()/86400
        weights=np.power(.5,age/self.spec.get('half_days',730.5))
        weights*=np.where(candidate_mask(x),self.spec.get('candidate_weight',1.),1.)
        params=dict(max_leaf_nodes=self.spec.get('leaves',7),max_iter=self.spec.get('iters',250),learning_rate=self.spec.get('lr',.04),l2_regularization=self.spec.get('l2',30.),min_samples_leaf=self.spec.get('min_leaf',80),early_stopping=False,random_state=20260921)
        self.model=HistGradientBoostingRegressor(**params)
        target=rows.points_core.copy()
        if self.spec.get('target_smoothing',0):
            valid=rows.expected_goals.notna()&rows.expected_assists.notna()&(rows.pos!=1)
            goal_points=np.where(rows.pos==2,6,np.where(rows.pos==3,5,4))
            adjustment=goal_points*(rows.expected_goals-rows.goals_scored)+3*(rows.expected_assists-rows.assists)
            target.loc[valid]+=self.spec['target_smoothing']*adjustment.loc[valid]
        if self.spec['kind']=='hurdle':
            self.appearance=HistGradientBoostingRegressor(**params)
            self.appearance.fit(xx,rows.played,sample_weight=weights)
            eligible=rows.played>0
            self.model.fit(xx[eligible],target[eligible],sample_weight=weights[eligible])
        else:self.model.fit(xx,target,sample_weight=weights)
        return self

    def predict(self,x):
        if self.spec['kind']=='incumbent':return np.clip(self.model.predict(x[CORE_FEATURES]),0,20)
        xx=enhance(x) if self.enhanced else x[CORE_FEATURES]
        out=self.model.predict(xx)
        if self.spec['kind']=='hurdle':out*=np.clip(self.appearance.predict(xx),0,1)
        return np.clip(out,0,20)

class BlendCore:
    def __init__(self,models,weights):self.models=models;self.weights=weights
    def predict(self,x):
        return sum(w*(x.ew4_points_core.to_numpy() if m is None else m.predict(x)) for m,w in zip(self.models,self.weights))

def fit_spec(spec,x,rows):
    if spec['kind']=='blend':
        return BlendCore([None if s['kind']=='ewm' else fit_spec(s,x,rows) for s in spec['members']],spec['weights'])
    return CandidateCore(spec).fit(x,rows)
