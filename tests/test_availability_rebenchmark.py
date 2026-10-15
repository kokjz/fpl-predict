import pandas as pd
import pytest
from availability_rebenchmark import align


def test_rebenchmark_rejects_duplicate_rows_and_missing_windows():
    f=pd.DataFrame(dict(season=['2025-26'],gameweek=[28],fixture=[1],fpl_code=[1]))
    with pytest.raises(ValueError,match='Duplicate'):align(pd.concat([f,f]),f,f,[])
    with pytest.raises(ValueError,match='Missing point weeks'):align(f,f,f,[])


def fixtures():
    from availability_rebenchmark import MODELS
    p=[];e=[];m=[];s=[]
    for gw in range(28,39):
        key=dict(season='2025-26',gameweek=gw,fixture=gw,fpl_code=1)
        p.append(dict(**key,actual=1.,minutes=90.,position=3,candidate=True,control=2.,structured=1.5))
        e.append(dict(**key,actual=1.,minutes=90.,position=3,candidate=True,
                      **{a:2. for a in MODELS if a!='availability_reference'}))
        market=dict(season='2025-26',gameweek=gw,fpl_code=1,actual=1.,
          inputs_as_of='2026-01-01T09:00Z',deadline='2026-01-01T10:00Z',blank_verified=0,fixture_count=1,
          **{a:2. for a in MODELS if a!='availability_reference'})
        m.append(market);blank=dict(market,fpl_code=2,actual=0.,fixture_count=0,blank_verified=1)
        blank.update({a:0. for a in MODELS if a!='availability_reference'});m.append(blank)
        s.append(dict(gameweek=gw,published_at='2026-01-01T09:30Z'))
    return pd.DataFrame(p),pd.DataFrame(e),pd.DataFrame(m),s


def test_alignment_preserves_blanks_and_earlier_quote_time():
    m,r=align(*fixtures())
    assert len(m)==22 and r['verified_blanks_filled']==11
    assert m[m.fpl_code.eq(2)].availability_reference.eq(0).all()
    assert m.inputs_as_of.eq('2026-01-01T09:30:00+00:00').all()
    assert m.quote_as_of.eq('2026-01-01T09:00Z').all()
    assert r['control_max_absolute_difference']==0


@pytest.mark.parametrize('kind',['control','actual','position','coverage','market','blank','late'])
def test_alignment_rejects_conflicts(kind):
    p,e,m,s=fixtures()
    if kind=='control':p.loc[0,'control']=2.1
    if kind=='actual':p.loc[0,'actual']=2.
    if kind=='position':p.loc[0,'position']=2
    if kind=='coverage':e=e.iloc[1:]
    if kind=='market':m.loc[0,'native_reference']=4.
    if kind=='blank':m.loc[1,'blank_verified']=0
    if kind=='late':s[0]['published_at']='2026-01-01T10:00Z'
    with pytest.raises(ValueError):align(p,e,m,s)
