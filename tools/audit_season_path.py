"""Independent admitted historical-season replay audit; stdlib only.

Checks a full frozen season path and its retained provisional actions. Does not
authenticate archive publication clocks, training recipes or native proposals.
"""
import argparse
from collections import Counter
from datetime import datetime
import gzip
import hashlib
import itertools
import json
from pathlib import Path


def read(path):
    path=Path(path)
    with (gzip.open if path.suffix=='.gz' else open)(path,'rb') as stream:
        raw=stream.read(128*1024**2+1)
    if len(raw)>128*1024**2:raise ValueError('Oversized audit input')
    def invalid(value):raise ValueError('Nonfinite JSON constant')
    return json.loads(raw,parse_constant=invalid)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def advance(state,market,action,blocked=()):
    """Reconstruct integer finance/resources without the engine's prepare code."""
    g=state['gameweek'];by={p['id']:p for p in market['rows']}
    season=state['season']
    assert season in ('2023-24','2024-25','2025-26') and market['season']==season and market['gameweek']==g
    old=dict(state['holdings']);buys=set(action['buys']);sells=set(action['sells'])
    assert len(buys)==len(action['buys']) and len(sells)==len(action['sells'])
    assert sells<=set(old) and not buys&set(old) and not buys&sells
    assert set(old)<=set(by) and buys<=set(by) and all(by[i]['can_buy'] for i in buys)
    ids=set(old)-sells|buys
    assert all(type(by[i]['price_tenths']) is int and by[i]['price_tenths']>0 for i in ids|set(old))
    assert len(ids)==15 and Counter(by[i]['position'] for i in ids)=={1:2,2:5,3:5,4:3}
    if buys or sells or g==1:assert max(Counter(by[i]['team'] for i in ids).values())<=3
    xi=set(action['starters']);bench=set(action['bench'])
    assert len(xi)==len(action['starters'])==11 and len(bench)==len(action['bench'])==4
    assert not xi&bench and xi|bench==ids
    position=Counter(by[i]['position'] for i in xi)
    assert position[1]==1 and position[2]>=3 and position[3]>=2 and position[4]>=1
    assert action['captain'] in xi and action['vice'] in xi and action['captain']!=action['vice']
    assert sum(by[i]['position']==1 for i in bench)==1
    chip=action['chip'];assert chip in (None,'wildcard','freehit','bboost','3xc')
    used=set(map(tuple,state['used_chips']))
    if chip:
        if season=='2023-24':start=21 if chip=='wildcard' and g>=21 else 2 if chip in ('wildcard','freehit') else 1
        else:start=20 if g>=20 and (season=='2025-26' or chip=='wildcard') else 2 if chip in ('wildcard','freehit') else 1
        token=(chip,start)
        assert token not in used and token not in set(map(tuple,blocked))
        assert (g>1 or chip not in ('wildcard','freehit')) and not (chip==state['previous_chip']=='freehit')
        used.add(token)
    received=sum(min(old[i],by[i]['price_tenths'])+max(0,by[i]['price_tenths']-old[i])//2 for i in sells)
    bank=state['bank']+received-sum(by[i]['price_tenths'] for i in buys);assert bank>=0
    ledger={i:q for i,q in old.items() if i not in sells};ledger.update({i:by[i]['price_tenths'] for i in buys})
    free=5 if g==16 and season=='2025-26' else state['free_transfers']
    hits=0 if g==1 or chip in ('wildcard','freehit') else 4*max(0,len(buys)-free)
    cap=2 if season=='2023-24' else 5
    assert 0<=free<=cap
    chip_after=1 if season=='2023-24' else free
    after=1 if g==1 else chip_after if chip in ('wildcard','freehit') else min(cap,max(0,free-len(buys))+1)
    result=dict(state,gameweek=g+1,holdings=sorted((old if chip=='freehit' else ledger).items()),
        bank=state['bank'] if chip=='freehit' else bank,free_transfers=after,
        used_chips=sorted(used),previous_chip=chip)
    return result,ids,hits,len(buys)


def expected(action,xp,g,hits):
    chip=action['chip']
    return (sum(xp[g,i] for i in action['starters'])+
        (2 if chip=='3xc' else 1)*xp[g,action['captain']]+
        (1. if chip=='bboost' else .1)*sum(xp[g,i] for i in action['bench'])-hits)


def actual(action,market,outcomes,hits):
    """Alternative formation-count enumeration preserves outfield bench priority."""
    by={p['id']:p for p in market['rows']};start=action['starters'];bench=action['bench']
    ids=set(start)|set(bench);assert ids<=set(outcomes)
    active=lambda i:outcomes[i]['minutes']>0 or outcomes[i]['cards']>0
    captain=next((i for i in [action['captain'],action['vice']] if outcomes[i]['minutes']>0),None)
    bonus=outcomes[captain]['actual'] if captain is not None else 0.
    parts=dict(base_xi=sum(outcomes[i]['actual'] for i in start),autosub_delta=0.,
        captain_bonus=bonus,bench_boost_points=0.,extra_captain_bonus=bonus if action['chip']=='3xc' else 0.)
    if action['chip']=='bboost':parts['bench_boost_points']=sum(outcomes[i]['actual'] for i in bench)
    else:
        keeper=next(i for i in start if by[i]['position']==1);reserve=next(i for i in bench if by[i]['position']==1)
        if not active(keeper) and active(reserve):parts['autosub_delta']+=outcomes[reserve]['actual']-outcomes[keeper]['actual']
        outbench=[i for i in bench if by[i]['position']!=1]
        formation=[sum(by[i]['position']==p for i in start) for p in (2,3,4)]
        missing=[sum(by[i]['position']==p and not active(i) for i in start) for p in (2,3,4)]
        assert all(outcomes[i]['actual']==0 for i in start if not active(i))
        for mask in itertools.product([1,0],repeat=3):
            incoming=[i for i,k in zip(outbench,mask) if k]
            if not all(active(i) for i in incoming) or len(incoming)>sum(missing):continue
            added=[sum(by[i]['position']==p for i in incoming) for p in (2,3,4)]
            if any(sum(out)==len(incoming) and all(formation[j]-out[j]+added[j]>=minimum for j,minimum in enumerate((3,2,1)))
                   for out in itertools.product(*(range(v+1) for v in missing))):
                parts['autosub_delta']+=sum(outcomes[i]['actual'] for i in incoming);break
    return sum(parts.values())-hits,parts


def same_state(a,b):
    assert dict(a['holdings'])==dict(b['holdings'])
    assert set(map(tuple,a['used_chips']))==set(map(tuple,b['used_chips']))
    for key in ['season','gameweek','bank','free_transfers','previous_chip','total_points']:assert a[key]==b[key]


def audit(decisions,outcomes,season_dir,horizon,opening=None):
    if not __debug__:raise ValueError('Audit requires Python assertions enabled')
    assert type(horizon) is int and 1<=horizon<=8
    assert decisions['schema_version']==outcomes['schema_version']==1
    weeks=decisions['weeks'];assert len(weeks)==38
    state=dict(season=weeks[0]['market']['season'],gameweek=1,holdings=[],bank=1000,free_transfers=0,used_chips=[],previous_chip=None,total_points=0.)
    assert state['season'] in ('2023-24','2024-25','2025-26')
    directory=Path(season_dir);points=hits=transfers=periods=0
    result=read(directory/'summary.json');settings=result['planner_settings']
    assert settings['bench_weight']==.1 and all(settings[k]==0 for k in ['terminal_ft_value','terminal_squad_weight','churn_cost']), 'Unsupported research objective'
    for g,spec in enumerate(weeks,1):
        market=spec['market'];forecast=spec['forecast'];clock=datetime.fromisoformat(market['as_of'])
        assert market['gameweek']==g and clock<datetime.fromisoformat(market['deadline'])
        assert datetime.fromisoformat(forecast['trained_through'])<clock
        assert all(datetime.fromisoformat(forecast[k])<=clock for k in ['feature_cutoff','source_as_of'])
        path=directory/f'GW{g:02d}_decision.json';d=read(path);z=read(directory/f'GW{g:02d}_settled.json')
        assert digest(path)==z['score']['decision_sha256'] and d['gameweek']==g and d['inputs_as_of']==market['as_of']
        if g==16 and state['season']=='2025-26':state['free_transfers']=5
        same_state(state,d['state_before']);assert d['action']==d['provisional_actions'][0]
        assert len(d['provisional_actions'])==min(horizon,39-g)
        xp={(r['gameweek'],r['id']):r['expected_points'] for r in forecast['rows']};current=state;objective=0.
        for target,action in enumerate(d['provisional_actions'],g):
            current,ids,paid,_=advance(current,dict(market,gameweek=target),action,spec['blocked_tokens'])
            if target==1 and opening is not None:assert ids==set(opening)
            objective+=expected(action,xp,target,paid);periods+=1
        assert abs(objective-d['report']['objective'])<1e-6
        old=dict(state['holdings']);by={p['id']:p for p in market['rows']};action=d['action']
        received=sum(min(old[i],by[i]['price_tenths'])+max(0,by[i]['price_tenths']-old[i])//2 for i in action['sells'])
        spent=sum(by[i]['price_tenths'] for i in action['buys']);playing_bank=state['bank']+received-spent
        state,ids,paid,count=advance(state,market,action,spec['blocked_tokens'])
        for key,value in dict(received=received,spent=spent,playing_bank=playing_bank,persisted_bank=state['bank'],next_free_transfers=state['free_transfers'],transfers=count).items():assert z['score'][key]==value
        hidden={int(i):v for i,v in outcomes['weeks'][str(g)].items()}
        net,parts=actual(d['action'],market,hidden,paid)
        assert abs(net-z['score']['net_points'])<1e-8 and z['score']['hits']==paid
        for key,value in parts.items():assert abs(value-z['score'].get(key,0.))<1e-8
        points+=net;hits+=paid;transfers+=count if g>1 else 0;state['total_points']=points
        same_state(state,z['state_after'])
    assert (result['net_points'],result['hits'],result['transfers'])==(points,hits,transfers)
    same_state(state,result['final_state'])
    return dict(deadlines=38,provisional_periods=periods,net_points=points,hits=hits,transfers=transfers,
        status='independently reconciled',scope=state['season']+' integer ledger, frozen decisions, final scoring and retained mean-objective plans; 2024/25 excludes Assistant Manager. No source-authenticity or global-optimality certification')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['decisions','outcomes','season-dir']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--horizon',type=int,required=True);p.add_argument('--opening',type=Path)
    a=p.parse_args();result=audit(read(a.decisions),read(a.outcomes),a.season_dir,a.horizon,read(a.opening) if a.opening else None)
    result['input_sha256']=dict(decisions=digest(a.decisions),outcomes=digest(a.outcomes),opening=digest(a.opening) if a.opening else None)
    print(json.dumps(result,indent=2,allow_nan=False))
if __name__=='__main__':main()
