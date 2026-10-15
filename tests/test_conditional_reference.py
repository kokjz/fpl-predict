import numpy as np
import pandas as pd
import pytest

import conditional_reference as ref


def test_calibration_normalises_and_is_independent_of_query():
    raw=np.tile([.4,.3,.2,.1],(80,1));labels=np.array([0,1,2,3]*20)
    cal=ref.calibrate(raw,labels);adjusted=ref.apply_calibration(raw,cal)
    np.testing.assert_allclose(adjusted.sum(axis=1),1.)
    assert cal["gamma"] in ref.POLICY["gamma"] and cal["weights"][2:]==[1.,1.]
    assert ref.blend_weight(pd.DataFrame({'gameweek':[20]*80,'fpl_code':range(80),'total_points':labels}),
                            labels.astype(float),labels.astype(float))==0.


def test_eight_heads_use_only_training_rows_and_validation_early_stopping():
    calls=[]
    class Head:
        def __init__(self,**kwargs):self.params=kwargs;self.best_iteration=2
        def fit(self,x,y,eval_set,verbose):
            calls.append((self.params,x.copy(),eval_set[0][0].copy()))
            assert np.asarray(x)[:,0].max()<200 and np.asarray(eval_set[0][0])[:,0].min()>=200
            self.classes_=np.arange(4 if self.params.get('num_class')==4 else 2)
            self.value=float(np.mean(y));return self
        def predict_proba(self,x):return np.full((len(x),len(self.classes_)),1/len(self.classes_))
        def predict(self,x):return np.full(len(x),self.value)
    class Factory:
        XGBClassifier=Head;XGBRegressor=Head
    t=pd.DataFrame({'minutes':[0,30,60,90,90,90,90,90],
                    'total_points':[0,-1,0,2,5,12,1,10]})
    v=t.assign(gameweek=20,fpl_code=range(8));progress=[]
    prediction,metadata=ref.fit_position(t,v,np.arange(100,108)[:,None],np.arange(200,208)[:,None],
                                       np.arange(300,305)[:,None],progress.append,Factory)
    assert len(calls)==len(progress)==8
    assert prediction.shape==(5,) and np.isfinite(prediction).all() and prediction.min()>=0
    assert metadata['direct_weight'] in ref.POLICY['direct_weights']
    assert all(c[0]['random_state']==42 and c[0]['n_jobs']==2 for c in calls)


def test_native_score_band_coverage_is_required_before_fitting():
    rows=pd.DataFrame([dict(position=pos,minutes=minute,total_points=point) for pos in range(1,5)
                       for minute,point in [(0,0),(30,-1),(90,0),(90,2),(90,5),(90,12)]])
    rows=pd.concat([rows,rows],ignore_index=True)
    mask=rows.index<len(rows)//2;masks={'train':mask,'validation':~mask}
    ref.check_populations(rows,masks)
    rows.loc[rows.total_points.eq(12),'total_points']=5
    with pytest.raises(ValueError,match='score band'):ref.check_populations(rows,masks)


def test_optional_xgb_best_iteration_prediction_contract():
    xgb=pytest.importorskip('xgboost',reason='optional reference dependency')
    x=np.arange(80,dtype=float).reshape(40,2)
    model=xgb.XGBRegressor(n_estimators=12,max_depth=1,n_jobs=2,early_stopping_rounds=2)
    model.fit(x,np.ones(40),eval_set=[(x,np.zeros(40))],verbose=False)
    assert model.best_iteration<11
    expected=model.get_booster().predict(xgb.DMatrix(x),iteration_range=(0,model.best_iteration+1))
    np.testing.assert_allclose(model.predict(x),expected)
