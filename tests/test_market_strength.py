from datetime import datetime, timedelta, timezone
import numpy as np
import pytest
from market_strength import (proportional, probabilities, solve_lambdas, market_probabilities,
                             fit_ratings, project, match_fixture, canonical_name)


def test_proportional_odds_and_complete_group_fallback():
    assert proportional([2.,4.,4.])==pytest.approx([.5,.25,.25])
    row=dict(AvgCH='2',AvgCD='4',AvgCA='4',AvgH='3',AvgD='3',AvgA='3',**{'Avg>2.5':'2','Avg<2.5':'2'})
    values,used=market_probabilities(row);assert values==pytest.approx([.5,.25,.5])
    assert used['one_x_two']==['AvgCH','AvgCD','AvgCA']
    row['AvgCA']='';values,used=market_probabilities(row)
    assert values==pytest.approx([1/3,1/3,.5])
    assert used['one_x_two']==['AvgH','AvgD','AvgA']
    with pytest.raises(ValueError):market_probabilities({})
    for values in ([1,2],[2,float('nan')],[2,-4]):
        with pytest.raises(ValueError):proportional(values)


@pytest.mark.parametrize('means',[(1.8,.9),(.05,6.),(1.2,1.2)])
def test_solver_recovers_known_independent_poisson_means(means):
    result=solve_lambdas(probabilities(*means))
    assert result['lambda_home']==pytest.approx(means[0],abs=2e-4)
    assert result['lambda_away']==pytest.approx(means[1],abs=2e-4)
    assert result['squared_error']<1e-9
    assert result==solve_lambdas(probabilities(*means))


def test_ratings_strict_cutoff_target_guard_and_projection_symmetry():
    cutoff=datetime(2022,1,1,tzinfo=timezone.utc)
    rows=[dict(season='2021-22',fixture=i,kickoff=cutoff-timedelta(days=20-i),home='A' if i%2 else 'B',
               away='B' if i%2 else 'A',lambda_home=1.6,lambda_away=1.) for i in range(1,9)]
    rating=fit_ratings(rows,cutoff)
    assert rating.mu==pytest.approx(0.,abs=1e-12)
    assert rating.home_advantage==pytest.approx(np.log(1.6),abs=1e-12)
    assert list(rating.attack.values())==pytest.approx([0.,0.],abs=1e-12)
    h=project(rating,'A','B',True);a=project(rating,'B','A',False)
    assert h['mkt_lambda_for']==pytest.approx(a['mkt_lambda_against'])
    assert h['mkt_cs_prob']==pytest.approx(np.exp(-h['mkt_lambda_against']))
    assert project(rating,'new','A',True)['cold_start_team']
    with pytest.raises(ValueError,match='strictly before'):fit_ratings([dict(rows[0],kickoff=cutoff)],cutoff)
    with pytest.raises(ValueError,match='strictly before'):fit_ratings([dict(rows[0],kickoff=cutoff+timedelta(seconds=1))],cutoff)
    with pytest.raises(ValueError,match='Target-match'):fit_ratings(rows,cutoff,target_match=('2021-22',1))
    with pytest.raises(ValueError,match='Duplicate'):fit_ratings([rows[0],rows[0]],cutoff)
    with pytest.raises(ValueError,match='No market'):fit_ratings([],cutoff)
    older=dict(rows[0],fixture=99,kickoff=cutoff-timedelta(days=731),lambda_home=6.)
    assert fit_ratings([*rows,older],cutoff)==rating


def test_audited_name_map_and_exact_fixture_identity():
    assert canonical_name('Tottenham')=='Spurs'
    fixtures={('2021-22','2022-01-01','Man Utd','Sheffield Utd'):dict(fixture=3,home_id=1,away_id=2)}
    assert match_fixture('2021-22','2022-01-01','Man United','Sheffield United',fixtures)['fixture']==3
    with pytest.raises(ValueError,match='Unmapped'):canonical_name('invented')
    with pytest.raises(ValueError,match='No exact'):match_fixture('2021-22','2022-01-02','Man United','Sheffield United',fixtures)
