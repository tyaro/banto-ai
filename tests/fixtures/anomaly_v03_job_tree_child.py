"""Invented CLI -> grandchild only; no registered observations or publication."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time


def main(argv):
    if len(argv) != 3:
        return 2
    role, mode, directory = argv
    target = Path(directory)
    if role == 'grandchild':
        (target / 'grandchild-started.txt').write_text(str(os.getpid()), encoding='ascii')
        time.sleep(0.25 if mode == 'success' else 30)
        return 0
    if role != 'parent' or mode not in ('success', 'timeout', 'parent-fail'):
        return 2
    child = subprocess.Popen(
        [sys.executable, '-B', str(Path(__file__).resolve()),
         'grandchild', mode, str(target)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, close_fds=True,
        creationflags=subprocess.CREATE_NO_WINDOW)
    (target / 'parent-started.txt').write_text(
        f'{os.getpid()}:{child.pid}', encoding='ascii')
    if mode == 'success':
        return child.wait(timeout=10)
    if mode == 'parent-fail':
        deadline = time.monotonic() + 5
        while not (target / 'grandchild-started.txt').is_file():
            if time.monotonic() >= deadline:
                return 3
            time.sleep(0.01)
        os._exit(17)
    time.sleep(30)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
