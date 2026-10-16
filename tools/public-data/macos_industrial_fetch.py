"""Bounded, non-overwriting official-source intake; never trains a model."""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from macos_demand_runtime import MacCheckpoint, _UsageV0, memory_observation


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def close(root, status):
    files = []
    for p in sorted(Path(root).iterdir()):
        if p.is_file():
            files.append({'name': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)})
    write(Path(root) / 'root-closed.json', {'status': status, 'files': files})


def child_memory(pid):
    u = _UsageV0()
    lib = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    fn = lib.proc_pid_rusage
    fn.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
    if fn(pid, 0, ctypes.byref(u)) != 0:
        return None
    return {'footprint': int(u.phys_footprint), 'resident': int(u.resident_size)}


def fetch(a):
    raw, records = Path(a.raw), Path(a.records)
    raw.mkdir(parents=True, exist_ok=False)
    records.mkdir(parents=True, exist_ok=False)
    source = Path(__file__)
    (records / 'source.py').write_bytes(source.read_bytes())
    write(records / 'request.json', vars(a))
    check = MacCheckpoint(seconds=900)
    part = raw / (a.name + '.partial')
    final = raw / a.name
    status, rc, proc = 'failed', None, None
    peak = {'footprint': 0, 'resident': 0}
    started = time.monotonic()
    try:
        cmd = ['curl', '--silent', '--show-error', '--fail', '--location',
               '--proto', '=https', '--proto-redir', '=https', '--connect-timeout', '20',
               '--max-time', '870', '--max-filesize', str(a.max_bytes), '--retry', '0',
               '--dump-header', str(records / 'http-headers.txt'), '--output', str(part),
               '--write-out', '%{json}', a.url]
        write(records / 'command.json', cmd)
        with (records / 'stdout.txt').open('xb') as out, (records / 'stderr.txt').open('xb') as err:
            proc = subprocess.Popen(cmd, stdout=out, stderr=err)
            while proc.poll() is None:
                check.check()
                m = child_memory(proc.pid)
                if m:
                    for k in peak: peak[k] = max(peak[k], m[k])
                    if max(m.values()) > 2 * 1024**3:
                        raise RuntimeError('curl resource limit exceeded')
                if part.exists() and part.stat().st_size > a.max_bytes:
                    raise RuntimeError('download size limit exceeded')
                if (records / 'stdout.txt').stat().st_size > 1024**2 or (records / 'stderr.txt').stat().st_size > 128*1024:
                    raise RuntimeError('stdio limit exceeded')
                time.sleep(.2)
            rc = proc.wait()
        write(records / 'exit.json', {'returncode': rc, 'elapsed_seconds': time.monotonic()-started})
        if rc != 0:
            raise RuntimeError(f'curl exit {rc}; partial bytes retained')
        http = json.loads((records / 'stdout.txt').read_text())
        if http['http_code'] != 200 or not http['url_effective'].startswith('https://'):
            raise ValueError('unexpected HTTP outcome')
        size = part.stat().st_size
        if not 0 < size <= a.max_bytes or (a.expected_bytes and size != a.expected_bytes):
            raise ValueError(f'archive length mismatch: {size}')
        sha = digest(part)
        if a.expected_sha256 and sha != a.expected_sha256:
            raise ValueError('archive digest mismatch')
        with part.open('rb') as f: magic = f.read(8)
        if a.kind == 'rar' and not magic.startswith(b'Rar!\x1a\x07'):
            raise ValueError('not a RAR archive')
        members = []
        if a.kind == 'zip':
            with zipfile.ZipFile(part) as z:
                names = set()
                for i in z.infolist():
                    if i.filename in names or i.filename.startswith('/') or '..' in Path(i.filename).parts:
                        raise ValueError('duplicate/unsafe ZIP member')
                    names.add(i.filename)
                    h, n = hashlib.sha256(), 0
                    if not i.is_dir():
                        with z.open(i) as f:
                            for b in iter(lambda: f.read(1024**2), b''):
                                check.check(); h.update(b); n += len(b)
                        if n != i.file_size: raise ValueError('member size mismatch')
                    members.append({'name': i.filename, 'bytes': i.file_size,
                                    'sha256': h.hexdigest() if not i.is_dir() else None,
                                    'crc32': f'{i.CRC:08x}'})
        # Only this fresh directory can be published; no existing path is replaced.
        if final.exists(): raise FileExistsError(final)
        os.link(part, final)
        part.unlink()
        write(raw / 'source-manifest.json', {'dataset_id': a.id, 'source_url': a.url,
              'landing_url': a.landing, 'archive': {'name': a.name, 'bytes': size, 'sha256': sha},
              'expected_pin_matched': bool(a.expected_sha256), 'members': members,
              'zip_all_members_crc_verified': a.kind == 'zip',
              'rar_multivolume_crc_verified': False if a.kind == 'rar' else None,
              'license': a.license, 'purpose': 'research intake only; no training or evaluation',
              'raw_source_input_is_not_experiment_output': True})
        status = 'complete'
    except BaseException:
        if proc and proc.poll() is None:
            proc.terminate()
            try: rc = proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); rc = proc.wait()
        write(records / 'failure.json', {'traceback': traceback.format_exc(), 'returncode': rc})
        raise
    finally:
        write(records / 'resource.json', {'parent': memory_observation(),
              'parent_sampled_peak_footprint': check.max_footprint,
              'elapsed_seconds': time.monotonic()-started, 'curl_sampled_peak': peak,
              'children_peak_rss_bytes': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
              'hard_os_cap': False})
        close(raw, status)
        close(records, status)
    print(json.dumps({'id': a.id, 'status': status, 'path': str(final), 'sha256': sha, 'bytes': size}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for k in ('id', 'raw', 'records', 'url', 'landing', 'name', 'kind', 'license'):
        p.add_argument('--'+k, required=True)
    p.add_argument('--max-bytes', type=int, default=800*1024**2)
    p.add_argument('--expected-bytes', type=int)
    p.add_argument('--expected-sha256')
    fetch(p.parse_args())
