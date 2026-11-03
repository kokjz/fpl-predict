import numpy as np
import pandas as pd
import pytest
import fpl_crowd_signal as t

def boundary(rows=1000,bad=1,season='2022-23'):
    ts=pd.Timestamp('2022-08-01T15:00Z')
    h=pd.DataFrame(dict(season=season,element=np.arange(rows),GW=1,ts=ts,cutoff=ts-pd.Timedelta(hours=1),selected=1000.,transfers_in=1.,transfers_out=0.,transfers_balance=1.,value=40.,pos=2,points_core=2.))
    h.loc[h.index[:bad],'transfers_balance']=-100.
    return h

@pytest.mark.parametrize('rows,bad,passes',[(1000,1,True),(999,1,False),(1001,1,True),(2000,2,True),(2000,3,False)])
def test_per_season_inclusive_boundary(rows,bad,passes):
    h=boundary(rows,bad)
    assert t.field_checks(h,False)['passed']==passes
    if passes:assert t.CrowdStore(h).report['passed']
    else:
        with pytest.raises(ValueError):t.CrowdStore(h)

def test_bound_is_each_season_not_pooled_and_other_checks_still_stop():
    h=pd.concat([boundary(999,1),boundary(10000,0,'2023-24')],ignore_index=True)
    assert not t.field_checks(h,False)['passed']
    for name,value in [('value',34),('selected',-1),('value',np.nan)]:
        h=boundary();h.loc[10,name]=value
        assert not t.field_checks(h,False)['passed']

def test_as_recorded_rank_share_smoothing_and_every_row_usage_report():
    h=boundary(2000);target=h.iloc[[0]].assign(GW=2,ts=h.ts.iloc[0]+pd.Timedelta(days=7),cutoff=h.ts.iloc[0]+pd.Timedelta(days=6))
    both=pd.concat([h,target],ignore_index=True);before=both.copy(deep=True)
    x,_,_=t.CrowdStore(both).transform(target)
    assert x.iloc[0].crowd_tb_share_last==-.05
    assert x.iloc[0].crowd_tb_pct_last==.0005
    assert x.iloc[0].crowd_ew4_tb_pct==t.ew([.0005],4,.5,2)
    rows=t.balance_discrepancies(both,both)
    assert len(rows)==2 and rows[0]['difference']==-101
    assert rows[0]['feeds_any_last'] and rows[0]['feeds_any_ew4']
    assert not rows[1]['feeds_any_last'] and not rows[1]['feeds_any_ew4']
    assert rows[0]['transfers_balance']==-100
    pd.testing.assert_frame_equal(both,before)
