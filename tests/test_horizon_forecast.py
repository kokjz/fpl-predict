import copy
import pandas as pd
import pytest
from horizon_forecast import Horizon,project
from season_engine import Market
from test_model import tiny
from fpl_model import normalise


def market():return Market.create('test',2,'2024-01-08T10:30Z','2024-01-08T09:00Z',[dict(id=1,position=2,team='1',price_tenths=50,can_buy=True),dict(id=2,position=4,team='2',price_tenths=50,can_buy=True)])


def params(m):return dict(trained_through='2023-01-01T00:00Z',feature_cutoff=m.as_of,source_as_of=m.as_of,model_id='synthetic')


def test_grid_coverage_origin_clocks_and_outcome_fields():
    m=market();rows=[dict(gameweek=2,id=i,expected_points=2.) for i in [1,2]];Horizon.create(m,rows,**params(m))
    with pytest.raises(ValueError,match='coverage'):Horizon.create(m,rows[:1],**params(m))
    with pytest.raises(ValueError,match='trained'):Horizon.create(m,rows,**dict(params(m),trained_through=m.as_of))
    with pytest.raises(ValueError,match='late'):Horizon.create(m,rows,**dict(params(m),source_as_of='2024-01-09T00:00Z'))
    rows[0]['actual']=100
    with pytest.raises(ValueError,match='fields'):Horizon.create(m,rows,**params(m))


def test_projection_origin_history_double_blank_and_future_mutation():
    class Model:
        def predict(self,x,pos):return pd.DataFrame(dict(expected_points=x.last5_points),index=x.index)
    d=normalise(tiny());m=market();f=pd.DataFrame([dict(id=i,event=gw,team_h=1,team_a=2,kickoff_time='2024-01-08T12:00Z') for i,gw in [(2,2),(3,2),(4,4)]])
    h,r=project(Model(),d,m,f,through=4,trained_through='2023-01-01T00:00Z',source_as_of=m.as_of,model_id='synthetic')
    assert h.values()[(2,1)]==2*h.values()[(4,1)] and h.values()[(3,1)]==0
    change=d.copy();change.loc[change.ts.ge(pd.Timestamp(m.as_of)),'points_core']=999
    b,_=project(Model(),change,m,f,through=4,trained_through='2023-01-01T00:00Z',source_as_of=m.as_of,model_id='synthetic')
    assert h.values()==b.values() and r['fixture_rows']==6


def test_projection_rejects_unadmitted_conditional_model():
    class Model:requires_availability=True
    with pytest.raises(ValueError,match='Conditional'):project(Model(),None,market(),None,through=3,trained_through='2023-01-01T00:00Z',source_as_of=market().as_of,model_id='x')
