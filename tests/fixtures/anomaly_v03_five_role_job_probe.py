"""Small invented CLI tree for the five-role Job owner's native checks."""
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
    root = Path(directory)
    if role == 'child':
        (root / f'child-{os.getpid()}.txt').write_text('started', encoding='ascii')
        time.sleep(0.2 if mode == 'success' else 30)
        return 0
    if role != 'parent' or mode not in ('success', 'parent-fail'):
        return 2
    children = [subprocess.Popen(
        [sys.executable, '-B', str(Path(__file__).resolve()),
         'child', mode, str(root)], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(5)]
    if mode == 'parent-fail':
        deadline = time.monotonic() + 5
        while len(list(root.glob('child-*.txt'))) < 5:
            if time.monotonic() >= deadline:
                return 3
            time.sleep(0.01)
        os._exit(17)
    return max(child.wait(timeout=10) for child in children)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
