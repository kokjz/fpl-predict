"""Synthetic checks for the frozen compliant combination."""
import hashlib
import json
from pathlib import Path

from fpl_model import CORE_FEATURES
from native_development import FPL
from market_stage_c import MARKET_FEATURES, canonical_hash
import numpy as np
import pandas as pd
import pytest
import fpl_native_combination as study
from test_native_history import data
from native_history import NativeHistory


def test_protocol_contract():
    path=Path(__file__).resolve().parents[1]/'docs/fpl_native_combination_protocol_2026-11-02.json'
    raw=path.read_bytes().replace(b'\r\n',b'\n')
    assert hashlib.sha256(raw).hexdigest()=='a6760823ffd6b145fc7e332d21a83ffde8bf26eea6e0448fa987525987b1d188'
    cfg=json.loads(raw)
    union=list(dict.fromkeys([*CORE_FEATURES,*FPL,*MARKET_FEATURES]))
    assert cfg['features']==dict(control=CORE_FEATURES,fpl_native=union)
    assert cfg['feature_list_canonical_sha256']==canonical_hash(union)
    assert len(cfg['fit_order'])==8
    assert cfg['stage_C']['retrieval']['attempts']==1
    assert [j['stage'] for j in cfg['fit_order']]==['B']*4+['C']*4


def fixture():
    p,t,_,snap=data()
    p['gameweek']=p.fixture;p['deadline']=pd.to_datetime(p.ts,utc=True)-pd.Timedelta(hours=5)
    return p,t,snap


def test_whitelist_builder_matches_original_fpl_bytes():
    p,t,snap=fixture();expected,_=NativeHistory(p,t).transform(p,snap)
    for i,name in enumerate(study.i4.POSITION,1):expected[name]=p.position.eq(i).astype(np.float32)
    actual,evidence=study.native_features(p,t)
    assert actual.to_numpy().tobytes()==expected[study.NATIVE].to_numpy().tobytes()
    assert study.static_audit()['passed']
    assert len(study.UNION)==198 and study.UNION[:49]==CORE_FEATURES
    stripped_p=p.drop(columns=[n for n in p if n.startswith('us_')])
    stripped_t=t.drop(columns=list(study.US_TEAM))
    other,_=study.native_features(stripped_p,stripped_t)
    assert actual.to_numpy().tobytes()==other.to_numpy().tobytes()


def test_ablation_detects_a_provider_dependency():
    p,t,_=fixture();_,receipt=study.ablation_invariance(p,t)
    assert receipt['passed'] and receipt['player_columns'] and receipt['team_columns']
    def bad(players,teams):
        x,e=study.native_features(players,teams);x.iloc[:,0]=players.us_xG.to_numpy();return x,e
    with pytest.raises(ValueError,match='ablation'):study.ablation_invariance(p,t,bad)


def test_closed_seasons_and_original_confirmation_are_unchanged():
    old=study.confirmation.SEASONS
    c24=study.scoped_confirmation('2024-25');c25=study.scoped_confirmation('2025-26')
    assert c24['SEASONS']==old and c25['SEASONS']==(*old,'2025-26')
    assert c24['select_control'].__code__ is study.confirmation.select_control.__code__
    assert c24['market_rows'].__code__ is study.confirmation.market_rows.__code__
    assert study.confirmation.SEASONS==old
    with pytest.raises(ValueError):study.fold_masks(np.array(['2026-27']),'2025-26')
    with pytest.raises(ValueError):study.scoped_confirmation('2026-27')


def test_full_score_uses_same_dc_term_and_sums_double_gameweek():
    z=pd.DataFrame(dict(season=['2025-26']*3,gameweek=[28,28,29],fpl_code=[1,1,2],candidate=[True]*3,pos=[2,2,1],dc_rate4=[.5,.25,np.nan],total_points=[3.,4.,2.],control=[2.,3.5,2.],fpl_native=[2.,3.5,2.]))
    full=study.full_scoring(z)
    assert full['passed'] and full['metrics']['control']['player_gw']==full['metrics']['fpl_native']['player_gw']
    z.loc[0,'dc_rate4']=np.nan
    with pytest.raises(ValueError,match='DC'):study.full_scoring(z)


def test_audit_gates_use_pooled_error_and_strict_interval_boundary():
    metrics={m:{k:dict(rmse=1.,mae=1.) for k in ('player_gw','fixture')} for m in study.METHODS}
    for k in ('player_gw','fixture'):metrics['fpl_native'][k]['rmse']=.994
    folds={f:{m:dict(candidate_player_gw=dict(rmse=1.)) for m in study.METHODS} for f in study.AUDITS}
    interval=dict(status='descriptive_interval',rmse=dict(upper=-.001))
    full=dict(passed=True,criteria={})
    assert study.audit_gates(metrics,folds,interval,0,full)['passed']
    interval['rmse']['upper']=0
    assert not study.audit_gates(metrics,folds,interval,0,full)['passed']
    interval['rmse']['upper']=-.001
    folds['2025-26']['fpl_native']['candidate_player_gw']['rmse']=1.006
    assert not study.audit_gates(metrics,folds,interval,0,full)['passed']


def native_bundle():
    from test_rich_market_combination import bundle
    a=bundle();a.pop('X_combined')
    a['X_fpl_native']=np.column_stack([a['X_control'].copy(),np.ones((len(a['y']),len(study.UNION)-49))])
    return a


def test_training_only_omission_and_byte_proof(monkeypatch):
    a=native_bundle();assert study.shared_proof(a,study.DEVELOPMENT)['core_bytes_identical']
    name=study.NATIVE[0];j=study.UNION.index(name);train=a['season']<'2022-23'
    a['X_fpl_native'][train,j]=np.nan;a['X_fpl_native'][~train,j]=999
    calls=[]
    class Model:
        def fit(self,x,y,sample_weight):calls.append(list(x));return self
        def predict(self,x):return np.full(len(x),2.)
        def get_params(self):return {'synthetic':True}
    monkeypatch.setattr(study,'estimator',lambda _:Model())
    _,info=study.fit_predict(a,'2022-23','fpl_native')
    assert name not in calls[-1] and name in info['omitted_features']
    a['y'][0]=np.nan
    with pytest.raises(ValueError,match='targets'):study.shared_proof(a,study.DEVELOPMENT)


def test_reused_development_analysis_and_gates_are_exact(monkeypatch):
    from test_rich_market_combination import bundle
    old=bundle();a=native_bundle()
    pred={(f,m):np.arange(8,dtype=float)+(.1 if m=='control' else 0) for f in study.DEVELOPMENT for m in study.METHODS}
    monkeypatch.setattr(study.i4,'replay',lambda z,p,m:{name:dict(mean_total=100.+(name!='control')) for name in m})
    panels={f:dict(first_gw=4,squads=[[],[]]) for f in study.DEVELOPMENT}
    expected,_=study.rich.analyse(old,{(f,'combined' if m=='fpl_native' else m):v for (f,m),v in pred.items()},panels)
    report,z=study.analyse(a,pred,panels,study.DEVELOPMENT)
    assert report['gate']==expected['gate'] and report['gate']['passed']
    assert report['metrics']['fpl_native']==expected['metrics']['combined']
    assert report['pooled_fixed_squad_delta']==1. and 'fpl_native' in z


def test_bootstrap_contract_and_confirmation_csv_reuse():
    assert study.scoped_confirmation('2024-25')['select_control'].__code__ is study.confirmation.select_control.__code__
    frame=pd.DataFrame(dict(season=['2025-26']*12,gameweek=np.arange(1,13),fpl_code=np.arange(12),actual=np.ones(12),control=np.zeros(12),fpl_native=np.ones(12)))
    interval=study.paired_block_errors(frame,'fpl_native','control')
    assert interval['samples']==1000 and interval['seed']==20261015 and interval['block_length']==4
    assert interval['rmse']['upper']<0


def test_two_audit_fold_analysis_and_full_score(monkeypatch):
    from test_rmc_confirmation import bundle
    original=bundle();a={}
    for k,v in original.items():
        if k in ('weights','X_combined'):continue
        extra=v[-8:].copy()
        if k=='season':extra[:]='2025-26'
        if k in ('cutoff_ns','ts_ns'):extra+=int(pd.Timedelta(days=365).value)
        if k=='gameweek':extra+=27
        a[k]=np.concatenate([v,extra])
    a['X_fpl_native']=np.column_stack([a['X_control'].copy(),np.ones((len(a['y']),len(study.UNION)-49))])
    a['dc_rate4']=np.full(len(a['y']),.25);a['total_points']=a['y']+np.where(a['pos']==1,0,.5)
    for fold in study.AUDITS:
        train=a['season']<fold;a['weights_'+fold]=study.sample_weights(pd.DataFrame({'ts':pd.to_datetime(a['ts_ns'][train],utc=True)}))
    predictions={(f,m):a['y'][a['season']==f]+(.1 if m=='control' else 0) for f in study.AUDITS for m in study.METHODS}
    monkeypatch.setattr(study.i4,'replay',lambda z,p,m:{name:dict(mean_total=100.+(name!='control')) for name in m})
    report,z=study.analyse(a,predictions,{f:dict(first_gw=4,squads=[[],[]]) for f in study.AUDITS},study.AUDITS)
    assert len(report['gate']['criteria'])==6 and report['full_scoring']['passed']
    assert report['full_scoring']['metrics']['fpl_native']['fixture']['rmse']==0
    assert report['gate']['criteria']['3_audit_season_stability']['passed']
