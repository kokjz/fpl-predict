import numpy as np
import pandas as pd
import pytest
import core_xg_mask as t
from fpl_model import CORE_FEATURES,PRIORS,normalise
from test_fpl_team_xg import bundle

def history():
    rows=[]
    for season in t.SEASONS:
        gws=[g for _,g in t.EXPECTED_UNPUBLISHED]+[16,17] if season=='2022-23' else [1,2,3,4]
        for gw in gws:
            ts=pd.Timestamp(f'{season[:4]}-08-01T15:00Z')+pd.Timedelta(days=7*(gw-1))
            for i in range(40):
                team=i%20+1;pos=1 if i<4 else 2 if i<16 else 3 if i<28 else 4
                value=np.nan if season<'2022-23' else 0. if season=='2022-23' and gw<16 else .12345678901234567
                rows.append(dict(season=season,GW=gw,fixture=gw*10+(team-1)//2,element=i+1,team_id=team,opponent_team=team+1 if team%2 else team-1,was_home=bool(team%2),minutes=90,pos=pos,value=40.,kickoff_time=ts.isoformat(),cutoff=ts-pd.Timedelta(minutes=90),total_points=2+(i%3),defensive_contribution=np.nan,expected_goals=value,expected_assists=value,expected_goals_conceded=value,team_gf=1,team_ga=1))
    return normalise(pd.DataFrame(rows))

def test_detection_mask_scope_prior_and_exclusion():
    h=history();before=h.copy(deep=True);masked,report=t.mask_history(h)
    pd.testing.assert_frame_equal(h,before)
    for f in t.FIELDS:
        assert len(report[f]['detected'])==14
        assert masked.loc[(masked.season=='2022-23')&(masked.GW<16),f].isna().all()
    pd.testing.assert_frame_equal(h.drop(columns=list(t.FIELDS)),masked.drop(columns=list(t.FIELDS)))
    targets=h[(h.season=='2022-23')&(h.GW==2)]
    rebuilt=t.rebuild(masked,targets)
    for n in t.COLUMNS:assert rebuilt[n].eq(PRIORS[n.split('_',1)[1]]).all()
    with pytest.raises(ValueError):t.mask_history(h.assign(season='2026-27'))
    with pytest.raises(ValueError):t.rebuild(h,h[h.season=='2023-24'])
    assert t.static_audit()['passed']

@pytest.mark.parametrize('kind',['partial','zero_minute_nonzero','nan','zero_goals'])
@pytest.mark.parametrize('field',t.FIELDS)
def test_detection_negative(kind,field):
    h=history();h=h[(h.season=='2022-23')&(h.GW==1)].copy()
    if kind=='partial':h.loc[h.index[0],field]=.1
    elif kind=='zero_minute_nonzero':h.loc[h.index[0],['minutes',field]]=[0,.1]
    elif kind=='nan':h.loc[h.index[0],field]=np.nan
    else:h['team_gf']=0
    assert t.unpublished_gameweeks(h,field)==[]

def test_expected_set_and_identity_guards():
    h=history();h.loc[(h.season=='2022-23')&(h.GW==1),'expected_assists']=.1
    with pytest.raises(ValueError,match='Unexpected unpublished'):t.mask_history(h)
    a=bundle();a.pop('X_team_xg');a['X_corrected']=a['X_control'].copy()
    assert t.shared_proof(a,t.DEVELOPMENT)['correction']['passed']
    for row,col in [(0,t.COLUMNS[0]),(16,'home')]:
        z=a['X_corrected'].copy();z[row,CORE_FEATURES.index(col)]+=1
        with pytest.raises(ValueError):t.correction_proof(a['X_control'],z,a['season'])

@pytest.mark.parametrize('folds',[t.DEVELOPMENT,t.AUDITS])
def test_gate_boundaries(folds):
    control={u:dict(rmse=10.,mae=5.) for u in ('player_gw','fixture')};control['ndcg10']=.5
    candidate={u:dict(rmse=10.,mae=1.005*5) for u in ('player_gw','fixture')};candidate['ndcg10']=.5
    fc={f:{u:dict(rmse=10.) for u in ('candidate_player_gw','candidate_fixture')} for f in folds}
    fn={f:{u:dict(rmse=1.005*10) for u in ('candidate_player_gw','candidate_fixture')} for f in folds}
    assert t.gate_details(candidate,control,fn,fc,0)['passed']
    assert len(t.gate_details(candidate,control,fn,fc,0)['criteria'])==(10 if folds==t.DEVELOPMENT else 6)
    for u in ('player_gw','fixture'):
        for metric in ('rmse','mae'):
            old=candidate[u][metric];candidate[u][metric]=np.nextafter(old,np.inf)
            assert not t.gate_details(candidate,control,fn,fc,0)['passed'];candidate[u][metric]=old
    candidate['ndcg10']=np.nextafter(.5,0)
    assert not t.gate_details(candidate,control,fn,fc,0)['passed'];candidate['ndcg10']=.5
    assert not t.gate_details(candidate,control,fn,fc,-1e-12)['passed']
    if folds==t.DEVELOPMENT:
        fn[folds[0]]['candidate_fixture']['rmse']=np.nextafter(1.005*10,np.inf)
        assert not t.gate_details(candidate,control,fn,fc,0)['passed']

def test_control_fit_parity():
    from threadpoolctl import threadpool_limits
    a=bundle();a['X_corrected']=a['X_control'].copy()
    with threadpool_limits(limits=2):
        x,_=t.fit_predict(a,'2023-24','control');y,_=t.fit_predict(a,'2023-24','corrected')
    assert x.tobytes()==y.tobytes()
