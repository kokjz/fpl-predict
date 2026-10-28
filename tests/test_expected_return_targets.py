import numpy as np
import pandas as pd
import pytest

import expected_return_targets as ert
from fpl_model import CORE_FEATURES


def rows():
    return pd.DataFrame([dict(season=s,position=p,minutes=90.,total_points=8.,goals_scored=1.,assists=1.,clean_sheets=1.,us_xG=1.,us_xA=1.,fixture=1,team_name='A',opponent_name='B') for s in ert.SEASONS for p in [1,2,3,4]])


def teams():
    return pd.DataFrame([dict(season=s,fixture=1,team_name='B',xg=0.) for s in ert.SEASONS])


def test_formula_position_points_and_whole_row_fallback():
    p=rows().iloc[:4].copy(); p.loc[p.index[1],'minutes']=0; p.loc[p.index[2],'us_xA']=np.nan
    y,fallback=ert.training_target(p,np.ones(4),dict(k_G=.8,k_A=1.2,k_CS=1.1))
    assert y[0]==pytest.approx(8-6-3-4+6*.8+3*1.2+4*1.1*np.exp(-1))
    assert y[1]==y[2]==8
    assert y[3]==pytest.approx(8-4-3+4*.8+3*1.2)
    assert fallback.tolist()==[False,True,True,False]


def test_sixty_minute_cs_boundary_and_no_target_clip():
    p=rows().iloc[:2].copy();p['minutes']=[59,60];p['total_points']=-100.
    y,_=ert.training_target(p,[0.,0.],dict(k_G=1.,k_A=1.,k_CS=1.))
    assert y.tolist()==[-104.,-100.]


def test_constants_only_eligible_rows_but_cs_has_own_mask():
    p=rows().iloc[:4].copy();p.loc[1,'us_xA']=np.nan
    k,details=ert.constants(p,np.zeros(4))
    assert k==dict(k_G=1.,k_A=1.,k_CS=1.)
    assert details['return_rows']==3 and details['cs_rows']==3


@pytest.mark.parametrize('fold',ert.FOLDS)
def test_test_row_poisoning_never_changes_k_training_labels_or_actual_test_targets(fold):
    p=rows(); t=teams(); first,info,train=ert.fold_labels(p,t,fold)
    poisoned=p.copy();poisoned.loc[~train,['us_xG','us_xA']]=np.inf
    tp=t.copy();tp.loc[tp.season.ge(fold),'xg']=np.nan
    second,other,mask=ert.fold_labels(poisoned,tp,fold)
    assert np.array_equal(first,second) and info==other and np.array_equal(train,mask)
    assert np.array_equal(second[~train],p.total_points.to_numpy()[~train])


def test_admission_and_coverage_gate_without_fit(monkeypatch):
    monkeypatch.setattr(ert,'estimator',lambda *_:pytest.fail('admission attempted a fit'))
    p=rows(); result=ert.admission(p,teams()); assert result['gate_A_pass'] and result['stage_A_fits']==0
    p.loc[0,'us_xG']=np.nan
    result=ert.admission(p,teams()); assert not result['gate_A_pass']; assert result['seasons']['2020-21']['coverage']==.75


def test_ambiguous_join_is_not_guessed():
    with pytest.raises(ValueError,match='Ambiguous'):ert.opponent_xg(rows(),pd.concat([teams(),teams()]))
    with pytest.raises(ValueError,match='Unsettled input columns'):ert.constants(rows().drop(columns='goals_scored'),np.zeros(16))


def arrays():
    n=4;x=np.zeros((n,len(CORE_FEATURES)));seasons=np.array(ert.SEASONS)
    return dict(X_control=x,X_expected_return=x.copy(),y=np.arange(n,dtype=float),season=seasons,gameweek=np.ones(n,int),fixture=np.arange(n),fpl_code=np.arange(n),cutoff_ns=np.zeros(n,int),ts_ns=np.ones(n,int),candidate=np.zeros(n,bool),**{'label_'+f:np.arange(n,dtype=float) for f in ert.FOLDS})


def test_shared_proof_rejects_feature_and_evaluation_label_changes():
    a=arrays(); assert ert.shared_proof(a)['feature_bytes_identical']
    a['X_expected_return'][0,0]=1
    with pytest.raises(ValueError,match='Feature bytes'):ert.shared_proof(a)
    a=arrays();a['label_2022-23'][-1]+=1
    with pytest.raises(ValueError,match='Evaluation targets'):ert.shared_proof(a)


def test_target_formula_uses_opponent_same_fixture_xg():
    p=rows();t=teams(); t['xg']=2.
    own=t.copy();own['team_name']='A';own['xg']=99
    assert np.array_equal(ert.opponent_xg(p,pd.concat([t,own])),np.full(len(p),2.))
