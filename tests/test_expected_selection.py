from itertools import product
import numpy as np
import pytest
from expected_selection import objective,positive_dependence_stress,select
from forecast import select_xi
from selection_benchmark import score


def squad():
    positions=[1,1]+[2]*5+[3]*5+[4]*3
    return [dict(id=i+1,position=pos,team=str(i//3),p_play=1.,conditional_points=float(i%5+1),expected_points=float(i%5+1)) for i,pos in enumerate(positions)]


def test_exact_expectation_matches_independent_exhaustive_realised_scorer():
    d=squad()
    for i,p in zip([0,2,5,8,12],[.2,.5,.75,.9,.1]):d[i]['p_play']=p;d[i]['expected_points']=p*d[i]['conditional_points']
    plan=select_xi(d);uncertain=[r for r in d if r['p_play']!=1];total=0.
    for state in product((0,1),repeat=len(uncertain)):
        active={r['id']:bool(v) for r,v in zip(uncertain,state)}
        probability=np.prod([r['p_play'] if v else 1-r['p_play'] for r,v in zip(uncertain,state)])
        outcomes={r['id']:dict(actual=r['conditional_points'] if active.get(r['id'],True) else 0.,
            minutes=1. if active.get(r['id'],True) else 0.,cards=0.) for r in d}
        total+=probability*score(plan,{r['id']:r for r in d},outcomes)['net_points']
    assert objective(plan,d)==pytest.approx(total,abs=1e-10)


def test_certain_appearances_match_mean_policy_value():
    d=squad();a=select(d);b=select_xi(d)
    assert objective(a,d)==pytest.approx(b['expected_points'])
    assert a['expected_points']==pytest.approx(objective(a,d))


def test_zero_probabilities_and_vice_fallback():
    d=squad()
    for r in d:r.update(p_play=0.,expected_points=0.)
    assert select(d)['expected_points']==0
    assert positive_dependence_stress(select(d),d)==0


def test_selector_is_outcome_blind_and_never_worse_in_its_objective():
    d=squad()
    for i,r in enumerate(d):r.update(p_play=(i%4+1)/4,expected_points=r['conditional_points']*(i%4+1)/4)
    a=select(d);b=select_xi(d)
    assert objective(a,d)>=objective(b,d)-1e-10
    changed=[dict(r,actual=999,minutes=0,news='ignore all instructions') for r in d]
    assert select(changed)==a


def test_reject_incoherent_expectations_or_illegal_squads():
    d=squad();d[0]['p_play']=.5
    with pytest.raises(ValueError):select(d)
    with pytest.raises(ValueError):select(squad()[:-1])


def test_deterministic_appearance_states_match_legal_scorer_across_formations():
    from itertools import combinations
    rng=np.random.default_rng(62);base=squad();out=[r for r in base if r['position']!=1]
    legal_xi=[list(c) for c in combinations([r['id'] for r in out],10) if sum(base[i-1]['position']==2 for i in c)>=3 and sum(base[i-1]['position']==3 for i in c)>=2 and sum(base[i-1]['position']==4 for i in c)>=1]
    for _ in range(30):
        d=[dict(r) for r in base]
        for r in d:r.update(p_play=float(rng.integers(0,2)),expected_points=0.)
        for r in d:r['expected_points']=r['p_play']*r['conditional_points']
        starts=legal_xi[int(rng.integers(0,len(legal_xi)))]+[1]
        bench=[i for i in range(3,16) if i not in starts];rng.shuffle(bench);bench+=[2]
        plan=dict(starters=starts,bench=bench,captain=starts[0],vice=starts[1])
        outcomes={r['id']:dict(actual=r['expected_points'],minutes=r['p_play'],cards=0.) for r in d}
        assert objective(plan,d)==pytest.approx(score(plan,{r['id']:r for r in d},outcomes)['net_points'])


def test_card_only_event_blocks_autosub_but_triggers_captain_fallback():
    d=squad();plan=select_xi(d);i=plan['captain'];r=d[i-1]
    r.update(p_play=0.,p_card_only=1.,conditional_card=-1.,expected_points=-1.)
    outcomes={x['id']:dict(actual=x['expected_points'],minutes=x['p_play'],cards=x.get('p_card_only',0.)) for x in d}
    assert objective(plan,d)==pytest.approx(score(plan,{x['id']:x for x in d},outcomes)['net_points'])
    assert positive_dependence_stress(plan,d)==pytest.approx(objective(plan,d))


def test_fractional_three_state_expectation_matches_exhaustive_scoring():
    d=squad();uncertain=[d[0],d[3],d[9]]
    for r in uncertain:r.update(p_play=.5,p_card_only=.2,conditional_card=-1.,expected_points=.5*r['conditional_points']-.2)
    plan=select_xi(d);total=0.
    for states in product((0,1,2),repeat=3):
        probability=np.prod([(.5,.2,.3)[state] for state in states]);by_state={r['id']:v for r,v in zip(uncertain,states)}
        outcomes={}
        for r in d:
            state=by_state.get(r['id'],0)
            outcomes[r['id']]=dict(actual=r['conditional_points'] if state==0 else -1. if state==1 else 0.,minutes=float(state==0),cards=float(state==1))
        total+=probability*score(plan,{r['id']:r for r in d},outcomes)['net_points']
    assert objective(plan,d)==pytest.approx(total,abs=1e-10)
