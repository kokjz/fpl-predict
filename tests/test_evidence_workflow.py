"""Synthetic end-to-end boundaries; never run forecasts for a real manager."""
import argparse
import hashlib
import json
import pandas as pd
from forecast import run


class SyntheticModel:
    metadata={"version":"synthetic"}
    residual_intervals={str(p):[-2,2] for p in range(1,5)}
    def predict(self,x,pos):
        return pd.DataFrame({"core_xp":4.,"dc_xp":0.,"expected_points":4.,
            "expected_minutes":70.,"p_play":.9,"p60":.8},index=x.index)


def test_sourced_override_applies_only_to_reviewed_gw_and_preserves_base_pointer(tmp_path,monkeypatch):
    import forecast
    root=tmp_path/'runtime';snapshot=root/'data/current/synthetic';(snapshot/'players').mkdir(parents=True)
    positions=[1,1]+[2]*5+[3]*5+[4]*3
    players=[{"id":i+1,"web_name":f"Synthetic {i+1}","element_type":p,
        "team":i//3+1,"now_cost":50,"status":"a","news":"","ep_next":"4.5"}
        for i,p in enumerate(positions)]
    fixtures=[]
    for gw in (6,7,8):
        for team in (1,3,5):
            fixtures.append({"id":gw*10+team,"event":gw,"team_h":team,"team_a":team+1,
                "kickoff_time":f"2026-10-{1 if gw==6 else 20 if gw==7 else 27:02d}T12:00:00Z",
                "finished":gw==6})
    b={"game_config":{"settings":{"static_content_url":"2026_27"}},
       "teams":[{"id":i,"short_name":f"T{i}"} for i in range(1,7)],"elements":players,
       "events":[{"id":7,"is_next":True,"deadline_time":"2030-10-20T10:00:00Z"},
                 {"id":8,"is_next":False,"deadline_time":"2030-10-27T10:00:00Z"}]}
    source={"file":"bootstrap.json","url":"https://example.org/bootstrap", "sha256":"synthetic",
            "retrieved_utc":"2026-10-10T09:00:00Z"}
    for name,obj in (("bootstrap.json",b),("fixtures.json",fixtures),
                     ("manifest.json",{"retrieved_utc":source['retrieved_utc'],"files":[source]})):
        (snapshot/name).write_text(json.dumps(obj))
    for p in players:
        fixture=next(f for f in fixtures if f['event']==6 and p['team'] in (f['team_h'],f['team_a']))
        h={"element":p['id'],"fixture":fixture['id'],"round":6,"kickoff_time":fixture['kickoff_time'],
           "was_home":p['team']==fixture['team_h'],"opponent_team":fixture['team_a'] if p['team']==fixture['team_h'] else fixture['team_h'],
           "minutes":90,"total_points":3,"team_h_score":1,"team_a_score":0}
        (snapshot/f"players/{p['id']}.json").write_text(json.dumps({"history":[h]}))
    state=tmp_path/'team.json';state.write_text(json.dumps({"players":[{"id":p['id'],"selling_price_tenths":50} for p in players],"bank_tenths":0,"free_transfers":1}))
    review=tmp_path/'review.json';review.write_text(json.dumps({"schema_version":1,"GW":7,
        "recorded_at_utc":"2026-10-10T10:00:00Z","players":[{"id":1,"minutes":0,
        "reason":"Synthetic no-appearance scenario","source_url":"https://example.org/news",
        "published_at_utc":"2026-10-10T09:00:00Z","checked_at_utc":"2026-10-10T09:30:00Z"}]}))
    artifact=tmp_path/'trusted';artifact.write_bytes(b'synthetic')
    (root/'forecasts').mkdir();(root/'forecasts/LATEST').write_text('preserved-base')
    monkeypatch.setattr(forecast,'ROOT',root)
    monkeypatch.setattr(forecast,'resolve_champion',lambda _: (artifact,'synthetic',{}))
    monkeypatch.setattr(forecast.joblib,'load',lambda _: SyntheticModel())
    run(argparse.Namespace(snapshot='synthetic',through_gw=8,team_state=str(state),overrides=None,availability_review=str(review)))
    output=next(p for p in (root/'forecasts').iterdir() if p.is_dir())
    rows=json.loads((output/'player_gameweek_predictions.json').read_text())
    first=next(r for r in rows if r['id']==1 and r['GW']==7)
    later=next(r for r in rows if r['id']==1 and r['GW']==8)
    assert first['expected_points']==0 and later['expected_points']==4
    assert first['official_ep_next']==4.5 and later['official_ep_next'] is None
    assert (root/'forecasts/LATEST').read_text()=='preserved-base'
    manifest=json.loads((output/'manifest.json').read_text())
    assert manifest['as_of_utc']=='2026-10-10T10:00:00+00:00'
    assert manifest['snapshot_as_of_utc']=='2026-10-10T09:00:00Z'
    assert manifest['availability_review']['GW']==7
    assert (output/'availability_observations.json').exists()


def test_finalised_scoring_aggregates_double_and_keeps_legacy_missing_baseline(tmp_path,monkeypatch):
    import score_forecast
    root=tmp_path/'runtime';outcome=root/'data/current/final';(outcome/'players').mkdir(parents=True)
    (outcome/'bootstrap.json').write_text(json.dumps({'events':[{'id':7,'finished':True,
        'data_checked':True,'deadline_time':'2026-10-10T10:00:00Z'}]}))
    (outcome/'players/1.json').write_text(json.dumps({'history':[
        {'round':7,'fixture':1,'minutes':30,'total_points':1},
        {'round':7,'fixture':2,'minutes':30,'total_points':1}]}))
    forecast_dir=tmp_path/'frozen';forecast_dir.mkdir()
    (forecast_dir/'manifest.json').write_text(json.dumps({'created_at_utc':'2026-10-09T12:00:00Z',
        'as_of_utc':'2026-10-09T11:00:00Z','model_sha256':'synthetic'}))
    (forecast_dir/'player_gameweek_predictions.json').write_text(json.dumps([
        {'id':1,'GW':7,'expected_points':3,'last5_xp':2,'ewm_xp':2,
         'candidate_pool':True,'expected_minutes':80,'p_play':.96}]))
    monkeypatch.setattr(score_forecast,'ROOT',root)
    args=argparse.Namespace(forecast=str(forecast_dir),gw=7,outcome_snapshot='final')
    score_forecast.run(args)
    report=json.loads((forecast_dir/'outcome_GW7_final.json').read_text())
    assert report['metrics']['candidates']['model']['mae']==1
    assert report['playing_time_diagnostics']['all']['minutes']['mae']==20
    assert report['playing_time_diagnostics']['all']['appearance_brier']>0
    assert report['official_ep_next_comparison']['all']['matched_rows']==0
    import pytest
    with pytest.raises(FileExistsError):score_forecast.run(args)
