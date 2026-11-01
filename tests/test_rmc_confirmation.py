import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import rmc_confirmation as s
from test_native_development import source_inputs
from test_rich_market_combination import bundle as development_bundle


def frames(tmp_path):
    paths=source_inputs(tmp_path);out={k:pd.read_csv(paths[k]).rename(columns={'GW':'gameweek'}) for k in ['players','teams','control']}
    for name,d in out.items():
        extra=d[d.season.eq('2023-24')].copy();extra['season']='2024-25'
        for k in ['ts','deadline','cutoff','source_max_ts']:
            if k in extra:extra[k]=(pd.to_datetime(extra[k],utc=True)+pd.DateOffset(years=1)).astype(str)
        out[name]=pd.concat([d,extra],ignore_index=True)
    return out


def bundle():
    a=development_bundle();out={}
    for k,v in a.items():
        if k.startswith('weights_'):continue
        extra=v[-8:].copy()
        if k=='season':extra[:]='2024-25'
        if k in ['cutoff_ns','ts_ns']:extra+=int(pd.Timedelta(days=366).value)
        out[k]=np.concatenate([v,extra])
    train=out['season']<'2024-25';out['weights']=s.sample_weights(pd.DataFrame({'ts':pd.to_datetime(out['ts_ns'][train],utc=True)}))
    return out


def test_later_rows_dropped_before_validation_and_feature_constructor(tmp_path,monkeypatch):
    d=frames(tmp_path);seen=[]
    for name in d:
        later=d[name].iloc[[0]].copy();later['season']='2025-26';later['ts']='UNPARSEABLE_LATER_CLOCK'
        if name in ['players','control']:later['total_points']='UNPARSEABLE_LATER_OUTCOME'
        d[name]=pd.concat([d[name],later],ignore_index=True)
    monkeypatch.setattr(s.base,'NativeHistory',lambda p,t:seen.append((set(p.season),set(t.season))))
    p,t,c=s.validate_inputs(d['players'],d['teams'],d['control'])
    assert set(p.season)==set(t.season)==set(c.season)==set(s.SEASONS)
    assert seen==[(set(s.SEASONS),set(s.SEASONS))]
    path=tmp_path/'scoped.csv';d['players'].to_csv(path,index=False)
    parsed=s.read_scoped(path);assert set(parsed.season)==set(s.SEASONS) and pd.api.types.is_numeric_dtype(parsed.total_points.dtype)


@pytest.mark.parametrize('problem',['target','gap','week','deadline','source','duplicate'])
def test_confirmation_admission_rejects_same_i4_gaps(tmp_path,problem):
    d=frames(tmp_path);p,c=d['players'],d['control'];j=p.index[p.season.eq(s.FOLD)][0]
    if problem=='target':c.loc[j,'points_core']=99
    elif problem=='gap':p.loc[j,'us_xG']=np.nan
    elif problem=='week':
        d['players']=p[~(p.season.eq(s.FOLD)&p.gameweek.eq(7))];d['control']=c[~(c.season.eq(s.FOLD)&c.gameweek.eq(7))]
    elif problem=='deadline':p.loc[j,'deadline']=p.loc[j,'ts'];c.loc[j,'cutoff']=p.loc[j,'ts']
    elif problem=='source':c.loc[j,'source_max_ts']=c.loc[j,'cutoff']
    else:d['players']=pd.concat([p,p.iloc[[j]]],ignore_index=True)
    with pytest.raises(ValueError):s.validate_inputs(d['players'],d['teams'],d['control'])


def test_control_export_selects_only_allowed_indices(tmp_path):
    d=frames(tmp_path)['control'].rename(columns={'gameweek':'GW'});d['value']=45.
    later=d.iloc[[0]].copy();later['season']='2025-26';later['element']=999
    d=pd.concat([d,later],ignore_index=True)
    x=d[s.CORE_FEATURES].copy();x['source_max_ts']=d.source_max_ts;x.loc[d.season.eq('2025-26'),s.CORE_FEATURES]=np.inf
    bridges={year:pd.DataFrame({'id':[11,22],'code':[11,22]}) for year in s.SEASONS}
    c=s.select_control(d,x,bridges)
    assert set(c.season)==set(s.SEASONS) and np.isfinite(c[s.CORE_FEATURES]).all().all()


def market_fixture():
    rows=[];p=[]
    for i in range(380):
        when=pd.Timestamp('2024-08-01T15:00:00Z')+pd.Timedelta(days=i)
        rows.append(dict(Date=when.strftime('%d/%m/%Y'),Time='15:00',HomeTeam='Arsenal',AwayTeam='Liverpool',AvgCH='2',AvgCD='3',AvgCA='4',**{'AvgC>2.5':'2','AvgC<2.5':'2'}))
        p.append(dict(season=s.FOLD,fixture=i+1,ts=when,home=True,team_name='Arsenal',opponent_name='Liverpool'))
    return rows,pd.DataFrame(p)


@pytest.mark.parametrize('problem',[None,'count','date','name','odds','duplicate'])
def test_market_admission_380_exact_matches_or_stop(monkeypatch,problem):
    monkeypatch.setattr(s,'solve_lambdas',lambda p:dict(lambda_home=1.2,lambda_away=.8))
    rows,p=market_fixture()
    if problem=='count':rows.pop()
    elif problem=='date':rows[0]['Date']='01/01/2020'
    elif problem=='name':rows[0]['HomeTeam']='Arsenal guessed alias'
    elif problem=='odds':rows[0]['AvgCH']=''
    elif problem=='duplicate':rows[1]=dict(rows[0])
    if problem:
        with pytest.raises(ValueError):s.admit_market(rows,p)
    else:
        lambdas,r=s.admit_market(rows,p)
        assert len(lambdas)==r['fpl_matched']==r['complete_odds']==380
        assert r['name_equivalences']=={'Ipswich':'Ipswich'}


def test_market_target_odds_never_enter_same_origin():
    old=[dict(season='2019-20',fixture=None,home='Liverpool',away='Arsenal',csv_kickoff='2024-01-01T15:00:00Z',canonical_kickoff=None,lambda_home=2.,lambda_away=1.)]
    target=dict(season=s.FOLD,fixture=1,home='Liverpool',away='Arsenal',csv_kickoff='2024-08-10T15:00:00Z',canonical_kickoff='2024-08-10T15:00:00Z',lambda_home=5.,lambda_away=.1)
    p=pd.DataFrame([dict(season=s.FOLD,fixture=1,team_name='Liverpool',opponent_name='Arsenal',home=True,ts=pd.Timestamp(target['canonical_kickoff']),deadline=pd.Timestamp('2024-08-10T12:00:00Z'))])
    first,e,_=s.market_rows(p,old+[target]);target['lambda_home']=.2;target['lambda_away']=5.
    second,_,_=s.market_rows(p,old+[target]);np.testing.assert_array_equal(first,second)
    assert all(pd.Timestamp(r['source_max'])<pd.Timestamp(r['cutoff']) for r in e)


def test_two_fit_methods_receive_only_training_rows_and_training_omission(monkeypatch):
    a=bundle();seen=[];j=s.base.COMBINED.index(s.base.i4.RICH[0]);train=a['season']<s.FOLD;a['X_combined'][train,j]=np.nan
    class Model:
        def fit(self,x,y,sample_weight):seen.append((list(x),y.copy(),sample_weight.copy()));return self
        def predict(self,x):return np.full(len(x),2.)
        def get_params(self):return {'synthetic':True}
    monkeypatch.setattr(s,'estimator',lambda _:Model())
    for method in ['control','combined']:
        prediction,t=s.fit_predict(a,method);assert len(prediction)==8
    assert s.base.i4.RICH[0] not in seen[1][0]
    assert all(len(y)==32 for _,y,_ in seen)
    a['season'][-1]='2025-26'
    with pytest.raises(ValueError):s.fit_predict(a,'control')
    with pytest.raises(ValueError):s.analyse(a,{},dict())


def test_gate_six_frozen_rules_and_single_fold_metrics(monkeypatch):
    a=bundle();pred={m:np.arange(8,dtype=float)+(.1 if m=='control' else 0) for m in s.base.METHODS}
    monkeypatch.setattr(s.base.i4,'replay',lambda z,p,m:{name:dict(mean_total=100.+(name=='combined')) for name in m})
    r,z=s.analyse(a,pred,dict(first_gw=4,squads=[[],[]]))
    assert r['gate']['passed'] and len(r['gate']['criteria'])==6 and r['points']['combined']['mean_delta']==1
    assert r['metrics']['control']['player_gw']['n']==4 and r['metrics']['control']['fixture']['n']==8
    assert not s.gate(r['metrics']['combined'],r['metrics']['control'],-1)['passed']


def test_panels_bound_before_fit_and_no_retry(tmp_path,monkeypatch):
    path=Path(__file__).parents[1]/'tools/run_rmc_confirmation.py';spec=importlib.util.spec_from_file_location('confirm_worker',path);w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
    a=bundle();d=tmp_path/'build';d.mkdir();panel=dict(first_gw=4,squads=[[]]*20)
    w.strict.save_npz(d/'bundle.npz',**a);w.strict.write_json(d/'panels.json',dict(panel=panel,created_before_fits=True))
    summary=dict(bundle_sha256=w.strict.digest(d/'bundle.npz'),panel_file_sha256=w.strict.digest(d/'panels.json'),panel_sha256=s.canonical_hash(panel),proof=s.shared_proof(a));w.strict.write_json(d/'summary.json',summary)
    calls=[];monkeypatch.setattr(s,'fit_predict',lambda a,m:(calls.append(m) or np.ones(8),{}));monkeypatch.setattr(w,'threadpool_info',lambda:[])
    out=tmp_path/'fit';out.mkdir();ledger=tmp_path/'ledger';w.fit(d/'bundle.npz','control',ledger,out)
    with pytest.raises(ValueError,match='no retry'):w.fit(d/'bundle.npz','control',ledger,out)
    assert calls==['control']
    (d/'panels.json').write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='panels'):w.load_bundle(d/'bundle.npz')
