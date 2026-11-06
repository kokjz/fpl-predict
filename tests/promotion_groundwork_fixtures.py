"""Entirely synthetic weekly inputs, including the existing season-rules sentinel."""
import hashlib
import json
from types import SimpleNamespace
import pandas as pd
import pytest
from test_model import tiny, squad
from test_approved_horizon import setup


class ConstantModel:
    metadata={'version':'synthetic-v1'}
    residual_intervals={str(i):[0.,0.] for i in range(1,5)}
    def predict(self,x,pos):
        return pd.DataFrame(dict(core_xp=3.,dc_xp=.2,expected_points=3.2,
            expected_minutes=60.,p_play=.8,p60=.7),index=x.index)


def forecast_output(directory):
    entries=list(directory.iterdir())
    runs=[p for p in entries if p.is_dir()]
    if len(runs)!=1:
        raise ValueError('Require exactly one forecast output directory')
    if any(p!=runs[0] and (p.name!='LATEST' or not p.is_file()) for p in entries):
        raise ValueError('Unexpected entry in forecast output directory')
    latest=directory/'LATEST'
    if latest.exists() and latest.read_text().strip()!=runs[0].name:
        raise ValueError('LATEST differs from forecast output directory')
    return runs[0]


def forecast_case(root,patch,model=None,review=None,overrides=None):
    import forecast
    root.mkdir(parents=True,exist_ok=True)
    snap=root/'data/current/synthetic';(snap/'players').mkdir(parents=True)
    stamp='2026-01-01T10:00:00Z'
    bootstrap=dict(game_config=dict(settings=dict(static_content_url='synthetic/2026_27/')),
        teams=[dict(id=i,short_name=f'T{i}') for i in range(1,7)],
        events=[dict(id=20,is_next=True,deadline_time='2026-01-01T12:00:00Z')],elements=[])
    fixtures=[]
    for gw in [1,20,21]:
        for home,away in [(1,2),(3,4),(5,6)]:
            fixtures.append(dict(id=gw*10+home,event=gw,team_h=home,team_a=away,
                finished=gw==1,kickoff_time='2025-12-01T13:00:00Z' if gw==1 else '2026-01-02T13:00:00Z'))
    for p in squad():
        bootstrap['elements'].append(dict(id=p['id'],code=1000+p['id'],web_name=f'P{p["id"]}',
            element_type=p['position'],team=p['team'],now_cost=50,status='a',news='',chance_of_playing_next_round=75))
        h=tiny().iloc[0].to_dict()
        h.update(element=p['id'],fixture=10+((p['team']-1)//2)*2+1,round=1,
            was_home=p['team']%2==1)
        (snap/f'players/{p["id"]}.json').write_text(json.dumps(dict(history=[h])))
    raw=json.dumps(bootstrap).encode();(snap/'bootstrap.json').write_bytes(raw)
    (snap/'fixtures.json').write_text(json.dumps(fixtures))
    (snap/'manifest.json').write_text(json.dumps(dict(retrieved_utc=stamp,files=[dict(
        file='bootstrap.json',sha256=hashlib.sha256(raw).hexdigest(),retrieved_utc=stamp)])))
    state=root/'state.json';state.write_text(json.dumps(dict(players=[dict(id=p['id'],selling_price_tenths=50) for p in squad()],bank_tenths=0,free_transfers=1)))
    artifact=root/'synthetic.bin';artifact.write_bytes(b'synthetic-only')
    patch.setattr(forecast,'ROOT',root)
    patch.setattr(forecast,'resolve_champion',lambda _: (artifact,'synthetic-v1',{}))
    patch.setattr(forecast.joblib,'load',lambda _:model or ConstantModel())
    review_path=root/'review.json';override_path=root/'overrides.json'
    if review is not None:review_path.write_text(json.dumps(review))
    if overrides is not None:override_path.write_text(json.dumps(overrides))
    forecast.run(SimpleNamespace(snapshot='synthetic',through_gw=21,team_state=str(state),
        overrides=str(override_path) if overrides is not None else None,
        availability_review=str(review_path) if review is not None else None))
    dest=forecast_output(root/'forecasts')
    return {name:json.loads((dest/(name+'.json')).read_text()) for name in
        ['fixture_predictions','player_gameweek_predictions','planning','manifest']}


def parity_case(root):
    from horizon_forecast import project
    from approved_decision import project_decision_approved
    with pytest.MonkeyPatch.context() as patch:
        r,h,m,f,k=setup(root,patch)
        direct,_=project(ConstantModel(),h,m,f,through=32,trained_through='2026-01-01T00:00Z',source_as_of=m.as_of,model_id='synthetic')
        approved,appearance,report=project_decision_approved(r,h,m,f,**k,allow_research_policy=True)
        a=dict(horizon=[dict(v) for v in direct.forecasts],approved=[dict(v) for v in approved.forecasts],
            appearance=appearance['rows'],mean_reproduction_max_abs_error=report['appearance']['mean_reproduction_max_abs_error'])
    with pytest.MonkeyPatch.context() as patch:
        forecast=forecast_case(root/'forecast',patch)
    a['forecast']={key:forecast[key] for key in ['fixture_predictions','player_gameweek_predictions','planning']}
    return a
