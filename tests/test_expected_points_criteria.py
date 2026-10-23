import importlib.util
from pathlib import Path
import copy
import pytest


def module():
    s=importlib.util.spec_from_file_location('criteria',Path(__file__).parents[1]/'tools/evaluate_season_policies.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def setup():
    p=dict(seasons=['2024-25','2025-26'],opening_seeds=[1,2],policies=['H1','H6','native'],paths=12,decision_framework=dict(material_season_loss_limit=19,material_single_opening_loss_limit=38))
    rows=[dict(season=s,seed=n,policy=a,status='completed',net_points=2000) for s in p['seasons'] for n in p['opening_seeds'] for a in p['policies']]
    return p,rows


def test_small_loss_does_not_veto_positive_mean_and_old_gate_not_relabelled():
    p,r=setup()
    gains=iter([110,-6,20,-10])
    for x in r:
        if x['policy']=='H6':x['net_points']+=next(gains)
    o=module().evaluate(r,p,integrity_verified=True);v=o['comparisons']['H1']
    assert v['research_support'] and v['equal_season_mean']==28.5 and v['losses']==2
    assert o['old_zero_negative_gate_unchanged'] and not o['policy_promotion']
    assert not module().evaluate(r,p,integrity_verified=False)['comparisons']['H1']['research_support']


def test_downside_and_zero_gain_guards_are_not_win_every_case_rule():
    p,r=setup();assert not module().evaluate(r,p,integrity_verified=True)['comparisons']['H1']['research_support']
    for x in r:
        if x['policy']=='H6':x['net_points']+=100 if x['season']=='2024-25' else -20
    o=module().evaluate(r,p,integrity_verified=True)['comparisons']['H1'];assert o['equal_season_mean']==40 and not o['research_support']
    for x in r:
        if x['policy']=='H6' and x['season']=='2025-26':x['net_points']+=1
    assert module().evaluate(r,p,integrity_verified=True)['comparisons']['H1']['research_support']


@pytest.mark.parametrize('damage',['missing','duplicate','failed','nonfinite','extra'])
def test_never_drop_losers_or_failures(damage):
    p,r=setup()
    if damage=='missing':r.pop()
    elif damage=='duplicate':r.append(copy.deepcopy(r[0]))
    elif damage=='failed':r[0]['status']='failed'
    elif damage=='nonfinite':r[0]['net_points']=float('nan')
    else:r[0]['seed']=99
    with pytest.raises(ValueError):module().evaluate(r,p,integrity_verified=True)
