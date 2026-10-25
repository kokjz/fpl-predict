from dataclasses import asdict
from pathlib import Path
from datetime import datetime, timedelta, timezone
from horizon_forecast import Horizon
from season_engine import Market
import importlib.util
import json
import pytest
from test_decision_management import fixture, fake_inner


def module():
    spec=importlib.util.spec_from_file_location('coherence_audit',Path(__file__).parents[1]/'tools/appearance_return_audit.py')
    tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool);return tool


def test_probability_and_conditional_scores_have_distinct_denominators():
    tool=module();m=tool.Metrics()
    for mu,p,actual,minutes,cards in [(2.,.5,4.,90.,0.),(2.,.5,0.,0.,0.),(0.,0.,-1.,0.,1.),(0.,0.,3.,90.,0.)]:
        v,q=tool.observation(mu,p,p,dict(actual=actual,minutes=minutes,cards=cards));m.add(v,q)
    r=m.report()
    assert r['n']==4 and r['observed_played_n']==2 and r['conditional_scored_n']==1
    assert r['conditional_mae']==0 and r['point_mae']==2
    assert r['zero_probability_played']==1 and r['card_only_outcomes']==1
    assert r['appearance_rate']==.5 and r['mean_probability']==.25
    assert r['brier']==pytest.approx(.375)
    with pytest.raises(ValueError):tool.observation(1.,0.,0.,dict(actual=0.,minutes=0.,cards=0.))
    with pytest.raises(ValueError):tool.observation(1.,1.1,.5,dict(actual=0.,minutes=0.,cards=0.))
    assert tool.Metrics().report()['point_mae'] is None


def test_declared_bins_and_joint_diagnostic_do_not_assume_independent_samples():
    tool=module()
    assert tool.probability_bin(.2)=='0.2:0.5' and tool.probability_bin(1.)=='0.95:1'
    assert tool.return_bin(20.)=='12:20' and tool.return_bin(20.1)=='above20'
    values,pairs=tool.joint([dict(p=.5,y=1.,team='a'),dict(p=.5,y=1.,team='a'),dict(p=1.,y=1.,team='b')])
    assert values['no_shows_expected']==1 and values['independent_variance']==.5
    assert pairs['same_club']==dict(n=1,residual_product=.25,predicted_joint=.25,observed_joint=1.)
    assert pairs['different_club']['n']==2 and pairs['different_club']['residual_product']==0


def fixture_files(tmp_path,tool):
    refs={};cases=[]
    protocol=tool.read(tool.PROTOCOL)
    for season in protocol['seasons']:
        directory=tmp_path/season;directory.mkdir();decisions=[];appearance=[];outcomes={}
        for g in range(1,39):
            state,m,h,a,cfg=fixture(g)
            state=type(state)(season,g,state.holdings,state.bank,min(g-1,5))
            year=int(season[:4]);origin=datetime(year,8,15,17,tzinfo=timezone.utc)+timedelta(weeks=g-1)
            market=dict(season=season,gameweek=g,deadline=(origin+timedelta(hours=1)).isoformat(),as_of=origin.isoformat(),rows=[dict(r) for r in m.players])
            m=Market.create(**market)
            h=Horizon.create(m,[dict(r) for r in h.forecasts],trained_through=f'{year}-05-25T18:00Z',feature_cutoff=m.as_of,source_as_of=m.as_of,model_id='invented')
            a=dict(a,as_of=m.as_of,trained_through=h.provenance['trained_through'])
            forecast=dict(rows=[dict(r) for r in h.forecasts],**{k:dict(v) if k=='source_hashes' else v for k,v in h.provenance.items()})
            decisions.append(dict(market=market,forecast=forecast,blocked_tokens=[]))
            acts,_=fake_inner(state,m,h,cfg)
            raw=dict(gameweek=g,inputs_as_of=m.as_of,state_before=asdict(state),action=asdict(acts[0]),provisional_actions=[asdict(acts[0])],forecast_provenance={**dict(h.provenance),'source_hashes':dict(h.provenance['source_hashes'])})
            (directory/f'GW{g:02d}_decision.json').write_text(json.dumps(raw))
            appearance.append(dict(a,rows=[dict(r,raw_p_play=r['p_play'],fixture_count=1,official_zero=False) for r in a['rows']]))
            outcomes[str(g)]={str(i):dict(actual=float(i%4),minutes=90.,cards=0.) for i in range(1,16)}
        path=directory/'decisions.json';path.write_text(json.dumps(dict(weeks=decisions)))
        for row in appearance:row['decision_sha256']=tool.file_hash(path)
        ap=directory/'appearance.json';ap.write_text(json.dumps(dict(weeks=appearance)))
        result=directory/'outcomes.json';result.write_text(json.dumps(dict(weeks=outcomes)))
        refs[season]={k:dict(path=str(p),sha256=tool.file_hash(p)) for k,p in [('decisions',path),('appearance',ap),('outcomes',result)]}
        for seed in protocol['paths']['opening_seeds']:
            for policy in protocol['paths']['policies']:
                cases.append(dict(name=f'{season}-{seed}-{policy}',season=season,seed=seed,policy=policy,repetition=1,directory=str(directory),decision_sha256={str(g):tool.file_hash(directory/f'GW{g:02d}_decision.json') for g in range(1,39)}))
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(dict(references=refs,paths=cases,protocol_sha256=tool.file_hash(tool.PROTOCOL))))
    return manifest,refs


def test_two_phase_audit_freezes_ex_ante_roles_and_rejects_source_mutations(tmp_path):
    tool=module();manifest,refs=fixture_files(tmp_path,tool)
    target=Path(refs['2024-25']['outcomes']['path']);original=target.read_bytes();target.write_text('not evaluator JSON')
    frozen=tmp_path/'memberships.json.gz'
    result=tool.freeze(manifest,tool.file_hash(manifest),frozen)
    assert result['panels']==456 and not result['evaluator_parsed']
    assert not tool.read(frozen)['actual_cumulative_points_retained']
    # Outcome bytes were never opened/parsed by freeze; evaluation checks them.
    with pytest.raises(ValueError,match='checksum'):tool.evaluate(frozen,result['sha256'],tmp_path/'wrong.json')
    target.write_bytes(original)
    output=tmp_path/'result.json';report=tool.evaluate(frozen,result['sha256'],output)
    assert report['forecast_cells']==1140 and report['current_squad_panels']==456
    data=tool.read(output)
    assert data['metrics']['2024-25/lead0/all_market']['n']==570
    assert data['metrics']['2024-25/lead1/p_bin/0:0.2']['n']==0
    # Same player held in six paths is counted only once in the role union.
    assert data['metrics']['2024-25/lead0/role/proposed_squad_any']['n']==570
    assert data['metrics']['case/2024-25-20261070-standingH6_fixedWork/lead0/held_before_current']['n']==555
    record=Path(refs['2024-25']['decisions']['path']).parent/'GW01_decision.json';record.write_text('{}')
    with pytest.raises(ValueError,match='checksum'):tool.evaluate(frozen,result['sha256'],tmp_path/'changed.json')
