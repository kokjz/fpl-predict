"""Exact expected legal autosub/vice value for a fixed 15-player squad.

The primary distribution assumes independent player-GW appearances and constant
conditional mean returns. This is a transparent research assumption, not a learned
joint distribution or a replacement for the production selector.
"""
from functools import lru_cache
from itertools import combinations, permutations, product
import numpy as np
from selection_benchmark import legal, score


def validate(players):
    d=sorted(players,key=lambda r:r['id'])
    if not legal(d):raise ValueError('Require a legal 15-player squad')
    for r in d:
        p=r['p_play'];q=r['conditional_points'];xp=r['expected_points']
        if not np.isfinite([p,q,xp]).all() or not 0<=p<=1 or not np.isclose(xp,p*q,rtol=0,atol=1e-9):
            raise ValueError('Incoherent probability/conditional expectation')
    return d


def poisson_binomial_missing(probabilities):
    result=np.array([1.])
    for p in probabilities:result=np.convolve(result,[p,1-p])
    return result


@lru_cache(maxsize=64)
def bench_table(formation,positions):
    """Selected bench indicators for missing counts and bench appearance masks.

    Lexicographic bench priority matches the public realised scorer. Missing
    starters retain their formation slots until a legal replacement is found.
    """
    missing=list(product(*(range(n+1) for n in formation)))
    masks=list(product((0,1),repeat=3));table=np.zeros((len(missing),8,3))
    for k,counts in enumerate(missing):
        for j,active in enumerate(masks):
            for code in range(7,-1,-1):
                selected=tuple((code>>(2-i))&1 for i in range(3))
                if any(selected[i]>active[i] for i in range(3)):continue
                incoming=tuple(sum(selected[i] for i in range(3) if positions[i]==p) for p in (2,3,4))
                n=sum(incoming)
                if n>sum(counts):continue
                feasible=any(sum(out)==n and all(formation[i]-out[i]+incoming[i]>=minimum
                    for i,minimum in enumerate((3,2,1))) for out in product(*(range(c+1) for c in counts)))
                if feasible:
                    table[k,j]=selected;break
    table.setflags(write=False)
    return table


def bench_value(start,bench):
    formation=tuple(sum(r['position']==p for r in start) for p in (2,3,4))
    distributions=[poisson_binomial_missing([r['p_play'] for r in start if r['position']==p]) for p in (2,3,4)]
    missing=np.einsum('i,j,k->ijk',*distributions).reshape(-1)
    p=np.array([r['p_play'] for r in bench]);q=np.array([r['conditional_points'] for r in bench])
    masks=np.array(list(product((0,1),repeat=3)))
    weights=np.prod(np.where(masks,p,1-p),axis=1)
    table=bench_table(formation,tuple(r['position'] for r in bench))
    inclusion=np.einsum('m,b,mbi->i',missing,weights,table,optimize=True)
    return float(inclusion@q)


def objective(selection,players):
    """Expected score under the primary independent marginal model."""
    d=validate(players);by={r['id']:r for r in d}
    # Reuse full legal-selection guards without realised outcomes.
    score(selection,by,{r['id']:dict(actual=0.,minutes=0.,cards=0.) for r in d})
    start=[by[i] for i in selection['starters']];bench=[by[i] for i in selection['bench']]
    out=[r for r in start if r['position']!=1];res=[r for r in bench if r['position']!=1]
    keeper=next(r for r in start if r['position']==1);reserve=next(r for r in bench if r['position']==1)
    c=by[selection['captain']];v=by[selection['vice']]
    return float(sum(r['expected_points'] for r in start)+bench_value(out,res)+
        (1-keeper['p_play'])*reserve['expected_points']+c['expected_points']+(1-c['p_play'])*v['expected_points'])


def select(players):
    """Enumerate every legal XI/bench order and optimise captain/vice exactly.

    Bench expectation depends only on the outfield XI; compute it once for both
    keeper choices. All tie resolution follows sorted IDs and permutation order.
    """
    d=validate(players);out=[r for r in d if r['position']!=1];keepers=[r for r in d if r['position']==1]
    ids=np.array([r['id'] for r in d]);p=np.array([r['p_play'] for r in d]);xp=np.array([r['expected_points'] for r in d])
    bonus=xp[:,None]+(1-p[:,None])*xp[None,:];np.fill_diagonal(bonus,-np.inf)
    byid={r['id']:i for i,r in enumerate(d)};best=None
    for ix in combinations(range(13),10):
        starters=[out[i] for i in ix]
        counts={pos:sum(r['position']==pos for r in starters) for pos in (2,3,4)}
        if counts[2]<3 or counts[3]<2 or counts[4]<1:continue
        used=set(ix);reserves=[out[i] for i in range(13) if i not in used]
        bench_best=None
        for ordered in permutations(reserves):
            value=bench_value(starters,ordered)
            if bench_best is None or value>bench_best[0]+1e-12:bench_best=(value,ordered)
        for keeper in keepers:
            reserve=next(r for r in keepers if r['id']!=keeper['id'])
            eleven=sorted([*starters,keeper],key=lambda r:r['id']);ii=[byid[r['id']] for r in eleven]
            pair=bonus[np.ix_(ii,ii)];ci,vi=np.unravel_index(np.argmax(pair),pair.shape)
            value=sum(r['expected_points'] for r in eleven)+bench_best[0]+(1-keeper['p_play'])*reserve['expected_points']+pair[ci,vi]
            if best is None or value>best['expected_points']+1e-12:
                best=dict(starters=[r['id'] for r in eleven],bench=[r['id'] for r in bench_best[1]]+[reserve['id']],
                    captain=eleven[ci]['id'],vice=eleven[vi]['id'],expected_points=float(value))
    if best is None:raise ValueError('No legal XI')
    return best


def positive_dependence_stress(selection,players,rho=.25):
    """Fixed-plan expectation in a mixture with a shared-uniform appearance shock.

    Both distributions preserve every marginal p; the common shock is deliberately
    a stress model, not an estimated football correlation. Do not optimise rho.
    """
    d=validate(players)
    if not 0<=rho<=1:raise ValueError('Invalid stress mixture')
    by={r['id']:r for r in d};boundaries=sorted({0.,1.,*(r['p_play'] for r in d)})
    common=0.
    for lo,hi in zip(boundaries,boundaries[1:]):
        u=(lo+hi)/2
        outcomes={r['id']:dict(actual=r['conditional_points'] if u<r['p_play'] else 0.,
            minutes=1. if u<r['p_play'] else 0.,cards=0.) for r in d}
        common+=(hi-lo)*score(selection,by,outcomes)['net_points']
    return float((1-rho)*objective(selection,d)+rho*common)
