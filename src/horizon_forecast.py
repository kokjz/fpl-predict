"""Origin-frozen forecast grids, built without observing future fixtures/results."""
from dataclasses import dataclass
from types import MappingProxyType
import numpy as np
import pandas as pd
from availability_evidence import utc
from fpl_model import FeatureStore


@dataclass(frozen=True)
class Horizon:
    season:str
    origin:int
    as_of:str
    gameweeks:tuple
    forecasts:tuple
    provenance:object

    @classmethod
    def create(cls,market,rows,*,trained_through,feature_cutoff,source_as_of,model_id,source_hashes=None):
        if utc(trained_through)>=utc(market.as_of):raise ValueError('Model trained after forecast origin')
        if utc(feature_cutoff)!=utc(market.as_of) or utc(source_as_of)>utc(market.as_of):raise ValueError('Feature/source origin differs or is late')
        if not str(model_id).strip():raise ValueError('Missing model identity')
        rows=list(rows)
        required={'gameweek','id','expected_points'}
        if any(set(r)!=required for r in rows):raise ValueError('Only origin-frozen forecast fields allowed')
        weeks=sorted({r['gameweek'] for r in rows});ids={p['id'] for p in market.players}
        if not weeks or weeks!=list(range(market.gameweek,weeks[-1]+1)) or weeks[-1]>38 or len(weeks)>8:raise ValueError('Require contiguous1–8GWorigin horizon')
        keys=[(r['gameweek'],r['id']) for r in rows]
        if len(keys)!=len(set(keys)) or set(keys)!={(g,i) for g in weeks for i in ids}:raise ValueError('Missing/duplicate forecast coverage')
        frozen=[]
        for r in sorted(rows,key=lambda v:(v['gameweek'],v['id'])):
            if type(r['gameweek']) is not int or type(r['id']) is not int or not np.isfinite(r['expected_points']):raise ValueError('Invalid forecast values')
            frozen.append(MappingProxyType(dict(r)))
        return cls(market.season,market.gameweek,market.as_of,tuple(weeks),tuple(frozen),MappingProxyType(dict(
            trained_through=utc(trained_through).isoformat(),feature_cutoff=utc(feature_cutoff).isoformat(),source_as_of=utc(source_as_of).isoformat(),
            model_id=model_id,source_hashes=MappingProxyType(dict(source_hashes or {})))))

    def values(self):return {(r['gameweek'],r['id']):float(r['expected_points']) for r in self.forecasts}


def project(model,history,market,fixtures,*,through,trained_through,source_as_of,model_id,source_hashes=None):
    """All future fixtures share origin form; later actual form is never fed back.

    Fixtures must come from the hash-verified as-of calendar adapter. Current
    roster metadata maps player IDs directly within the season. Team IDs in the
    calendar/roster must use the same namespace. Missing new registrations are
    excluded until a subsequent origin actually lists them.
    """
    if through<market.gameweek or through>min(38,market.gameweek+7):raise ValueError('Invalid forecast horizon')
    if getattr(model,'requires_availability',False):raise ValueError('Conditional experimental models need separately admitted availability adapters')
    origin=utc(market.as_of)
    if utc(trained_through)>=origin or utc(source_as_of)>origin:raise ValueError('Late training/calendar')
    required={'id','event','team_h','team_a','kickoff_time'}
    if required-set(fixtures):raise ValueError('Missing calendar fields')
    if fixtures.id.duplicated().any():raise ValueError('Duplicate fixture')
    if 'team_id' not in history or 'opponent_team' not in history:raise ValueError('History needs original fixture club identities')
    # Market.team is an audited numeric-ID string for this adapter, not a display name.
    targets=[]
    for p in market.players:
        try:team=int(p['team'])
        except (TypeError,ValueError):raise ValueError('Projection adapter requires numeric club-ID strings') from None
        for f in fixtures.itertuples():
            if pd.isna(f.event) or not market.gameweek<=f.event<=through or team not in (f.team_h,f.team_a):continue
            home=team==f.team_h
            targets.append(dict(element=p['id'],season=market.season,fixture=int(f.id),GW=int(f.event),pos=p['position'],team_id=team,
                opponent_team=int(f.team_a if home else f.team_h),was_home=home,cutoff=origin,kickoff_time=f.kickoff_time))
    out={(g,p['id']):0. for g in range(market.gameweek,through+1) for p in market.players}
    source_max=None
    if targets:
        t=pd.DataFrame(targets);x=FeatureStore(history).transform(t)
        ts=pd.to_datetime(x.source_max_ts,utc=True)
        if (ts.notna()&ts.ge(origin-pd.Timedelta(hours=3))).any():raise ValueError('Future feature source')
        source_max=ts.max().isoformat() if ts.notna().any() else None
        prediction=model.predict(x,t.pos)
        if not prediction.index.equals(x.index) or not np.isfinite(prediction.expected_points).all():raise ValueError('Invalid model predictions')
        for row,value in zip(t.itertuples(),prediction.expected_points):out[(int(row.GW),int(row.element))]+=float(value)
    rows=[dict(gameweek=g,id=i,expected_points=v) for (g,i),v in out.items()]
    horizon=Horizon.create(market,rows,trained_through=trained_through,feature_cutoff=market.as_of,source_as_of=source_as_of,model_id=model_id,source_hashes=source_hashes)
    report=dict(fixture_rows=len(targets),player_gw_rows=len(rows),source_max_ts=source_max,
        zero_fixture_scope='Zero means no fixture in the origin-known calendar; future rearrangements are unknown, not guaranteed actual blanks',
        approximation='Origin form/roster/availability held fixed; multiweek projections not independently validated')
    return horizon,report
