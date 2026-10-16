"""Offline common-policy selection research; never changes a squad or model registry."""
from __future__ import annotations
import argparse
from collections import Counter
from itertools import combinations
import json
import importlib.metadata
import platform
import re
from pathlib import Path
import time
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix

from experiment_runner import file_hash
from forecast import select_xi

POSITIONS = {1: 2, 2: 5, 3: 5, 4: 3}
DECISION = ['fpl_code', 'position', 'team', 'price_tenths', 'can_buy', 'prior_minutes', 'ownership']


def legal(players):
    return (len(players) == 15 and len({p['id'] for p in players}) == 15 and
            Counter(p['position'] for p in players) == POSITIONS and
            max(Counter(p['team'] for p in players).values()) <= 3)


def formation(ids, players):
    c = Counter(players[i]['position'] for i in ids)
    return len(ids) == 11 and c[1] == 1 and c[2] >= 3 and c[3] >= 2 and c[4] >= 1


def score(selection, players, outcomes, hits=0, *, check_clubs=True):
    """Cards count for autosubs; captain fallback uses minutes, per published rules.

    Non-appearing original starters still occupy formation slots. Choose the
    lexicographically first eligible bench set that preserves the legal XI.
    """
    squad=list(players.values())
    if len(squad)!=15 or len({p['id'] for p in squad})!=15 or Counter(p['position'] for p in squad)!=POSITIONS or (check_clubs and max(Counter(p['team'] for p in squad).values())>3):raise ValueError('Illegal squad')
    starters = list(selection['starters']); bench = list(selection['bench'])
    if (len(set(starters + bench)) != 15 or set(starters + bench) != set(players) or
            not formation(starters, players) or len(bench) != 4 or
            selection['captain'] == selection['vice'] or
            not {selection['captain'], selection['vice']} <= set(starters) or
            type(hits) is not int or hits < 0):
        raise ValueError('Illegal selection/hits')
    if not set(players) <= set(outcomes): raise ValueError('Unknown outcome')
    for p in players:
        if any(not np.isfinite(outcomes[p][k]) for k in ('actual', 'minutes', 'cards')):
            raise ValueError('Non-finite outcome')
        if min(outcomes[p]['minutes'], outcomes[p]['cards']) < 0: raise ValueError('Negative appearance data')
    active = lambda p: outcomes[p]['minutes'] > 0 or outcomes[p]['cards'] > 0
    ids = starters.copy(); keeper = next(i for i in ids if players[i]['position'] == 1)
    reserve = next(i for i in bench if players[i]['position'] == 1)
    if not active(keeper) and active(reserve): ids[ids.index(keeper)] = reserve
    missing = [i for i in ids if players[i]['position'] != 1 and not active(i)]
    reserves = [i for i in bench if players[i]['position'] != 1]
    best = ((0, 0, 0), ids)
    for n in range(1, min(len(missing), 3) + 1):
        for incoming in combinations(reserves, n):
            if not all(active(i) for i in incoming): continue
            priority = tuple(int(i in incoming) for i in reserves)
            for outgoing in combinations(missing, n):
                candidate = [i for i in ids if i not in outgoing] + list(incoming)
                if formation(candidate, players) and priority > best[0]: best = (priority, candidate)
    captain = next((p for p in (selection['captain'], selection['vice']) if outcomes[p]['minutes'] > 0), None)
    base = float(sum(outcomes[i]['actual'] for i in starters))
    after = float(sum(outcomes[i]['actual'] for i in best[1]))
    bonus = float(outcomes[captain]['actual']) if captain is not None else 0.
    return dict(base_xi=base, autosub_delta=after-base, captain_bonus=bonus,
                hits=hits, net_points=after+bonus-hits, scoring_xi=best[1], scoring_captain=captain)


def sell_price(purchase, current):
    if any(type(v) is not int or v <= 0 for v in (purchase, current)): raise ValueError('Invalid price')
    return current if current <= purchase else purchase + (current-purchase)//2


def validate(frame, models):
    required = ['season', 'gameweek', 'deadline', 'inputs_as_of', 'actual', 'minutes', 'cards', *DECISION, *models]
    if not models or len(set(models)) != len(models) or any(m in required[:-len(models)] for m in models):
        raise ValueError('Declare distinct forecast columns')
    if set(required)-set(frame): raise ValueError('Missing normalized columns')
    if frame.empty or frame.duplicated(['season', 'gameweek', 'fpl_code']).any(): raise ValueError('Empty/duplicate market')
    for key in ['gameweek', 'fpl_code', 'position', 'price_tenths']:
        x = pd.to_numeric(frame[key], errors='raise')
        if not np.isfinite(x).all() or not (x == x.astype(int)).all() or (x <= 0).any(): raise ValueError('Invalid identity/price')
    if not frame.position.isin(POSITIONS).all() or not frame.gameweek.between(1, 38).all(): raise ValueError('Invalid position/GW')
    numeric = frame[['actual', 'minutes', 'cards', 'prior_minutes', 'ownership', *models]].to_numpy(float)
    if not np.isfinite(numeric).all() or (frame[['minutes', 'cards', 'prior_minutes', 'ownership']] < 0).any().any():
        raise ValueError('Invalid values')
    if (not frame.can_buy.isin([0, 1]).all() or
            not frame.team.map(lambda v:isinstance(v,str) and bool(v.strip())).all()):
        raise ValueError('Invalid buy/club')
    def season_valid(v):
        return (isinstance(v,str) and re.fullmatch(r'20[0-9]{2}-[0-9]{2}',v) is not None and
                (int(v[:4])+1)%100 == int(v[-2:]))
    if not frame.season.map(season_valid).all(): raise ValueError('Invalid season')
    for _, week in frame.groupby(['season', 'gameweek']):
        if week.deadline.nunique() != 1 or week.inputs_as_of.nunique() != 1: raise ValueError('Ambiguous cutoff')
        deadline = pd.Timestamp(week.deadline.iloc[0]); cutoff = pd.Timestamp(week.inputs_as_of.iloc[0])
        if deadline.tzinfo is None or cutoff.tzinfo is None or cutoff >= deadline: raise ValueError('Not predeadline')
    return frame.sort_values(['season', 'gameweek', 'fpl_code']).reset_index(drop=True)


def choices(week, ids, model):
    d = week.set_index('fpl_code')
    if not set(ids) <= set(d.index): raise ValueError('Missing held-player coverage')
    # Explicit whitelist: realised outcomes never reach a selector.
    return [{'id': int(i), 'position': int(d.loc[i, 'position']), 'team': d.loc[i, 'team'],
             'price_tenths': int(d.loc[i, 'price_tenths']), 'expected_points': float(d.loc[i, model])} for i in sorted(ids)]


def scenarios(week, count=12, seed=20261015, minimum_cost=900):
    """Neutral, source-only stratified scenarios, independent of all predictions."""
    if type(count) is not int or count <= 0 or count % 3: raise ValueError('Count must be positive multiple of three')
    pool = week[week.can_buy.eq(1)].sort_values('fpl_code'); rng = np.random.default_rng(seed)
    result = []; seen = set()
    for stratum in ('balanced', 'ownership', 'rotation'):
        found = 0
        for _ in range(20000):
            ids = []
            for pos, n in POSITIONS.items():
                group = pool[pool.position.eq(pos)]
                if len(group) < n: raise ValueError('Incomplete positional market')
                # Common price tilt makes the declared budget band feasible
                # without consulting forecasts or target outcomes.
                weight = (group.price_tenths.to_numpy(float)/50)**2
                if stratum == 'ownership': weight *= np.sqrt(group.ownership.to_numpy(float)+.1)
                if stratum == 'rotation': weight /= 1+group.prior_minutes.to_numpy(float)/30
                chosen = rng.choice(group.fpl_code.to_numpy(), n, replace=False, p=weight/weight.sum())
                ids.extend(map(int, chosen))
            key = tuple(sorted(ids)); squad = choices(pool, ids, 'price_tenths')
            cost = sum(p['price_tenths'] for p in squad)
            if key not in seen and legal(squad) and minimum_cost <= cost <= 1000:
                result.append(dict(stratum=stratum, ids=list(key))); seen.add(key); found += 1
                if found == count//3: break
        if found != count//3: raise ValueError(f'Scenario construction budget exhausted: {stratum}, {found}/{count//3}')
    return result


def optimise(week, model, *, owned=None, bank=1000, free_transfers=1, seconds=10):
    """Exact common mean-XI/captain + 0.1 reserve heuristic, minus transfer hits.

    owned maps IDs to original purchase prices. Quotes are supplied snapshot
    prices; this is not a historical tick-by-tick execution simulator.
    """
    if type(bank) is not int or bank < 0 or type(free_transfers) is not int or not 1 <= free_transfers <= 5:
        raise ValueError('Invalid bank/FT')
    if owned is not None and len(owned) != 15: raise ValueError('Invalid purchase ledger')
    market = week[DECISION + [model]].copy().sort_values('fpl_code')
    if owned is not None and not set(owned) <= set(market.fpl_code): raise ValueError('Missing owned quotes')
    market = market[market.can_buy.eq(1) | market.fpl_code.isin(owned or {})].reset_index(drop=True)
    n = len(market); size = 3*n+1; objective = np.zeros(size)
    xp = market[model].to_numpy(float)
    objective[:n] = -.1*xp; objective[n:2*n] = -.9*xp; objective[2*n:3*n] = -xp
    objective[-1] = 4
    rows = []; lower = []; upper = []
    def constraint(values, lo, hi):
        rows.append(values); lower.append(lo); upper.append(hi)
    def vector(): return np.zeros(size)
    for pos, count in POSITIONS.items():
        mask = market.position.eq(pos).to_numpy(); row = vector(); row[:n] = mask
        constraint(row, count, count)
        row = vector(); row[n:2*n] = mask
        constraint(row, {1:1, 2:3, 3:2, 4:1}[pos], {1:1, 2:5, 3:5, 4:3}[pos])
    for start, count in ((n,11), (2*n,1)):
        row = vector(); row[start:start+n] = 1; constraint(row, count, count)
    for i in range(n):
        row = vector(); row[n+i] = 1; row[i] = -1; constraint(row, -np.inf, 0)
        row = vector(); row[2*n+i] = 1; row[n+i] = -1; constraint(row, -np.inf, 0)
    for team in sorted(market.team.unique()):
        row = vector(); row[:n] = market.team.eq(team); constraint(row, -np.inf, 3)
    prices = market.price_tenths.to_numpy(int); costs = prices.copy(); funds = bank
    if owned is not None:
        for i, code in enumerate(market.fpl_code):
            if code in owned: costs[i] = sell_price(owned[code], int(prices[i])); funds += int(costs[i])
        row = vector(); row[:n] = ~market.fpl_code.isin(owned); row[-1] = -1
        constraint(row, -np.inf, free_transfers)
    row = vector(); row[:n] = costs; constraint(row, -np.inf, funds)
    bounds_hi = np.ones(size); bounds_hi[-1] = 15 if owned is not None else 0
    started = time.monotonic()
    # SciPy forwards this native HiGHS option but warns because it is not in
    # its smaller documented wrapper list. Limit the actual solver pool too.
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message="Unrecognized options detected:.*threads.*", category=RuntimeWarning)
        answer = milp(objective, integrality=np.ones(size), bounds=Bounds(np.zeros(size), bounds_hi),
                      constraints=LinearConstraint(csr_matrix(np.array(rows)), lower, upper),
                      options={'time_limit': seconds, 'mip_rel_gap': 1e-8, 'threads': 2})
    if answer.status != 0 or answer.x is None: raise ValueError(f'No proven optimal solution: {answer.message}')
    ids = [int(market.fpl_code.iloc[i]) for i in range(n) if answer.x[i] > .5]
    squad = choices(market, ids, model)
    if not legal(squad): raise ValueError('Solver returned illegal squad')
    # Tie policy and vice/bench order identical to owned-squad selector.
    selection = select_xi(squad)
    bought = set(ids)-set(owned or {}); sold = set(owned or {})-set(ids)
    transfers = len(bought) if owned is not None else 0
    hits = 4*max(0, transfers-free_transfers)
    if owned is None:
        ledger = {p['id']: p['price_tenths'] for p in squad}; next_bank = bank-sum(ledger.values())
    else:
        quotes = dict(zip(market.fpl_code, prices))
        next_bank = bank + sum(sell_price(owned[i], int(quotes[i])) for i in sold) - sum(int(quotes[i]) for i in bought)
        ledger = {i: owned[i] if i in owned else int(quotes[i]) for i in ids}
    if next_bank < 0: raise ValueError('Insolvent solution')
    return dict(selection=selection, ledger=ledger, bank=int(next_bank), transfers=transfers, hits=hits,
                free_transfers=min(5, max(0, free_transfers-transfers)+1), solve_seconds=time.monotonic()-started)


def paired_summary(rows, models, reference, *, block=4, repetitions=4000, seed=20261015, margin=.25):
    """Season-local circular moving blocks; simultaneous centred max deviation.

    Average scenarios inside each GW first. Reused historical observations make
    these descriptive sensitivity intervals, not fresh confirmatory evidence.
    """
    if reference not in models or block < 1 or repetitions < 100: raise ValueError('Invalid inference spec')
    table = rows.pivot(index=['season','gameweek','scenario'], columns='model', values='net_points')
    if table[models].isna().any().any(): raise ValueError('Unequal model coverage')
    gw = table[models].groupby(['season','gameweek']).mean()
    if len(gw) < 2: return {'gameweeks':len(gw), 'means':gw.mean().to_dict(), 'comparisons':{}, 'intervals':'insufficient gameweeks'}
    rivals = [m for m in models if m != reference]
    delta = gw[rivals].subtract(gw[reference], axis=0); point = delta.mean().to_numpy()
    rng = np.random.default_rng(seed); draws = []
    for _ in range(repetitions):
        sampled = []
        for _, group in delta.groupby(level='season'):
            a = group.to_numpy(); weeks = group.index.get_level_values('gameweek').to_numpy()
            # Do not bridge missing GWs: only contiguous segments are resampled.
            for indices in np.split(np.arange(len(a)), np.where(np.diff(weeks) != 1)[0]+1):
                segment = a[indices]; n = len(segment); length = min(block,n)
                starts = rng.integers(0,n,size=int(np.ceil(n/length)))
                ii = np.concatenate([(s+np.arange(length)) % n for s in starts])[:n]
                sampled.append(segment[ii])
        draws.append(np.concatenate(sampled).mean(axis=0))
    q = float(np.quantile(np.max(np.abs(np.asarray(draws)-point),axis=1),.95))
    comparisons = {}
    for m, d in zip(rivals,point):
        lo, hi = float(d-q),float(d+q)
        verdict = 'inconclusive'
        if lo > margin: verdict = 'challenger advantage'
        elif hi < -margin: verdict = 'reference advantage'
        elif lo >= -margin and hi <= margin: verdict = 'within material margin'
        comparisons[m] = dict(challenger_minus_reference=float(d), simultaneous_interval=[lo,hi], verdict=verdict)
    return dict(gameweeks=len(gw), panels=len(table), means=gw.mean().to_dict(), comparisons=comparisons,
                block=block, repetitions=repetitions, margin=margin, interpretation='retrospective descriptive; not model promotion')


def run(frame, models, *, reference, panels=12, rolling=6, reset=True, per_week=False, legacy=None):
    frame = validate(frame, models)
    if frame.season.nunique() != 1: raise ValueError('Run seasons separately')
    if reference not in models or rolling < 0 or rolling > panels: raise ValueError('Invalid run spec')
    groups = list(frame.groupby('gameweek', sort=True)); first = groups[0][1]
    if rolling and any(b[0] != a[0]+1 for a,b in zip(groups,groups[1:])):
        raise ValueError('Rolling weeks must be consecutive')
    frozen = legacy if legacy is not None else (None if per_week else scenarios(first, panels))
    schedule = {int(gw):scenarios(week,panels,seed=20261015+int(gw),minimum_cost=0)
                if per_week else frozen for gw,week in groups}
    records = []; actions = []; states = {}
    rolling_ids = [i for i in range(len(frozen or [])) if i % (panels//3) < rolling//3] if rolling else []
    if rolling and (per_week or legacy is not None or rolling % 3): raise ValueError('Unsupported rolling scenarios')
    for gw, week in groups:
        frozen = schedule[int(gw)]
        outcomes = {int(r.fpl_code):{'actual':float(r.actual),'minutes':float(r.minutes),'cards':float(r.cards)} for r in week.itertuples()}
        def record(layer, sid, model, squad, selection, hits=0, **details):
            points = score(selection, {p['id']:p for p in squad}, outcomes, hits)
            records.append(dict(season=frame.season.iloc[0],gameweek=int(gw),scenario=sid,model=model,layer=layer,
                                **{k:v for k,v in points.items() if k not in ('scoring_xi','scoring_captain')}, **details))
            actions.append(dict(gameweek=int(gw),scenario=sid,model=model,layer=layer,selection=selection,
                                squad=[p['id'] for p in squad], **details))
        for model in models:
            for sid, panel in enumerate(frozen):
                squad = choices(week, panel['ids'], model)
                record('owned',sid,model,squad,select_xi(squad))
            if reset:
                result = optimise(week, model); squad = choices(week,result['ledger'],model)
                record('reset',0,model,squad,result['selection'], solve_seconds=result['solve_seconds'])
            for sid in rolling_ids:
                key = (model,sid)
                if key not in states:
                    opening = choices(first,frozen[sid]['ids'],model)
                    ledger = {p['id']:p['price_tenths'] for p in opening}
                    states[key] = dict(ledger=ledger,bank=1000-sum(ledger.values()),free_transfers=1)
                previous = states[key]
                result = optimise(week,model,owned=previous['ledger'],bank=previous['bank'],free_transfers=previous['free_transfers'])
                states[key] = result; squad = choices(week,result['ledger'],model)
                record('rolling',sid,model,squad,result['selection'],result['hits'],bank=result['bank'],
                       transfers=result['transfers'],free_transfers=result['free_transfers'],solve_seconds=result['solve_seconds'])
        print(f'Completed GW{gw}: {len(records)} scored panels',flush=True)
    rows = pd.DataFrame(records); summaries = {}
    for layer in ('owned','reset'):
        sub = rows[rows.layer.eq(layer)]
        if not sub.empty:
            summaries[layer] = {str(b):paired_summary(sub,models,reference,block=b) for b in (2,4,6)}
    rolling_rows = rows[rows.layer.eq('rolling')]
    if not rolling_rows.empty:
        totals = rolling_rows.groupby(['scenario','model']).net_points.sum().unstack()
        summaries['rolling'] = dict(mean_episode_points=totals.mean().to_dict(),
            mean_episode_difference=totals.subtract(totals[reference],axis=0).mean().to_dict(),
            scenario_totals=totals.to_dict('index'),inference='One path-dependent window; no independent-episode CI')
    return rows,actions,dict(summaries=summaries,scenario_schedule=schedule,models=models,reference=reference,
                             model_promotion=False,normal_weekly_workflow_changed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--models',nargs='+',required=True)
    parser.add_argument('--reference',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--panels',type=int,default=12)
    parser.add_argument('--rolling',type=int,default=6)
    parser.add_argument('--no-reset',action='store_true')
    parser.add_argument('--per-week',action='store_true')
    args = parser.parse_args()
    if file_hash(args.input) != args.sha256: parser.error('Input checksum mismatch')
    if args.output.exists(): parser.error('Output exists; runs are immutable')
    frame = pd.read_csv(args.input)
    args.output.mkdir(parents=True)
    (args.output/'spec.json').write_text(json.dumps(dict(input_sha256=args.sha256,models=args.models,reference=args.reference,
        panels=args.panels,rolling=args.rolling,reset=not args.no_reset,per_week=args.per_week,
        engine_sha256=file_hash(Path(__file__)),selector_sha256=file_hash(Path(__file__).parent/'forecast.py'),
        environment={name:importlib.metadata.version(name) for name in ('numpy','pandas','scipy','scikit-learn')},
        python=platform.python_version(),protocol_sha256=file_hash(Path(__file__).parent/'fpl_predict_resources/selection_protocol.json')),
        indent=2))
    rows, actions, report = run(frame,args.models,reference=args.reference,panels=args.panels,rolling=args.rolling,
                                reset=not args.no_reset,per_week=args.per_week)
    rows.to_csv(args.output/'scores.csv',index=False)
    (args.output/'actions.json').write_text(json.dumps(actions,indent=2,allow_nan=False))
    (args.output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))


if __name__ == '__main__': main()
