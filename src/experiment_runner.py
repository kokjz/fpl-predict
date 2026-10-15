"""Sampled POSIX process-group watchdog for explicitly requested local jobs.

Not a security sandbox or an OS-guaranteed memory quota. Never starts a job by
importing this module, and never chooses or promotes a prediction model.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

THREAD_VARIABLES = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                    "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")
RESERVED = {"run.json", "stdout.log", "stderr.log"}


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def sample_group(group):
    """Observed sum of RSS for a process group; zombies do not consume RSS."""
    raw = subprocess.check_output(["ps", "-axo", "pgid=,rss=,stat="], text=True,
                                  timeout=5, stderr=subprocess.DEVNULL)
    rss = 0; processes = 0
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) >= 3 and int(fields[0]) == group and not fields[2].startswith("Z"):
            rss += int(fields[1]) * 1024; processes += 1
    return rss, processes



def storage_state(root):
    """Logical regular-file bytes, without following symlinks outside the root."""
    size = 0; pending = [Path(root)]
    while pending:
        try:
            with os.scandir(pending.pop()) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False): pending.append(Path(entry.path))
                        else: size += entry.stat(follow_symlinks=False).st_size
                    except FileNotFoundError: pass  # concurrent cache removal
        except FileNotFoundError: pass
    return dict(project_bytes=size, free_bytes=shutil.disk_usage(root).free)


def storage_exceeded(state, baseline, limits):
    return (state['project_bytes'] > limits['max_project_mib'] * 1024**2 or
            state['project_bytes'] - baseline['project_bytes'] > limits['max_growth_mib'] * 1024**2 or
            state['free_bytes'] < limits['min_free_mib'] * 1024**2)

def _stop(group, process):
    # The new session is ours, never the calling shell's process group.
    if group <= 0 or group == os.getpgrp():
        raise RuntimeError("Refusing to signal the supervisor process group")
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try: os.killpg(group, sig)
        except ProcessLookupError: pass
        if sig == signal.SIGTERM:
            try: process.wait(timeout=.3)
            except subprocess.TimeoutExpired: pass
    process.wait(timeout=5)


def _relative_outputs(outputs):
    if not isinstance(outputs, list) or not outputs or len(outputs) != len(set(outputs)):
        raise ValueError("Declare unique expected output files")
    for value in outputs:
        if not isinstance(value, str): raise ValueError("Output paths must be strings")
        path = Path(value)
        if path.is_absolute() or '..' in path.parts or path.name in RESERVED or value in ('', '.'):
            raise ValueError("Outputs must be relative files outside reserved runner names")
    return outputs


def _output_hashes(directory, outputs):
    result = {}
    for name in outputs:
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file():
            raise ValueError("Missing or escaping output artifact")
        result[name] = file_hash(path)
    return result


def run_job(argv, directory, *, inputs, outputs, threads=2, seconds=1800,
            memory_mib=4096, poll_seconds=.25, reuse_completed=False,
            storage_root=None, max_project_mib=2048, max_growth_mib=512,
            min_free_mib=5120, storage_poll_seconds=5):
    """Supervise one trusted job; separate immutable directories make folds resumable."""
    if os.name != 'posix' or not shutil.which('ps'):
        raise ValueError("This watchdog requires POSIX ps/process-group support; Windows is unsupported")
    if not isinstance(argv, list) or not argv or not all(isinstance(v, str) and v for v in argv):
        raise ValueError("argv must be a nonempty list; no shell execution is supported")
    if type(threads) is not int or not 1 <= threads <= 4:
        raise ValueError("threads must be an integer from1 to4")
    for value, maximum in ((seconds, 7200), (memory_mib, 8192), (poll_seconds, 1)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= maximum:
            raise ValueError("Invalid watchdog budget")
    for value in (max_project_mib, max_growth_mib, min_free_mib, storage_poll_seconds):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError("Invalid storage budget")
    outputs = _relative_outputs(outputs)
    if not isinstance(inputs, dict): raise ValueError("inputs must map local files to expected SHA256")
    original_count = len(inputs)
    inputs = {str(Path(p).resolve()): sha for p, sha in inputs.items()}
    if len(inputs) != original_count: raise ValueError("Aliased input paths")
    actual_inputs = {p: file_hash(p) for p in inputs}
    if actual_inputs != inputs: raise ValueError("Input checksum mismatch")
    sample_group(-1)  # Fail before launching if monitoring is unavailable.
    directory = Path(directory).resolve()
    storage_root = Path(storage_root or directory.parent).resolve()
    if not storage_root.is_dir() or not directory.is_relative_to(storage_root):
        raise ValueError("Run directory must be within an existing monitored storage root")
    disk_limits = dict(max_project_mib=max_project_mib, max_growth_mib=max_growth_mib, min_free_mib=min_free_mib)
    baseline = storage_state(storage_root)
    if storage_exceeded(baseline, baseline, disk_limits): raise ValueError("Storage budget already exceeded")
    limits = dict(threads=threads, seconds=seconds, memory_mib=memory_mib, poll_seconds=poll_seconds,
                  **disk_limits, storage_poll_seconds=storage_poll_seconds)
    runner_sha = file_hash(__file__)
    signature = _hash(dict(argv=argv, inputs=actual_inputs, outputs=outputs, limits=limits,
                           runner_sha256=runner_sha, python_version=sys.version))
    if directory.exists():
        if not reuse_completed: raise ValueError("Run directory exists; use a new destination")
        saved = json.loads((directory / 'run.json').read_text())
        if saved.get('status') != 'completed' or saved.get('signature') != signature:
            raise ValueError("Existing run is incomplete or its specification changed")
        if _output_hashes(directory, outputs) != saved.get('output_sha256'):
            raise ValueError("Completed output checksum mismatch")
        return {**saved, 'reused': True}
    directory.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    environment.update({name: str(threads) for name in THREAD_VARIABLES})
    result = dict(schema_version=1, signature=signature, command_sha256=_hash(argv),
                  input_sha256=sorted(actual_inputs.values()), limits=limits, runner_sha256=runner_sha,
                  started_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  monitoring='sampled process-group RSS; not hard OS quota or security sandbox',
                  model_promotion=False, status='launch_error', exit_code=None,
                  peak_observed_rss_bytes=0, reused=False, storage_initial=baseline,
                  peak_observed_project_bytes=baseline['project_bytes'],
                  minimum_observed_free_bytes=baseline['free_bytes'])
    process = None; start = time.monotonic(); last_storage = start
    try:
        with (directory / 'stdout.log').open('xb') as stdout, (directory / 'stderr.log').open('xb') as stderr:
            process = subprocess.Popen(argv, cwd=directory, env=environment, stdout=stdout,
                                       stderr=stderr, start_new_session=True, shell=False)
            while True:
                exit_code = process.poll()
                rss, count = sample_group(process.pid)
                result['peak_observed_rss_bytes'] = max(result['peak_observed_rss_bytes'], rss)
                elapsed = time.monotonic() - start
                if elapsed - (last_storage - start) >= storage_poll_seconds or exit_code is not None:
                    disk = storage_state(storage_root); last_storage = time.monotonic()
                    result['peak_observed_project_bytes'] = max(result['peak_observed_project_bytes'], disk['project_bytes'])
                    result['minimum_observed_free_bytes'] = min(result['minimum_observed_free_bytes'], disk['free_bytes'])
                    if storage_exceeded(disk, baseline, disk_limits):
                        result['status'] = 'storage_limit'; break
                if rss > memory_mib * 1024**2:
                    result['status'] = 'memory_limit'; break
                if elapsed >= seconds:
                    result['status'] = 'timeout'; break
                if exit_code is not None:
                    result['status'] = 'descendants_remaining' if count else ('completed' if exit_code == 0 else 'failed')
                    break
                time.sleep(poll_seconds)
    except KeyboardInterrupt:
        result['status'] = 'interrupted'
    except (OSError, subprocess.SubprocessError, ValueError):
        result['status'] = 'monitor_error' if process is not None else 'launch_error'
    finally:
        if process is not None:
            if result['status'] in ('completed', 'failed'): process.wait(timeout=5)
            else: _stop(process.pid, process)
            result['exit_code'] = process.returncode
        result['elapsed_seconds'] = time.monotonic() - start
        result['finished_at_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        if result['status'] == 'completed':
            try:
                if {p: file_hash(p) for p in inputs} != actual_inputs:
                    raise ValueError("Worker modified a declared input")
                result['output_sha256'] = _output_hashes(directory, outputs)
            except (ValueError, OSError): result['status'] = 'artifact_error'
        with (directory / 'run.json').open('x') as stream:
            stream.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True, type=Path)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--reuse-completed', action='store_true')
    parser.add_argument('--storage-root', required=True, type=Path)
    args = parser.parse_args()
    try:
        from external_benchmark import _json, _read
        spec = _json(_read(args.spec))
        inputs = {str((args.spec.parent / path).resolve()): sha for path, sha in spec['inputs'].items()}
        result = run_job(spec['argv'], args.directory, inputs=inputs, outputs=spec['outputs'],
                         **spec.get('limits', {}), storage_root=args.storage_root, reuse_completed=args.reuse_completed)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f'Experiment rejected: {exc}\n')
    print(f"Experiment status: {result['status']}; no promotion performed.")
    if result['status'] != 'completed': parser.exit(1)


if __name__ == '__main__': main()
