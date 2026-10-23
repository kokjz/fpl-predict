"""Independent stdlib native proposal audit for admitted historical profiles.

No planner, ML package or external solver imports. Integer ledger/resource rules
are reconstructed by audit_season_path; XI objectives use separate positional
prefix enumeration. Native timeouts remain expected attempts, not scored plans.
"""
import argparse,gzip,json,math
from pathlib import Path
from collections import Counter
from audit_season_path import advance,expected


def mean_selection(ids,players,xp,g):
    pools={p:sorted((i for i in ids if players[i]['position']==p),key=lambda i:(-xp[g,i],i)) for p in (1,2,3,4)};best=None
    for keeper in pools[1]:
        for defenders in range(3,6):
            for mids in range(2,6):
                forwards=10-defenders-mids
                if not 1<=forwards<=3:continue
                start=[keeper,*pools[2][:defenders],*pools[3][:mids],*pools[4][:forwards]]
                if len(start)!=11:continue
                cap=max(start,key=lambda i:(xp[g,i],-i));value=sum(xp[g,i] for i in start)
                if best is None or value>best[0]:
                    vice=next(i for i in sorted(start,key=lambda i:(-xp[g,i],i)) if i!=cap)
                    best=(value,dict(starters=start,bench=sorted(ids-set(start)),captain=cap,vice=vice))
    assert best is not None
    return best[1]


def validate(request,reply):
    assert set(request)=={'schema_version','market','state','xp','through','chip_schedule','opening_ids','seconds'} and request['schema_version']==1
    assert set(request['state'])=={'season','gameweek','holdings','bank','free_transfers','used_chips','previous_chip'}
    market=request['market'];state=dict(request['state'],total_points=0.);g=state['gameweek'];end=request['through']
    assert market['season']==state['season'] and state['season'] in ('2024-25','2025-26') and market['gameweek']==g and g<=end<=min(38,g+5)
    players={p['id']:p for p in market['rows']};assert len(players)==len(market['rows'])
    assert all(set(p)=={'id','position','team','price_tenths','can_buy'} for p in market['rows'])
    xp={(w,i):v for w,i,v in request['xp']};assert len(xp)==len(request['xp']) and set(xp)=={(w,i) for w in range(g,end+1) for i in players} and all(math.isfinite(v) for v in xp.values())
    if reply['status']!='completed':
        assert (reply.get('error_type'),reply.get('message'))==('ValueError','No feasible native incumbent');return 0
    assert reply['native_status'] in ('HighsModelStatus.kOptimal','HighsModelStatus.kTimeLimit') and math.isfinite(reply['objective'])
    seen=set();rosters={w:set() for w in range(g,end+1)}
    for p in reply['picks']:
        w=p['week'];i=p['id'];assert w in rosters and i in players and (w,i) not in seen and type(p['squad']) is int and p['squad'] in (0,1);seen.add((w,i))
        if p['squad']:rosters[w].add(i)
    value=0.
    for w in range(g,end+1):
        ids=rosters[w];assert len(ids)==15;old=dict(state['holdings']);selection=mean_selection(ids,players,xp,w);chip=request['chip_schedule'].get(str(w))
        action=dict(buys=sorted(ids-set(old)),sells=sorted(set(old)-ids),chip=chip,**selection)
        free=5 if state['season']=='2025-26' and w==16 else state['free_transfers']
        if w==g and request['opening_ids'] is not None:assert ids==set(request['opening_ids'])
        state,actual_ids,hits,n=advance(state,dict(market,gameweek=w),action)
        assert actual_ids==ids;stats=reply['statistics'][str(w)]
        assert abs(stats['ft']-free)<1e-5 and abs(stats['pt']*4-hits)<1e-5 and abs(stats['itb']*10-state['bank'])<1e-5
        value+=expected(action,xp,w,hits)
    assert value>=reply['objective']-1e-5
    if reply['native_status']=='HighsModelStatus.kOptimal':assert abs(value-reply['objective'])<1e-5
    return end-g+1


def audit(path):
    if not __debug__:raise ValueError('Assertions must be enabled')
    calls=completed=failed=periods=0;errors=Counter()
    with gzip.open(path,'rt') as stream:
        for line in stream:
            r=json.loads(line);calls+=1;assert r['index']==calls;periods+=validate(r['request'],r['reply'])
            if r['reply']['status']=='completed':completed+=1
            else:failed+=1;errors[r['reply']['error_type']+':'+r['reply']['message']]+=1
    return dict(calls=calls,completed=completed,expected_failures=failed,completed_provisional_periods=periods,errors=dict(errors),status='independently_reconciled',scope='Every completed Solio reply: integer finance, chip inventory and separate common-mean selection objective; no source timestamp or global-optimum certification')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trace',type=Path,required=True);a=p.parse_args();print(json.dumps(audit(a.trace),indent=2))


if __name__=='__main__':main()
