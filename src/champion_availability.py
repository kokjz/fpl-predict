"""Availability admission for a separately registered conditional champion.

Official and reviewed chance labels are learned covariates, never output factors.
No retrieval, registry selection, model fitting or artifact writes occur here.
"""
from copy import deepcopy
import hashlib
import json
import numpy as np
import pandas as pd
from availability_evidence import scoped_overrides, utc
from conditional_forecaster import current_availability, SIGNALS

POLICY_KEY='champion_availability_p6'
POLICY_SHA256=hashlib.sha256(b'conditional-champion-next-gw-label-only-p6-v1').hexdigest()


def reviewed_labels(document,bootstrap,generated_at):
    """Validate the existing evidence envelope with a label-only assumption."""
    surrogate=deepcopy(document)
    labels={}
    for entry in surrogate['players']:
        if type(entry['id']) is not int or entry['id']<1:
            raise ValueError('Invalid reviewed football player identity')
        if 'minutes' in entry or 'availability' in entry:
            raise ValueError('P6 refuses next-GW availability/minutes output scaling')
        keys=set(entry)&{'chance','out'}
        if len(keys)!=1:
            raise ValueError('P6 requires exactly one chance or out replacement label')
        key=keys.pop();value=entry[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value):
            raise ValueError('Invalid replacement chance label')
        if (key=='chance' and value not in (0,25,50,75,100)) or (key=='out' and value!=0):
            raise ValueError('Invalid replacement chance label')
        labels[entry['id']]=float(value)
        del entry[key]
        # Reuse the frozen timing/source/identity validator; this surrogate
        # scaling assumption is validation-only and never reaches predictions.
        entry['availability']=0.
    gw,recorded,validated=scoped_overrides(surrogate,bootstrap,generated_at)
    return gw,recorded,{i:dict((k,v) for k,v in row.items() if k!='availability')|{'chance':labels[i]}
                        for i,row in validated.items()}


def admit_market(market,bootstrap,retrieved_at):
    if bootstrap is None or retrieved_at is None:
        raise ValueError('Conditional champion requires an admitted availability bootstrap')
    events=[e for e in bootstrap['events'] if e.get('is_next')]
    if len(events)!=1 or events[0]['id']!=market.gameweek or utc(events[0]['deadline_time'])!=utc(market.deadline):
        raise ValueError('Conditional availability origin differs from market')
    if utc(retrieved_at)!=utc(market.as_of):
        raise ValueError('Availability and market snapshot clocks differ')
    roster={}
    for p in bootstrap['elements']:
        if p['id'] in roster:raise ValueError('Duplicate roster identity')
        roster[p['id']]=p
    for p in market.players:
        if p['id'] not in roster:raise ValueError('Unknown inference identity')
        if p['position']!=roster[p['id']]['element_type']:raise ValueError('Inference position conflict')


def prepare(x,target,bootstrap,retrieved_at,*,review=None,generated_at=None,
            overrides=None,override_gameweek=None):
    if bootstrap is None or retrieved_at is None:
        raise ValueError('Conditional champion requires an admitted availability bootstrap')
    augmented,report=current_availability(x,target,bootstrap,retrieved_at)
    gw=report['next_gw'];overrides=overrides or {}
    for row in target.itertuples():
        if row.element not in overrides or (override_gameweek is not None and row.GW!=override_gameweek):continue
        assumption=overrides[row.element]
        if set(assumption)&{'chance','out'}:
            raise ValueError('Replacement labels require a sourced pre-deadline availability review')
        if row.GW==gw and set(assumption)&{'availability','minutes'}:
            raise ValueError('P6 refuses next-GW availability/minutes output scaling')
    manual=[]
    if review is not None:
        if type(review.get('GW')) is not int or review['GW']!=gw:
            raise ValueError('Availability review must target the next gameweek')
        review_gw,recorded,labels=reviewed_labels(review,bootstrap,generated_at or retrieved_at)
        if review_gw!=gw:raise ValueError('Availability review must target the next gameweek')
        roster={p['id']:p for p in bootstrap['elements']}
        for ident,entry in labels.items():
            mask=target.element.eq(ident)&target.GW.eq(gw)
            augmented.loc[mask,SIGNALS]=[entry['chance']/100.,0.]
            manual.append(dict(id=ident,GW=gw,official_chance_label=roster[ident].get('chance_of_playing_next_round'),
                replacement_chance_label=entry['chance'],fixture_rows=int(mask.sum()),
                recorded_at_utc=recorded.isoformat(),**{k:v for k,v in entry.items() if k!='chance'}))
        report['review_recorded_at_utc']=recorded.isoformat()
    report.update(manual_labels=manual,
        effective_known_label_fixture_rows=int(augmented.availability_missing.eq(0).sum()),
        p6='Next-GW labels enter only as learned covariates; later-GW illustrative sensitivity remains allowed',
        bootstrap_canonical_sha256=hashlib.sha256(json.dumps(bootstrap,sort_keys=True,allow_nan=False).encode()).hexdigest())
    return augmented,report


def predict(model,x,pos,target,bootstrap,retrieved_at,**kwargs):
    if len(pos)!=len(target) or not np.array_equal(np.asarray(pos),target.pos.to_numpy()):
        raise ValueError('Inference position conflict')
    augmented,report=prepare(x,target,bootstrap,retrieved_at,**kwargs)
    return model.predict(augmented,pos),report


def refuse_next_scenario(horizon,gameweek):
    if POLICY_KEY in horizon.provenance['source_hashes'] and gameweek==horizon.origin:
        raise ValueError('P6 refuses next-GW output scaling; use a sourced replacement label before prediction')
