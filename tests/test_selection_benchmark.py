import copy
from itertools import combinations
import numpy as np
import pandas as pd
import pytest
from selection_benchmark import (choices, legal, optimise, paired_summary, run,
                                 scenarios, score, sell_price, validate)
from forecast import select_xi

MODELS=['reference','other']


def market(extra=True):
    rows=[]; code=0
    for pos,n in {1:2,2:5,3:5,4:3}.items():
        for j in range(n+int(extra)):
            code+=1
            rows.append(dict(season='2025-26',gameweek=28,deadline='2026-02-27T18:30:00Z',
                inputs_as_of='2026-02-27T13:00:00Z',fpl_code=code,position=pos,team=f'T{code%8}',
                price_tenths=50,can_buy=1,prior_minutes=45.,ownership=1.,actual=float(code%5),
                minutes=90.,cards=0.,reference=float(code%7+1),other=float(code%7+1)))
    return pd.DataFrame(rows)


def owned():
    d=market(False); squad=choices(d,d.fpl_code,'reference')
    outcomes={p['id']:dict(actual=2.,minutes=90.,cards=0.) for p in squad}
    return d,squad,select_xi(squad),outcomes


def test_scoring_and_negative_captain():
    _,s,selection,o=owned(); players={p['id']:p for p in s}
    assert score(selection,players,o)['net_points']==24
    o[selection['captain']]['actual']=-2
    assert score(selection,players,o)['net_points']==16
    assert score(selection,players,o,4)['net_points']==12


def test_captain_minutes_and_card_autosub_separate():
    _,s,selection,o=owned(); players={p['id']:p for p in s}
    cap=selection['captain']; vice=selection['vice']
    o[cap]=dict(actual=-1.,minutes=0.,cards=1.)
    result=score(selection,players,o)
    assert cap in result['scoring_xi']
    assert result['scoring_captain']==vice
    assert result['autosub_delta']==0
    o[vice]['minutes']=0
    assert score(selection,players,o)['scoring_captain'] is None


def test_keeper_and_outfield_substitutions():
    _,s,selection,o=owned(); players={p['id']:p for p in s}
    keeper=next(i for i in selection['starters'] if players[i]['position']==1)
    reserve=next(i for i in selection['bench'] if players[i]['position']==1)
    o[keeper]['minutes']=0; o[keeper]['actual']=0; o[reserve]['actual']=8
    result=score(selection,players,o)
    assert reserve in result['scoring_xi'] and keeper not in result['scoring_xi']
    assert result['autosub_delta']==8


def test_formation_overrides_bench_priority():
    d,s,_,o=owned(); players={p['id']:p for p in s}
    by={p:[x['id'] for x in s if x['position']==p] for p in (1,2,3,4)}
    starters=by[1][:1]+by[2][:3]+by[3][:4]+by[4][:3]
    bench=by[3][4:]+by[2][3:]+by[1][1:]
    selection=dict(starters=starters,bench=bench,captain=by[4][0],vice=by[4][1])
    missing=by[2][0]; o[missing]=dict(actual=0.,minutes=0.,cards=0.)
    result=score(selection,players,o)
    assert by[2][3] in result['scoring_xi'] and by[3][4] not in result['scoring_xi']


def test_no_appearance_no_bonus_or_sub():
    _,s,selection,o=owned(); players={p['id']:p for p in s}
    for p in o: o[p]=dict(actual=0.,minutes=0.,cards=0.)
    assert score(selection,players,o)['net_points']==0


@pytest.mark.parametrize('purchase,current,expected',[(50,53,51),(50,54,52),(50,48,48),(50,50,50)])
def test_selling(purchase,current,expected): assert sell_price(purchase,current)==expected


def test_invalid_selection_or_unknown_outcome():
    _,s,sel,o=owned(); players={p['id']:p for p in s}
    o.pop(s[0]['id'])
    with pytest.raises(ValueError,match='Unknown'): score(sel,players,o)
    sel['bench'][0]=sel['starters'][0]
    with pytest.raises(ValueError,match='Illegal'): score(sel,players,o)


def test_optimizer_exact_against_small_exhaustive_market():
    d=market(); result=optimise(d,'reference',bank=750)
    squad=choices(d,result['ledger'],'reference')
    assert legal(squad) and result['bank']==0
    achieved=result['selection']['expected_points']+.1*sum(p['expected_points'] for p in squad if p['id'] in result['selection']['bench'])
    best=-np.inf
    groups=[list(combinations(d[d.position.eq(pos)].fpl_code,n)) for pos,n in {1:2,2:5,3:5,4:3}.items()]
    from itertools import product
    for parts in product(*groups):
        ids=sum((list(p) for p in parts),[]); candidate=choices(d,ids,'reference')
        if not legal(candidate): continue
        selection=select_xi(candidate)
        value=selection['expected_points']+.1*sum(p['expected_points'] for p in candidate if p['id'] in selection['bench'])
        best=max(best,value)
    assert achieved==pytest.approx(best)


def test_decision_outcomes_mutation_and_no_buy():
    d=market(); a=optimise(d,'reference')
    altered=d.copy(); altered[['actual','minutes','cards']]=99999
    assert optimise(altered,'reference')['ledger']==a['ledger']
    high=int(d.fpl_code.iloc[-1]); d.loc[d.fpl_code.eq(high),'can_buy']=0
    assert high not in optimise(d,'reference')['ledger']
    assert scenarios(altered,3,minimum_cost=0)==scenarios(market(),3,minimum_cost=0)


def test_rolling_hold_bank_and_ft_cap():
    d,s,_,_=owned(); ledger={p['id']:50 for p in s}
    result=optimise(d,'reference',owned=ledger,bank=23,free_transfers=5)
    assert result['transfers']==0 and result['bank']==23 and result['free_transfers']==5
    assert result['ledger']==ledger
    d=d[d.fpl_code.ne(s[0]['id'])]
    with pytest.raises(ValueError,match='quotes'): optimise(d,'reference',owned=ledger)


def test_paid_transfer_and_ledger_half_profit():
    d=market(); opening=optimise(d,'reference',bank=750)
    ledger=opening['ledger']; absent=next(i for i in d.fpl_code if i not in ledger)
    pos=int(d.set_index('fpl_code').loc[absent,'position'])
    old=next(i for i in ledger if int(d.set_index('fpl_code').loc[i,'position'])==pos)
    d.loc[d.fpl_code.eq(old),'price_tenths']=54
    d.loc[d.fpl_code.eq(absent),'reference']=100
    result=optimise(d,'reference',owned=ledger,bank=0,free_transfers=1)
    assert absent in result['ledger'] and result['ledger'][absent]==50
    assert result['transfers']>=1 and result['hits']==4*max(0,result['transfers']-1)
    assert result['bank']>=0


@pytest.mark.parametrize('change', ['duplicate','late','nan','fraction','buy'])
def test_invalid_normalized_input(change):
    d=market()
    if change=='duplicate': d=pd.concat([d,d.iloc[:1]])
    if change=='late': d['inputs_as_of']=d.deadline
    if change=='nan': d.loc[0,'reference']=np.nan
    if change=='fraction':
        d['price_tenths']=d.price_tenths.astype(float); d.loc[0,'price_tenths']=1.5
    if change=='buy': d.loc[0,'can_buy']=2
    with pytest.raises(ValueError): validate(d,MODELS)


def test_identical_predictions_zero_paired_interval_and_panel_dependence():
    rows=[]
    for gw in range(28,39):
        for panel in range(12):
            for model in MODELS:
                rows.append(dict(season='2025-26',gameweek=gw,scenario=panel,model=model,net_points=float(gw+panel)))
    result=paired_summary(pd.DataFrame(rows),MODELS,'reference')
    assert result['gameweeks']==11
    assert result['comparisons']['other']['simultaneous_interval']==[0,0]
    assert result['comparisons']['other']['verdict']=='within material margin'
    rows.pop()
    with pytest.raises(ValueError,match='coverage'): paired_summary(pd.DataFrame(rows),MODELS,'reference')


def test_owned_run_equal_methods_and_missing_player_failure():
    d=market(); d['price_tenths']=60; later=d.copy(); later['gameweek']=29
    rows,actions,report=run(pd.concat([d,later]),MODELS,reference='reference',panels=3,rolling=0,reset=False)
    assert len(rows)==12 and len(actions)==12
    assert report['summaries']['owned']['4']['comparisons']['other']['challenger_minus_reference']==0
    assert not report['model_promotion']


def test_original_adapter_uses_lagged_metadata_and_exposes_cold_starts():
    from selection_inputs import dastan_market
    archive=pd.DataFrame([dict(gameweek=15,fpl_code=i,position='MID',actual=7.,minutes=90.,v1=3.,dastan=4.,value=999) for i in (1,2)])
    raw=pd.DataFrame([dict(season='2024-25',gameweek=14,fixture=100,fpl_code=1,position=3,
        ts='2024-12-01T12:00Z',deadline='2024-12-01T10:30Z',team_name='A',total_points=2.,minutes=80.,yellow_cards=0,red_cards=0),
        *[dict(season='2024-25',gameweek=15,fixture=200,fpl_code=i,position=3,
        ts='2024-12-07T12:00Z',deadline='2024-12-07T10:30Z',team_name='B',total_points=7.,minutes=90.,yellow_cards=0,red_cards=0) for i in (1,2)]])
    prices=pd.DataFrame([dict(fpl_code=1,fixture=100,ts='2024-12-01T12:00Z',value=50),dict(fpl_code=1,fixture=200,ts='2024-12-07T12:00Z',value=999)])
    frame,audit=dastan_market(archive,raw,['v1','dastan'],prices)
    assert len(frame)==1 and frame.price_tenths.iloc[0]==50 and frame.team.iloc[0]=='A'
    assert audit['weeks'][0]['excluded_no_prior_metadata']==[2]


def test_normalized_selector_rejects_missing_held_players():
    d=market()
    with pytest.raises(ValueError,match='coverage'): choices(d,[999],'reference')


def test_native_adapter_positive_blank_and_missing_forecast(tmp_path):
    import json
    from experiment_runner import file_hash
    from selection_inputs import native_market
    deadline='2026-02-27T18:30:00Z'; capture='2026-02-27T13:00:00Z'
    boot=dict(events=[dict(id=i,deadline_time='2025-08-01T12:00Z' if i==1 else deadline,
        is_next=i==28,finished=False) for i in range(1,39)],
        teams=[dict(id=i,name=f'T{i}') for i in (1,2,3)],elements=[dict(id=i,code=i*10,team=i,element_type=3,
        now_cost=50,can_select=True,selected_by_percent='1.0') for i in (1,2,3)])
    path=tmp_path/'boot.json'; path.write_text(json.dumps(boot))
    manifest=dict(season='2025-26',snapshots=[dict(gameweek=28,file='boot.json',sha256=file_hash(path),captured_at=capture)])
    base=tmp_path/'fixtures.csv'
    pd.DataFrame([dict(id=1,event=28,kickoff_time='2026-02-28T15:00Z',finished=False,started=False,
                      team_h_score=np.nan,team_a_score=np.nan,team_h=1,team_a=3)]).to_csv(base,index=False)
    calendar=dict(base_screens=[dict(file=base.name,sha256=file_hash(base),captured_at='2026-02-01T12:00Z')],updates=[])
    pred=pd.DataFrame([dict(season='2025-26',gameweek=28,fixture=1,fpl_code=i*10,position=3,
        actual=2.,minutes=90.,reference=3.) for i in (1,3)])
    raw=pd.DataFrame([dict(season='2025-26',gameweek=28,fixture=1,fpl_code=i*10,position=3,total_points=2.,minutes=90.,
        yellow_cards=0,red_cards=0,ts='2026-02-28T15:00Z',team_name=f'T{i}') for i in (1,3)])
    frame,audit=native_market(pred,raw,manifest,tmp_path,calendar,tmp_path,['reference'])
    blank=frame.set_index('fpl_code').loc[20]
    assert blank.blank_verified==1 and blank.reference==0 and blank.actual==0 and blank.minutes==0
    assert audit['weeks'][0]['verified_blank_players']==1
    with pytest.raises(ValueError,match='missing played-club'):
        native_market(pred.iloc[:1],raw,manifest,tmp_path,calendar,tmp_path,['reference'])
    path.write_text('{}')
    with pytest.raises(ValueError,match='checksum'):
        native_market(pred,raw,manifest,tmp_path,calendar,tmp_path,['reference'])
