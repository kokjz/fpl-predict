import importlib.util
import json
import hashlib
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import market_stage_c as stage
import native_development as i4
from fpl_model import CORE_FEATURES


def bundle():
    seasons=np.repeat(['2020-21','2021-22','2022-23','2023-24'],8);n=len(seasons)
    base=np.ones((n,len(CORE_FEATURES)),dtype=np.float64)
    base[:,CORE_FEATURES.index('n_history')]=3
    base[:,CORE_FEATURES.index('last5_minutes')]=60
    ts=pd.DatetimeIndex([pd.Timestamp(f'{int(s[:4])}-09-01T15:00:00Z')+pd.Timedelta(days=int(i%8)) for i,s in enumerate(seasons)]).as_unit('ns').asi8
    return dict(X_control=base,X_market_strength=np.column_stack([base.copy(),np.ones((n,3))]),
        y=np.tile(np.arange(8,dtype=float),4),minutes=np.full(n,90.),season=seasons,
        gameweek=np.tile(np.repeat([1,2],4),4),fixture=np.tile([1,2,1,2,3,4,3,4],4),
        fpl_code=np.tile([1,1,2,2,1,1,2,2],4),element=np.tile([1,1,2,2,1,1,2,2],4),pos=np.full(n,2),n_history=np.full(n,3.),
        ts_ns=ts,cutoff_ns=np.repeat(ts.reshape(4,8)[:,::4],4,axis=1).ravel()-int(pd.Timedelta(days=1).value),
        candidate=np.ones(n,dtype=bool),cold_market_team=np.zeros(n,dtype=bool),cold_market_opponent=np.zeros(n,dtype=bool))


@pytest.mark.parametrize('problem',['nonmarket_bytes','nonfinite','duplicate','candidate','dgw_cutoff'])
def test_shared_proof_fails_closed_before_fit(problem):
    a=bundle();assert stage.shared_proof(a)['nonmarket_bytes_identical']
    if problem=='nonmarket_bytes':
        a['X_control'][0,0]=0.;a['X_market_strength'][0,0]=-0.  # Equal numeric values, different original bytes.
    elif problem=='nonfinite':a['X_market_strength'][0,-1]=np.nan
    elif problem=='duplicate':
        for k in ['season','gameweek','fixture','fpl_code']:a[k][1]=a[k][0]
    elif problem=='candidate':a['candidate'][0]=False
    else:a['cutoff_ns'][1]-=1
    with pytest.raises(ValueError):stage.shared_proof(a)


def test_market_is_own_fixture_raw_and_future_odds_invariant():
    markets=[dict(season='2019-20',fixture=None,home='Liverpool',away='Arsenal',
        csv_kickoff='2019-12-01T15:00:00Z',canonical_kickoff=None,lambda_home=3.,lambda_away=.5),
        dict(season='2019-20',fixture=None,home='Arsenal',away='Liverpool',
        csv_kickoff='2020-01-01T15:00:00Z',canonical_kickoff=None,lambda_home=1.,lambda_away=2.5)]
    rows=[]
    for fixture,opponent in [(1,'Arsenal'),(2,'Chelsea')]:
        when=f'2020-09-0{fixture+1}T15:00:00Z'
        markets.append(dict(season='2020-21',fixture=fixture,home='Liverpool',away=opponent,
            csv_kickoff=when,canonical_kickoff=when,lambda_home=5.5,lambda_away=.2))
        rows.append(dict(season='2020-21',fixture=fixture,team_name='Liverpool',opponent_name=opponent,
            home=True,ts=pd.Timestamp(when),deadline=pd.Timestamp('2020-09-01T12:00:00Z')))
    p=pd.DataFrame(rows);first,evidence,origins=stage.market_rows(p,markets)
    markets[-2]['lambda_home']=.05;markets[-1]['lambda_away']=6.
    second,_,_=stage.market_rows(p,markets)
    np.testing.assert_array_equal(first,second)
    np.testing.assert_allclose(first[:,2],np.exp(-first[:,1]))
    assert first[0,1]!=first[1,1] and evidence[1]['cold_start_opponent'] and origins==1
    assert all(pd.Timestamp(r['source_max'])<pd.Timestamp(r['cutoff']) for r in evidence)
    p.loc[0,'home']=False
    with pytest.raises(ValueError,match='fixture/club/venue'):stage.market_rows(p,markets)


def test_fit_uses_exact_i4_core_hyperparameters_weights_and_train_only(monkeypatch):
    a=bundle();calls=[]
    class Model:
        def fit(self,x,y,sample_weight):
            calls.append((list(x),np.asarray(y).copy(),sample_weight.copy()));self.mean=float(np.mean(y));return self
        def predict(self,x):return np.full(len(x),self.mean)
        def get_params(self):return {'synthetic':True}
    monkeypatch.setattr(stage,'estimator',lambda name:Model())
    monkeypatch.setattr(i4,'estimator',lambda name:Model())
    new,_=stage.fit_predict('control',a,'2022-23')
    rows=pd.DataFrame({'ts':pd.to_datetime(a['ts_ns'],utc=True),'total_points':a['y']})
    train=a['season']<'2022-23';valid=a['season']=='2022-23'
    old=i4.fit_predict('control',pd.DataFrame(a['X_control'],columns=CORE_FEATURES),rows,train,valid)
    np.testing.assert_array_equal(new,old)
    assert calls[0][0]==calls[1][0]==CORE_FEATURES
    np.testing.assert_array_equal(calls[0][1],calls[1][1]);np.testing.assert_array_equal(calls[0][2],calls[1][2])
    a['y'][valid]=999999
    again,_=stage.fit_predict('market_strength',a,'2022-23')
    np.testing.assert_array_equal(again,new)
    assert calls[-1][0]==CORE_FEATURES+stage.MARKET_FEATURES and len(calls[-1][1])==16


def test_gate_details_keeps_both_errors_both_maes_and_each_fold():
    old={k:dict(rmse=3.,mae=2.) for k in ['fixture','player_gw']};old['ndcg10']=.5
    new={k:dict(rmse=2.985,mae=2.01) for k in ['fixture','player_gw']};new['ndcg10']=.5
    control={f:{k:dict(rmse=3.) for k in ['candidate_player_gw','candidate_fixture']} for f in stage.FOLDS}
    challenger={f:{k:dict(rmse=3.*1.005) for k in ['candidate_player_gw','candidate_fixture']} for f in stage.FOLDS}
    assert stage.gate_details(new,old,challenger,control,0.)['passed']
    challenger['2023-24']['candidate_fixture']['rmse']=3.016
    assert not stage.gate_details(new,old,challenger,control,0.)['passed']
    challenger['2023-24']['candidate_fixture']['rmse']=3.
    new['fixture']['mae']=2.011
    assert not stage.gate_details(new,old,challenger,control,0.)['passed']


def test_analysis_preserves_doubles_and_reports_all_gates_without_fit(monkeypatch):
    a=bundle();pred={(f,m):np.arange(8,dtype=float)+(.1 if m=='control' else 0.) for f in stage.FOLDS for m in stage.METHODS}
    monkeypatch.setattr(i4,'replay',lambda z,p,m:{name:dict(mean_total=100.+(1 if name=='market_strength' else 0)) for name in m})
    panels={f:dict(first_gw=4,squads=[[],[]]) for f in stage.FOLDS}
    result,z=stage.analyse(a,pred,panels)
    assert result['metrics']['control']['player_gw']['n']==8
    assert result['metrics']['control']['fixture']['n']==16
    assert result['gate']['passed'] and len(result['gate']['criteria'])==10
    assert result['pooled_fixed_squad_delta']==1.
    assert all(len(result['points'][f]['control']['totals'])==2 for f in stage.FOLDS)


def test_worker_reserves_four_slot_ledger_and_never_retries(tmp_path,monkeypatch):
    path=Path(__file__).resolve().parents[1]/'tools/run_market_stage_c.py'
    spec=importlib.util.spec_from_file_location('stage_c_worker',path);worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    a=bundle();build=tmp_path/'build';build.mkdir();worker.save_npz(build/'bundle.npz',**a)
    summary=dict(bundle_sha256=worker.digest(build/'bundle.npz'),protocol_lf_sha256=worker.PROTOCOL_SHA,proof=stage.shared_proof(a))
    worker.write_json(build/'summary.json',summary)
    calls=[]
    monkeypatch.setattr(worker,'fit_predict',lambda *args:(calls.append(args[2]) or np.ones(8),{'heads':1}))
    output=tmp_path/'fit';output.mkdir();ledger=tmp_path/'ledger'
    worker.fit(build/'bundle.npz','2022-23','control',ledger,output)
    assert calls==['2022-23'] and len(list(ledger.glob('*.json')))==1
    assert json.loads(next(ledger.glob('*.json')).read_text())['status']=='completed'
    with pytest.raises(ValueError,match='no retry'):worker.fit(build/'bundle.npz','2022-23','control',ledger,output)
    assert calls==['2022-23']


def test_i4_source_qualification_rejects_executed_xi_changes(tmp_path):
    path=Path(__file__).resolve().parents[1]/'tools/run_market_stage_c.py'
    spec=importlib.util.spec_from_file_location('stage_c_qualification',path);worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    root=path.parents[1]/'src';original={}
    for name in i4.code_hashes():
        shutil.copyfile(root/name,tmp_path/name)
        original[name]=hashlib.sha256((root/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    receipt=worker.qualify_i4_sources(original,tmp_path)
    assert all(receipt[n]['executed_scope_equal_original'] for n in ['native_history.py','forecast.py','fpl_model.py'])
    p=tmp_path/'forecast.py';p.write_text(p.read_text(encoding='utf-8').replace('return best\n','return None\n'),encoding='utf-8')
    with pytest.raises(ValueError,match='Executed I4 source changed'):worker.qualify_i4_sources(original,tmp_path)
