import importlib.util
from pathlib import Path
from itertools import product
import pytest
from decision_value import players, realised
from forecast import select_xi
from test_expected_selection import squad


def module():
    spec=importlib.util.spec_from_file_location('decision_objective_audit',Path(__file__).parents[1]/'tools/audit_decision_objective.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


@pytest.mark.parametrize('chip',[None,'3xc','bboost'])
def test_independent_capacity_enumeration_matches_realised_expectation(chip):
    raw=squad();p={r['id']:1. for r in raw}
    for i,v in zip([1,3,8,15],[.1,.4,.7,.5]):p[i]=v
    rows=players(raw,p);selection=select_xi(rows);uncertain=[r for r in rows if r['p_play']!=1];total=0.
    for state in product((0,1),repeat=len(uncertain)):
        by={r['id']:v for r,v in zip(uncertain,state)};weight=1.
        for r,v in zip(uncertain,state):weight*=r['p_play'] if v else 1-r['p_play']
        hidden={r['id']:dict(actual=r['conditional_points'] if by.get(r['id'],1) else 0.,minutes=float(by.get(r['id'],1)),cards=0.) for r in rows}
        total+=weight*realised(selection,rows,hidden,chip)
    assert module().expectation(selection,rows,chip)==pytest.approx(total,abs=1e-10)
