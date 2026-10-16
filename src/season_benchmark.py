"""Chronological management replay; policies see one admitted origin at a time."""
from dataclasses import asdict,dataclass,replace
import json,time
from pathlib import Path
from adaptive_planner import plan_adaptive,Budget
from horizon_forecast import Horizon
from rolling_planner import plan,Settings
from season_engine import State,Market,prepare,settle,rules_for,available_transfers
from experiment_runner import file_hash
from availability_evidence import utc


def read_bundle(path):
    """Bound decompressed local JSON while allowing compact historical bundles."""
    import gzip
    path=Path(path);opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rb') as stream:raw=stream.read(128*1024**2+1)
    if len(raw)>128*1024**2:raise ValueError('Oversized replay bundle')
    return json.loads(raw)


@dataclass(frozen=True)
class Policy:
    horizon:int=6
    chips:bool=True
    seconds:float=4.
    solve_seconds:float=.5
    max_trials:int=12

    def __post_init__(self):
        if type(self.horizon) is not int or not 1<=self.horizon<=8 or type(self.chips) is not bool:raise ValueError('Invalid management policy')
        Budget(self.seconds,self.solve_seconds,self.max_trials)


def forecast(market,spec,horizon):
    h=Horizon.create(market,**spec)
    end=min(38,market.gameweek+horizon-1)
    if h.gameweeks[-1]<end:raise ValueError('Missing requested horizon')
    return Horizon.create(market,[dict(v) for v in h.forecasts if v['gameweek']<=end],**dict(h.provenance))


def run(decisions,outcomes,directory,*,policy=None,opening_ids=None):
    """Write action before settlement for all38GWs, keep all state and chips.

    decisions contains market/forecast/blocked_tokens, outcomes is a distinct
    evaluator mapping. API separation is not a sandbox for untrusted Python.
    No result can influence earlier actions. Historical freezing is retrospective,
    not proof a forecast actually existed at the historical deadline.
    """
    cfg=policy or Policy();directory=Path(directory)
    if directory.exists():raise ValueError('Output exists; retain frozen evidence')
    if len(decisions)!=38 or [v['market']['gameweek'] for v in decisions]!=list(range(1,39)) or set(outcomes)!=set(range(1,39)):raise ValueError('Require38complete ordered origins and outcomes')
    state=State(decisions[0]['market']['season']);rows=[];actions=[];logs=[];previous=None;start=time.monotonic()
    # Validate the complete origin inventory before emitting any forecast action.
    for v in decisions:
        m=Market.create(**v['market']);h=forecast(m,v['forecast'],cfg.horizon)
        if m.season!=state.season or (previous is not None and utc(m.as_of)<=previous):raise ValueError('Nonchronological season')
        previous=utc(m.deadline)
    directory.mkdir(parents=True)
    for spec in decisions:
        market=Market.create(**spec['market']);h=forecast(market,spec['forecast'],cfg.horizon)
        state=replace(state,free_transfers=available_transfers(state,rules_for(state.season)))
        if market.gameweek==1 and opening_ids is not None:
            if len(set(opening_ids))!=15 or not set(opening_ids)<=set(market.indexed()) or not all(market.indexed()[i]['can_buy'] for i in opening_ids):raise ValueError('Invalid common opening roster')
            # Fix only first-period membership. Future provisional periods must
            # retain access to the full market, not an artificially closed roster.
        first_ids=opening_ids if market.gameweek==1 else None
        if cfg.chips:
            proposed,report=plan_adaptive(state,market,[('admitted',1.,h)],settings=Settings(),budget=Budget(cfg.seconds,cfg.solve_seconds,cfg.max_trials),blocked=[tuple(v) for v in spec['blocked_tokens']],opening_ids=first_ids)
        else:proposed,report=plan(state,market,h,Settings(seconds=cfg.solve_seconds),opening_ids=first_ids)
        action=proposed[0];prepared=prepare(state,market,action)
        record=dict(gameweek=market.gameweek,inputs_as_of=market.as_of,state_before=asdict(state),
            forecast_provenance={**dict(h.provenance),'source_hashes':dict(h.provenance['source_hashes'])},
            action=asdict(action),provisional_actions=[asdict(v) for v in proposed],report=report)
        path=directory/f'GW{market.gameweek:02d}_decision.json'
        with path.open('x') as stream:json.dump(record,stream,indent=2,allow_nan=False)
        # Hidden evaluator outcomes are accessed only after the decision is saved.
        state,result=settle(prepared,outcomes[market.gameweek]);result['decision_sha256']=file_hash(path)
        with (directory/f'GW{market.gameweek:02d}_settled.json').open('x') as stream:json.dump(dict(state_after=asdict(state),score=result),stream,indent=2,allow_nan=False)
        rows.append(result);actions.append(action);logs.append(report)
    if state.gameweek!=39:raise ValueError('Incomplete season')
    summary=dict(policy=asdict(cfg),initialisation='ownGW1squad' if opening_ids is None else 'commonGW1roster',
        final_state=asdict(state),net_points=state.total_points,hits=sum(v['hits'] for v in rows),transfers=sum(v['transfers'] for v in rows[1:]),
        chips=[dict(gameweek=v['gameweek'],name=v['chip']) for v in rows if v['chip']],seconds=time.monotonic()-start,
        budget_exhausted_origins=sum(bool(v.get('budget_exhausted',False)) for v in logs),
        scope='Historical38GWcontinuousmanagement with origin quotes and official PGW outcomes; not prospective evidence or full-system promotion')
    with (directory/'summary.json').open('x') as stream:json.dump(summary,stream,indent=2,allow_nan=False)
    return summary


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('decisions','outcomes'):
        p.add_argument('--'+name,type=Path,required=True);p.add_argument('--'+name+'-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--horizon',type=int,default=6);p.add_argument('--no-chips',action='store_true')
    p.add_argument('--seconds',type=float,default=4.);p.add_argument('--solve-seconds',type=float,default=.5);p.add_argument('--max-trials',type=int,default=12);a=p.parse_args()
    if file_hash(a.decisions)!=a.decisions_sha256 or file_hash(a.outcomes)!=a.outcomes_sha256:p.error('Input checksum mismatch')
    d=read_bundle(a.decisions);o=read_bundle(a.outcomes)
    if d.get('schema_version')!=1 or o.get('schema_version')!=1:p.error('Unsupported bundle')
    hidden={int(g):{int(i):v for i,v in row.items()} for g,row in o['weeks'].items()}
    run(d['weeks'],hidden,a.output,policy=Policy(a.horizon,not a.no_chips,a.seconds,a.solve_seconds,a.max_trials),opening_ids=d.get('opening_ids'))
    with (a.output/'provenance.json').open('x') as stream:json.dump(dict(decisions_sha256=file_hash(a.decisions),outcomes_sha256=file_hash(a.outcomes),source_sha256=file_hash(__file__)),stream,indent=2)


if __name__=='__main__':main()
