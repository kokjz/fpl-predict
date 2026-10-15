import json
import os
from pathlib import Path
import sys
import pytest
import experiment_runner as runner

pytestmark=pytest.mark.skipif(os.name!='posix',reason='POSIX watchdog backend')


def command(code):return [sys.executable,'-c',code]


def job(tmp_path,code="from pathlib import Path; Path('result.txt').write_text('ok')",**kwargs):
    return runner.run_job(command(code),tmp_path/'job',inputs={},outputs=['result.txt'],
                          seconds=3,poll_seconds=.02,**kwargs)


def test_completed_outputs_hashes_thread_limits_and_reuse(tmp_path):
    code="import os; from pathlib import Path; Path('result.txt').write_text(os.environ['OMP_NUM_THREADS'])"
    r=job(tmp_path,code);assert r['status']=='completed'
    assert (tmp_path/'job/result.txt').read_text()=='2'
    assert r['output_sha256']['result.txt']==runner.file_hash(tmp_path/'job/result.txt')
    assert not r['model_promotion'] and r['peak_observed_project_bytes']>=0
    again=job(tmp_path,code,reuse_completed=True);assert again['reused']
    (tmp_path/'job/result.txt').write_text('changed')
    with pytest.raises(ValueError,match='checksum'):job(tmp_path,code,reuse_completed=True)


def test_timeout_stops_and_never_caches_success(tmp_path):
    r=runner.run_job(command('import time; time.sleep(10)'),tmp_path/'job',inputs={},outputs=['x'],seconds=.15,poll_seconds=.02)
    assert r['status']=='timeout' and r['exit_code']!=0
    with pytest.raises(ValueError):job(tmp_path,reuse_completed=True)


def test_failed_worker_or_missing_artifact_never_completed(tmp_path):
    r=job(tmp_path,'raise SystemExit(9)');assert r['status']=='failed' and r['exit_code']==9
    other=tmp_path/'other';other.mkdir();r=job(other,'pass');assert r['status']=='artifact_error'


def test_sampled_memory_limit_stops_job(tmp_path,monkeypatch):
    real=runner.sample_group
    monkeypatch.setattr(runner,'sample_group',lambda group:(0,0) if group==-1 else (10*1024**2,1))
    r=job(tmp_path,'import time; time.sleep(10)',memory_mib=1)
    assert r['status']=='memory_limit'
    monkeypatch.setattr(runner,'sample_group',real)


def test_descendant_left_after_parent_exit_is_killed(tmp_path):
    code="import subprocess,sys; from pathlib import Path; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(10)']); Path('result.txt').write_text(str(p.pid))"
    r=job(tmp_path,code);assert r['status']=='descendants_remaining'
    assert 'output_sha256' not in r


def test_storage_growth_stops_without_deleting_evidence(tmp_path):
    code="from pathlib import Path; import time; Path('result.txt').write_bytes(b'x'*20000); time.sleep(10)"
    r=job(tmp_path,code,max_growth_mib=.005,storage_poll_seconds=.02)
    assert r['status']=='storage_limit'
    assert (tmp_path/'job/result.txt').exists()
    assert (tmp_path/'job/run.json').exists()


def test_initial_storage_limit_prevents_launch(tmp_path):
    with pytest.raises(ValueError,match='Storage'):
        job(tmp_path,min_free_mib=10**12)
    assert not (tmp_path/'job').exists()


def test_symlinks_are_not_followed_for_storage_or_output_escape(tmp_path):
    outside=tmp_path/'outside';outside.mkdir();(outside/'big').write_bytes(b'x'*10000)
    root=tmp_path/'root';root.mkdir();(root/'link').symlink_to(outside,target_is_directory=True)
    assert runner.storage_state(root)['project_bytes']<10000
    code="from pathlib import Path; Path('result.txt').symlink_to('../outside/big')"
    r=job(tmp_path,code);assert r['status']=='artifact_error'


@pytest.mark.parametrize('bad', [['../outside'],['/absolute'],['stdout.log'],['x','x']])
def test_invalid_outputs_fail_before_launch(tmp_path,bad):
    with pytest.raises(ValueError):runner.run_job(command('pass'),tmp_path/'job',inputs={},outputs=bad)
    assert not (tmp_path/'job').exists()


def test_input_hash_change_or_monitor_failure_never_launches(tmp_path,monkeypatch):
    source=tmp_path/'source';source.write_text('known')
    with pytest.raises(ValueError,match='checksum'):
        runner.run_job(command('pass'),tmp_path/'job',inputs={str(source):'wrong'},outputs=['x'])
    assert not (tmp_path/'job').exists()
    monkeypatch.setattr(runner,'sample_group',lambda group:(_ for _ in ()).throw(ValueError('monitor unavailable')))
    with pytest.raises(ValueError):job(tmp_path)
    assert not (tmp_path/'job').exists()


def test_monitor_loss_during_job_stops_and_records_incomplete(tmp_path,monkeypatch):
    def sample(group):
        if group==-1:return (0,0)
        raise ValueError('monitor lost')
    monkeypatch.setattr(runner,'sample_group',sample)
    r=job(tmp_path,'import time; time.sleep(10)')
    assert r['status']=='monitor_error'


def test_modified_input_invalidates_completion(tmp_path):
    source=tmp_path/'source';source.write_text('before')
    code=f"from pathlib import Path; Path({str(source)!r}).write_text('after'); Path('result.txt').write_text('ok')"
    r=runner.run_job(command(code),tmp_path/'job',inputs={str(source):runner.file_hash(source)},outputs=['result.txt'],seconds=3,poll_seconds=.02)
    assert r['status']=='artifact_error'


def test_changed_spec_cannot_reuse_completed_fold(tmp_path):
    job(tmp_path)
    with pytest.raises(ValueError,match='specification changed'):
        job(tmp_path,threads=1,reuse_completed=True)


def test_actual_process_monitor_reports_our_group():
    rss,count=runner.sample_group(os.getpgrp())
    assert rss>0 and count>0
