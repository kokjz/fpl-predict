"""Whole-policy admission uses no timed optimisation or external datasets."""
import copy
import json
from dataclasses import replace
import pytest
from season_benchmark import run,Policy
from rolling_planner import _fallback,_objective,Settings
from test_season_benchmark import bundle


def hold(state,market,horizon,*,settings,policy,blocked,opening_ids):
    ids=dict(state.holdings) or {i:market.indexed()[i]['price_tenths'] for i in (opening_ids or range(1,16))}
    actions=_fallback(state,market,horizon,{'ledger':ids})
    value,_=_objective(state,market,horizon,actions,settings)
    return actions,dict(objective=value,budget_exhausted=False)


def test_whole_policy_freezes_before_hidden_outcomes_and_records_identity(tmp_path):
    decisions,outcomes=bundle();root=tmp_path/'first'
    class Evaluator(dict):
        def __getitem__(self,gameweek):
            assert (root/f'GW{gameweek:02d}_decision.json').exists()
            return super().__getitem__(gameweek)
    summary=run(decisions,Evaluator(outcomes),root,policy=Policy(chips=False),
        management_policy=hold,management_policy_id='hold-no-chips-v1')
    assert summary['net_points']==456 and summary['management_policy_id']=='hold-no-chips-v1'
    changed=copy.deepcopy(outcomes)
    for row in changed[38].values():row['actual']=3
    run(decisions,changed,tmp_path/'second',policy=Policy(chips=False),
        management_policy=hold,management_policy_id='hold-no-chips-v1')
    for g in range(1,39):
        a=json.loads((root/f'GW{g:02d}_decision.json').read_text())
        b=json.loads((tmp_path/f'second/GW{g:02d}_decision.json').read_text())
        assert a['action']==b['action'] and a['management_policy_id']=='hold-no-chips-v1'


@pytest.mark.parametrize('damage',['incomplete','objective','blocked','disabled','illegal'])
def test_invalid_whole_policy_stops_before_outcome_access(tmp_path,damage):
    decisions,outcomes=bundle();decisions[0]['blocked_tokens']=[['bboost',1]]
    class Hidden(dict):
        def __getitem__(self,key):pytest.fail('Outcomes accessed before policy admission')
    def bad(*args,**kwargs):
        actions,report=hold(*args,**kwargs)
        if damage=='incomplete':actions=actions[:-1]
        elif damage=='objective':report['objective']+=1
        elif damage in ('blocked','disabled'):actions[0]=replace(actions[0],chip='bboost')
        else:actions[0]=replace(actions[0],captain=99999)
        return actions,report
    with pytest.raises(ValueError):run(decisions,Hidden(outcomes),tmp_path/damage,
        policy=Policy(chips=damage!='disabled'),management_policy=bad,management_policy_id='damaged-v1')


def test_policy_identity_and_incompatible_inner_fail_before_output(tmp_path):
    d,o=bundle()
    for kwargs in [dict(management_policy=hold),dict(management_policy_id='orphan'),
        dict(management_policy=hold,management_policy_id='hold-v1',inner_planner=hold)]:
        with pytest.raises(ValueError):run(d,o,tmp_path/'absent',**kwargs)
        assert not (tmp_path/'absent').exists()


def test_whole_policy_cannot_change_common_opening_or_ignore_unknown_block(tmp_path):
    d,o=bundle()
    for row in d:
        row['market']['rows']=[*row['market']['rows'],dict(row['market']['rows'][0],id=16,team='OTHER')]
        row['forecast']['rows'].extend(dict(r,id=16) for r in list(row['forecast']['rows']) if r['id']==1)
    def different(*args,**kwargs):
        kwargs['opening_ids']=list(range(2,17))
        return hold(*args,**kwargs)
    with pytest.raises(ValueError,match='common opening'):
        run(d,o,tmp_path/'wrong-opening',opening_ids=list(range(1,16)),
            management_policy=different,management_policy_id='wrong-opening-v1')
    d[0]['blocked_tokens']=[['imaginary',1]]
    with pytest.raises(ValueError,match='blocked chip'):
        run(d,o,tmp_path/'unknown-block',management_policy=hold,management_policy_id='hold-v1')


def test_callback_receives_an_immutable_copy_of_common_opening(tmp_path):
    d,o=bundle();opening=list(range(1,16));seen=[]
    def check(*args,**kwargs):
        if kwargs['opening_ids'] is not None:
            assert type(kwargs['opening_ids']) is tuple
            seen.append(kwargs['opening_ids'])
        return hold(*args,**kwargs)
    run(d,o,tmp_path/'copy',opening_ids=opening,policy=Policy(chips=False),
        management_policy=check,management_policy_id='hold-v1')
    assert seen==[tuple(opening)] and opening==list(range(1,16))
