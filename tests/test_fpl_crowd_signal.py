import numpy as np
import pandas as pd
import pytest
import fpl_crowd_signal as t
from fpl_model import CORE_FEATURES,ew
from test_fpl_team_xg import bundle


def history():
    rows=[]
    for season in ('2022-23','2023-24'):
        for gw in (1,2,3):
            for element in (1,2,3):
                ts=pd.Timestamp(f'{season[:4]}-08-01T15:00Z')+pd.Timedelta(days=7*(gw-1))
                tb=5000 if element==1 else -5000
                rows.append(dict(season=season,element=element,GW=gw,ts=ts,cutoff=ts-pd.Timedelta(hours=1),selected=10 if element<3 else 30,transfers_in=max(tb,0),transfers_out=max(-tb,0),transfers_balance=tb,value=40+gw,pos=2,points_core=element))
    return pd.DataFrame(rows)


def test_lag_ties_dedup_fallback_share_value_reset_and_own_gw_exclusion():
    h=history();store=t.CrowdStore(h);x,proof,fallback=store.transform(h)
    assert list(x)==t.NEW_FEATURES and len(t.NEW_FEATURES)==6 and proof['passed']
    assert x.loc[h.GW.eq(1),t.NEW_FEATURES[:4]].eq([.5,.5,0,.5]).all().all()
    assert fallback.sum()==6 and x.crowd_value_change.eq(h.GW-1).all()
    i=h.index[(h.season=='2022-23')&(h.GW==2)&(h.element==1)][0]
    assert x.loc[i,'crowd_sel_pct_last']==.5 # two tied ranks: mean(1,2)/3
    assert x.loc[i,'crowd_tb_pct_last']==1
    assert x.loc[i,'crowd_tb_share_last']==1
    assert x.loc[i+1,'crowd_tb_share_last']==-1
    assert x.loc[i,'crowd_ew4_tb_pct']==ew([1.],4,.5,2)
    changed=h.copy();changed.loc[h.GW.eq(2),['selected','transfers_in','transfers_out','transfers_balance']]=[9999,8888,0,8888]
    y,_,_=t.CrowdStore(changed).transform(h[h.GW.eq(2)])
    assert y.to_numpy().tobytes()==x.loc[h.GW.eq(2)].to_numpy().tobytes()
    doubled=pd.concat([h,h.iloc[[0]].assign(ts=h.ts.iloc[0]+pd.Timedelta(days=1))])
    y,_,_=t.CrowdStore(doubled).transform(h)
    assert x.to_numpy().tobytes()==y.to_numpy().tobytes()
    # A qualifying timestamp from the same GW still must never enter.
    target=h.iloc[[0]].copy();target.cutoff+=pd.Timedelta(days=2)
    y,_,_=store.transform(target);assert y.iloc[0,:4].tolist()==[.5,.5,0,.5]
    for delta in (pd.Timedelta(hours=3),pd.Timedelta(hours=3,seconds=1)):
        target=h.iloc[[i]].copy();target.cutoff=h.ts.iloc[0]+delta
        y,_,_=store.transform(target)
        assert y.iloc[0].crowd_tb_pct_last==(.5 if delta==pd.Timedelta(hours=3) else 1.)


@pytest.mark.parametrize('field',t.FIELDS)
def test_schema_nan_and_dgw_consistency_stop(field):
    h=history();assert not t.field_checks(h.drop(columns=field),False)['passed']
    h.loc[0,field]=np.nan
    with pytest.raises(ValueError):t.CrowdStore(h)
    h=history();duplicate=h.iloc[[0]].copy();duplicate[field]+=1
    with pytest.raises(ValueError):t.CrowdStore(pd.concat([h,duplicate]))


def test_integrity_excluded_season_and_clock_proof():
    for name,value in [('selected',-1),('value',34),('value',161),('transfers_balance',99)]:
        h=history();h.loc[0,name]=value
        with pytest.raises(ValueError):t.CrowdStore(h)
    with pytest.raises(ValueError):t.CrowdStore(history().assign(season='2026-27'))
    with pytest.raises(ValueError):t.fold_masks(['2026-27'],'2025-26')
    h=history();h.loc[2,'ts']+=pd.Timedelta(days=20)
    with pytest.raises(ValueError,match='population'):t.CrowdStore(h).transform(history().iloc[[3]])
    assert t.static_audit()['passed']


def test_corrected_core_identity_and_gate_contract():
    a=bundle();a.pop('X_team_xg');a['X_crowd']=np.column_stack([a['X_control'],np.zeros((len(a['y']),6))])
    assert t.shared_proof(a,t.DEVELOPMENT)['core_bytes_identical']
    a['X_crowd'][0,0]+=1
    with pytest.raises(ValueError,match='CORE'):t.shared_proof(a,t.DEVELOPMENT)
    assert t.gate_details is t.previous.gate_details


def test_gate_boundaries():
    c={u:dict(rmse=10.,mae=5.) for u in ('player_gw','fixture')};c['ndcg10']=.5
    n={u:dict(rmse=.995*10,mae=1.005*5) for u in ('player_gw','fixture')};n['ndcg10']=.5
    fc={f:{u:dict(rmse=10.) for u in ('candidate_player_gw','candidate_fixture')} for f in t.DEVELOPMENT}
    fn={f:{u:dict(rmse=1.005*10) for u in ('candidate_player_gw','candidate_fixture')} for f in t.DEVELOPMENT}
    assert t.gate_details(n,c,fn,fc,0)['passed']
    for u in ('player_gw','fixture'):
        for metric in ('rmse','mae'):
            old=n[u][metric];n[u][metric]=np.nextafter(old,np.inf)
            assert not t.gate_details(n,c,fn,fc,0)['passed'];n[u][metric]=old
    assert not t.gate_details(n,c,fn,fc,-1e-12)['passed']
