"""Current fixture forecasts plus legal-XI and planning comparisons; no account writes."""
import argparse
import datetime as dt
from collections import Counter
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from fpl_model import FeatureStore,normalise
from model_registry import resolve_champion
from conditional_forecaster import predict_current
from availability_evidence import observations, scoped_overrides, official_baselines

from runtime import workspace_root
ROOT = workspace_root()

def legal_squad(players):
    return len(players)==15 and len({p['id'] for p in players})==15 and Counter(p['position'] for p in players)=={1:2,2:5,3:5,4:3} and max(Counter(p['team'] for p in players).values())<=3

def select_xi(players):
    """Exact for sum of XI mean points plus highest mean captain; no autosubs assumed."""
    by={pos:sorted([p for p in players if p['position']==pos],key=lambda p:(-p['expected_points'],p['id'])) for pos in range(1,5)}
    best=None
    for defs in range(3,6):
        for mids in range(2,6):
            fwds=10-defs-mids
            if not 1<=fwds<=3:continue
            counts={1:1,2:defs,3:mids,4:fwds}
            if any(len(by[p])<n for p,n in counts.items()):continue
            xi=[q for p,n in counts.items() for q in by[p][:n]]
            ranked=sorted(xi,key=lambda q:(-q['expected_points'],q['id']))
            value=sum(p['expected_points'] for p in xi)+ranked[0]['expected_points']
            if best is None or value>best['expected_points']:
                ids={p['id'] for p in xi}
                bench=sorted([p for p in players if p['id'] not in ids],key=lambda p:(p['position']==1,-p['expected_points']))
                best={'starters':[p['id'] for p in xi],'captain':ranked[0]['id'],'vice':ranked[1]['id'],'bench':[p['id'] for p in bench],'expected_points':float(value),'bench_boost_increment':float(sum(p['expected_points'] for p in bench)),'triple_captain_increment':float(ranked[0]['expected_points'])}
    if best is None:raise ValueError('No legal XI')
    return best

def aggregate_fixture_predictions(records,players,gws):
    """Confirmed blanks are zero, doubles are sums; never assume one fixture per GW."""
    buckets={}
    for r in records:buckets.setdefault((r['id'],r['GW']),[]).append(r)
    result=[]
    for p in players:
        for gw in gws:
            rr=buckets.get((p['id'],gw),[])
            result.append({**p,'GW':gw,'fixtures':[r['fixture'] for r in rr],'opponents':[r['opponent'] for r in rr],'expected_points':sum(r['expected_points'] for r in rr),'core_xp':sum(r['core_xp'] for r in rr),'dc_xp':sum(r['dc_xp'] for r in rr),'last5_xp':sum(r.get('last5_xp',0) for r in rr),'ewm_xp':sum(r.get('ewm_xp',0) for r in rr),'expected_minutes':sum(r['expected_minutes'] for r in rr),'p_play':1-float(np.prod([1-r['p_play'] for r in rr])) if rr else 0.,'n_history':rr[0]['n_history'] if rr else 0,'candidate_pool':bool(rr and rr[0].get('candidate_pool',False))})
    return result

def run(args):
    tag=args.snapshot or (ROOT/'data/current/LATEST').read_text().strip()
    root=ROOT/'data/current'/tag
    manifest=json.loads((root/'manifest.json').read_text());b=json.loads((root/'bootstrap.json').read_text());fixtures=json.loads((root/'fixtures.json').read_text())
    season='2026-27'
    config=b.get('game_config',{}).get('settings',{}).get('static_content_url','')
    if '2026_27' not in config:raise ValueError('Season/rules changed: review before forecasting')
    now=pd.Timestamp(manifest['retrieved_utc']);fx={f['id']:f for f in fixtures};teams={t['id']:t for t in b['teams']}
    players=[];history=[]
    for p in b['elements']:
        if p['element_type'] not in [1,2,3,4]:continue
        players.append({'id':p['id'],'name':p['web_name'],'position':p['element_type'],'team':p['team'],'club':teams[p['team']]['short_name'],'price_tenths':p['now_cost'],'status':p['status'],'news':p['news'],'news_added':p.get('news_added')})
        obj=json.loads((root/f'players/{p["id"]}.json').read_text())
        for h in obj['history']:
            f=fx.get(h['fixture'])
            if not f or not f.get('finished'):continue
            # Only completed matches, not live or provisional rows.
            history.append({**h,'season':season,'GW':h['round'],'pos':p['element_type'],'name':p['web_name'],'team_id':f['team_h'] if h['was_home'] else f['team_a']})
    hist=normalise(pd.DataFrame(history));assert not hist.duplicated(['element','fixture']).any()
    nextgw=next(e['id'] for e in b['events'] if e['is_next'])
    through=args.through_gw or (19 if nextgw<=19 else 38)
    gws=list(range(nextgw,min(through,38)+1))
    if not gws:raise ValueError('No requested future GWs')
    rows=[]
    for p in players:
        for f in fixtures:
            if f.get('event') not in gws or p['team'] not in (f['team_h'],f['team_a']):continue
            home=p['team']==f['team_h'];opp=f['team_a'] if home else f['team_h']
            rows.append({'element':p['id'],'season':season,'fixture':f['id'],'GW':f['event'],'pos':p['position'],'team_id':p['team'],'opponent_team':opp,'was_home':home,'cutoff':now,'kickoff_time':f.get('kickoff_time'),'opponent':teams[opp]['short_name']+(' H' if home else ' A')})
    target=pd.DataFrame(rows);x=FeatureStore(hist).transform(target)
    model_path,champion_version,_=resolve_champion(ROOT)
    model=joblib.load(model_path)
    if model.metadata['version']!=champion_version:raise ValueError('Registry/model version mismatch')
    if getattr(model,'requires_availability',False):
        source=next((v for v in manifest['files'] if v['file']=='bootstrap.json'),None)
        if not source or source.get('sha256')!=hashlib.sha256((root/'bootstrap.json').read_bytes()).hexdigest():
            raise ValueError('Conditional availability bootstrap checksum mismatch')
        if pd.Timestamp(source['retrieved_utc'])!=now:raise ValueError('Bootstrap and snapshot clocks differ')
    pred,learned_availability=predict_current(model,x,target.pos,target,b,manifest['retrieved_utc'])
    overrides=json.loads(Path(args.overrides).read_text()) if args.overrides else {}
    review_path=getattr(args,'availability_review',None)
    review=json.loads(Path(review_path).read_text()) if review_path else None
    scoped={};review_gw=None
    if review:
        review_gw,recorded,scoped=scoped_overrides(review,b,dt.datetime.now(dt.timezone.utc))
        if review_gw!=nextgw:raise ValueError('Availability review must target the next gameweek')
        if set(map(int,overrides))&set(scoped):raise ValueError('Conflicting legacy and reviewed overrides')
        now=max(now,recorded)
    out=[]
    for i,r in target.iterrows():
        v=pred.loc[i].to_dict();override=scoped.get(int(r.element),{}) if int(r.GW)==review_gw and int(r.element) in scoped else overrides.get(str(r.element),{})
        dc_base=0. if r.pos==1 else 2*float(x.loc[i,'dc_rate4'])
        v['last5_xp']=float(x.loc[i,'last5_points'])+dc_base
        v['ewm_xp']=float(x.loc[i,'ew4_points_core'])+dc_base
        factor=float(override.get('availability',1.))
        if not 0<=factor<=1:raise ValueError('availability must lie in [0,1]')
        if 'minutes' in override:
            minutes=float(override['minutes'])
            if not 0<=minutes<=90:raise ValueError('minutes must lie in [0,90]')
            # An explicit sensitivity approximation, not a retrained conditional forecast.
            factor*=minutes/max(v['expected_minutes'],10.)
        for k in v:v[k]*=factor
        v['p_play']=min(v['p_play'],1.);v['p60']=min(v['p60'],v['p_play']);v['expected_minutes']=min(v['expected_minutes'],90.)
        v['dc_xp']=min(v['dc_xp'],2*v['p_play'])
        v['expected_points']=v['core_xp']+v['dc_xp']
        lo,hi=model.residual_intervals[str(int(r.pos))]
        out.append({'id':int(r.element),'GW':int(r.GW),'fixture':int(r.fixture),'opponent':r.opponent,**v,'core_interval80_low':max(-3,v['core_xp']+lo) if factor else 0.,'core_interval80_high':v['core_xp']+hi if factor else 0.,'n_history':int(x.loc[i,'n_history']),'candidate_pool':bool(x.loc[i,'n_history']>=3 and x.loc[i,'last5_minutes']>=45),'override':override})
    aggregate=aggregate_fixture_predictions(out,players,gws)
    official=official_baselines(b)
    for row in aggregate:
        row['official_ep_next']=official.get((row['id'],row['GW']))
    state=json.loads(Path(args.team_state).read_text());ids=[p['id'] for p in state['players']]
    indexed={(r['id'],r['GW']):r for r in aggregate};meta={p['id']:p for p in players}
    owned=[{**meta[i],'selling_price_tenths':next(p['selling_price_tenths'] for p in state['players'] if p['id']==i)} for i in ids]
    if not legal_squad(owned):raise ValueError('Current squad violates roster constraints; review team/club changes')
    plans={gw:select_xi([indexed[(i,gw)] for i in ids]) for gw in gws}
    horizon=gws[:6];base=sum(plans[g]['expected_points'] for g in horizon)
    transfers=[]
    for old in owned:
        for new in players:
            if new['id'] in ids or new['position']!=old['position'] or new['status']!='a':continue
            if new['price_tenths']>old['selling_price_tenths']+state['bank_tenths']:continue
            row=indexed[(new['id'],nextgw)]
            if row['n_history']<3 or row['p_play']<.65:continue
            newids=[new['id'] if i==old['id'] else i for i in ids]
            if not legal_squad([meta[i] for i in newids]):continue
            total=sum(select_xi([indexed[(i,g)] for i in newids])['expected_points'] for g in horizon)
            hit=0 if state['free_transfers']>=1 else 4
            transfers.append({'out':old['id'],'in':new['id'],'out_name':old['name'],'in_name':new['name'],'six_gw_gross_gain':total-base,'hit':hit,'net_gain':total-base-hit,'remaining_bank_tenths':state['bank_tenths']+old['selling_price_tenths']-new['price_tenths']})
    transfers.sort(key=lambda z:z['net_gain'],reverse=True)
    assumptions={'legacy':overrides,'review':review}
    runid=tag+'-'+hashlib.sha256(model_path.read_bytes()).hexdigest()[:8]+('-'+hashlib.sha256(json.dumps(assumptions,sort_keys=True).encode()).hexdigest()[:8] if overrides or review else '')
    dest=ROOT/'forecasts'/runid;dest.mkdir(parents=True,exist_ok=False)
    provenance={'snapshot':tag,'as_of_utc':now.isoformat(),'model':model.metadata,'champion_registry_version':champion_version,'model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),'source_sha256':{name:hashlib.sha256((Path(__file__).resolve().parent/name).read_bytes()).hexdigest() for name in ['fpl_model.py','forecast.py','model_registry.py','availability_evidence.py']},'inputs_manifest_sha256':hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),'overrides':overrides,'start_gw':nextgw,'through_gw':gws[-1],'current_history_rows':len(hist),'supported_horizon':'one-GW empirical test; all further horizons are unvalidated planning approximations','caveats':['Current forecasts use this-season form and pooled historical patterns; no individual carryover across seasons.','Doubtful/injured status requires scenario review; official percentage is not used as a start probability.','No news-adjusted forecast unless an explicit documented override is supplied.','Six-GW transfer comparison holds the rest of the squad and roles fixed, allows captain changes, and excludes autosubs, future transfers and banked-FT option value. It is not a globally optimal season strategy.','XI objective omits vice-captain fallback and autosub expectation; captain/vice pair is a practical ranking.','Double-GW appearance probability assumes independent matches and is approximate.','Selling prices come from the last manager-confirmed state; reconfirm affordability before action.','Direct core-point model carries historical assist/BPS changes; exact current BPS outcome prediction is not established.','Empirical 80% intervals apply to core match points only; they exclude current DC/fitness uncertainty and are not summed into a multiweek confidence interval.']}
    provenance['timing_note']='as_of_utc is the input snapshot; created_at_utc is when this forecast was generated.'
    provenance['availability_review']=review
    provenance['learned_availability']=learned_availability
    provenance['snapshot_as_of_utc']=manifest['retrieved_utc']
    provenance['timing_note']='as_of_utc includes any recorded availability review; snapshot_as_of_utc dates API inputs; created_at_utc dates generation.'
    provenance['official_ep_next_scope']='Unadjusted official next-GW projection only; no extrapolation or missing-value imputation.'
    source=next((v for v in manifest['files'] if v['file']=='bootstrap.json'),None)
    if source:(dest/'availability_observations.json').write_text(json.dumps(observations(b,source),indent=2)+'\n')
    for filename,data in [('fixture_predictions.json',out),('player_gameweek_predictions.json',aggregate),('planning.json',{'lineups':plans,'single_transfer_comparisons':transfers[:30],'first_half_chip_windows':{'triple_captain':sorted([{'GW':g,'increment':plans[g]['triple_captain_increment']} for g in gws if g<=19],key=lambda x:-x['increment']),'bench_boost':sorted([{'GW':g,'increment':plans[g]['bench_boost_increment']} for g in gws if g<=19],key=lambda x:-x['increment'])}})]:
        (dest/filename).write_text(json.dumps(data,indent=2,default=str)+'\n')
    names=lambda ii:', '.join(meta[i]['name'] for i in ii)
    lines=[f'# Model-assisted FPL forecast — GW{nextgw}', '',f'Data collected {now.isoformat()}. Model v{model.metadata["version"]}. Team state unchanged. Forecasts are expected values, not exact scores.','', '**Availability review required:** figures below reflect historical selection patterns before explicit current injury overrides. Flagged players require fresh news.','', f'| Owned player | GW{nextgw} fixture | xPts | Expected minutes | Status |','|---|---|---:|---:|---|']
    for i in ids:
        z=indexed[(i,nextgw)];lines.append(f'| {z["name"]} | {", ".join(z["opponents"])} | {z["expected_points"]:.2f} | {z["expected_minutes"]:.1f} | {z["status"]} |')
    plan=plans[nextgw]
    lines+=['',f'Numerical XI: {names(plan["starters"])}.',f'Captain ranking: {meta[plan["captain"]]["name"]}; next option {meta[plan["vice"]]["name"]}.',f'Bench (outfield priority then goalkeeper): {names(plan["bench"])}.','', '## Six-gameweek comparisons','', 'These compare one transfer now against keeping the same squad; they do not price the option value of saving a free transfer. Selling prices require reconfirmation. No transfer is executed.','', '| Out | In | Forecast net gain | Hit |','|---|---|---:|---:|']
    for t in transfers[:8]:lines.append(f'| {t["out_name"]} | {t["in_name"]} | {t["net_gain"]:.2f} | {t["hit"]} |')
    lines+=['','## Chip planning','', 'The planning JSON ranks conditional Triple Captain and Bench Boost increments through GW19 for the unchanged squad. These are comparison inputs, not a joint chip schedule: only one chip can be played per GW, and Wildcard/Free Hit change future squads. Retain the existing conditional chip plan until news, bench readiness and actual fixture changes justify revision.','','## Limits','']+['- '+c for c in provenance['caveats']]
    (dest/'REPORT.md').write_text('\n'.join(lines)+'\n')
    provenance['created_at_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
    (dest/'manifest.json').write_text(json.dumps(provenance,indent=2,default=str)+'\n')
    if not overrides and not review:(ROOT/'forecasts'/'LATEST').write_text(runid+'\n')
    print('Forecast saved',dest,flush=True);print('Captain',meta[plan['captain']]['name'],'vice',meta[plan['vice']]['name'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot');p.add_argument('--through-gw',type=int);p.add_argument('--team-state',required=True);p.add_argument('--overrides');p.add_argument('--availability-review');args=p.parse_args()
    with threadpool_limits(limits=4):run(args)
