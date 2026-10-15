import copy
import numpy as np
import pandas as pd
import pytest
from benchmark_evaluation import paired_block_errors
from external_benchmark import compare,prepare_outcomes
from test_external_benchmark import outcomes,forecast,manifest


def errors():
    return pd.DataFrame([dict(season='2024-25',gameweek=gw,actual=i,left=i+.5,right=i+1.)
                         for gw in range(20,32) for i in range(1+(gw%3))])


def test_paired_intervals_preserve_pooling_with_unequal_week_sizes():
    r=paired_block_errors(errors(),'left','right')
    assert r['status']=='descriptive_interval'
    assert r['rmse']['delta']==pytest.approx(-.5)
    assert r['mae']['lower']==pytest.approx(-.5)
    assert r['rmse']['upper']==pytest.approx(-.5)
    assert r==paired_block_errors(errors(),'left','right')


def test_identical_forecasts_have_zero_paired_difference_and_short_runs_no_interval():
    d=errors();d['right']=d.left
    r=paired_block_errors(d,'left','right');assert r['rmse']==dict(delta=0.,lower=0.,upper=0.)
    r=paired_block_errors(d[d.gameweek<24],'left','right')
    assert r['status']=='insufficient_contiguous_weeks' and 'rmse' not in r


def test_blocks_never_cross_season_or_missing_gameweek_gap():
    d=errors();d.loc[d.gameweek>=26,'gameweek']+=4
    d2=d.copy();d2['season']='2025-26'
    r=paired_block_errors(pd.concat([d,d2]),'left','right')
    assert r['contiguous_segments']==[6,6,6,6]
    assert r['status']=='insufficient_contiguous_weeks'


def test_diagnostics_do_not_change_primary_candidate_membership():
    truth=outcomes().assign(minutes=[30,60,90,0],position=[2,2,4,1],n_history=[4,4,4,0])
    r=compare(truth,[(forecast(),manifest()),(forecast(),manifest('second'))])
    section=r['all_model_intersection']
    assert section['cohorts']['predeadline_candidates']['rows']==2
    assert section['diagnostics']['actual_zero_minutes_diagnostic']['rows']==1
    assert section['diagnostics']['cold_start_history_under3']['rows']==1
    assert 'actual' not in section['cohorts']


@pytest.mark.parametrize('col,values',[('minutes',[90,91,90,0]),('position',[1,2,4,1]),
                                     ('n_history',[4,4,2,0])])
def test_invalid_auxiliary_metadata_rejected_before_coverage_filter(col,values):
    truth=outcomes();truth[col]=values
    with pytest.raises(ValueError):prepare_outcomes(truth)


def squad_inputs():
    positions=[1,1]+[2]*5+[3]*5+[4]*3
    truth=pd.DataFrame([dict(season='2025-26',gameweek=20,fpl_code=i,fixture=190,
          actual=0 if i==1 else 10 if i==3 else 2,minutes=0 if i==1 else 90,
          position=positions[i-1],candidate=True,deadline='2026-01-01T10:00:00Z') for i in range(1,16)])
    a=truth[['season','gameweek','fpl_code']].assign(prediction=[100,14,90]+list(range(12,0,-1)))
    b=a.copy();b['prediction']=[15,100,90]+list(range(12,0,-1))
    panel=dict(id='synthetic-panel',season='2025-26',gameweek=20,origin='retrospective_fixed',
               inputs_as_of='2026-01-01T09:00:00Z',created_at='2026-10-15T10:00:00Z',
               players=[dict(fpl_code=i,position=positions[i-1],team='club'+str(i%5),price_tenths=50) for i in range(1,16)])
    return truth,a,b,dict(schema_version=1,panels=[panel])


def test_same_squad_replay_includes_keeper_autosub_and_vice_fallback():
    truth,a,b,spec=squad_inputs()
    r=compare(truth,[(a,manifest()),(b,manifest('second'))],squads=spec)
    result=r['fixed_squads'];assert result['eligible_panels']==1
    assert result['mean_points']=={'first':40.,'second':32.}
    assert 'fpl_code' not in str(result)
    assert 'no transfers' in result['scope']


def test_missing_any_methods_prediction_excludes_whole_squad_panel():
    truth,a,b,spec=squad_inputs()
    r=compare(truth,[(a,manifest()),(b.iloc[:-1],manifest('second'))],squads=spec)['fixed_squads']
    assert r['eligible_panels']==0 and r['mean_points']=={'first':None,'second':None}


@pytest.mark.parametrize('bad',['late_inputs','fake_archive','budget','club','position','duplicate'])
def test_invalid_or_backdated_panels_rejected(bad):
    truth,a,b,spec=squad_inputs();panel=spec['panels'][0]
    if bad=='late_inputs':panel['inputs_as_of']='2026-01-02T09:00:00Z'
    elif bad=='fake_archive':panel['origin']='archived_predeadline'
    elif bad=='budget':
        for p in panel['players']:p['price_tenths']=100
    elif bad=='club':
        for p in panel['players']:p['team']='oneclub'
    elif bad=='position':panel['players'][0]['position']=2
    else:spec['panels'].append(copy.deepcopy(panel))
    with pytest.raises(ValueError):compare(truth,[(a,manifest()),(b,manifest('second'))],squads=spec)


def test_reported_delta_is_pooled_rmse_not_average_of_weekly_rmse():
    d=errors();d['left']=d.actual+(d.gameweek%3);d['right']=d.actual+.5
    expected=float(np.sqrt(np.mean((d.left-d.actual)**2))-.5)
    r=paired_block_errors(d,'left','right')
    assert r['rmse']['delta']==pytest.approx(expected)
    assert r['rmse']['lower']<=r['rmse']['upper']
