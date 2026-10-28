import numpy as np
import pandas as pd
import pytest

import expected_return_amendment as a


def row(**changes):
    r=dict(season='2020-21',fixture=1,fpl_code=10,gameweek=1,team_name='A',opponent_name='B',ts='2020-09-20T12:00Z',deadline='2020-09-20T10:00Z',position=1,minutes=90.,total_points=6.,goals_scored=0.,assists=0.,us_xG=0.,us_xA=0.,goals_conceded=0.,saves=0.,penalties_saved=0.,penalties_missed=0.,yellow_cards=0.,red_cards=0.,own_goals=0.,bonus=0.)
    r.update(changes);return r


@pytest.mark.parametrize('minutes,conceded,clean,points',[(59,0,0,1),(60,0,1,6),(90,1,0,2),(90,2,0,1),(90,3,0,1),(90,4,0,0)])
def test_derivation_and_gk_conceded_floor(minutes,conceded,clean,points):
    q=a.reconcile(pd.DataFrame([row(minutes=minutes,goals_conceded=conceded,total_points=points)]))
    assert q.clean_sheets.iloc[0]==clean and q['_recomputed_points'].iloc[0]==points and q['_reconciled'].iloc[0]


@pytest.mark.parametrize('saves,points',[(2,6),(3,7),(5,7),(6,8)])
def test_gk_save_floor(saves,points):
    q=a.reconcile(pd.DataFrame([row(saves=saves,total_points=points)]));assert q['_reconciled'].iloc[0]


def test_full_reconciliation_rules_and_failure():
    p=pd.DataFrame([row(goals_scored=1,assists=1,saves=7,penalties_saved=1,penalties_missed=1,goals_conceded=3,yellow_cards=1,red_cards=1,own_goals=1,bonus=3,total_points=12)])
    # 2+6+3+2+5-2-1-1-3-2+3 = 12.
    q=a.reconcile(p);assert q['_reconciled'].iloc[0]
    p['total_points']=13;assert not a.reconcile(p)['_reconciled'].iloc[0]
    p=pd.DataFrame([row(position=4,goals_conceded=4,total_points=2)])
    assert a.reconcile(p)['_reconciled'].iloc[0]


def test_unreconciled_whole_row_fallback_and_exclusion_from_all_k():
    good=row(goals_scored=1,assists=1,us_xG=1,us_xA=1,total_points=15)
    bad=row(fpl_code=11,goals_scored=100,assists=100,us_xG=100,us_xA=100,total_points=123)
    p=pd.DataFrame([good,bad]);k,sums=a.constants(p,[0.,0.])
    assert k==dict(k_G=1.,k_A=1.,k_CS=1.)
    assert sums['return_rows']==sums['cs_rows']==1
    assert sums['denominators']==dict(k_G=1.,k_A=1.,k_CS=1.)
    y,fallback=a.training_target(p,[0.,0.],dict(k_G=.8,k_A=.8,k_CS=.8))
    assert y[1]==123 and fallback.tolist()==[False,True]
    assert y[0]==pytest.approx(15-6-3-4+6*.8+3*.8+4*.8)


def test_missing_us_still_fallback_and_cs_k_excludes_only_unreconciled():
    p=pd.DataFrame([row(goals_scored=1,assists=1,us_xG=1,us_xA=1,total_points=15),row(fpl_code=11,us_xG=np.nan,total_points=6)])
    k,sums=a.constants(p,[0.,0.]);assert sums['cs_rows']==2 and sums['return_rows']==1
    y,f=a.training_target(p,[0.,0.],k);assert y[1]==6 and f[1]


def test_non_fixture_rows_blocked_and_all_schema_gaps_reported():
    p=pd.DataFrame([row(),row()]);t=pd.DataFrame([dict(season='2020-21',fixture=1,team_name='B',opponent_name='A',ts='2020-09-20T12:00Z',xg=0.)])
    with pytest.raises(ValueError,match='Not one row per player-fixture'):a.reconcile(p)
    p=p.drop(columns=['saves','bonus']);t=t.drop(columns=['xg']);p['assists']='bad'
    report=a.schema_preflight(p,t);assert not report['passed']
    assert {x.get('column') for x in report['gaps']} >= {'saves','bonus','xg','assists'}
    assert any(x['kind']=='nonunique_or_null_fixture_key' for x in report['gaps'])


def test_preflight_never_calls_label_statistics(tmp_path,monkeypatch):
    def forbidden(*args,**kwargs):pytest.fail('Preflight must not compute labels or statistics')
    monkeypatch.setattr(a,'reconcile',forbidden);monkeypatch.setattr(a,'constants',forbidden)
    p=tmp_path/'p.csv';t=tmp_path/'t.csv';pd.DataFrame([row()]).to_csv(p,index=False)
    pd.DataFrame([dict(season='2020-21',fixture=1,team_name='B',opponent_name='A',ts='2020-09-20T12:00Z',xg=0.)]).to_csv(t,index=False)
    assert a.preflight_files(p,t)['passed']


def test_training_only_poisoning_and_gate_counts():
    rows=[];teams=[]
    for season in a.SEASONS:
        teams.append(dict(season=season,fixture=1,team_name='B',xg=0.))
        for pos in [1,2,3,4]:
            gp={1:6,2:6,3:5,4:4}[pos];cs={1:4,2:4,3:1,4:0}[pos]
            rows.append(row(season=season,position=pos,fpl_code=pos,goals_scored=1,assists=1,us_xG=1,us_xA=1,total_points=2+gp+3+cs))
    p=pd.DataFrame(rows);t=pd.DataFrame(teams)
    result=a.admission(p,t);assert result['gate_A_pass']
    assert result['seasons']['2020-21']['reconciled_share']==1.
    labels,info,mask=a.fold_labels(p,t,'2022-23');p['us_xG']=p.us_xG.astype(float);p.loc[~mask,'us_xG']=np.inf
    second,other,_=a.fold_labels(p,t,'2022-23');assert info==other and np.array_equal(labels,second)
    p.loc[0,'total_points']+=1;bad=a.admission(p,t)
    assert not bad['gate_A_pass'] and bad['seasons']['2020-21']['unreconciled_played_rows']==1
