import json
import os
from pathlib import Path
import sys

import pytest
from windows_worker_guard import run

pytestmark=pytest.mark.skipif(os.name!='nt',reason='Windows job-object qualification runs on receiving host')


def invoke(tmp_path,name,code,**kwargs):
    return run([sys.executable,'-c',code],directory=tmp_path/name,cwd=tmp_path,storage_root=tmp_path,
               min_free_bytes=1024**2,**kwargs)


def test_actual_worker_descendants_and_os_peak_are_accounted(tmp_path):
    code="import subprocess,sys; a=bytearray(24*1024**2); subprocess.run([sys.executable,'-c','import time; a=bytearray(40*1024**2); time.sleep(.2)'],check=True)"
    r=invoke(tmp_path,'descendants',code,memory_bytes=256*1024**2,seconds=10)
    assert r['status']=='completed' and r['active_processes_after']==0
    assert r['peaks']['total_processes']>=3 and r['peaks']['job_commit_bytes']>64*1024**2


def test_memory_allocation_denied_in_descendant(tmp_path):
    child="import sys;\ntry: a=bytearray(256*1024**2)\nexcept MemoryError: print('job-memory-denied',flush=True); sys.exit(42)\nsys.exit(0)"
    code="import subprocess,sys; sys.exit(subprocess.run([sys.executable,'-c',"+repr(child)+"]).returncode)"
    r=invoke(tmp_path,'memory',code,memory_bytes=96*1024**2,seconds=10)
    assert r['status']=='failed' and r['exit_code']==42
    assert 'job-memory-denied' in (tmp_path/'memory/stdout.log').read_text()
    assert r['peaks']['total_processes']>=3 and r['active_processes_after']==0
    # This host's native peak counter includes the rejected allocation attempt.
    # Allocation denial and the queried native limit establish enforcement.
    assert r['native_job_memory_limit_bytes']==96*1024**2


def test_timeout_terminates_all_descendants(tmp_path):
    code="import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); time.sleep(30)"
    r=invoke(tmp_path,'timeout',code,memory_bytes=256*1024**2,seconds=.7)
    assert r['guard_reason']=='wall_time' and r['active_processes_after']==0
    assert r['peaks']['total_processes']>=3


def test_output_growth_guard(tmp_path):
    code="from pathlib import Path; import time; Path('large.bin').write_bytes(b'x'*(2*1024**2)); time.sleep(10)"
    r=invoke(tmp_path,'growth',code,memory_bytes=256*1024**2,seconds=5,max_growth_bytes=1024**2)
    assert r['guard_reason']=='growth' and r['active_processes_after']==0
