"""Offline 2023/24 admission and fixed prior-only historical reference.

No downloads, tuning or operational artifact changes. As-of calendar views are
whitelisted; final fixtures/results remain evaluator-only. Git/archive clocks
are publisher claims. This reused validation year is not an untouched test.
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
from deadline_provenance import read_snapshot,extract_bootstrap
from season_sources import COLUMNS
from season_engine import Market,rules_for
from horizon_forecast import project,Horizon
from fpl_model import ForecastModel,CORE_FEATURES,fit_estimator,sample_weights
from prepare_season_2024 import eligibility,origin_outcomes


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def admitted_origin(spec,e,ce,codes):
    root=Path(spec['source_root']);b=read_snapshot(root/e['file'],e['compressed_sha256'])
    info,_=extract_bootstrap(b,'2023-24',e['gameweek'],e['captured_at'])
    if info['deadline']!=pd.Timestamp(e['deadline']).isoformat():raise ValueError('Origin deadline differs')
    if any(codes.get(z['id'])!=z['code'] for z in b['elements']):raise ValueError('Stable identity bridge differs')
    # Missing executable chip metadata requires separately dated official rules.
    settings=b['game_settings'];expected=dict(squad_squadplay=11,squad_squadsize=15,squad_team_limit=3,squad_total_spend=1000,transfers_cap=20,transfers_sell_on_fee=.5)
    if any(settings.get(k)!=v for k,v in expected.items()):raise ValueError('Historical financial settings differ')
    if 'max_extra_free_transfers' in settings and settings['max_extra_free_transfers']!=1:raise ValueError('Historical FT cap differs')
    path=root/ce['file']
    if digest(path)!=ce['sha256'] or ce['as_of']!=e['captured_at'] or pd.Timestamp(ce['source_clock'])>=pd.Timestamp(e['captured_at']):raise ValueError('Calendar checksum/origin differs')
    f=pd.read_csv(path)
    if list(f)!=COLUMNS or f.id.duplicated().any():raise ValueError('Calendar view must contain only whitelisted fixture metadata')
    rows=[dict(id=z['id'],position=z['element_type'],team=str(z['team']),price_tenths=z['now_cost'],can_buy=eligibility(z)[0],status=z['status']) for z in b['elements']]
    return b,Market.create('2023-24',e['gameweek'],info['deadline'],e['captured_at'],rows),f


def prepare(spec,output,*,trust_local_cache=False,fit=False):
    if not trust_local_cache:raise ValueError('Explicit trust required before local executable cache loading')
    if spec['season']!='2023-24' or spec['training_seasons']!=['2020-21','2021-22','2022-23']:raise ValueError('Fixed prior-only research scope differs')
    out=Path(output).resolve();repo=Path(__file__).resolve().parents[1]
    if out.is_relative_to(repo) or out.exists():raise ValueError('Require new private output directory')
    for e in spec['inputs'].values():
        if digest(e['path'])!=e['sha256']:raise ValueError('Input checksum differs')
    get=lambda k:Path(spec['inputs'][k]['path']);tick=time.monotonic();d=pd.read_pickle(get('history'));x=pd.read_pickle(get('features'))
    if not d.index.equals(x.index):raise ValueError('History/features alignment differs')
    t=d.season.lt('2023-24')
    if set(d.loc[t,'season'])!=set(spec['training_seasons']):raise ValueError('Training scope differs')
    cutoff=pd.to_datetime(d.loc[t,'cutoff'],utc=True);latest=pd.to_datetime(x.loc[t,'source_max_ts'],utc=True)
    if not (latest.isna()|latest.lt(cutoff-pd.Timedelta(hours=3))).all():raise ValueError('Late training feature source')
    p=pd.read_csv(get('merged'));raw=pd.read_csv(get('players'));teams=pd.read_csv(get('teams'));team_ids=dict(zip(teams.name,teams.id));codes=dict(zip(raw.id,raw.code))
    if p.duplicated(['element','fixture']).any() or not p.team.isin(team_ids).all():raise ValueError('Ambiguous outcomes/clubs')
    sums=p.groupby('element').total_points.sum().reindex(raw.id,fill_value=0)
    if not np.array_equal(sums.to_numpy(),raw.total_points.to_numpy()):raise ValueError('Season totals do not reconcile')
    f=p[['fixture','GW','team','opponent_team','was_home','kickoff_time']].drop_duplicates();tid=f.team.map(team_ids)
    f['team_h']=np.where(f.was_home,tid,f.opponent_team);f['team_a']=np.where(f.was_home,f.opponent_team,tid)
    fixtures=f[['fixture','GW','team_h','team_a','kickoff_time']].drop_duplicates()
    if len(fixtures)!=380 or fixtures.fixture.duplicated().any():raise ValueError('Actual380fixture identities differ')
    markets=json.loads(get('markets').read_text());calendars=json.loads(get('calendars').read_text())
    if not markets['complete'] or not calendars['complete'] or [e['gameweek'] for e in markets['market_origins']]!=list(range(1,39)) or [e['gameweek'] for e in calendars['entries']]!=list(range(1,39)):raise ValueError('Incomplete38origins')
    # Audit every source/outcome before any fit. Never use final fixtures in project().
    hidden=dict(schema_version=1,weeks={});audits=[];origins=[]
    for e,ce in zip(markets['market_origins'],calendars['entries']):
        b,m,calendar=admitted_origin(spec,e,ce,codes);gw=m.gameweek;truth=fixtures[fixtures.GW.eq(gw)]
        values,changes=origin_outcomes(b['elements'],p[p.GW.eq(gw)],truth,team_ids)
        hidden['weeks'][gw]=values;origins.append((b,m,calendar,e,ce))
        audits.append(dict(gameweek=gw,listed=len(m.players),club_changes_evaluator_only=changes,forecast_only_fixtures=sorted(set(map(int,calendar.loc[calendar.event.eq(gw),'id']))-set(map(int,truth.fixture))),outcome_only_fixtures=sorted(set(map(int,truth.fixture))-set(map(int,calendar.loc[calendar.event.eq(gw),'id'])))))
    differences=[(a['gameweek'],a['forecast_only_fixtures'],a['outcome_only_fixtures']) for a in audits if a['forecast_only_fixtures'] or a['outcome_only_fixtures']]
    if differences!=[(17,[162],[])]:raise ValueError('Undeclared calendar/outcome membership difference')
    metadata=dict(version='standing-prior3-no-dc-2023-v1',training_rows=int(t.sum()),training_scope=spec['training_seasons'],trained_through=(pd.to_datetime(d.loc[t,'ts'],utc=True).max()+pd.Timedelta(hours=3)).isoformat(),approval='Historical research only; reused2023/24 validation year, no deployment promotion')
    if pd.Timestamp(metadata['trained_through'])>=pd.Timestamp(origins[0][1].as_of):raise ValueError('Prior fit cutoff is late')
    report=dict(status='admitted_without_fit',model=metadata,rules=rules_for('2023-24'),origins=audits,season_totals_reconciled=len(raw),fixtures=380,inputs=spec['inputs'],model_promotion=False,source_limitations=['Archive and Git timestamps are publisher claims','Snapshots may precede deadline by several hours','Status-based purchase eligibility is an explicit older-API proxy','No historical article/news input beyond frozen official status/chance labels','GW17 abandonment unknown at origin; final void/autosubs evaluator-only','Reused validation year and retrospectively chosen model recipe; not prospective/untouched','Prior-only source-lag approximation3h; final-stat revision provenance is incomplete'])
    out.mkdir(parents=True)
    if fit:
        models={};fit_start=time.monotonic()
        with threadpool_limits(limits=2):
            for head,target in [('core','points_core'),('minutes','minutes'),('played','played'),('sixty','sixty')]:
                models[head]=fit_estimator('hgb7',x.loc[t,CORE_FEATURES],d.loc[t,target],sample_weights(d[t]));print('Fitted prior-only',head,flush=True)
        model=ForecastModel(models['core'],'hgb7',1.,models['minutes'],models['played'],models['sixty'],None,'none',{str(pos):[0.,0.] for pos in range(1,5)},metadata)
        joblib.dump(model,out/'prior_model.joblib');model_hash=digest(out/'prior_model.joblib');report.update(model_sha256=model_hash,fit_seconds=time.monotonic()-fit_start);decisions=dict(schema_version=1,weeks=[]);history=d[d.season.eq('2023-24')].copy()
        for b,m,calendar,e,ce in origins:
            with threadpool_limits(limits=2):h,projection=project(model,history,m,calendar,through=min(38,m.gameweek+5),trained_through=metadata['trained_through'],source_as_of=m.as_of,model_id=metadata['version'],source_hashes=dict(bootstrap=e['compressed_sha256'],calendar=ce['sha256'],model=model_hash,history=spec['inputs']['history']['sha256']))
            zero={z['id'] for z in b['elements'] if z.get('chance_of_playing_next_round')==0 and z['status']!='a'};provenance=dict(h.provenance);provenance['source_hashes']=dict(provenance['source_hashes']);provenance['model_id']+='/official-zero-origin-v1'
            rs=[dict(v,expected_points=0. if v['gameweek']==m.gameweek and v['id'] in zero else v['expected_points']) for v in h.forecasts];hs=Horizon.create(m,rs,**provenance)
            decisions['weeks'].append(dict(market=dict(season=m.season,gameweek=m.gameweek,deadline=m.deadline,as_of=m.as_of,rows=[dict(v) for v in m.players]),forecast=dict(rows=[dict(v) for v in hs.forecasts],**provenance),blocked_tokens=[]));audits[m.gameweek-1].update(projection=projection,official_zero=len(zero));print('Prepared origin',m.gameweek,flush=True)
        for name,value in [('decisions',decisions),('outcomes',hidden)]:
            with gzip.open(out/(name+'.json.gz'),'xt') as stream:json.dump(value,stream,separators=(',',':'),allow_nan=False)
        report.update(status='prepared38origins',bundles={n:digest(out/(n+'.json.gz')) for n in ['decisions','outcomes']})
    report['seconds']=time.monotonic()-tick;(out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--trust-local-cache',action='store_true');p.add_argument('--fit',action='store_true');a=p.parse_args()
    if digest(a.manifest)!=a.manifest_sha256:p.error('Manifest checksum differs')
    prepare(json.loads(a.manifest.read_text()),a.output,trust_local_cache=a.trust_local_cache,fit=a.fit)


if __name__=='__main__':main()
