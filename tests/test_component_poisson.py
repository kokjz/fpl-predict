"""Synthetic component contracts; no private data, downloads or fits."""
import numpy as np
import pandas as pd
import pytest
import component_poisson as c
from fpl_model import estimator
from test_rich_market_combination import bundle as old_bundle

def bundle():
    a=old_bundle();a.pop('X_combined');a['X_components']=a['X_control'].copy()
    a['targets']=np.column_stack([np.zeros((len(a['y']),4)),a['y']])
    return a

def test_head_specs():
    base=estimator('hgb7').get_params()
    for head in c.HEADS:
        actual=c.head_estimator(head).get_params()
        assert actual==dict(base,loss='squared_error' if head=='R' else 'poisson')

def test_rule_equals_prior_reconcile_on_synthetic_rows():
    import expected_return_amendment as old
    from test_expected_return_amendment import row
    p=pd.DataFrame([row(fpl_code=i,position=pos,minutes=minutes,goals_scored=1,assists=2,goals_conceded=gc,saves=7,bonus=2,red_cards=1,yellow_cards=1,penalties_saved=1,penalties_missed=1,own_goals=1) for i,(pos,minutes,gc) in enumerate([(1,90,3),(2,60,0),(3,59,0),(4,0,4)])])
    actual=c.reconcile(p.drop(columns=['us_xG','us_xA']))
    assert np.array_equal(actual,old.reconcile(p)['_recomputed_points'].to_numpy())

def test_targets_and_recombination():
    f=pd.DataFrame(dict(points_core=[12.,-2.,4.,20.],minutes=[90]*4,goals_scored=[1,0,0,3],assists=[1,0,1,1],clean_sheets=[1,0,0,0],bonus=[2,0,1,3]))
    pos=np.array([1,2,3,4]);h=c.targets(f,pos)
    assert h[0,4]==-3
    assert np.array_equal(c.contributions(h,pos).sum(axis=1),f.points_core)
    assert np.array_equal(c.recombine(h,pos),[12.,0.,4.,20.])
    assert np.array_equal(c.recombine(np.ones((4,5)),pos),[15,15,11,9])

@pytest.mark.parametrize('column,value',[('goals_scored',-1),('assists',np.nan),('bonus',.5),('clean_sheets',2)])
def test_invalid_poisson_targets(column,value):
    f=pd.DataFrame(dict(points_core=[2.],minutes=[90.],goals_scored=[0.],assists=[0.],clean_sheets=[0.],bonus=[0.]))
    f[column]=value
    with pytest.raises(ValueError):c.targets(f,[2])
    f[column]=0;f['clean_sheets']=1;f['minutes']=59
    with pytest.raises(ValueError):c.targets(f,[2])

def sidecar_fixture():
    h=pd.DataFrame(dict(season=['2020-21']*2,GW=[1,2],element=[10,10],fixture=[1,2],total_points=[6,1],points_core=[6,1],minutes=[90,30],goals_scored=[0,0],assists=[0,0],clean_sheets=[1,0],bonus=[0,0]),index=[7,9])
    bridges={'2020-21':pd.DataFrame(dict(id=[10],code=[123]))}
    exported=h.reset_index(drop=True).copy();exported['fpl_code']=123
    return h,bridges,exported

def test_sidecar_alignment_positive_negative():
    h,b,e=sidecar_fixture();s,r=c.sidecar(h,b,e,lambda x:x.copy())
    assert s.index.tolist()==[7,9] and r['passed'] and s.clean_sheets.tolist()==[1,0]
    for bad in [e.iloc[::-1],e.assign(points_core=[5,1]),e.assign(minutes=[89,30]),e.assign(fpl_code=[124,123])]:
        with pytest.raises(ValueError,match='alignment'):c.sidecar(h,b,bad,lambda x:x.copy())

def test_admission_counts_and_failures():
    h,b,e=sidecar_fixture();s,_=c.sidecar(h,b,e,lambda x:x.copy())
    control=e.rename(columns={'GW':'gameweek'}).assign(pos=2)
    p=control.rename(columns={'pos':'position'}).copy()
    for n in ('saves','goals_conceded','penalties_saved','penalties_missed','yellow_cards','red_cards','own_goals'):p[n]=0
    _,r=c.admission(p,control,s)
    assert r['passed'] and r['played']==2 and r['crosscheck_mismatches']['clean_sheets']==0
    p.loc[0,'bonus']=1
    _,bad=c.admission(p,control,s)
    assert not bad['passed'] and bad['unreconciled_played']==1 and bad['crosscheck_mismatches']['bonus']==1

def test_static_audit_and_later_season_exclusion(tmp_path):
    assert c.static_audit()['passed']
    for season in ('2026-27','2027-28'):
        with pytest.raises(ValueError):c.fold_masks(np.array([season]),'2025-26')
    p=tmp_path/'data.csv';p.write_text('season,minutes,us_xG\n2020-21,90,notparsed\n2026-27,later,notparsed\n')
    f=c.read_scoped(p,['season','minutes'],['2020-21'])
    assert list(f)==['season','minutes'] and f.minutes.tolist()==[90]
    with pytest.raises(ValueError):c.read_scoped(p,['us_xG'],['2020-21'])

def test_fit_control_and_components_share_inputs_and_weights(monkeypatch):
    a=bundle();calls=[]
    class Model:
        def __init__(self):self.params=estimator('hgb7').get_params()
        def set_params(self,**kw):self.params.update(kw);return self
        def fit(self,x,y,sample_weight):calls.append((x.to_numpy().tobytes(),sample_weight.tobytes(),self.params['loss']));return self
        def predict(self,x):return np.ones(len(x))
        def get_params(self):return self.params
    monkeypatch.setattr(c,'estimator',lambda _:Model())
    control,_,_=c.fit_predict(a,'2022-23','control')
    candidate,info,heads=c.fit_predict(a,'2022-23','components')
    assert len(calls)==6 and len({x[0] for x in calls})==1 and len({x[1] for x in calls})==1
    assert [x[2] for x in calls]==['squared_error']+['poisson']*4+['squared_error']
    assert info['heads']==5 and np.array_equal(candidate,c.recombine(heads,a['pos'][a['season']=='2022-23']))
    assert c.control_parity(control,control.copy())['passed']
    with pytest.raises(ValueError):c.control_parity(control,control+.1)

def test_gate_and_analysis_preserve_original(monkeypatch):
    a=bundle();panels={f:dict(first_gw=4,squads=[[],[]]) for f in c.DEVELOPMENT}
    monkeypatch.setattr(c.previous.i4,'replay',lambda z,p,m:{n:dict(mean_total=100.+(n!='control')) for n in m})
    pred={(f,m):np.arange(8,dtype=float)+(.1 if m=='control' else 0) for f in c.DEVELOPMENT for m in c.METHODS}
    report,z=c.analyse(a,pred,panels,c.DEVELOPMENT)
    assert report['gate']['passed'] and len(report['gate']['criteria'])==10
    assert report['metrics']['control']['player_gw']['n']==8
    assert report['metrics']['control']['fixture']['n']==16
    assert report['pooled_fixed_squad_delta']==1.
    pred={(f,m):np.arange(8,dtype=float)+(1 if m=='components' else .1) for f in c.DEVELOPMENT for m in c.METHODS}
    assert not c.analyse(a,pred,panels,c.DEVELOPMENT)[0]['gate']['passed']
