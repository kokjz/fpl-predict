"""Phase 1 of the frozen conditional availability experiment; research only."""
import numpy as np
import pandas as pd
import availability_prospective as previous
from conditional_forecaster import fit as conditional_fit
from fpl_model import CORE_FEATURES, DC_FEATURES
from incumbent_availability import SIGNALS, augment
from market_stage_c import canonical_hash, array_hash
from benchmark_metrics import evaluate

SEASONS=previous.SEASONS
KEYS=previous.KEYS
TRAINING=['played','minutes','sixty','dc_hit','yellow_cards','red_cards','points_core','ts']
EXTRA=[n for n in DC_FEATURES if n not in CORE_FEATURES]
FEATURES={'control':CORE_FEATURES,'conditional':CORE_FEATURES+EXTRA+SIGNALS}
LEARNERS={'control':CORE_FEATURES,'conditional_core':CORE_FEATURES,
          'conditional_played':CORE_FEATURES+SIGNALS,'conditional_minutes':CORE_FEATURES,
          'conditional_sixty':CORE_FEATURES,'conditional_dc':DC_FEATURES}
FEATURE_HASHES={k:canonical_hash(v) for k,v in LEARNERS.items()}
phase1_scope=previous.phase1_scope
keyed_block=previous.keyed_block
masks=previous.masks
first_prospective_gameweek=previous.first_prospective_gameweek
phase2_gates=previous.phase2_gates
census=previous.census


def attach_loader(control,history,features,bridges):
    """Align loader targets and DC features by stable keys after CORE export."""
    phase1_scope(control.season,'admission')
    if not history.index.equals(features.index):raise ValueError('Loader alignment')
    h=history.copy()
    h['fpl_code']=np.nan
    for season,bridge in bridges.items():
        if bridge.id.duplicated().any() or bridge.code.duplicated().any():raise ValueError('Ambiguous bridge')
        ix=h.season.eq(season);h.loc[ix,'fpl_code']=h.loc[ix,'element'].map(bridge.set_index('id').code)
    if h.fpl_code.isna().any():raise ValueError('Missing loader stable code')
    h['fpl_code']=h.fpl_code.astype('int64')
    names=[n for n in TRAINING if n not in control]
    block=pd.concat([h[KEYS+names],features[EXTRA]],axis=1)
    ix=pd.MultiIndex.from_frame(control[KEYS]);bi=pd.MultiIndex.from_frame(block[KEYS])
    if bi.has_duplicates or ix.has_duplicates or set(ix)!=set(bi):raise ValueError('Loader key coverage')
    block=block.set_index(KEYS).loc[ix].reset_index()
    attached=keyed_block(control,block,names+EXTRA)
    result=control.copy()
    for n in names:result[n]=attached[n]
    x=result[CORE_FEATURES].copy()
    for n in EXTRA:x[n]=attached[n]
    if x[CORE_FEATURES].to_numpy(float).tobytes()!=control[CORE_FEATURES].to_numpy(float).tobytes():raise ValueError('CORE bytes changed')
    return result,x


def augment_control(rows,features,bridge,observations):
    phase1_scope(rows.season,'admission')
    if list(features)!=CORE_FEATURES+EXTRA or not rows.index.equals(features.index):raise ValueError('Feature alignment')
    out,coverage=augment(rows,features,bridge,observations)
    if list(out)!=FEATURES['conditional']:raise ValueError('Feature order')
    if out[CORE_FEATURES].to_numpy(float).tobytes()!=features[CORE_FEATURES].to_numpy(float).tobytes():raise ValueError('CORE bytes changed')
    unknown=rows.season.ne('2025-26')|rows.GW.le(3)
    if out.loc[unknown,'availability_missing'].ne(1).any():raise ValueError('Unexpected historical availability')
    return out,coverage


def fit(rows,features,method,stage):
    phase1_scope(rows.season,'fit')
    if method not in FEATURES or list(features)!=FEATURES[method] or not rows.index.equals(features.index):raise ValueError('Fit feature contract')
    train,test=masks(rows,stage)
    if method=='control':return previous.fit(rows,features,'control',stage)
    if set(TRAINING)-set(rows):raise ValueError('Missing conditional training columns')
    model=conditional_fit(rows,features,train,version='conditional-prospective-cpr-r1')
    pred=model.predict(features.loc[test],rows.loc[test,'pos']) if test.any() else None
    receipt=dict(train_rows=int(train.sum()),test_rows=int(test.sum()),features={k:v for k,v in LEARNERS.items() if k!='control'},feature_sha256=FEATURE_HASHES,
                 training_row_sha256=canonical_hash(rows.loc[train,KEYS].to_dict('records')),
                 training_feature_sha256=array_hash(features.loc[train].to_numpy(float)),metadata=model.metadata)
    return model,pred,receipt


def gate_b(candidate,control):
    checks={}
    for name,metric,ratio in [('player_gw_rmse','rmse',1.),('player_gw_mae','mae',1.005)]:
        value=candidate['candidate_player_gw'][metric];limit=ratio*control['candidate_player_gw'][metric]
        checks[name]=dict(candidate=float(value),threshold=float(limit),passed=bool(value<=limit))
    return dict(passed=all(v['passed'] for v in checks.values()),criteria=checks)


def score(rows,features,predictions):
    phase1_scope(rows.season,'score');_,test=masks(rows,'B');d=rows.loc[test]
    reports={m:evaluate(d,features.loc[test,CORE_FEATURES],predictions[m]) for m in FEATURES}
    split={}
    for name,lo,hi in [('GW20-27',20,27),('GW28-38',28,38)]:
        ix=d.GW.between(lo,hi)
        split[name]={m:evaluate(d.loc[ix],features.loc[d.index[ix],CORE_FEATURES],np.asarray(predictions[m])[ix.to_numpy()]) for m in FEATURES}
    return dict(metrics=reports,gate=gate_b(reports['conditional'],reports['control']),window_split=split)


def fixed_squad(rows,features,predictions):
    report=previous.fixed_squad(rows,features,dict(control=predictions['control'],availability=predictions['conditional']))
    report['totals']['conditional']=report['totals'].pop('availability')
    return report
