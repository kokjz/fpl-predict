"""Locked-runner mechanics using synthetic replay inputs and fake workers."""
import contextlib
import copy
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import season_qualification as q
from test_season_benchmark import bundle


def inputs(tmp_path):
    d,o=bundle();paths={}
    for name,value in [('decisions',dict(schema_version=1,weeks=d)),
                       ('outcomes',dict(schema_version=1,weeks=o)),('opening',list(range(1,16)))]:
        p=tmp_path/(name+'.json');p.write_text(json.dumps(value));paths[name]=p
    p=q.protocol();p['forecast_bundle_sha256']=q.file_hash(paths['decisions']);p['outcome_bundle_sha256']=q.file_hash(paths['outcomes']);p['common_opening_sha256']=q.file_hash(paths['opening'])
    p['resources'].update(outer_seconds=.2,inner_seconds=.01,max_trials=1)
    proto=tmp_path/'protocol.json';proto.write_text(json.dumps(p));paths['protocol_path']=proto
    home=tmp_path/'private';lock=home/'lock.json'
    q.create_lock(paths['decisions'],paths['outcomes'],paths['opening'],lock,protocol_path=proto,home=home)
    return paths,home,lock


def test_twenty_declared_paths_order_and_no_duplicate_arm_ids():
    a=q.arms(q.protocol());assert len(a)==len({r['name'] for r in a})==20
    assert [r['horizon'] for r in a[:4]]==[1,6,6,6]
    assert a[0]['name']=='r1_own_standingH1_adaptive' and a[8]['replication']==2
    assert [r['policy'] for r in a[16:]]==['fixed_calendar','fixed_calendar','hold_no_chips','hold_no_chips']


def test_lock_has_no_input_paths_and_cannot_be_overwritten(tmp_path):
    paths,home,lock=inputs(tmp_path);data=json.loads(lock.read_text())
    assert str(tmp_path) not in lock.read_text() and len(data['arms'])==20
    with pytest.raises(FileExistsError):q.create_lock(paths['decisions'],paths['outcomes'],paths['opening'],lock,protocol_path=paths['protocol_path'],home=home)
    with pytest.raises(ValueError,match='private runtime'):
        q.create_lock(paths['decisions'],paths['outcomes'],paths['opening'],tmp_path/'outside.json',protocol_path=paths['protocol_path'],home=home)


def test_output_cannot_target_unignored_repository_files():
    repo=Path(q.__file__).resolve().parent.parent
    with pytest.raises(ValueError,match='ignored runtime'):q.output_path(repo/'docs/unwanted-output',home=repo)
    assert q.output_path(repo/'var/qualification',home=repo)==repo/'var/qualification'


@pytest.mark.parametrize('damage',['lock','input','source','runtime','arm'])
def test_drift_or_undeclared_arm_stops_before_output(tmp_path,monkeypatch,damage):
    paths,home,lock=inputs(tmp_path);sha=q.file_hash(lock);name='control_own_hold_no_chips'
    if damage=='lock':sha='0'*64
    elif damage=='input':paths['outcomes'].write_text(paths['outcomes'].read_text()+' ')
    elif damage=='source':monkeypatch.setattr(q,'SOURCE_FILES',q.SOURCE_FILES[1:])
    elif damage=='runtime':
        real=q.importlib.metadata.version
        monkeypatch.setattr(q.importlib.metadata,'version',lambda name:real(name)+'changed' if name=='numpy' else real(name))
    else:name='unregistered-policy'
    destination=home/'arm'
    with pytest.raises(ValueError):q.run_arm(name,paths['decisions'],paths['outcomes'],paths['opening'],lock,sha,destination,protocol_path=paths['protocol_path'],home=home)
    assert not destination.exists()


def test_synthetic_hold_arm_runs38weeks_and_preserves_lock_identity(tmp_path):
    paths,home,lock=inputs(tmp_path);destination=home/'arm';sha=q.file_hash(lock)
    result=q.run_arm('control_common_hold_no_chips',paths['decisions'],paths['outcomes'],paths['opening'],lock,sha,destination,protocol_path=paths['protocol_path'],home=home)
    assert result['net_points']==456 and result['qualification_lock_sha256']==sha
    assert not result['policy_promotion'] and result['native_calls']==0
    assert len(list((destination/'season').glob('*_decision.json')))==38
    with pytest.raises(ValueError,match='exists'):q.run_arm('control_common_hold_no_chips',paths['decisions'],paths['outcomes'],paths['opening'],lock,sha,destination,protocol_path=paths['protocol_path'],home=home)


def test_trace_keeps_every_reply_and_rejects_unrecognised_failure(tmp_path):
    class Actor:
        def __init__(self):self.replies=iter([dict(status='completed',value=1),dict(status='failed',error_type='NativeBudgetExpired'),dict(status='failed',error_type='StatementError',message='NativeBudgetExpired')])
        def request(self,value):return next(self.replies)
    with contextlib.ExitStack() as stack:
        trace=q.Trace(Actor(),tmp_path,'airsenal',stack)
        trace.request(dict(seconds=.1));trace.request(dict(seconds=.1))
        with pytest.raises(RuntimeError,match='Unexpected'):trace.request(dict(seconds=.1))
    records=[json.loads(line) for line in gzip.open(tmp_path/'native_trace.jsonl.gz','rt')]
    assert len(records)==3 and trace.calls==3 and trace.failed==2
    assert (tmp_path/'native_failure_0003.json').exists()


def test_completed_invalid_native_and_inconsistent_bound_are_fatal(tmp_path):
    trace=SimpleNamespace(calls=1,last=({'id':1},dict(status='completed')))
    def bad(*args,**kwargs):return [],dict(selected_plan_bound=dict(status='unavailable'),solver_diagnostics=dict(native_error_type='ValueError'))
    with pytest.raises(ValueError,match='failed admission'):q.Guarded(bad,tmp_path,trace)()
    assert (tmp_path/'native_invalid_0001.json').exists()
    with pytest.raises(ValueError,match='Inconsistent'):q.Guarded(lambda: ([],dict(selected_plan_bound=dict(status='inconsistent_dual'))),tmp_path)()
