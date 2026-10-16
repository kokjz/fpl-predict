"""Bounded serial JSON transport for optional trusted research workers."""
import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path
from native_solver_worker import MAX_MESSAGE,read_json

class NativeTransportError(RuntimeError):pass


class JsonProcess:
    """One serial JSON worker; inherits the supervisor's process group."""
    def __init__(self,argv,cwd,log_path,*,site_packages=None,startup_timeout=30.):
        self.process=None;self.stream=None;self.reader=None;self.lock=threading.Lock();self.messages=queue.Queue(maxsize=4);self.closed=False
        path=Path(log_path);path.parent.mkdir(parents=True,exist_ok=True);self.stream=path.open('xb')
        env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','SYSTEMROOT','TMP','TEMP','TMPDIR')}
        env.update(OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',VECLIB_MAXIMUM_THREADS='2',PYTHONUNBUFFERED='1')
        if site_packages is not None:env['PYTHONPATH']=str(Path(site_packages).resolve())
        tick=time.monotonic()
        try:
            self.process=subprocess.Popen([str(v) for v in argv],cwd=cwd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stream)
            self.reader=threading.Thread(target=self._read,daemon=True);self.reader.start()
            self.metadata=self._receive(startup_timeout)
            self.startup_seconds=time.monotonic()-tick
        except Exception:
            self.close();raise

    def _read(self):
        try:
            while raw:=self.process.stdout.readline(MAX_MESSAGE+1):
                if len(raw)>MAX_MESSAGE or not raw.endswith(b'\n'):raise NativeTransportError('Oversized or incomplete native response')
                self.messages.put(raw,timeout=.2)
            self.messages.put(NativeTransportError('Native worker exited'),timeout=.2)
        except Exception as error:
            try:self.messages.put(error,timeout=.2)
            except queue.Full:pass

    def _receive(self,timeout):
        try:raw=self.messages.get(timeout=timeout)
        except queue.Empty:raise NativeTransportError('Native response timed out') from None
        if isinstance(raw,Exception):raise NativeTransportError('Native response stream failed') from raw
        try:value=read_json(raw)
        except (ValueError,UnicodeError):raise NativeTransportError('Invalid native JSON response') from None
        if not isinstance(value,dict):raise NativeTransportError('Native response must be an object')
        return value

    def request(self,value,*,timeout=None):
        raw=(json.dumps(value,allow_nan=False,separators=(',',':'))+'\n').encode()
        if len(raw)>MAX_MESSAGE:raise ValueError('Oversized native request')
        with self.lock:
            if self.closed or self.process.poll() is not None:raise NativeTransportError('Native worker is unavailable')
            try:
                self.process.stdin.write(raw);self.process.stdin.flush()
                return self._receive(timeout if timeout is not None else value['seconds']+5.)
            except Exception as error:
                self.close()
                if isinstance(error,NativeTransportError):raise
                raise NativeTransportError('Native request stream failed') from error

    def close(self):
        if self.closed:return
        self.closed=True
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:self.process.wait(timeout=2.)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=2.)
            if self.reader is not None:self.reader.join(timeout=.5)
            for stream in (self.process.stdin,self.process.stdout):
                if stream is not None:stream.close()
        if self.stream is not None:self.stream.close()

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
