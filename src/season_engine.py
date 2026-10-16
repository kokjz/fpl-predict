"""Deterministic deadline-to-deadline FPL state, independent of any planner.

Points are supplied as final official player-GW totals, never reconstructed from
incomplete BPS/assist data. Decision inputs and hidden outcomes are separate.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass,replace
import json
import math
from pathlib import Path
from types import MappingProxyType
from availability_evidence import utc
from selection_benchmark import score,sell_price,POSITIONS

CHIPS=('wildcard','freehit','bboost','3xc')


def integer(value,minimum=0):
    if type(value) is not int or value<minimum:raise ValueError('Expected bounded integer')
    return value


def rules_for(season):
    profiles=json.loads((Path(__file__).parent/'fpl_predict_resources/season_rules.json').read_text())
    if season not in profiles['seasons']:raise ValueError('Unsupported season; audit rules first')
    return deepcopy(profiles['seasons'][season])


@dataclass(frozen=True)
class State:
    season:str
    gameweek:int=1
    holdings:tuple=()  # (stable ID, original purchase quote in tenths)
    bank:int=1000
    free_transfers:int=0
    used_chips:tuple=()  # (chip name, window start)
    previous_chip:str|None=None
    total_points:float=0.

    def __post_init__(self):
        integer(self.gameweek,1);integer(self.bank);integer(self.free_transfers)
        if self.gameweek>39 or self.free_transfers>5 or not math.isfinite(self.total_points):raise ValueError('Invalid state')
        if not isinstance(self.holdings,tuple) or len({i for i,_ in self.holdings})!=len(self.holdings):raise ValueError('Duplicate/mutable ledger')
        for i,p in self.holdings:integer(i,1);integer(p,1)
        if (not self.holdings and self.gameweek!=1) or (self.holdings and len(self.holdings)!=15):raise ValueError('Missing/full initial squad required')
        if not isinstance(self.used_chips,tuple) or len(set(self.used_chips))!=len(self.used_chips):raise ValueError('Invalid chip history')
        if self.previous_chip not in (*CHIPS,None):raise ValueError('Invalid previous chip')
        for name,start in self.used_chips:
            if name not in CHIPS or start not in (1,2,20):raise ValueError('Invalid chip token')


@dataclass(frozen=True)
class Market:
    season:str
    gameweek:int
    deadline:str
    as_of:str
    players:tuple

    @classmethod
    def create(cls,season,gameweek,deadline,as_of,rows):
        integer(gameweek,1)
        if gameweek>38 or utc(as_of)>=utc(deadline):raise ValueError('Decision snapshot must be predeadline')
        allowed={'id','position','team','price_tenths','can_buy','expected_points','p_play','expected_minutes','status'}
        required={'id','position','team','price_tenths','can_buy'};players=[];ids=set()
        for row in rows:
            if set(row)-allowed or required-set(row):raise ValueError('Unknown/outcome or missing decision fields')
            r=deepcopy(row);integer(r['id'],1);integer(r['price_tenths'],1)
            if r['id'] in ids or r['position'] not in POSITIONS or not isinstance(r['team'],str) or not r['team'].strip() or type(r['can_buy']) is not bool:raise ValueError('Invalid roster')
            ids.add(r['id'])
            for k in ['expected_points','p_play','expected_minutes']:
                if k in r and (not math.isfinite(r[k]) or (k=='p_play' and not 0<=r[k]<=1) or (k=='expected_minutes' and not 0<=r[k]<=180)):raise ValueError('Invalid forecast')
            players.append(MappingProxyType(r))
        if not players:raise ValueError('Empty market')
        return cls(season,gameweek,deadline,as_of,tuple(players))

    def indexed(self):return {p['id']:dict(p) for p in self.players}


@dataclass(frozen=True)
class Action:
    buys:tuple
    sells:tuple
    starters:tuple
    bench:tuple
    captain:int
    vice:int
    chip:str|None=None

    def selection(self):return dict(starters=list(self.starters),bench=list(self.bench),captain=self.captain,vice=self.vice)


@dataclass(frozen=True)
class Prepared:
    state:State
    gameweek:int
    squad:tuple
    selection:dict
    chip:str|None
    hits:int
    transfers:int
    spent:int
    received:int
    playing_bank:int


def available_transfers(state,rules):
    return int(rules['ft_topups'].get(str(state.gameweek),state.free_transfers))


def prepare(state,market,action,rules=None):
    """Validate a deadline action and finances, without accepting any outcomes."""
    rules=rules_for(state.season) if rules is None else rules
    Market.create(market.season,market.gameweek,market.deadline,market.as_of,[dict(p) for p in market.players])
    if rules['season']!=state.season or market.season!=state.season or market.gameweek!=state.gameweek or state.gameweek>38:raise ValueError('Season/GW mismatch')
    if state.gameweek==1 and (state.holdings or state.bank!=rules['initial_budget'] or state.free_transfers or state.used_chips or state.total_points or state.previous_chip):raise ValueError('GW1 must start with audited initial capital and no prior actions')
    if not isinstance(action,Action):raise ValueError('Policy must return an Action')
    for seq in [action.buys,action.sells,action.starters,action.bench]:
        if not isinstance(seq,tuple) or len(set(seq))!=len(seq):raise ValueError('Mutable/duplicate action IDs')
        for i in seq:integer(i,1)
    if set(action.buys)&set(action.sells):raise ValueError('No intradeadline round trips in deadline-only replay')
    roster=market.indexed();old=dict(state.holdings)
    if not set(old)<=set(roster):raise ValueError('Missing held-player quote/roster; never impute zero')
    if not set(action.sells)<=set(old) or set(action.buys)&set(old) or not set(action.buys)<=set(roster):raise ValueError('Invalid buys/sells')
    if not all(roster[i]['can_buy'] for i in action.buys):raise ValueError('Unavailable purchase')
    if action.chip not in (*CHIPS,None):raise ValueError('Unsupported chip')
    used=state.used_chips
    if action.chip:
        windows=[w for w in rules['chip_windows'] if w['name']==action.chip and w['start']<=state.gameweek<=w['stop']]
        if len(windows)!=1 or (action.chip,windows[0]['start']) in used:raise ValueError('Chip expired/unavailable/already used')
        if action.chip=='freehit' and state.previous_chip=='freehit':raise ValueError('Consecutive Free Hits prohibited')
        used=(*used,(action.chip,windows[0]['start']))
    received=sum(sell_price(old[i],roster[i]['price_tenths']) for i in action.sells)
    spent=sum(roster[i]['price_tenths'] for i in action.buys);bank=state.bank+received-spent
    if bank<0:raise ValueError('Insufficient funds')
    ledger={i:p for i,p in old.items() if i not in action.sells};ledger.update({i:roster[i]['price_tenths'] for i in action.buys})
    squad=[roster[i] for i in sorted(ledger)]
    if len(squad)!=15 or Counter(p['position'] for p in squad)!=POSITIONS:raise ValueError('Illegal positional squad')
    # A real club transfer may leave an untouched squad over the club limit.
    # Any subsequent FPL transfer must restore compliance.
    if (action.buys or action.sells or not old) and max(Counter(p['team'] for p in squad).values())>3:raise ValueError('Club limit exceeded')
    if len(action.buys)!=len(action.sells) and old:raise ValueError('Unbalanced transfers')
    n=len(action.buys);free=available_transfers(state,rules)
    if old and action.chip not in ('wildcard','freehit') and n>rules['transfer_cap']:raise ValueError('Transfer cap exceeded')
    hits=0 if not old or action.chip in ('wildcard','freehit') else 4*max(0,n-free)
    if not old:next_ft=1
    elif action.chip in ('wildcard','freehit'):next_ft=free
    else:next_ft=min(rules['ft_cap'],max(0,free-n)+1)
    integer(action.captain,1);integer(action.vice,1)
    selection=action.selection();by={p['id']:p for p in squad}
    score(selection,by,{i:dict(actual=0.,minutes=0.,cards=0.) for i in by},check_clubs=False)
    persisted=old if action.chip=='freehit' else ledger
    persisted_bank=state.bank if action.chip=='freehit' else bank
    after=State(state.season,state.gameweek+1,tuple(sorted(persisted.items())),persisted_bank,next_ft,tuple(used),action.chip,state.total_points)
    return Prepared(after,state.gameweek,tuple(MappingProxyType(p) for p in squad),selection,action.chip,hits,n,spent,received,bank)


def settle(prepared,outcomes):
    """Final official GW totals (both DGW fixtures already summed), once per GW."""
    players={p['id']:dict(p) for p in prepared.squad}
    result=score(prepared.selection,players,outcomes,prepared.hits,check_clubs=False)
    if prepared.chip=='bboost':
        result['bench_boost_points']=float(sum(outcomes[i]['actual'] for i in prepared.selection['bench']))
        result['autosub_delta']=0.
        result['scoring_xi']=list(prepared.selection['starters'])
        result['net_points']=float(sum(outcomes[i]['actual'] for i in players)+result['captain_bonus']-prepared.hits)
    elif prepared.chip=='3xc':result['net_points']+=result['captain_bonus'];result['extra_captain_bonus']=result['captain_bonus']
    else:result['bench_boost_points']=0.
    after=replace(prepared.state,total_points=prepared.state.total_points+result['net_points'])
    return after,dict(gameweek=prepared.gameweek,chip=prepared.chip,transfers=prepared.transfers,
        received=prepared.received,spent=prepared.spent,playing_bank=prepared.playing_bank,
        persisted_bank=after.bank,next_free_transfers=after.free_transfers,**result)


def replay(markets,outcomes,policy,state=None,*,require_full_season=True):
    """Policy sees only current market/current state; outcomes go to settlement.

    This is an API separation, not a sandbox for arbitrary untrusted Python code.
    """
    if not markets:raise ValueError('No deadline markets')
    state=State(markets[0].season) if state is None else state;start=state.gameweek
    if require_full_season and (start!=1 or len(markets)!=38):raise ValueError('Full season requires exactly38 deadlines fromGW1')
    rows=[];actions=[];previous_deadline=None
    for market in markets:
        if previous_deadline is not None and utc(market.as_of)<=previous_deadline:raise ValueError('Nonchronological snapshots')
        previous_deadline=utc(market.deadline)
        if market.gameweek!=state.gameweek:raise ValueError('Missing/duplicate/out-of-order deadline')
        state=replace(state,free_transfers=available_transfers(state,rules_for(state.season)))
        action=policy(state,market)
        prepared=prepare(state,market,action)
        if market.gameweek not in outcomes:raise ValueError('Missing final outcome GW')
        state,result=settle(prepared,outcomes[market.gameweek]);rows.append(result);actions.append(action)
    if require_full_season and state.gameweek!=39:raise ValueError('Incomplete season')
    return state,rows,actions


def audit_bootstrap(bootstrap,season,gameweek):
    """Check executable active-chip rules; flag unsupported future overrides."""
    rules=rules_for(season);settings=bootstrap['game_settings']
    expected=dict(squad_squadplay=11,squad_squadsize=15,squad_team_limit=3,squad_total_spend=1000,
                  transfers_cap=20,transfers_sell_on_fee=.5,max_extra_free_transfers=4)
    mismatches=[k for k,v in expected.items() if settings.get(k)!=v]
    expected_windows={(w['name'],w['start'],w['stop']) for w in rules['chip_windows']}
    got={(w['name'],w['start_event'],w['stop_event']) for w in bootstrap['chips']}
    if got!=expected_windows:mismatches.append('chip_windows')
    active=[];future=[]
    for chip in bootstrap['chips']:
        overrides=chip.get('overrides',{})
        unsupported=any(overrides.get(k) for k in ('rules','scoring','element_types','pick_multiplier'))
        if chip.get('number')!=1:unsupported=True
        if unsupported and chip['stop_event']>=gameweek:
            (active if chip['start_event']<=gameweek else future).append(dict(name=chip['name'],start=chip['start_event'],stop=chip['stop_event']))
    return dict(active_rules_compatible=not mismatches and not active,full_future_chip_configuration_supported=not future and not active,
        mismatches=mismatches,unsupported_active_chips=active,unsupported_future_chips=future)


def main():
    import argparse
    from dataclasses import asdict
    from experiment_runner import file_hash
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('markets','actions','outcomes'):
        p.add_argument('--'+name,type=Path,required=True);p.add_argument('--'+name+'-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    paths={n:getattr(a,n) for n in ('markets','actions','outcomes')}
    if a.output.exists():p.error('Output exists; preserve earlier evidence')
    if any(file_hash(path)!=getattr(a,n+'_sha256') for n,path in paths.items()):p.error('Input checksum mismatch')
    inputs={n:json.loads(path.read_text()) for n,path in paths.items()}
    if any(v.get('schema_version')!=1 for v in inputs.values()):p.error('Unsupported replay schema')
    markets=[Market.create(**v) for v in inputs['markets']['weeks']]
    actions={}
    for v in inputs['actions']['weeks']:
        z=dict(v);gw=z.pop('gameweek')
        if gw in actions:p.error('Duplicate action GW')
        for k in ('buys','sells','starters','bench'):z[k]=tuple(z[k])
        actions[gw]=Action(**z)
    hidden={}
    for v in inputs['outcomes']['weeks']:
        gw=v['gameweek']
        if gw in hidden:p.error('Duplicate outcome GW')
        ids=[r['id'] for r in v['players']]
        if len(ids)!=len(set(ids)):p.error('Duplicate outcome player')
        hidden[gw]={r['id']:{k:r[k] for k in ('actual','minutes','cards')} for r in v['players']}
    if set(actions)!=set(range(1,39)) or set(hidden)!=set(range(1,39)):p.error('Require38complete action/outcome GWs')
    final,rows,used=replay(markets,hidden,lambda state,market:actions[state.gameweek])
    a.output.mkdir(parents=True)
    report=dict(schema_version=1,scope='Full38GW replay of supplied frozen actions; not an adaptive-planner benchmark',
        final_state=asdict(final),rows=rows,actions=[asdict(v) for v in used],
        input_sha256={n:file_hash(path) for n,path in paths.items()},engine_sha256=file_hash(Path(__file__)),
        scorer_sha256=file_hash(Path(__file__).with_name('selection_benchmark.py')),
        rules_sha256=file_hash(Path(__file__).parent/'fpl_predict_resources/season_rules.json'))
    (a.output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
