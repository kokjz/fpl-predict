"""Controlled historical four-arm owned-squad study, with incumbent anchor."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from benchmark_metrics import point_scores
from conditional_integration import POLICY
from deadline_provenance import extract_bootstrap,read_snapshot
from expected_selection import select,objective,positive_dependence_stress
from experiment_runner import file_hash
from forecast import select_xi
from selection_benchmark import choices,paired_summary,scenarios,score,validate

ARMS=POLICY['arms']
KEYS=['season','gameweek','fixture','fpl_code']


def aggregate(frame):
    groups=frame.groupby(['season','gameweek','fpl_code'])
    if groups.position.nunique().ne(1).any() or groups.candidate.nunique().ne(1).any():raise ValueError('Inconsistent fixture metadata')
    out=groups.agg(actual=('actual','sum'),minutes=('minutes','sum'),position=('position','first'),
        candidate=('candidate','first'),anchor=('anchor','sum'),old_xp=('old_xp','sum'),new_xp=('new_xp','sum'),fixture_count=('fixture','size')).reset_index()
    for arm in ['old','new']:
        records=[]
        for _,g in groups:
            p=g[arm+'_p'].to_numpy(float)
            pc=g[arm+'_p_card'].to_numpy(float) if arm+'_p_card' in g else np.zeros(len(g))
            qc=g.conditional_card.to_numpy(float) if 'conditional_card' in g else np.zeros(len(g))
            xp=float(g[arm+'_xp'].sum());record={}
            for suffix,persistent in [('',False),('_persistent',True)]:
                play=float(p.max()) if persistent else 1-float(np.prod(1-p))
                active=float((p+pc).max()) if persistent else 1-float(np.prod(1-p-pc))
                card=max(0.,active-play)
                if persistent:zero_mass=float(np.sum(np.maximum(0.,p+pc-play)*qc))
                else:zero_mass=float(sum(pc[i]*qc[i]*np.prod(np.delete(1-p,i)) for i in range(len(p))))
                record.update({arm+suffix+'_p':play,arm+suffix+'_pc':card,
                    arm+suffix+'_q':(xp-zero_mass)/play if play else 0.,
                    arm+suffix+'_qc':zero_mass/card if card else 0.})
            records.append(record)
        for key in records[0]:out[key]=[r[key] for r in records]
    return out


def prepare_market(predictions,anchor,players,snapshot_manifest,snapshot_root,source_audits,retained_market):
    if predictions.duplicated(KEYS).any() or anchor.duplicated(KEYS).any():raise ValueError('Duplicate fixture keys')
    a=anchor[KEYS+['control','actual','minutes','position','candidate']].rename(columns={'control':'anchor'})
    joined=predictions.merge(a,on=KEYS,how='outer',validate='one_to_one',indicator=True,suffixes=('','_anchor'))
    if not joined._merge.eq('both').all():raise ValueError('Anchor prediction coverage mismatch')
    for c in ['actual','minutes','position','candidate']:
        if not np.array_equal(joined[c],joined[c+'_anchor']):raise ValueError('Anchor target metadata conflict')
    grouped=aggregate(joined);markets=[];audits=[]
    raw=players[players.season.eq('2025-26')].copy();raw['ts']=pd.to_datetime(raw.ts,utc=True)
    times={a['gameweek']:pd.Timestamp(a['published_at']) for a in source_audits}
    if len(times)!=len(source_audits):raise ValueError('Duplicate source weeks')
    for gw,g in grouped.groupby('gameweek',sort=True):
        entries=[r for r in snapshot_manifest['snapshots'] if r['gameweek']==gw]
        if len(entries)!=1:raise ValueError('Missing snapshot')
        entry=entries[0];root=Path(snapshot_root).resolve();path=(root/entry['file']).resolve()
        if not path.is_relative_to(root):raise ValueError('Snapshot path escapes root')
        boot=read_snapshot(path,entry['sha256']);info,_=extract_bootstrap(boot,'2025-26',int(gw),entry['captured_at'])
        quote=pd.Timestamp(entry['captured_at']);deadline=pd.Timestamp(info['deadline']);cutoff=max(quote,times[int(gw)])
        if cutoff>=deadline:raise ValueError('Source or quote not predeadline')
        history=raw[raw.ts.lt(quote-pd.Timedelta(hours=3))].sort_values('ts')
        prior=history.groupby('fpl_code').tail(4).groupby('fpl_code').minutes.mean()
        teams={r['id']:r['name'] for r in boot['teams']};target=raw[raw.gameweek.eq(gw)]
        cards=target.groupby('fpl_code')[['yellow_cards','red_cards']].sum().sum(axis=1)
        bycode=g.set_index('fpl_code');listed=[];blank=0
        previous=retained_market[retained_market.gameweek.eq(gw)].set_index('fpl_code') if gw>=28 else None
        for p in boot['elements']:
            if p['element_type'] not in (1,2,3,4):continue
            code=p['code']
            if code in bycode.index:
                r=bycode.loc[code]
                if int(r.position)!=p['element_type']:raise ValueError('Roster position conflict')
                values=r.to_dict();values.pop('position');values.pop('season');values.pop('gameweek')
                values['cards']=float(cards.loc[code]);values['blank_verified']=0
            else:
                # Only reuse an already independently verified listed blank.
                if previous is None or code not in previous.index or not(previous.loc[code,'blank_verified']==1 and previous.loc[code,'fixture_count']==0):
                    raise ValueError('Unexplained missing listed prediction')
                blank+=1
                values={k:0. for k in ['actual','minutes','cards','anchor','old_xp','new_xp','old_p','new_p','old_persistent_p','new_persistent_p','old_q','new_q','old_pc','new_pc','old_qc','new_qc','old_persistent_pc','new_persistent_pc','old_persistent_q','new_persistent_q','old_persistent_qc','new_persistent_qc','fixture_count']}
                values.update(candidate=False,blank_verified=1)
            if gw>=28:
                if code not in previous.index:raise ValueError('New roster differs from retained market')
                prev=previous.loc[code]
                if not np.allclose([values['actual'],values['minutes'],values['anchor'],values['cards']],prev[['actual','minutes','reference','cards']].to_numpy(float),rtol=0,atol=1e-10):
                    raise ValueError('Retained outcomes/control disagree')
                if p['now_cost']!=prev.price_tenths or teams[p['team']]!=prev.team:raise ValueError('Retained price/team disagree')
            listed.append(dict(season='2025-26',gameweek=int(gw),fpl_code=code,position=p['element_type'],team=teams[p['team']],
                price_tenths=p['now_cost'],can_buy=int(p['can_select']),ownership=float(p['selected_by_percent']),
                prior_minutes=float(prior.get(code,0.)),deadline=deadline.isoformat(),inputs_as_of=cutoff.isoformat(),quote_as_of=quote.isoformat(),**values))
        if gw>=28 and {r['fpl_code'] for r in listed}!=set(previous.index):raise ValueError('Retained roster coverage differs')
        markets.extend(listed);audits.append(dict(gameweek=int(gw),listed=len(listed),verified_blanks=blank,
            forecasts_outside_listed=len(set(g.fpl_code)-{r['fpl_code'] for r in listed}),snapshot_sha256=entry['sha256'],
            quote_as_of=quote.isoformat(),news_published_at=times[int(gw)].isoformat(),comparison_as_of=cutoff.isoformat()))
    market=pd.DataFrame(markets);validate(market,['anchor','old_xp','new_xp'])
    for arm in ['old','new']:
        if not np.isfinite(market[[arm+'_p',arm+'_q',arm+'_persistent_p']]).all().all():raise ValueError('Nonfinite mixture')
    metrics={}
    for name,lo,hi in [('validation',20,27),('audit',28,38)]:
        z=grouped[grouped.gameweek.between(lo,hi)];c=z[z.candidate]
        metrics[name]={m:dict(candidates=point_scores(c,m),all=point_scores(z,m)) for m in ['anchor','old_xp','new_xp']}
    return market,dict(weeks=audits,metrics=metrics,fixture_rows=len(joined),player_gw_rows=len(grouped),
        source_scope='All original error rows retained; selection uses independently listed roster, audit blanks from retained proof; development fixtures inherit reconstructed-history limitation')


def inputs_for(week,ids,arm,persistent=False):
    # Whitelist source metadata and model outputs; never pass outcomes to selector.
    label='old' if arm.startswith('old') else 'new'
    result=choices(week,ids,label+'_xp');by=week.set_index('fpl_code')
    for r in result:
        prefix=label+('_persistent' if persistent else '')
        r.update(p_play=float(by.loc[r['id'],prefix+'_p']),
            conditional_points=float(by.loc[r['id'],prefix+'_q']),
            p_card_only=float(by.loc[r['id'],prefix+'_pc']),conditional_card=float(by.loc[r['id'],prefix+'_qc']))
    return result


def progression(metrics,owned_means):
    m=metrics['validation'];a=m['anchor']['candidates'];n=m['new_xp']['candidates']
    checks=dict(candidate_rmse_improvement=n['rmse']<=a['rmse']*.995,
        mae_within_half_percent=n['mae']<=a['mae']*1.005,ndcg_no_worse=n['mean_within_gw_ndcg10']>=a['mean_within_gw_ndcg10'],
        owned_vs_anchor_nonnegative=owned_means['new_expected']>=owned_means['anchor'],
        owned_vs_old_mean_nonnegative=owned_means['new_expected']>=owned_means['old_mean'])
    return dict(passed=all(checks.values()),checks=checks,finalist='new_expected',model_promotion=False)


def run(market,*,pilot=False):
    records=[];actions=[];timing={};schedules={};stress=[]
    for name,lo,hi in [('validation',20,27),('audit',28,38)]:
        weeks=market[market.gameweek.between(lo,hi)]
        if set(weeks.gameweek)!=set(range(lo,hi+1)):raise ValueError('Incomplete owned window')
        first=weeks[weeks.gameweek.eq(lo)];panels=scenarios(first,12);schedules[name]=panels
        if pilot:weeks=first
        for gw,week in weeks.groupby('gameweek',sort=True):
            outcomes=None if pilot else {int(r.fpl_code):dict(actual=float(r.actual),minutes=float(r.minutes),cards=float(r.cards)) for r in week.itertuples()}
            for sid,panel in enumerate(panels[:1] if pilot else panels):
                ids=panel['ids'];players={p['id']:p for p in choices(week,ids,'anchor')}
                for arm in ARMS:
                    start=time.monotonic()
                    if arm=='anchor':data=choices(week,ids,'anchor');plan=select_xi(data)
                    else:
                        data=inputs_for(week,ids,arm);plan=select(data) if arm.endswith('expected') else select_xi(data)
                    elapsed=time.monotonic()-start;timing[arm]=timing.get(arm,0.)+elapsed
                    if pilot:
                        # Mechanical pilot never consults or scores outcomes.
                        records.append(dict(window=name,gameweek=int(gw),scenario=sid,arm=arm,selector_seconds=elapsed));continue
                    value=score(plan,players,outcomes)
                    records.append(dict(window=name,season='2025-26',gameweek=int(gw),scenario=sid,model=arm,layer='owned',
                        **{k:v for k,v in value.items() if k not in ('scoring_xi','scoring_captain')}))
                    actions.append(dict(window=name,gameweek=int(gw),scenario=sid,model=arm,squad=ids,selection=plan))
                    if arm!='anchor':
                        stress.append(dict(window=name,gameweek=int(gw),scenario=sid,arm=arm,
                            independent_objective=objective(plan,data),positive_dependence_objective=positive_dependence_stress(plan,data)))
                    if arm!='anchor' and sid in POLICY['sensitivity_squads']:
                        alt=inputs_for(week,ids,arm,persistent=True)
                        alternate=select(alt) if arm.endswith('expected') else select_xi(alt)
                        alt_value=score(alternate,players,outcomes)
                        actions.append(dict(window=name,gameweek=int(gw),scenario=sid,model=arm+'_persistent',squad=ids,selection=alternate))
                        records.append(dict(window=name,season='2025-26',gameweek=int(gw),scenario=sid,model=arm+'_persistent',layer='persistent',
                            **{k:v for k,v in alt_value.items() if k not in ('scoring_xi','scoring_captain')}))
            print('Completed',name,'GW',gw,flush=True)
    rows=pd.DataFrame(records)
    if pilot:return rows,actions,dict(pilot=True,outcomes_scored=False,timing=timing,schedules=schedules)
    summaries={}
    for name in ['validation','audit']:
        r=rows[rows.window.eq(name)&rows.layer.eq('owned')]
        summaries[name]={str(b):paired_summary(r,ARMS,'old_mean',block=b) for b in [2,4,6]}
        table=r.pivot(index=['gameweek','scenario'],columns='model',values='net_points')
        summaries[name]['factorial_mean_effects']={
            'availability_with_mean':float((table.new_mean-table.old_mean).mean()),
            'availability_with_expected':float((table.new_expected-table.old_expected).mean()),
            'selector_with_old':float((table.old_expected-table.old_mean).mean()),
            'selector_with_new':float((table.new_expected-table.new_mean).mean()),
            'combined_vs_old_mean':float((table.new_expected-table.old_mean).mean()),
            'combined_vs_anchor':float((table.new_expected-table.anchor).mean()),
            'interaction':float((table.new_expected-table.old_expected-table.new_mean+table.old_mean).mean())}
    return rows,actions,dict(pilot=False,summaries=summaries,timing=timing,schedules=schedules,stress=stress,model_promotion=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--market',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--pilot',action='store_true');a=p.parse_args()
    if file_hash(a.market)!=a.sha256:p.error('Market checksum mismatch')
    if a.output.exists():p.error('Output exists')
    market=pd.read_csv(a.market);validate(market,['anchor','old_xp','new_xp'])
    a.output.mkdir(parents=True)
    (a.output/'spec.json').write_text(json.dumps(dict(policy=POLICY,market_sha256=a.sha256,pilot=a.pilot,
        code_sha256=file_hash(Path(__file__)),selector_sha256=file_hash(Path(__file__).with_name('expected_selection.py'))),indent=2))
    rows,actions,report=run(market,pilot=a.pilot)
    rows.to_csv(a.output/'scores.csv',index=False)
    (a.output/'actions.json').write_text(json.dumps(actions,indent=2,allow_nan=False))
    (a.output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))


if __name__=='__main__':main()
