"""Deterministic minimum-cost feasible roster, independent of forecasts.

The position-to-club flow network has one unit-capacity edge per player. Its
integer capacities enforce squad composition and the three-per-club limit.
Fifteen shortest augmenting paths find the cheapest legal roster without a
mixed-integer solve, a prediction score, or a random restart.
"""
from selection_benchmark import POSITIONS


def cheapest_opening(market, bank):
    if type(bank) is not int or bank < 0:
        raise ValueError('Invalid opening budget')
    players = sorted((p for p in market.players if p['can_buy']), key=lambda p:p['id'])
    clubs = {team:i+5 for i,team in enumerate(sorted({p['team'] for p in players}))}
    sink = 5 + len(clubs)
    graph = [[] for _ in range(sink+1)]

    def edge(a,b,capacity,cost):
        forward = [b,len(graph[b]),capacity,cost]
        reverse = [a,len(graph[a]),0,-cost]
        graph[a].append(forward);graph[b].append(reverse)
        return forward

    for position,count in POSITIONS.items():
        edge(0,position,count,0)
    selected = [(p,edge(p['position'],clubs[p['team']],1,p['price_tenths'])) for p in players]
    for club in clubs.values():
        edge(club,sink,3,0)
    for _ in range(15):
        distance = [float('inf')]*len(graph);distance[0] = 0
        previous = [None]*len(graph)
        # Reverse edges may have negative costs. Bellman-Ford also permits
        # reassignment across positions/clubs when greedy choices would fail.
        for _ in range(len(graph)-1):
            changed = False
            for a,edges in enumerate(graph):
                for index,(b,reverse,capacity,cost) in enumerate(edges):
                    if capacity and distance[a]+cost < distance[b]:
                        distance[b] = distance[a]+cost;previous[b] = (a,index);changed = True
            if not changed:
                break
        if previous[sink] is None:
            raise ValueError('No legal opening squad')
        node = sink
        while node:
            a,index = previous[node];forward = graph[a][index]
            forward[2] -= 1;graph[node][forward[1]][2] += 1;node = a
    ledger = {p['id']:p['price_tenths'] for p,forward in selected if not forward[2]}
    if sum(ledger.values()) > bank:
        raise ValueError('No affordable legal opening squad')
    return ledger
