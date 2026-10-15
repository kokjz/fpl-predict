import pandas as pd
import pytest
from benchmark_readiness import join_seasonal_bridge, preflight
from test_external_benchmark import outcomes, forecast, manifest


def frames():
    p=pd.DataFrame({'element':[7,8],'gw':[20,20],'openfpl_xpts':[3.,4.],'actual_points':[2,6]})
    b=pd.DataFrame({'season':['2025-26']*2,'element':[7,8],'gameweek':[20,20],
                    'fixture':[191,192],'fpl_code':[11,22]})
    return p,b


def test_bridge_requires_exact_keys_and_preserves_scores():
    p,b=frames();r=join_seasonal_bridge(p,b)
    assert r.prediction.tolist()==[3,4]
    assert r.fpl_code.tolist()==[11,22]
    assert 'created_at' not in r


@pytest.mark.parametrize('bad',['duplicate','missing','season','identity','nan'])
def test_bad_bridge_never_silently_loses_rows(bad):
    p,b=frames()
    if bad=='duplicate':p=pd.concat([p,p.iloc[[0]]])
    elif bad=='missing':p=p.iloc[[0]]
    elif bad=='season':b.loc[0,'season']='2024-25'
    elif bad=='identity':b.loc[1,'fpl_code']=11
    else:p.loc[0,'openfpl_xpts']=float('nan')
    with pytest.raises(ValueError):join_seasonal_bridge(p,b)


def test_preflight_reports_target_failure_without_ranking_or_admission():
    a=manifest();a['target_by_season']['2025-26']='core'
    r=preflight(outcomes(),[(forecast(),a),(forecast(),manifest('second'))])
    assert not r['all_contracts_valid']
    assert not r['independent_provenance_certified']
    assert r['models'][1]['contract_valid']
    assert 'rmse' not in str(r)


def test_valid_declared_contracts_are_not_independent_provenance_certification():
    r=preflight(outcomes(),[(forecast(),manifest()),(forecast(),manifest('second'))])
    assert r['all_contracts_valid'] and not r['model_promotion']
    assert r['remaining_manual_checks']
