import pandas as pd
import pytest
from forecaster_qualification import join_market,development


def markets():
    m=pd.DataFrame(dict(season=['x','x'],gameweek=[28,28],fpl_code=[20,10],actual=[1.,2.],minutes=[90.,0.],position=[3,4],price_tenths=[50,55],prior_minutes=[90.,60.],cards=[0,0],fixture_count=[1,1],blank_verified=[0,0],team=['A','B'],reference=[3.,4.],inputs_as_of=['2026-01-01T00:00Z']*2))
    n=m.rename(columns={'reference':'anchor'}).copy();n['new_xp']=[1.5,2.5]
    return m,n


def test_market_join_invariant_to_source_row_order():
    m,n=markets();a=join_market(m,n);b=join_market(m,n.iloc[::-1])
    pd.testing.assert_frame_equal(a,b);assert a.conditional_forecaster.tolist()==[1.5,2.5]
    c=join_market(m.iloc[::-1],n);assert c.conditional_forecaster.tolist()==[2.5,1.5]


def test_market_join_rejects_coverage_duplicates_and_metadata_conflicts():
    m,n=markets()
    with pytest.raises(ValueError,match='coverage'):join_market(m,n.iloc[:1])
    with pytest.raises(ValueError,match='Duplicate'):join_market(m,pd.concat([n,n]))
    n.loc[0,'actual']=99
    with pytest.raises(ValueError,match='metadata'):join_market(m,n)
