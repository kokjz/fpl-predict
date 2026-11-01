import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import rich_market_combination as r
from test_market_stage_c import bundle as market_bundle
from test_native_development import source_inputs


def bundle():
    a=market_bundle();a.pop('X_market_strength')
    a['X_combined']=np.column_stack([a['X_control'].copy(),np.ones((len(a['y']),len(r.COMBINED)-len(r.CORE_FEATURES)))])
    for fold in r.FOLDS:
        train=a['season']<fold
        a['weights_'+fold]=r.sample_weights(pd.DataFrame({'ts':pd.to_datetime(a['ts_ns'][train],utc=True)}))
    return a


def test_union_exact_order_dedupe_and_frozen_contract():
    assert r.COMBINED==list(dict.fromkeys([*r.CORE_FEATURES,*r.i4.RICH,*r.MARKET_FEATURES]))
    assert len(r.COMBINED)==len(set(r.COMBINED)) and r.COMBINED[:49]==r.CORE_FEATURES
    assert r.COMBINED[-3:]==r.MARKET_FEATURES
    cfg=json.loads((Path(__file__).parents[1]/'docs/rich_market_combination_protocol_2026-10-29.json').read_text())
    assert cfg['features']==r.FEATURES and cfg['combined_features_canonical_sha256']==r.canonical_hash(r.COMBINED)


def test_rich_market_alignment_and_own_fixture_values():
    p=pd.DataFrame(dict(season=['2020-21']*2,gameweek=[1,1],fixture=[10,11],fpl_code=[1,2]))
    c=p.copy()
    for k in r.CORE_FEATURES:c[k]=3. if k=='n_history' else 60. if k=='last5_minutes' else 1.
    rich=pd.DataFrame(4.,index=p.index,columns=r.i4.RICH);e=pd.DataFrame({'candidate':[True,True]})
    market=np.array([[1.,2.,.2],[3.,4.,.1]])
    x=r.align_union(p,c,rich,e,market)
    np.testing.assert_array_equal(x[r.MARKET_FEATURES],market)
    np.testing.assert_array_equal(x[r.CORE_FEATURES],c[r.CORE_FEATURES])
    assert x[r.i4.RICH].eq(4).all().all()
    with pytest.raises(ValueError,match='index'):r.align_union(p,c,rich.iloc[::-1],e,market)
    c.loc[0,'fixture']=99
    with pytest.raises(ValueError,match='keys'):r.align_union(p,c,rich,e,market)


def test_training_only_omission_and_exact_control_fit(monkeypatch):
    a=bundle();calls=[];name=r.i4.RICH[0];j=r.COMBINED.index(name)
    train=a['season']<'2022-23';a['X_combined'][train,j]=np.nan;a['X_combined'][~train,j]=999
    class Model:
        def fit(self,x,y,sample_weight):calls.append((list(x),y.copy(),sample_weight.copy()));return self
        def predict(self,x):return np.full(len(x),2.)
        def get_params(self):return {'synthetic':True}
    monkeypatch.setattr(r,'estimator',lambda _:Model());monkeypatch.setattr(r.i4,'estimator',lambda _:Model())
    _,info=r.fit_predict(a,'2022-23','combined')
    assert name not in calls[-1][0] and info['omitted_features']==[name]
    pred,_=r.fit_predict(a,'2022-23','control')
    rows=pd.DataFrame({'ts':pd.to_datetime(a['ts_ns'],utc=True),'total_points':a['y']})
    old=r.i4.fit_predict('control',pd.DataFrame(a['X_control'],columns=r.CORE_FEATURES),rows,train,a['season']=='2022-23')
    np.testing.assert_array_equal(pred,old)
    for i in (0,1,2):np.testing.assert_array_equal(calls[-1][i],calls[-2][i])


@pytest.mark.parametrize('problem',['core_bytes','market_nan','duplicate_key','candidate','dgw_cutoff','weight','later_season','target_nan'])
def test_shared_proof_rejects_mutations_before_fit(problem):
    a=bundle();assert r.shared_proof(a)['core_bytes_identical']
    if problem=='core_bytes':a['X_control'][0,0]=0.;a['X_combined'][0,0]=-0.
    elif problem=='market_nan':a['X_combined'][0,-1]=np.nan
    elif problem=='duplicate_key':
        for k in r.i4.KEYS:a[k][1]=a[k][0]
    elif problem=='candidate':a['candidate'][0]=False
    elif problem=='dgw_cutoff':a['cutoff_ns'][1]-=1
    elif problem=='weight':a['weights_2022-23'][0]+=1
    elif problem=='later_season':a['season'][0]='2024-25'
    else:a['y'][0]=np.nan
    with pytest.raises(ValueError):r.shared_proof(a)


def test_preflight_reports_all_gaps_and_counts_later_only(tmp_path):
    paths=source_inputs(tmp_path)
    p=pd.read_csv(paths['players']);later=p.iloc[[0]].copy();later['season']='2024-25';later['total_points']='UNPARSEABLE_OUTCOME'
    p=p.drop(columns=['us_xA','starts']);later=later.drop(columns=['us_xA','starts'])
    pd.concat([p,later],ignore_index=True).to_csv(paths['players'],index=False)
    t=pd.read_csv(paths['teams']).drop(columns=['xga','deep']);t.to_csv(paths['teams'],index=False)
    report=r.preflight_files(paths)
    missing={(g['table'],g.get('column')) for g in report['gaps']}
    assert {('players','us_xA'),('players','starts'),('teams','xga'),('teams','deep')}<=missing
    assert report['season_counts']['players']['2024-25']==1
    assert report['confirmation_rows_present']==dict(players=True,teams=False)
    assert ('players','total_points') not in missing
    assert 'total_points' in [x['name'] for x in report['tables']['players']['inventory']]


def preflight_frames(tmp_path):
    paths=source_inputs(tmp_path)
    return {name:pd.read_csv(paths[name]).rename(columns={'GW':'gameweek'}) for name in ['players','teams','control']}


def test_nullable_object_clock_without_history_passes(tmp_path):
    frames=preflight_frames(tmp_path);c=frames['control']
    c['source_max_ts']=c.source_max_ts.astype(object)
    c.loc[0,'source_max_ts']=None;c.loc[0,'n_history']=0
    report=r.schema_preflight(frames)
    assert report['passed'] and report['control_clock_counts']==dict(missing_with_history=0,unparseable=0)


def test_missing_clock_with_history_is_counted(tmp_path):
    frames=preflight_frames(tmp_path);c=frames['control']
    c['source_max_ts']=c.source_max_ts.astype(object)
    c.loc[[0,1],'source_max_ts']=None;c.loc[0,'n_history']=0
    report=r.schema_preflight(frames)
    assert not report['passed'] and report['control_clock_counts']==dict(missing_with_history=1,unparseable=0)
    assert report['gaps']==[dict(table='control',kind='missing_source_with_history',column='source_max_ts',count=1)]


@pytest.mark.parametrize('value',['not-a-clock','2020-01-01T00:00:00'])
def test_present_clock_uses_exact_i4_parser(tmp_path,value):
    frames=preflight_frames(tmp_path);c=frames['control'];c['source_max_ts']=c.source_max_ts.astype(object)
    c.loc[0,'source_max_ts']=value
    with pytest.raises(ValueError):r.i4._timestamp(value)
    report=r.schema_preflight(frames)
    assert report['control_clock_counts']==dict(missing_with_history=0,unparseable=1)
    assert report['gaps']==[dict(table='control',kind='unparseable_source_timestamp',column='source_max_ts',count=1)]


def test_clock_gaps_accumulate_with_original_schema_gaps(tmp_path):
    frames=preflight_frames(tmp_path);c=frames['control'];c['source_max_ts']=c.source_max_ts.astype(object)
    c.loc[0,'source_max_ts']=None;c.loc[1,'source_max_ts']='not-a-clock'
    frames['players']=frames['players'].drop(columns=['us_xA','starts'])
    frames['teams']=frames['teams'].drop(columns=['xga','deep'])
    report=r.schema_preflight(frames)
    missing={(g['table'],g.get('column')) for g in report['gaps'] if g['kind']=='missing_column'}
    assert missing=={('players','us_xA'),('players','starts'),('teams','xga'),('teams','deep')}
    assert {'missing_source_with_history','unparseable_source_timestamp'}<={g['kind'] for g in report['gaps']}
    assert report['control_clock_counts']==dict(missing_with_history=1,unparseable=1)


def test_confirmation_masks_never_touch_2025():
    s=np.array([*r.SEASONS,'2024-25']);train,test=r.fold_masks(s,'2024-25',confirmation=True)
    assert list(s[train])==list(r.SEASONS) and list(s[test])==['2024-25']
    with pytest.raises(ValueError):r.fold_masks(np.append(s,'2025-26'),'2024-25',confirmation=True)
    with pytest.raises(ValueError):r.fold_masks(s,'2024-25')


def test_analysis_preserves_gate_and_double_gw_aggregation(monkeypatch):
    a=bundle();pred={(f,m):np.arange(8,dtype=float)+(.1 if m=='control' else 0.) for f in r.FOLDS for m in r.METHODS}
    monkeypatch.setattr(r.i4,'replay',lambda z,p,m:{n:dict(mean_total=100.+(n=='combined')) for n in m})
    panels={f:dict(first_gw=4,squads=[[],[]]) for f in r.FOLDS}
    report,z=r.analyse(a,pred,panels)
    assert report['gate']['passed'] and len(report['gate']['criteria'])==10
    assert report['metrics']['control']['player_gw']['n']==8
    assert report['metrics']['control']['fixture']['n']==16
    assert report['pooled_fixed_squad_delta']==1.


def test_exclusive_ledger_blocks_retry(tmp_path,monkeypatch):
    path=Path(__file__).parents[1]/'tools/run_rich_market_combination.py'
    spec=importlib.util.spec_from_file_location('rmc_worker',path);w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
    a=bundle();build=tmp_path/'build';build.mkdir();w.strict.save_npz(build/'bundle.npz',**a)
    w.strict.write_json(build/'summary.json',dict(protocol_lf_sha256=w.PROTOCOL_SHA,bundle_sha256=w.strict.digest(build/'bundle.npz'),proof=r.shared_proof(a)))
    calls=[];monkeypatch.setattr(r,'fit_predict',lambda *args:(calls.append(args[2]) or np.ones(8),{}))
    monkeypatch.setattr(w,'threadpool_info',lambda:[])
    out=tmp_path/'fit';out.mkdir();ledger=tmp_path/'ledger'
    w.fit(build/'bundle.npz','2022-23','control',ledger,out)
    with pytest.raises(ValueError,match='no retry'):w.fit(build/'bundle.npz','2022-23','control',ledger,out)
    assert calls==['control']
