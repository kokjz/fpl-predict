"""Optional chronological two-parameter appearance calibration for research.

No registry/default change. Point means and explicit zero-support flags are not
modified. Historical simulated label clocks and actual fit time are distinct.
"""
from copy import deepcopy
from datetime import datetime,timezone
import math
import numpy as np
from sklearn.linear_model import LogisticRegression
from availability_evidence import utc

EPS=1e-6


def logit(p):
    p=np.clip(np.asarray(p,dtype=float),EPS,1-EPS)
    return np.log(p/(1-p))


def fit(rows,target_as_of,*,source_hashes):
    rows=list(rows);target=utc(target_as_of)
    if not rows or not source_hashes or any(len(v)!=64 for v in source_hashes.values()):raise ValueError('Missing calibration cohort/provenance')
    ps=[];ys=[];clocks=[];keys=set()
    for r in rows:
        key=(r['season'],r['gameweek'],r['id']);p=r['p_play'];y=r['label']
        if key in keys or type(y) is not int or y not in (0,1) or type(p) not in (int,float) or not math.isfinite(p) or not 0<p<=1:raise ValueError('Invalid/duplicate calibration cell')
        keys.add(key);origin=utc(r['as_of']);available=utc(r['available_at'])
        if not origin<available<target:raise ValueError('Calibration label clock is late or invalid')
        ps.append(p);ys.append(y);clocks.append(available)
    if set(ys)!={0,1}:raise ValueError('Calibration needs both classes')
    latest=max(clocks);age=np.array([(latest-c).total_seconds()/86400 for c in clocks]);weights=np.power(.5,age/730.5)
    estimator=LogisticRegression(C=1.,solver='lbfgs',max_iter=200,random_state=20261026)
    estimator.fit(logit(ps).reshape(-1,1),ys,sample_weight=weights)
    slope=float(estimator.coef_[0,0]);intercept=float(estimator.intercept_[0])
    if not math.isfinite(slope+intercept) or slope<0 or estimator.n_iter_[0]>=200:raise ValueError('Calibration fit is nonmonotone or unconverged; do not substitute another candidate')
    return dict(schema_version=1,method='chronological_platt_v1',slope=slope,intercept=intercept,probability_clip=EPS,
        training_cells=len(rows),positive_labels=sum(ys),training_data_available_through=latest.isoformat(),
        target_not_before=target.isoformat(),executed_at_utc=datetime.now(timezone.utc).isoformat(),
        source_hashes=dict(source_hashes),half_life_days=730.5,approval='Historical research only; no operational promotion')


def transform(probabilities,calibration,as_of):
    c=calibration
    if c.get('schema_version')!=1 or c.get('method')!='chronological_platt_v1' or c.get('probability_clip')!=EPS:raise ValueError('Unknown calibration recipe')
    if utc(as_of)<utc(c['target_not_before']) or utc(c['training_data_available_through'])>=utc(as_of):raise ValueError('Late calibration label cutoff')
    if any(type(c[k]) not in (int,float) or not math.isfinite(c[k]) for k in ('slope','intercept')) or c['slope']<0:raise ValueError('Invalid calibration parameters')
    p=np.asarray(probabilities,dtype=float)
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Invalid appearance probabilities')
    z=np.clip(c['slope']*logit(p)+c['intercept'],-709,709)
    return 1/(1+np.exp(-z))


def apply(sidecar,calibration):
    """Copy only p fields; official/no-fixture/zero support is never cleared."""
    result=deepcopy(sidecar);values=[];indices=[]
    for i,r in enumerate(result['rows']):
        p=r['p_play']
        if type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=1:raise ValueError('Invalid sidecar probability')
        if r['official_zero'] or r['fixture_count']==0:
            if p!=0:raise ValueError('Conflicting zero-support sidecar')
        elif p>0:indices.append(i);values.append(p)
    mapped=transform(values,calibration,sidecar['as_of'])
    for i,p in zip(indices,mapped):
        r=result['rows'][i];r['uncalibrated_p_play']=r['p_play'];r['p_play']=float(p)
    result['trained_through']=max(utc(sidecar['trained_through']),utc(calibration['training_data_available_through'])).isoformat()
    result['calibration']=deepcopy(calibration)
    result['report']=dict(result.get('report',{}),calibration='Prior-season Platt player-GW mapping; original means unchanged; raw_p_play retains pre-mixture base-head probability')
    return result
