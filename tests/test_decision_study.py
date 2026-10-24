import importlib.util
from pathlib import Path
import pytest


def module():
    spec=importlib.util.spec_from_file_location('decision_study',Path(__file__).parents[1]/'tools/run_decision_value_study.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def test_progression_requires_all_cases_and_allows_small_losing_opening():
    p=dict(seasons=['2024-25','2025-26'],opening_seeds=[1,2],fixed_roster_pilot=dict(cost_limit_mean_seconds_per_selection=1.,progression=dict(season_average_loss_limit=19,single_opening_loss_limit=38)))
    rows=[]
    for (s,n),delta in zip([(s,n) for s in p['seasons'] for n in p['opening_seeds']],[10,-1,4,0]):
        rows.append(dict(season=s,seed=n,net_points=dict(saved_mean=2000,chip_aware_expected=2000+delta),mean_new_selection_seconds=.2,mean_preservation_verified=True,independently_reconciled_scores=114))
    assert module().progression(rows,p)['integration_admitted']
    with pytest.raises(ValueError):module().progression(rows[:-1],p)
    rows[0]['mean_selection_seconds']=2
    rows[0]['mean_new_selection_seconds']=4
    assert not module().progression(rows,p)['integration_admitted']


def test_progression_does_not_proceed_on_neutral_or_negative_realised_value():
    p=dict(seasons=['2024-25','2025-26'],opening_seeds=[1,2],fixed_roster_pilot=dict(cost_limit_mean_seconds_per_selection=1.,progression=dict(season_average_loss_limit=19,single_opening_loss_limit=38)))
    rows=[dict(season=s,seed=n,net_points=dict(saved_mean=2000,chip_aware_expected=2000),mean_new_selection_seconds=.2,mean_preservation_verified=True,independently_reconciled_scores=114) for s in p['seasons'] for n in p['opening_seeds']]
    assert not module().progression(rows,p)['integration_admitted']
