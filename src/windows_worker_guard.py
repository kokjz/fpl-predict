"""Windows job-object guard for explicitly authorised research workers.

Assigns a suspended launcher before execution; its Python worker/descendants
inherit the job. The OS caps aggregate committed memory, not sampled launcher
RSS. Wall time and output growth are sampled and kill the entire job.
This is resource supervision, not a filesystem/network security sandbox.
"""
from datetime import datetime, timezone
import ctypes as c
from ctypes import wintypes as w
import json
import math
import os
from pathlib import Path
import subprocess
import time

from experiment_runner import storage_state, THREAD_VARIABLES


class BasicLimits(c.Structure):
    _fields_=[('process_time',c.c_int64),('job_time',c.c_int64),('flags',w.DWORD),
              ('min_working',c.c_size_t),('max_working',c.c_size_t),('active_limit',w.DWORD),
              ('affinity',c.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]


class IO(c.Structure):
    _fields_=[(n,c.c_uint64) for n in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]


class ExtendedLimits(c.Structure):
    _fields_=[('basic',BasicLimits),('io',IO),('process_memory',c.c_size_t),
              ('job_memory',c.c_size_t),('peak_process_memory',c.c_size_t),('peak_job_memory',c.c_size_t)]


class Accounting(c.Structure):
    _fields_=[(n,c.c_int64) for n in ('user_time','kernel_time','period_user','period_kernel')]+[
              (n,w.DWORD) for n in ('faults','total_processes','active_processes','terminated_processes')]


def run(command, *, directory, cwd, storage_root, memory_bytes=4*1024**3,
        seconds=900., max_growth_bytes=256*1024**2, min_free_bytes=5*1024**3,
        baseline_bytes=None, poll=.05):
    if os.name!='nt':raise RuntimeError('This qualified backend requires Windows')
    if not command or not all(isinstance(a,str) for a in command):raise ValueError('Explicit argv required')
    if not math.isfinite(seconds) or seconds<=0 or not .01<=poll<=1:
        raise ValueError('Invalid time/poll limits')
    for v in (memory_bytes,max_growth_bytes,min_free_bytes):
        if type(v) is not int or v<=0:raise ValueError('Positive resource limits required')
    directory=Path(directory).resolve();root=Path(storage_root).resolve()
    if not directory.is_relative_to(root) or directory.exists():raise ValueError('New output below storage root required')
    directory.mkdir(parents=True);state=storage_state(root)
    baseline=state['project_bytes'] if baseline_bytes is None else baseline_bytes
    record=dict(status='starting',command=command,started_at=datetime.now(timezone.utc).isoformat(),
                memory_limit_bytes=memory_bytes,seconds_limit=seconds,max_growth_bytes=max_growth_bytes,
                storage_baseline_bytes=baseline,min_free_bytes=min_free_bytes,threads=2,
                backend='Windows job object, suspended assignment; inherited descendants; committed-memory hard cap',
                security_sandbox=False)
    def save():
        (directory/'run.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    save()
    if state['free_bytes']<min_free_bytes or state['project_bytes']-baseline>max_growth_bytes:
        record.update(status='failed',guard_reason='storage_preflight');save();return record
    import _winapi
    import msvcrt
    kernel=c.WinDLL('kernel32',use_last_error=True)
    kernel.CreateJobObjectW.argtypes=[c.c_void_p,w.LPCWSTR];kernel.CreateJobObjectW.restype=w.HANDLE
    kernel.SetInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD];kernel.SetInformationJobObject.restype=w.BOOL
    kernel.QueryInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.c_void_p];kernel.QueryInformationJobObject.restype=w.BOOL
    kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];kernel.AssignProcessToJobObject.restype=w.BOOL
    kernel.TerminateJobObject.argtypes=[w.HANDLE,w.UINT];kernel.TerminateJobObject.restype=w.BOOL
    kernel.ResumeThread.argtypes=[w.HANDLE];kernel.ResumeThread.restype=w.DWORD
    kernel.TerminateProcess.argtypes=[w.HANDLE,w.UINT];kernel.TerminateProcess.restype=w.BOOL
    kernel.CloseHandle.argtypes=[w.HANDLE];kernel.CloseHandle.restype=w.BOOL
    def checked(ok):
        if not ok:raise c.WinError(c.get_last_error())
    job=kernel.CreateJobObjectW(None,None)
    if not job:raise c.WinError(c.get_last_error())
    process=thread=None;started=False;tick=time.monotonic();reason=None
    limits=ExtendedLimits();limits.basic.flags=0x200|0x2000  # JOB_MEMORY | KILL_ON_JOB_CLOSE
    limits.job_memory=memory_bytes
    peaks=dict(job_commit_bytes=0,process_commit_bytes=0,total_processes=0)
    def query(kind,structure):
        checked(kernel.QueryInformationJobObject(job,kind,c.byref(structure),c.sizeof(structure),None))
        return structure
    try:
        checked(kernel.SetInformationJobObject(job,9,c.byref(limits),c.sizeof(limits)))
        configured=query(9,ExtendedLimits())
        if configured.job_memory!=memory_bytes or configured.basic.flags&0x2200!=0x2200:
            raise RuntimeError('Native memory/kill-on-close limits not applied')
        record['native_job_memory_limit_bytes']=configured.job_memory
        env=os.environ.copy();env.update({name:'2' for name in THREAD_VARIABLES})
        env.update(LOKY_MAX_CPU_COUNT='2',PYTHONDONTWRITEBYTECODE='1')
        with (directory/'stdout.log').open('wb') as out,(directory/'stderr.log').open('wb') as err,open(os.devnull,'rb') as inp:
            handles=[msvcrt.get_osfhandle(f.fileno()) for f in (inp,out,err)]
            for handle in handles:os.set_handle_inheritable(handle,True)
            startup=subprocess.STARTUPINFO();startup.dwFlags=subprocess.STARTF_USESTDHANDLES
            startup.hStdInput,startup.hStdOutput,startup.hStdError=handles
            try:
                process,thread,pid,tid=_winapi.CreateProcess(command[0],subprocess.list2cmdline(command),
                    None,None,True,0x4|0x08000000,env,str(Path(cwd).resolve()),startup)
            finally:
                for handle in handles:os.set_handle_inheritable(handle,False)
            checked(kernel.AssignProcessToJobObject(job,process))
            if kernel.ResumeThread(thread)==0xffffffff:raise c.WinError(c.get_last_error())
            started=True;record['launcher_pid']=pid;save();next_storage=0.
            while True:
                now=time.monotonic()-tick
                memory=query(9,ExtendedLimits());account=query(1,Accounting())
                peaks['job_commit_bytes']=max(peaks['job_commit_bytes'],memory.peak_job_memory)
                peaks['process_commit_bytes']=max(peaks['process_commit_bytes'],memory.peak_process_memory)
                peaks['total_processes']=max(peaks['total_processes'],account.total_processes)
                if now>=next_storage:
                    state=storage_state(root);next_storage=now+.1
                    if state['project_bytes']-baseline>max_growth_bytes:reason='growth'
                    if state['free_bytes']<min_free_bytes:reason='free_space'
                if now>seconds:reason='wall_time'
                if peaks['job_commit_bytes']>memory_bytes:reason='memory'
                if reason:
                    checked(kernel.TerminateJobObject(job,125))
                    _winapi.WaitForSingleObject(process,5000)
                    break
                # Observe the job, not just the launcher: orphan children cannot
                # make a successful launcher look like completed research.
                if account.active_processes==0:break
                time.sleep(poll)
            account=query(1,Accounting());memory=query(9,ExtendedLimits())
            peaks['job_commit_bytes']=max(peaks['job_commit_bytes'],memory.peak_job_memory)
            peaks['total_processes']=max(peaks['total_processes'],account.total_processes)
            if peaks['job_commit_bytes']>memory_bytes:reason=reason or 'memory'
            code=_winapi.GetExitCodeProcess(process)
            if account.active_processes:
                # Termination is asynchronous; wait for all descendants to exit.
                end=time.monotonic()+5
                while account.active_processes and time.monotonic()<end:
                    time.sleep(.02);account=query(1,Accounting())
            record.update(status='completed' if code==0 and not reason and not account.active_processes else 'failed',
                          guard_reason=reason,exit_code=code,active_processes_after=account.active_processes,
                          elapsed_seconds=time.monotonic()-tick,peaks=peaks,storage_after=storage_state(root))
    except BaseException as error:
        if process:kernel.TerminateProcess(process,126)
        kernel.TerminateJobObject(job,126)
        record.update(status='failed',guard_reason='supervisor_exception',error=repr(error),elapsed_seconds=time.monotonic()-tick)
        save();raise
    finally:
        if thread:_winapi.CloseHandle(thread)
        if process:_winapi.CloseHandle(process)
        kernel.CloseHandle(job)  # KILL_ON_JOB_CLOSE also covers parent interruption.
    save();return record
