import pandas as pd
import pytest
from decision_availability import project_probabilities
from horizon_forecast import project, Horizon
from test_horizon_forecast import market, params
from test_model import tiny
from fpl_model import normalise


class Model:
    metadata = dict(trained_through='2023-01-01T00:00Z', approval='Research reference')

    def predict(self, x, pos):
        return pd.DataFrame(dict(expected_points=x.last5_points, p_play=.5), index=x.index)


def inputs():
    d = normalise(tiny())
    m = market()
    f = pd.DataFrame([dict(id=i,event=gw,team_h=1,team_a=2,kickoff_time='2024-01-08T12:00Z')
                      for i,gw in [(2,2),(3,2),(4,4)]])
    h,_ = project(Model(),d,m,f,through=4,trained_through=Model.metadata['trained_through'],source_as_of=m.as_of,model_id='synthetic')
    return d,m,f,h


def test_double_blank_and_unchanged_means_replay_with_future_mutation():
    d,m,f,h = inputs()
    rows,report = project_probabilities(Model(),d,m,f,h)
    by = {(r['gameweek'],r['id']):r for r in rows}
    assert by[2,1]['p_play'] == .75 and by[3,1]['p_play'] == 0
    assert by[4,1]['p_play'] == .5 and report['mean_reproduction_max_abs_error'] == 0
    changed = d.copy()
    changed.loc[changed.ts.ge(pd.Timestamp(m.as_of)),'points_core'] = 999
    assert project_probabilities(Model(),changed,m,f,h) == (rows,report)


def test_mismatched_forecast_vintage_and_late_model_rejected():
    d,m,f,h = inputs()
    rs = [dict(r,expected_points=r['expected_points']+1) for r in h.forecasts]
    wrong = Horizon.create(m,rs,**params(m))
    with pytest.raises(ValueError,match='vintages'):project_probabilities(Model(),d,m,f,wrong)
    model = Model()
    model.metadata = dict(trained_through=m.as_of,approval='Research reference')
    with pytest.raises(ValueError,match='after'):project_probabilities(model,d,m,f,h)


def test_official_zero_is_current_origin_only_and_requires_matching_means():
    d,m,f,h = inputs()
    rs = [dict(r,expected_points=0. if r['gameweek']==2 and r['id']==1 else r['expected_points']) for r in h.forecasts]
    h = Horizon.create(m,rs,**params(m))
    rows,_ = project_probabilities(Model(),d,m,f,h,official_zero_ids={1})
    by = {(r['gameweek'],r['id']):r for r in rows}
    assert by[2,1]['p_play'] == 0 and by[4,1]['p_play'] == .5
    with pytest.raises(ValueError,match='identity'):project_probabilities(Model(),d,m,f,h,official_zero_ids={999})
