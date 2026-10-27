import copy
from datetime import datetime,timedelta,timezone
import numpy as np
import pytest
from fpl_model import ew
from market_stage_b import (features,FEATURES,identity,source_clock,finite_shared,fold_masks,scores,paired_blocks)


def invented():
    t=datetime(2020,9,12,12,tzinfo=timezone.utc)
    warm=dict(season='2019-20',fixture=None,date='2020-07-01',csv_kickoff=t-timedelta(days=70),
              home='Arsenal',away='Chelsea',lambda_home=1.6,lambda_away=1.)
    rows=[]
    for i in range(3):
        kickoff=t+timedelta(days=7*i)
        rows.append(dict(season='2020-21',fixture=i+1,home='Arsenal',away='Chelsea',deadline=kickoff-timedelta(hours=2),
            fpl_kickoff=kickoff,csv_kickoff=kickoff+timedelta(minutes=30),gameweek=i+1,
            goals_home=2.+i,goals_away=1.,xg_home=1.8+i*.1,xg_away=.9))
    market=[warm,*[dict(r,date=r['fpl_kickoff'].date().isoformat(),lambda_home=1.5,lambda_away=1.) for r in rows]]
    return rows,market


def test_max_clock_and_history_only_identity():
    rows,market=invented();r=rows[0]
    assert source_clock(r)==r['csv_kickoff']
    assert identity(market[0])==('2019-20','fd','2020-07-01','Arsenal','Chelsea')
    assert identity(r)==('2020-21','fpl',1)
    with pytest.raises(ValueError,match='Warmup'):features([dict(r,season='2019-20')],market)


def test_amended_ew_operator_priors_cohort_and_no_future_label_or_odds_leakage():
    rows,market=invented();x,y,keys,meta=features(rows,market)
    assert len(keys)==len(y)==6 and len(set(keys))==6
    # First-origin team/opp goal AND xG histories reset to the exact C prior.
    for a in ['C','U']:
        names=FEATURES[a]
        assert x[a][0,names.index('team_ew4_gf')]==1.35
        if a=='U':assert x[a][0,names.index('team_ew4_xgf')]==1.35
    assert x['U'][2,FEATURES['U'].index('team_ew4_xgf')]==pytest.approx(ew([1.8],4,1.35,4.))
    poisoned=copy.deepcopy(rows);poisoned[1].update(goals_home=999.,goals_away=999.,xg_home=999.,xg_away=999.)
    poisoned_market=copy.deepcopy(market);poisoned_market[2].update(lambda_home=6.,lambda_away=.05)
    other,_,_,_=features(poisoned,poisoned_market)
    # Origin2 cannot consume its own result or odds; later origins may consume it.
    for a in ['C','U','M']:assert np.array_equal(x[a][:4],other[a][:4])
    assert all(timestamp<row['cutoff'] for row in meta for timestamp in row['source_max'].values() if timestamp)


def test_clock_strictness_same_cutoff_match_is_not_admitted():
    rows,market=invented();cutoff=rows[1]['deadline']-timedelta(hours=3)
    # Move a source's later clock exactly to origin2: it cannot affect origin2.
    changed=copy.deepcopy(market);changed[1]['csv_kickoff']=cutoff
    changed[1]['lambda_home']=6.
    a,_,_,_=features(rows,changed)
    changed[1]['lambda_home']=.05;b,_,_,_=features(rows,changed)
    assert np.array_equal(a['M'][2:4],b['M'][2:4])


def test_nonfinite_in_any_arm_aborts_shared_cohort_no_row_drop():
    x={a:np.ones((3,len(FEATURES[a]))) for a in ['C','U','M']};x['U'][1,0]=np.nan
    with pytest.raises(ValueError,match='Non-finite'):finite_shared(x,np.ones(3))


def test_train_season_masks_and_algebraic_diagnostics():
    train,test=fold_masks(np.array(['2020-21','2021-22','2022-23','2023-24']),'2022-23')
    assert train.tolist()==[True,True,False,False] and test.tolist()==[False,False,True,False]
    y=np.array([0.,1.,2.,3.]);p=np.array([.5,1.,2.,2.5]);r=scores(y,p)
    from sklearn.metrics import mean_poisson_deviance
    assert r['mean_poisson_deviance']==mean_poisson_deviance(y,p)
    assert r['calibration_rate_slope']==pytest.approx(np.cov(p,y,bias=True)[0,1]/np.var(p))
    z=paired_blocks(y,p,p,[1,5,9,13]);assert z['mean_delta']==0 and z['descriptive_95_interval']==[0.,0.]


def test_worker_fits_scaler_on_train_only_and_serialises_without_extra_model_fit(tmp_path,monkeypatch):
    import importlib.util
    import json
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('market_worker',Path(__file__).parents[1]/'tools/run_market_stage_b.py')
    worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    n=4*760;seasons=np.repeat(['2020-21','2021-22','2022-23','2023-24'],760)
    base=np.arange(n,dtype=float);base[seasons>='2022-23']+=10000
    values={'X_'+a:np.repeat(base[:,None],len(FEATURES[a]),axis=1) for a in ['C','U','M']}
    values.update(y=np.ones(n),season=seasons,fixture=np.arange(n),team=np.repeat('invented',n),
                  gameweek=np.tile(np.arange(760)%38+1,4),cutoff=np.repeat('2020-01-01T00:00:00+00:00',n))
    bundle=tmp_path/'bundle.npz';worker.save_npz(bundle,**values)
    proof=worker.canonical_hash([dict(key=[str(s),int(f),str(t)],target=float(y),cutoff=str(c))
        for s,f,t,y,c in zip(seasons,values['fixture'],values['team'],values['y'],values['cutoff'])])
    worker.write_json(tmp_path/'summary.json',dict(bundle_sha256=worker.digest(bundle),shared_keys_targets_origins_sha256=proof))
    class InventedLearner:
        def __init__(self,**kwargs):self.n_iter_=1
        def fit(self,x,y):
            assert len(y)==1520 and np.max(abs(x.mean(axis=0)))<1e-12
            self.coef_=np.zeros(x.shape[1]);self.intercept_=0.;return self
        def predict(self,x):return np.ones(len(x))
    monkeypatch.setattr(worker,'PoissonRegressor',InventedLearner)
    out=tmp_path/'fit';out.mkdir()
    worker.fit(bundle,'2022-23','C',tmp_path/'ledger',out)
    result=json.loads((out/'result.json').read_text())
    assert result['scaler_mean']==pytest.approx([759.5]*len(FEATURES['C']))
    assert result['train_rows']==1520 and result['test_rows']==760
    assert result['calibration_rate_slope'] is None
    # Same scientific fit slot cannot be repeated; this test used a mock learner.
    with pytest.raises(ValueError,match='order/budget'):worker.fit(bundle,'2022-23','C',tmp_path/'ledger',out)
