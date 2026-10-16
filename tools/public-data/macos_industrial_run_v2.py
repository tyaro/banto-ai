"""Capture a fresh bounded preparation process, including unsuccessful exits."""
import argparse
import os
import signal
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback
from macos_industrial_fetch import child_memory, close, digest, write


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--records', required=True)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    if a.command[:1] == ['--']: a.command.pop(0)
    root = Path(a.records); root.mkdir(parents=True, exist_ok=False)
    write(root/'command.json', a.command)
    source = {}
    for name in ('macos_industrial_run_v2.py','macos_industrial_prepare.py','industrial_data.py','macos_xjtu_7zip_prepare.py'):
        f = Path(__file__).with_name(name)
        if f.is_file():
            (root/name).write_bytes(f.read_bytes()); source[name] = digest(f)
    write(root/'source-pins.json', source)
    start = time.monotonic(); peak = {'footprint': 0, 'resident': 0}; proc = None; status = 'failed'; rc = None
    try:
        with (root/'stdout.txt').open('xb') as out, (root/'stderr.txt').open('xb') as err:
            proc = subprocess.Popen(a.command, stdout=out, stderr=err, start_new_session=True)
            while proc.poll() is None:
                if time.monotonic()-start > 870: raise TimeoutError('child 870s deadline')
                m = child_memory(proc.pid)
                if m:
                    for k in peak: peak[k] = max(peak[k],m[k])
                    if max(m.values()) > 2*1024**3: raise MemoryError('sampled child memory limit')
                if (root/'stdout.txt').stat().st_size > 1024**2 or (root/'stderr.txt').stat().st_size > 128*1024:
                    raise RuntimeError('stdio limit')
                time.sleep(.2)
            rc = proc.wait()
        status = 'complete' if rc == 0 else 'failed'
    except BaseException:
        if proc and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try: rc = proc.wait(timeout=5)
            except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL); rc = proc.wait()
        write(root/'failure.json',{'traceback':traceback.format_exc()})
    finally:
        write(root/'exit.json',{'returncode':rc,'elapsed_seconds':time.monotonic()-start,
              'sampled_child_peak':peak,'child_peak_rss_bytes':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
              'hard_os_cap':False,'parent_limit_seconds':900,'child_limit_seconds':870})
        close(root,status)
    print(json.dumps({'status':status,'returncode':rc,'records':str(root)}))
    return 0 if status == 'complete' else 1


if __name__ == '__main__': sys.exit(main())
