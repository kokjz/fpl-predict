"""Independent cold-start/origin/identity counterexamples."""
import pandas as pd
import pytest
from horizon_forecast import Horizon
from preseason_reference import apply,previous_season
from season_engine import Market


def inputs():
    m=Market.create('2025-26',1,'2025-08-15T17:30Z','2025-08-15T12:00Z',[
        dict(id=9,position=3,team='1',price_tenths=50,can_buy=True),dict(id=3,position=4,team='2',price_tenths=50,can_buy=True)])
    f=pd.DataFrame([dict(id=i,event=g,team_h=1,team_a=2) for i,g in [(1,1),(2,1),(3,3)]])
    b=Horizon.create(m,[dict(gameweek=g,id=i,expected_points=4. if g==1 else 2. if g==3 else 0.) for g in [1,2,3] for i in [9,3]],
        trained_through='2025-05-30T12:00Z',feature_cutoff=m.as_of,source_as_of=m.as_of,model_id='fake')
    # Player9 now has code333; old season-local player3 must not match current3.
    h=pd.DataFrame([dict(season='2024-25',code=333,fixture=1,ts='2025-05-25T12:00Z',position=3,points_core=8.,dc_hit=float('nan')),
                    dict(season='2024-25',code=999,fixture=1,ts='2025-05-25T12:00Z',position=4,points_core=1.,dc_hit=0.)])
    r=pd.DataFrame([dict(id=9,code=333,position=3,ep_next=5.),dict(id=3,code=555,position=4,ep_next=None)])
    return b,m,f,h,r


def run(b,m,f,h,r,**kw):return apply(b,m,f,h,r,source_as_of=m.as_of,**kw)


def test_stable_identity_shrinkage_double_blank_and_missing_player():
    b,m,f,h,r=inputs();p,report=run(b,m,f,h,r)
    # One8+.24 prior observation, two2-point pseudo-observations:4.08 per fixture.
    assert p.values()[1,9]==pytest.approx(8.16)
    assert p.values()[3,9]==pytest.approx(4.08)
    assert p.values()[2,9]==0. and p.values()[1,3]==4.
    assert report['players'][0]['stable_code']==333
    assert b.values()[1,9]==4. # Does not mutate input.


def test_official_is_only_origin_gw_total_and_does_not_fill_blank():
    b,m,f,h,r=inputs();p,_=run(b,m,f,h,r,official=True)
    assert p.values()[1,9]==5. and p.values()[3,9]==pytest.approx(4.08)
    assert p.values()[2,9]==0. and p.values()[1,3]==4.


def test_current_season_fade_ignores_current_points_and_is_zero_after_six():
    b,m,f,h,r=inputs()
    rows=[dict(season='2025-26',code=333,fixture=i,ts=f'2025-08-{i:02d}T12:00Z',position=3,points_core=100.,dc_hit=1.) for i in range(1,7)]
    two=pd.concat([h,pd.DataFrame(rows[:2])]);p,report=run(b,m,f,two,r)
    assert p.values()[1,9]==pytest.approx(4.+(8.16-4.)*2/3)
    two.loc[two.season.eq(m.season),'points_core']=-100.
    q,_=run(b,m,f,two,r);assert p.values()==q.values()
    q,report=run(b,m,f,pd.concat([h,pd.DataFrame(rows)]),r)
    assert q.values()==b.values() and report['players'][0]['carryover_weight']==0.


def test_future_results_and_nonadjacent_seasons_cannot_change_forecast():
    b,m,f,h,r=inputs();p,_=run(b,m,f,h,r)
    later=h.iloc[[0]].assign(season='2025-26',ts='2025-08-15T18:00Z',points_core=999.)
    ancient=h.iloc[[0]].assign(season='2023-24',points_core=999.)
    q,_=run(b,m,f,pd.concat([h,later,ancient]),r);assert p.values()==q.values()


def test_position_change_does_not_reuse_old_position_points():
    b,m,f,h,r=inputs();h.loc[h.code.eq(333),'position']=2
    q,report=run(b,m,f,h,r);assert q.values()==b.values() and not report['players'][0]['position_compatible']


@pytest.mark.parametrize('fault',['duplicate_code','roster','late','duplicate_history','blank'])
def test_admission_failures(fault):
    b,m,f,h,r=inputs()
    if fault=='duplicate_code':r.loc[1,'code']=333
    if fault=='roster':r.loc[0,'position']=2
    if fault=='duplicate_history':h=pd.concat([h,h.iloc[[0]]])
    if fault=='blank':f=f[f.event.ne(1)]
    with pytest.raises(ValueError):
        if fault=='late':apply(b,m,f,h,r,source_as_of='2025-08-16T00:00Z')
        else:run(b,m,f,h,r)


def test_season_parsing_not_lexicographic_guess():
    assert previous_season('2025-26')=='2024-25'
    for value in ['2025-27','test','25-26']:
        with pytest.raises(ValueError):previous_season(value)


def test_observed_dc_is_not_replaced_with_missing_award_prior():
    b,m,f,h,r=inputs();h.loc[h.code.eq(333),'dc_hit']=1.
    q,_=run(b,m,f,h,r)
    assert q.values()[3,9]==pytest.approx((10.+4.)/3.)


def test_provenance_cannot_replace_base_hash_or_hide_later_base_source():
    b,m,f,h,r=inputs()
    b=Horizon.create(m,[dict(z) for z in b.forecasts],trained_through=b.provenance['trained_through'],
        source_as_of=m.as_of,feature_cutoff=m.as_of,model_id='fake',source_hashes={'bootstrap':'original'})
    with pytest.raises(ValueError,match='Conflicting'):
        run(b,m,f,h,r,source_hashes={'bootstrap':'different'})
    with pytest.raises(ValueError,match='source'):
        apply(b,m,f,h,r,source_as_of='2025-08-15T11:00Z')
