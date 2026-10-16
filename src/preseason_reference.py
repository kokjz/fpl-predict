"""Explicit cold-start research references; no estimator or registry mutation.

Prior history uses stable codes, never season-local player/club IDs. Historical
point rates are a deliberately simple benchmark, not trained carryover features
passed into a model fitted on season-reset features.
"""
import numpy as np
import pandas as pd
from availability_evidence import utc
from fpl_model import ew
from horizon_forecast import Horizon


def previous_season(season):
    try:
        start, end = season.split('-')
        if len(start) != 4 or len(end) != 2 or (int(start)+1) % 100 != int(end): raise ValueError()
        return f'{int(start)-1}-{int(start)%100:02d}'
    except (AttributeError, TypeError, ValueError):
        raise ValueError('Require YYYY-YY season') from None


def apply(base, market, fixtures, history, roster, *, source_as_of, source_hashes=None, official=False):
    """Blend a fixed prior-season rate into an admitted origin-frozen grid.

    history: season, code, fixture, ts, position, points_core, dc_hit (NaN when
    that award was not observed). roster: id/code/position and optional ep_next,
    extracted from the *same* pinned deadline bootstrap used for market.

    Carryover uses at most24 latest prior-season records, match half-life4,
    shrinkage2 toward the reset forecast's per-fixture mean. Its weight is
    max(0,1-current_completed_records/6). Position changes/new players retain
    reset forecasts. Missing prior DC uses an explicit .12 award prior for
    outfield players, zero for GK. Current-season data is used only to count
    available records; it never becomes a prior-season target.

    official=True replaces ONLY the origin GW total with finite ep_next for
    players with an origin-known fixture. Never multiply this GW-total by a
    double's fixture count or propagate it to later GWs. Unknown stays unknown.
    """
    origin = utc(market.as_of)
    if (base.season, base.origin, utc(base.as_of)) != (market.season, market.gameweek, origin):
        raise ValueError('Base horizon and market origin differ')
    if not utc(base.provenance['source_as_of']) <= utc(source_as_of) <= origin: raise ValueError('Late/inconsistent source')
    prior_season = previous_season(market.season)
    need = {'season','code','fixture','ts','position','points_core','dc_hit'}
    if need-set(history) or {'id','code','position'}-set(roster): raise ValueError('Missing stable-code history/roster')
    h = history.loc[:,sorted(need)].copy(); h['ts'] = pd.to_datetime(h.ts, utc=True, errors='raise')
    if h.ts.isna().any() or h.duplicated(['season','code','fixture']).any(): raise ValueError('Missing time/duplicate history')
    for column in ('code','fixture','position'):
        a=pd.to_numeric(h[column],errors='raise')
        if not np.isfinite(a).all() or not a.gt(0).all() or not a.eq(a.round()).all(): raise ValueError('Invalid history identity')
    if not h.position.isin([1,2,3,4]).all(): raise ValueError('Invalid history position')
    # Exclude later/current targets before consulting point values. Mutation of
    # future results must not change an earlier forecast or its validity.
    h=h[h.ts.lt(origin-pd.Timedelta(hours=3)) & h.season.isin([prior_season,market.season])]
    if not np.isfinite(h.points_core).all() or not h.dc_hit.dropna().isin([0,1]).all(): raise ValueError('Invalid admitted points')
    roster=roster.copy()
    for column in ('id','code','position'):
        a=pd.to_numeric(roster[column],errors='raise')
        if not np.isfinite(a).all() or not a.gt(0).all() or not a.eq(a.round()).all(): raise ValueError('Invalid roster identity')
    if roster.id.duplicated().any() or roster.code.duplicated().any(): raise ValueError('Ambiguous stable identity')
    by=market.indexed()
    if set(roster.id)!=set(by) or any(r.position!=by[r.id]['position'] for r in roster.itertuples()): raise ValueError('Roster differs from market')
    if {'id','event','team_h','team_a'}-set(fixtures) or fixtures.id.duplicated().any(): raise ValueError('Invalid calendar')
    if set(base.values())!={(g,i) for g in base.gameweeks for i in by}: raise ValueError('Base coverage differs')
    values=base.values(); reports=[]; source_times=[]
    for r in roster.itertuples():
        try: club=int(by[r.id]['team'])
        except (TypeError,ValueError): raise ValueError('Numeric calendar club IDs required') from None
        counts={g:int((fixtures.event.eq(g)&(fixtures.team_h.eq(club)|fixtures.team_a.eq(club))).sum()) for g in base.gameweeks}
        past=h[h.code.eq(r.code)].sort_values(['ts','fixture'])
        prior=past[past.season.eq(prior_season)].tail(24)
        current=past[past.season.eq(market.season)]
        n=len(current); alpha=max(0.,1.-n/6.)
        compatible=bool(len(prior) and prior.position.iloc[-1]==r.position)
        # A changed position is not silently translated using old scoring.
        if compatible: prior=prior[prior.position.eq(r.position)]
        else: alpha=0.
        for g,count in counts.items():
            if not count:
                if values[g,r.id] != 0.: raise ValueError('Nonzero base for origin-known blank')
                continue
            if alpha:
                dc=np.where(prior.dc_hit.notna(),prior.dc_hit,0. if r.position==1 else .12)
                rate=ew(prior.points_core.to_numpy()+2*dc,4,values[g,r.id]/count,2.)
                values[g,r.id]=(1-alpha)*values[g,r.id]+alpha*max(0.,float(rate))*count
        official_used=False
        if official and counts[market.gameweek] and hasattr(r,'ep_next') and not pd.isna(r.ep_next):
            value=float(r.ep_next)
            if not np.isfinite(value): raise ValueError('Nonfinite official projection')
            values[market.gameweek,r.id]=value; official_used=True
        if n: source_times.append(current.ts.max())
        if alpha: source_times.append(prior.ts.max())
        reports.append(dict(id=int(r.id),stable_code=int(r.code),current_records=n,prior_records=len(prior) if compatible else 0,
                            carryover_weight=alpha,position_compatible=compatible,official_origin_used=official_used))
    hashes=dict(base.provenance['source_hashes'])
    if any(k in hashes and hashes[k]!=v for k,v in (source_hashes or {}).items()): raise ValueError('Conflicting base source hash')
    hashes.update(source_hashes or {})
    model_id=str(base.provenance['model_id'])+('/carryover-official-origin-v1' if official else '/carryover-v1')
    result=Horizon.create(market,[dict(gameweek=g,id=i,expected_points=v) for (g,i),v in values.items()],
        trained_through=base.provenance['trained_through'],feature_cutoff=market.as_of,source_as_of=source_as_of,model_id=model_id,source_hashes=hashes)
    return result,dict(players=reports,source_max_ts=max(source_times).isoformat() if source_times else None,
        scope='Fixed research reference; rate carryover is fixture-neutral and ignores role/club/fitness changes; no model promotion',
        official_scope='Origin GW only, already a player-GW total; never extended to future targets',
        missing_dc='Unobserved previous-season DC uses explicit .12 award prior for outfield, zero for GK; not observed evidence')
