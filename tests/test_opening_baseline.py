from collections import Counter
from itertools import combinations
import pytest
from opening_baseline import cheapest_opening
from season_engine import Market


def market(rows):
    return Market.create('2025-26',1,'2025-08-15T17:30Z','2025-08-15T12:00Z',rows)


def players():
    positions = [1]*3+[2]*6+[3]*6+[4]*4
    return [dict(id=i+1,position=p,team=str(i%6),price_tenths=40+(i*7)%31,can_buy=True)
            for i,p in enumerate(positions)]


def test_minimum_cost_matches_exhaustive_position_club_budget_search():
    rows = players();expected = []
    for roster in combinations(rows,15):
        if Counter(p['position'] for p in roster)!={1:2,2:5,3:5,4:3}:
            continue
        if max(Counter(p['team'] for p in roster).values())<=3:
            expected.append(sum(p['price_tenths'] for p in roster))
    answer = cheapest_opening(market(rows),1000)
    assert len(answer)==15 and sum(answer.values())==min(expected)
    assert cheapest_opening(market(list(reversed(rows))),1000)==answer
    with pytest.raises(ValueError,match='affordable'):
        cheapest_opening(market(rows),min(expected)-1)


def test_network_reassigns_a_greedy_club_choice_and_excludes_unbuyable():
    # The mandatory defenders/midfielders fill A/B/C/D/E to three each except
    # A/B's one vacancy. A cheap keeper in A must be moved to B so A's sole
    # available forward can enter. Position-by-position cheapest fails here.
    positions = [2]*5+[3]*5+[4]*2
    clubs = ['A','A','C','C','C','D','D','D','E','E','E','B']
    rows = [dict(id=i+1,position=p,team=t,price_tenths=40,can_buy=True)
            for i,(p,t) in enumerate(zip(positions,clubs))]
    rows += [dict(id=13,position=1,team='A',price_tenths=40,can_buy=True),
             dict(id=14,position=1,team='B',price_tenths=41,can_buy=True),
             dict(id=15,position=1,team='B',price_tenths=42,can_buy=True),
             dict(id=16,position=4,team='A',price_tenths=40,can_buy=True),
             dict(id=17,position=4,team='F',price_tenths=1,can_buy=False)]
    answer = cheapest_opening(market(rows),1000)
    assert set(answer)==set(range(1,13))|{14,15,16}


def test_infeasible_position_and_club_markets_are_reported():
    rows = players()
    with pytest.raises(ValueError,match='No legal'):
        cheapest_opening(market([p for p in rows if p['position']!=1]),1000)
    with pytest.raises(ValueError,match='No legal'):
        cheapest_opening(market([dict(p,team='same') for p in rows]),1000)
    with pytest.raises(ValueError,match='budget'):
        cheapest_opening(market(rows),True)
