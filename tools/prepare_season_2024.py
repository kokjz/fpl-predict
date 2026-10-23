"""Offline prior-only 2024/25 reference and restricted-no-AM replay inputs.

Requires trusted, checksummed local history/feature caches and pinned source
receipts. Does not download, tune, promote, or change operational artifacts.
Archive timestamps/corrections remain publisher claims. The evaluator uses final
club identities; those identities never replace the origin's market/forecast.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from deadline_provenance import read_snapshot,replay_event_assignments
from season_sources import calendar,restricted_2024_bootstrap
from season_engine import Market
from horizon_forecast import project,Horizon
from fpl_model import ForecastModel,CORE_FEATURES,STATS,fit_estimator,sample_weights


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def eligibility(player):
    """Older API lacks can_select: retain explicit, conservative status proxy."""
    if 'can_select' in player:
        if type(player['can_select']) is not bool:raise ValueError('Unknown purchase eligibility')
        return player['can_select'],'archived_can_select'
    if player['status'] not in ('a','d','i','s','u','n'):raise ValueError('Unknown historical status')
    return player['status'] not in ('u','n'),'legacy_status_proxy_excluding_u_n'


def origin_outcomes(elements,actual,fixtures,team_names):
    """Every listed identity accounted for, including true blanks/club changes."""
    hidden={};changes=[]
    for p in elements:
        ar=actual[actual.element.eq(p['id'])]
        clubs=set(ar.team.map(team_names)) if len(ar) else {p['team']}
        if None in clubs or any(pd.isna(c) for c in clubs):raise ValueError('Unknown evaluator club')
        expected=set(fixtures.loc[fixtures.team_h.isin(clubs)|fixtures.team_a.isin(clubs),'fixture'])
        if set(ar.fixture)!=expected or ar.fixture.duplicated().any():raise ValueError('Incomplete/conflicting listed-player outcome coverage')
        if len(ar) and clubs!={p['team']}:
            changes.append(dict(id=p['id'],origin_team=p['team'],evaluator_teams=sorted(map(int,clubs)),fixtures=sorted(map(int,ar.fixture))))
        hidden[p['id']]=dict(actual=float(ar.total_points.sum()),minutes=float(ar.minutes.sum()),cards=float(ar.yellow_cards.sum()+ar.red_cards.sum()))
    return hidden,changes


def prepare(spec,output,*,trust_local_cache=False):
    if not trust_local_cache:raise ValueError('Explicit trust required before executable cache/model loading')
    if spec['season']!='2024-25' or spec['policy_space']!='restricted_no_assistant_manager':raise ValueError('Unsupported historical scope')
    out=Path(output).resolve();repo=Path(__file__).resolve().parents[1]
    if out.is_relative_to(repo) or out.exists():raise ValueError('Require new private output directory')
    for e in spec['inputs'].values():
        if digest(e['path'])!=e['sha256']:raise ValueError('Input checksum differs')
    get=lambda key:Path(spec['inputs'][key]['path']);tick=time.monotonic()
    d=pd.read_pickle(get('history'));x=pd.read_pickle(get('features'))
    if not d.index.equals(x.index):raise ValueError('History/features alignment differs')
    t=d.season.lt('2024-25')
    if set(d.loc[t,'season'])!={'2020-21','2021-22','2022-23','2023-24'}:raise ValueError('Fixed four-year prior training scope differs')
    cutoff=pd.to_datetime(d.loc[t,'cutoff'],utc=True);latest=pd.to_datetime(x.loc[t,'source_max_ts'],utc=True)
    if not (latest.isna()|latest.lt(cutoff-pd.Timedelta(hours=3))).all():raise ValueError('Training feature source is late')
    p=pd.read_csv(get('merged'));p=p[p.position.isin(['GK','GKP','DEF','MID','FWD'])].copy()
    if p.duplicated(['element','fixture']).any():raise ValueError('Conflicting outcome rows')
    correction=pd.read_csv(get('correction'));corrections=[]
    if set(correction.element)!={123}:raise ValueError('Undeclared correction identity')
    for row in correction.to_dict('records'):
        mask=p.element.eq(row['element'])&p.fixture.eq(row['fixture'])
        if mask.sum()!=1:raise ValueError('Correction key coverage differs')
        changed={}
        for key,value in row.items():
            if key in p and key in {*STATS,'total_points','yellow_cards','red_cards','goals_conceded','own_goals','penalties_missed','penalties_saved','starts'}:
                old=p.loc[mask,key].iloc[0]
                if not (pd.isna(old) and pd.isna(value)) and old!=value:changed[key]=dict(before=old.item() if hasattr(old,'item') else old,after=value);p.loc[mask,key]=value
        if changed:corrections.append(dict(element=row['element'],fixture=row['fixture'],changes=changed))
    if [r['fixture'] for r in corrections]!=[239]:raise ValueError('Unexpected correction set; review before admission')
    raw=pd.read_csv(get('players'));raw=raw[raw.element_type.isin([1,2,3,4])];codes=dict(zip(raw.id,raw.code))
    sums=p.groupby('element').total_points.sum().reindex(raw.id,fill_value=0)
    if not np.array_equal(sums.to_numpy(),raw.total_points.to_numpy()):raise ValueError('Season totals do not reconcile')
    teams=pd.read_csv(get('teams'));team_ids=dict(zip(teams.name,teams.id))
    f=p[['fixture','GW','team','opponent_team','was_home','kickoff_time']].drop_duplicates();f['team_id']=f.team.map(team_ids)
    f['team_h']=np.where(f.was_home,f.team_id,f.opponent_team);f['team_a']=np.where(f.was_home,f.opponent_team,f.team_id)
    fixtures=f[['fixture','GW','team_h','team_a','kickoff_time']].drop_duplicates()
    if len(fixtures)!=380 or fixtures.fixture.duplicated().any() or set(fixtures.GW)!=set(range(1,39)):raise ValueError('Final380fixture identity audit fails')
    # The derived correction affects origin features only after its match cutoff.
    history=d[d.season.eq('2024-25')].copy()
    for c in corrections:
        mask=history.element.eq(c['element'])&history.fixture.eq(c['fixture']);row=p[p.element.eq(c['element'])&p.fixture.eq(c['fixture'])].iloc[0]
        if mask.sum()!=1:raise ValueError('Correction cannot be matched to history')
        for key in STATS:
            if key in row:history.loc[mask,key]=row[key]
        history.loc[mask,'points_core']=row.total_points;history.loc[mask,'played']=float(row.minutes>0);history.loc[mask,'sixty']=float(row.minutes>=60)
    metadata=dict(version='standing-prior4-no-dc-2024-v1',training_rows=int(t.sum()),training_scope='2020/21..2023/24 only',trained_through=(pd.to_datetime(d.loc[t,'ts'],utc=True).max()+pd.Timedelta(hours=3)).isoformat(),approval='Historical research reference, no deployment promotion')
    out.mkdir(parents=True);models={};fit_start=time.monotonic()
    with threadpool_limits(limits=2):
        for head,target in [('core','points_core'),('minutes','minutes'),('played','played'),('sixty','sixty')]:
            models[head]=fit_estimator('hgb7',x.loc[t,CORE_FEATURES],d.loc[t,target],sample_weights(d[t]));print('Fitted prior-only',head,flush=True)
    model=ForecastModel(models['core'],'hgb7',1.,models['minutes'],models['played'],models['sixty'],None,'none',{str(pos):[0.,0.] for pos in range(1,5)},metadata)
    joblib.dump(model,out/'prior_model.joblib');model_hash=digest(out/'prior_model.joblib');fit_seconds=time.monotonic()-fit_start
    markets=json.loads(get('markets').read_text());calendars=json.loads(get('calendars').read_text());updates=json.loads(get('updates').read_text())
    if len(markets['market_origins'])!=38 or len(calendars['entries'])!=38:raise ValueError('Incomplete origins')
    decisions=dict(schema_version=1,weeks=[]);hidden=dict(schema_version=1,weeks={});audits=[]
    for gw in range(1,39):
        e=next(z for z in markets['market_origins'] if z['gameweek']==gw);ce=next(z for z in calendars['entries'] if z['gameweek']==gw)
        b=read_snapshot(Path(spec['market_root'])/e['file'],e['compressed_sha256']);b,info,bridge,rule=restricted_2024_bootstrap(b,gw,e['captured_at'])
        if any(codes.get(z['id'])!=z['code'] for z in b['elements']):raise ValueError('Stable identity bridge differs')
        f=calendar(ce,spec['calendar_root'],audit_only=True)
        relevant=[u for u in updates if pd.Timestamp(u['available_at'])>pd.Timestamp(ce['publication_claim'])]
        assignment=replay_event_assignments(f,ce['publication_claim'],relevant,e['captured_at']);f['event']=f.id.map(assignment.set_index('id').event)
        if ce['captured_at']!=e['captured_at']:raise ValueError('Calendar/market origin differs')
        rows=[];eligibility_sources={}
        for z in b['elements']:
            can_buy,source=eligibility(z);eligibility_sources[source]=eligibility_sources.get(source,0)+1
            rows.append(dict(id=z['id'],position=z['element_type'],team=str(z['team']),price_tenths=z['now_cost'],can_buy=can_buy,status=z['status']))
        m=Market.create('2024-25',gw,info['deadline'],e['captured_at'],rows)
        with threadpool_limits(limits=2):
            horizon,projection=project(model,history,m,f,through=min(38,gw+5),trained_through=metadata['trained_through'],source_as_of=m.as_of,model_id=metadata['version'],source_hashes=dict(bootstrap=e['compressed_sha256'],calendar=ce['sha256'],updates=spec['inputs']['updates']['sha256'],model=model_hash,history=spec['inputs']['history']['sha256'],correction=spec['inputs']['correction']['sha256'],protocol=spec['inputs']['protocol']['sha256']))
        zero={z['id'] for z in b['elements'] if z.get('chance_of_playing_next_round')==0 and z['status']!='a'}
        provenance=dict(horizon.provenance);provenance['source_hashes']=dict(provenance['source_hashes']);provenance['model_id']+='/official-zero-origin-v1'
        rs=[dict(v,expected_points=0. if v['gameweek']==gw and v['id'] in zero else v['expected_points']) for v in horizon.forecasts];hs=Horizon.create(m,rs,**provenance)
        decisions['weeks'].append(dict(market=dict(season=m.season,gameweek=gw,deadline=m.deadline,as_of=m.as_of,rows=rows),forecast=dict(rows=[dict(v) for v in hs.forecasts],**provenance),blocked_tokens=[]))
        truth=fixtures[fixtures.GW.eq(gw)];ar=p[p.GW.eq(gw)];values,changes=origin_outcomes(b['elements'],ar,truth,team_ids);hidden['weeks'][gw]=values
        planned=set(f.loc[f.event.eq(gw),'id']);actual=set(truth.fixture)
        audits.append(dict(gameweek=gw,listed=len(rows),rule=rule,eligibility_sources=eligibility_sources,official_zero=len(zero),projection=projection,club_changes_evaluator_only=changes,forecast_only_fixtures=sorted(map(int,planned-actual)),outcome_only_fixtures=sorted(map(int,actual-planned))))
        print('Prepared origin',gw,len(rows),'players',flush=True)
    for name,value in [('decisions',decisions),('outcomes',hidden)]:
        with gzip.open(out/(name+'.json.gz'),'xt') as f:json.dump(value,f,separators=(',',':'),allow_nan=False)
    report=dict(status='prepared38origins_restricted_no_AM',model=metadata,model_sha256=model_hash,fit_seconds=fit_seconds,seconds=time.monotonic()-tick,origins=audits,corrections=corrections,season_totals_reconciled=len(raw),fixture_count=380,inputs=spec['inputs'],bundles={n:digest(out/(n+'.json.gz')) for n in ['decisions','outcomes']},model_promotion=False,source_limitations=['Publisher archive/commit/date claims are not independently witnessed','Origin snapshots up to24h before actual deadline, no later news imported','Legacy status-based purchase eligibility is an explicit proxy where API field absent','Conditional rescheduling unresolved at origin is not forecast with future cup results','Official final per-player histories correct one stale merged row; original files preserved','Prior-only reference on reused research years, not saved champion backcast'])
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--trust-local-cache',action='store_true');a=p.parse_args()
    if digest(a.manifest)!=a.manifest_sha256:p.error('Manifest checksum differs')
    prepare(json.loads(a.manifest.read_text()),a.output,trust_local_cache=a.trust_local_cache)


if __name__=='__main__':main()
