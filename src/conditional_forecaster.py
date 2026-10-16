"""Persistable conditional forecaster; experimental until registry qualification."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from availability_evidence import utc
from fpl_model import CORE_FEATURES, DC_FEATURES, fit_estimator, sample_weights
SIGNALS=['availability_chance','availability_missing']


def missing_availability(x):
    out=x.copy();out[SIGNALS[0]]=0.;out[SIGNALS[1]]=1.
    return out


def current_availability(x,target,bootstrap,retrieved_at):
    """Use official labels only for their next GW, never as assigned probabilities."""
    if not x.index.equals(target.index) or not x.index.is_unique:raise ValueError('Unaligned inference rows')
    events=[e for e in bootstrap['events'] if e.get('is_next')]
    if len(events)!=1:raise ValueError('Require one next gameweek')
    event=events[0];stamp=utc(retrieved_at);deadline=utc(event['deadline_time'])
    if stamp>=deadline:raise ValueError('Availability snapshot is not predeadline')
    listed={}
    for p in bootstrap['elements']:
        ident=p['id']
        if ident in listed:raise ValueError('Duplicate roster identity')
        listed[ident]=p
    out=missing_availability(x);known=0;next_rows=0
    for i,r in target.iterrows():
        if r.element not in listed:raise ValueError('Unknown inference identity')
        p=listed[r.element]
        if int(r.pos)!=p['element_type']:raise ValueError('Inference position conflict')
        cutoff=utc(r.cutoff)
        if cutoff!=stamp:raise ValueError('Availability and feature snapshot clocks differ')
        if r.GW!=event['id']:continue
        next_rows+=1;value=p.get('chance_of_playing_next_round')
        if value is None:continue
        chance=float(value)
        if not np.isfinite(chance) or not 0<=chance<=100:raise ValueError('Invalid chance covariate')
        out.loc[i,SIGNALS]=[chance/100.,0.];known+=1
    return out,dict(scope='Official snapshot label learned as covariate for next GW only; later horizons missing',
        retrieved_at=stamp.isoformat(),deadline=deadline.isoformat(),next_gw=event['id'],next_fixture_rows=next_rows,
        known_label_fixture_rows=known,later_fixture_rows=int(len(target)-next_rows))


@dataclass
class ConditionalForecaster:
    core:object
    played:object
    minutes:object
    sixty:object
    dc:object
    card_rate:float
    card_return:float
    residual_intervals:dict
    metadata:dict
    requires_availability=True

    def predict(self,x,pos):
        if set(CORE_FEATURES+DC_FEATURES+SIGNALS)-set(x):raise ValueError('Missing conditional model features')
        if len(pos)!=len(x) or not np.isin(np.asarray(pos),(1,2,3,4)).all():raise ValueError('Invalid inference positions')
        a=x[SIGNALS].to_numpy(float)
        if not np.isfinite(a).all() or not np.isin(a[:,1],[0.,1.]).all() or (a[:,0]<0).any() or (a[:,0]>1).any() or ((a[:,1]==1)&(a[:,0]!=0)).any():raise ValueError('Invalid availability encoding')
        with threadpool_limits(limits=2):
            p=np.clip(self.played.predict(x[CORE_FEATURES+SIGNALS]),0,1)
            q=np.clip(self.core.predict(x[CORE_FEATURES]),0,20)
            minutes=p*np.clip(self.minutes.predict(x[CORE_FEATURES]),1,90)
            sixty=np.minimum(p,np.clip(self.sixty.predict(x[CORE_FEATURES]),0,1))
            dc=np.zeros(len(x)) if self.dc is None else np.where(np.asarray(pos)==1,0,p*np.clip(self.dc.predict(x[DC_FEATURES]),0,1))
        core=p*q+(1-p)*self.card_rate*self.card_return
        out=pd.DataFrame(dict(core_xp=core,dc_xp=2*dc,expected_points=core+2*dc,
            expected_minutes=minutes,p_play=p,p60=sixty),index=x.index)
        if not np.isfinite(out.to_numpy()).all():raise ValueError('Nonfinite model output')
        return out


def fit(d,x,train,version='conditional-qualification-v1'):
    """One fixed learner specification. No evaluation rows affect fitting/weights."""
    if not d.index.equals(x.index) or not train.index.equals(d.index):raise ValueError('Unaligned training')
    if not train.any():raise ValueError('No training rows')
    earlier=d.loc[train];features=x.loc[train];weights=pd.Series(sample_weights(earlier),index=earlier.index)
    playing=earlier.played.eq(1);zero=~playing;cards=(earlier.yellow_cards+earlier.red_cards).gt(0);card=zero&cards
    if not zero.any() or not playing.any():raise ValueError('Need playing and nonplaying training rows')
    if (zero&earlier.points_core.ne(0)&~cards).any():raise ValueError('Unexplained training zero-minute points')
    rate=float(weights[card].sum()/weights[zero].sum())
    card_return=float(np.average(earlier.loc[card,'points_core'],weights=weights[card])) if card.any() else 0.
    with threadpool_limits(limits=2):
        core=fit_estimator('hgb7',features.loc[playing,CORE_FEATURES],earlier.loc[playing,'points_core'],weights[playing])
        played=fit_estimator('hgb7',features[CORE_FEATURES+SIGNALS],earlier.played,weights)
        minutes=fit_estimator('hgb7',features.loc[playing,CORE_FEATURES],earlier.loc[playing,'minutes'],weights[playing])
        sixty=fit_estimator('hgb7',features[CORE_FEATURES],earlier.sixty,weights)
        dc_rows=playing&earlier.dc_hit.notna()
        dc=fit_estimator('hgb7',features.loc[dc_rows,DC_FEATURES],earlier.loc[dc_rows,'dc_hit'],weights[dc_rows]) if dc_rows.any() else None
    metadata=dict(version=version,architecture='conditional-availability-v1',training_rows=len(earlier),
        training_seasons=sorted(earlier.season.unique()),training_label_complete=(pd.to_datetime(earlier.ts,utc=True).max()+pd.Timedelta(hours=3)).isoformat(),
        appearing_training_rows=int(playing.sum()),dc_training_rows=int(dc_rows.sum()),
        card_prior=dict(nonappearance_rows=int(zero.sum()),card_only_rows=int(card.sum()),rate=rate,mean_return=card_return),
        approval='experimental, no registry promotion',intervals='not calibrated; do not interpret zero offsets as confidence intervals')
    return ConditionalForecaster(core,played,minutes,sixty,dc,rate,card_return,{str(p):[0.,0.] for p in range(1,5)},metadata)


def predict_current(model,x,pos,target,bootstrap,retrieved_at):
    if not getattr(model,'requires_availability',False):return model.predict(x,pos),None
    augmented,report=current_availability(x,target,bootstrap,retrieved_at)
    return model.predict(augmented,pos),report
