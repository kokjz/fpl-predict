import json
from pathlib import Path
import pytest
from experiment_runner import file_hash
from participation_audit import history,preflight


def write(path,value):path.write_text(json.dumps(value))


def fixture(tmp_path):
    forecast=tmp_path/'forecast';forecast.mkdir();snapshot=tmp_path/'snapshot';snapshot.mkdir()
    outcome=tmp_path/'outcome';(outcome/'players').mkdir(parents=True)
    boot=dict(events=[dict(id=7,is_next=True,finished=False,data_checked=False,deadline_time='2026-10-18T10:00:00Z')],
        elements=[dict(id=i,code=100+i,element_type=3,status='a',news='',chance_of_playing_next_round=None) for i in (1,2)])
    origin=tmp_path/'origin.json';write(origin,boot);write(snapshot/'bootstrap.json',boot)
    def bind():
        write(snapshot/'manifest.json',dict(retrieved_utc='2026-10-17T08:31:00Z',files=[dict(file='bootstrap.json',
            url='https://fantasy.premierleague.com/api/bootstrap-static/',sha256=file_hash(snapshot/'bootstrap.json'),
            retrieved_utc='2026-10-17T08:30:00Z')]))
    bind()
    write(forecast/'manifest.json',dict(as_of_utc='2026-10-17T08:00:00Z',created_at_utc='2026-10-17T08:10:00Z',model_sha256='synthetic'))
    write(forecast/'player_gameweek_predictions.json',[dict(id=i,GW=7,position=3,fixtures=[88],candidate_pool=i==1,
        expected_points=4. if i==1 else 3.,expected_minutes=70.,p_play=.9 if i==1 else .6,status='a',news='') for i in (1,2)])
    final=json.loads(json.dumps(boot));final['events'][0].update(finished=True,data_checked=True,is_next=False)
    write(outcome/'bootstrap.json',final)
    for i in (1,2):write(outcome/'players'/f'{i}.json',dict(history=[dict(fixture=88,round=7,minutes=0 if i==1 else 90,total_points=0 if i==1 else 8)]))
    return forecast,origin,outcome,snapshot,bind


def test_history_points_and_probability_risk_have_correct_denominators(tmp_path):
    f,o,end,_,_=fixture(tmp_path);r=history(f,o,end,7)
    assert r['point_risk']['all']['points_mse']==20.5
    zero=r['point_risk']['all']['by_actual_minutes_diagnostic_only']['zero']
    assert zero['contribution_to_total_mse']==8
    candidate=r['point_risk']['candidates']
    assert candidate['n']==1 and candidate['high_probability_nonappearance']['nonappearances']==1
    assert candidate['by_predicted_probability']['.8_to_.95']['nonappearance_contribution_to_total_mse']==16
    assert r['playing_time']['candidates']['appearance_brier']==pytest.approx(.81)
    assert r['scope'].startswith('Retained frozen')


@pytest.mark.parametrize('kind',['late','naive','nan','probability','duplicate','identity','unfinalised','history_duplicate','missing_file'])
def test_history_rejects_integrity_failures(tmp_path,kind):
    f,o,end,_,_=fixture(tmp_path)
    if kind in ('late','naive'):
        m=json.loads((f/'manifest.json').read_text());m['created_at_utc']='2026-10-18T10:00:00Z' if kind=='late' else '2026-10-17T08:10:00';write(f/'manifest.json',m)
    if kind in ('nan','probability','duplicate'):
        p=f/'player_gameweek_predictions.json';rows=json.loads(p.read_text())
        if kind=='nan':rows[0]['expected_points']=float('nan')
        if kind=='probability':rows[0]['p_play']=1.01
        if kind=='duplicate':rows.append(rows[0])
        write(p,rows)
    if kind in ('identity','unfinalised'):
        p=end/'bootstrap.json';b=json.loads(p.read_text())
        if kind=='identity':b['elements'][0]['code']=999
        if kind=='unfinalised':b['events'][0]['data_checked']=False
        write(p,b)
    if kind=='history_duplicate':
        p=end/'players/1.json';h=json.loads(p.read_text());h['history']*=2;write(p,h)
    if kind=='missing_file':(end/'players/1.json').unlink()
    with pytest.raises((ValueError,FileNotFoundError)):history(f,o,end,7)


def test_empty_retained_history_is_explicit_but_missing_file_is_not_zero(tmp_path):
    f,o,end,_,_=fixture(tmp_path);write(end/'players/1.json',dict(history=[]))
    assert history(f,o,end,7)['empty_retained_histories']==1


def test_preflight_has_no_outcome_dependency_and_never_clears_fitness(tmp_path):
    f,_,end,s,_=fixture(tmp_path)
    a=preflight(f,s,7,'2026-10-17T09:00:00Z')
    assert a['status']=='no_machine_detected_issues' and not a['fitness_clearance']
    write(end/'players/1.json',dict(history=[dict(actual=1000)]))
    assert preflight(f,s,7,'2026-10-17T09:00:00Z')==a


def test_flags_and_additional_owned_ids_are_reviewed(tmp_path):
    f,_,_,s,bind=fixture(tmp_path);p=s/'bootstrap.json';b=json.loads(p.read_text());b['elements'][1].update(status='i',news='Synthetic concern',chance_of_playing_next_round=25);write(p,b);bind()
    assert preflight(f,s,7,'2026-10-17T09:00:00Z')['status']=='no_machine_detected_issues'
    r=preflight(f,s,7,'2026-10-17T09:00:00Z',include_ids=[2])
    assert r['status']=='review_required' and r['checked_players']==2
    assert 'flagged_status' in r['review_queue'][0]['reasons'] and 'no_sourced_sensitivity_review' in r['review_queue'][0]['reasons']
    with pytest.raises(ValueError,match='Unknown'):preflight(f,s,7,'2026-10-17T09:00:00Z',include_ids=[999])


def test_sourced_review_does_not_erase_flag(tmp_path):
    f,_,_,s,bind=fixture(tmp_path);p=s/'bootstrap.json';b=json.loads(p.read_text());b['elements'][0]['status']='i';write(p,b);bind()
    review=tmp_path/'review.json';write(review,dict(schema_version=1,GW=7,recorded_at_utc='2026-10-17T08:50:00Z',players=[dict(id=1,minutes=0,reason='Synthetic assumption',source_url='https://example.org/club',published_at_utc='2026-10-17T08:00:00Z',checked_at_utc='2026-10-17T08:45:00Z')]))
    r=preflight(f,s,7,'2026-10-17T09:00:00Z',review)
    assert r['status']=='review_required' and r['review_queue'][0]['sourced_assumption_present']
    assert 'no_sourced_sensitivity_review' not in r['review_queue'][0]['reasons']


@pytest.mark.parametrize('kind',['late','future','old_snapshot','tampered','wrong_url','wrong_gw','unknown_position'])
def test_preflight_rejects_wrong_timing_and_provenance(tmp_path,kind):
    f,_,_,s,bind=fixture(tmp_path);asof='2026-10-17T09:00:00Z'
    if kind=='late':asof='2026-10-18T10:00:00Z'
    if kind=='future':asof='2026-10-17T08:20:00Z'
    if kind in ('old_snapshot','wrong_url'):
        p=s/'manifest.json';m=json.loads(p.read_text())
        if kind=='old_snapshot':m['retrieved_utc']='2026-10-17T07:00:00Z';m['files'][0]['retrieved_utc']='2026-10-17T06:59:00Z'
        if kind=='wrong_url':m['files'][0]['url']='https://example.org/football'
        write(p,m)
    if kind in ('tampered','wrong_gw','unknown_position'):
        p=s/'bootstrap.json';b=json.loads(p.read_text())
        if kind=='wrong_gw':b['events'][0]['is_next']=False
        if kind=='unknown_position':b['elements'][0]['element_type']=2
        if kind=='tampered':b['elements'][0]['news']='Unbound change'
        write(p,b)
        if kind!='tampered':bind()
    with pytest.raises(ValueError):preflight(f,s,7,asof)


def test_stale_inputs_require_review(tmp_path):
    f,_,_,s,_=fixture(tmp_path)
    r=preflight(f,s,7,'2026-10-18T09:00:00Z')
    assert 'bootstrap_older_than_6h' in r['global_issues']
    assert 'forecast_older_than_24h' in r['global_issues']


def test_external_club_evidence_flags_conflict_without_changing_forecast(tmp_path):
    f,_,_,s,_=fixture(tmp_path);p=tmp_path/'external.json'
    write(p,dict(schema_version=1,GW=7,recorded_at_utc='2026-10-17T08:55:00Z',players=[dict(id=1,
        source_kind='club',source_url='https://example.org/team-news',summary='Synthetic report of absence',
        reported_availability='out',published_at_utc='2026-10-17T08:40:00Z',checked_at_utc='2026-10-17T08:50:00Z')]))
    original=file_hash(f/'player_gameweek_predictions.json')
    r=preflight(f,s,7,'2026-10-17T09:00:00Z',evidence=p)
    assert 'external_reported_out' in r['review_queue'][0]['reasons']
    assert r['review_queue'][0]['external_evidence_present'] and not r['fitness_clearance']
    assert file_hash(f/'player_gameweek_predictions.json')==original
    d=json.loads(p.read_text());d['players'][0]['reported_availability']='available';write(p,d)
    assert preflight(f,s,7,'2026-10-17T09:00:00Z',evidence=p)['status']=='review_required'
    d['players'][0]['published_at_utc']='2026-10-18T10:01:00Z';write(p,d)
    with pytest.raises(ValueError):preflight(f,s,7,'2026-10-17T09:00:00Z',evidence=p)


def test_origin_bridge_and_deadline_mismatch_rejected(tmp_path):
    f,o,end,s,bind=fixture(tmp_path)
    assert preflight(f,s,7,'2026-10-17T09:00:00Z',origin=o)['identity_bridge_verified']
    b=json.loads((s/'bootstrap.json').read_text());b['elements'][0]['code']=999;write(s/'bootstrap.json',b);bind()
    with pytest.raises(ValueError,match='stable identity'):preflight(f,s,7,'2026-10-17T09:00:00Z',origin=o)
    b=json.loads(o.read_text());b['events'][0]['deadline_time']='2025-10-18T10:00:00Z';write(o,b)
    with pytest.raises(ValueError,match='deadline'):history(f,o,end,7)


def test_empty_candidate_cohort_stays_unknown_not_perfect(tmp_path):
    f,o,end,_,_=fixture(tmp_path);p=f/'player_gameweek_predictions.json';rows=json.loads(p.read_text())
    for row in rows:row['candidate_pool']=False
    write(p,rows);r=history(f,o,end,7)
    assert r['point_risk']['candidates']['n']==0 and r['point_risk']['candidates']['points_mse'] is None
    assert r['playing_time']['candidates']['appearance_brier'] is None


def test_external_boolean_id_cannot_alias_football_id(tmp_path):
    f,_,_,s,_=fixture(tmp_path);p=tmp_path/'bad.json'
    write(p,dict(schema_version=1,GW=7,recorded_at_utc='2026-10-17T08:55:00Z',players=[dict(id=True,
        source_kind='club',source_url='https://example.org/news',summary='Synthetic',reported_availability='out',
        published_at_utc='2026-10-17T08:40:00Z',checked_at_utc='2026-10-17T08:50:00Z')]))
    with pytest.raises(ValueError,match='player ID'):preflight(f,s,7,'2026-10-17T09:00:00Z',evidence=p)
