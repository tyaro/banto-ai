"""Prepare a pinned Git input policy for a later invented five-role trial.

This is a preparation step.  It does not own the later Git calls or the
five-role Job, and its output is not source/runtime closure evidence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_owned_git as owned_git
from banto_ai import anomaly_v03_reader_evidence as observed
from banto_ai import _anomaly_v03_io as io
from banto_ai import _anomaly_v03_runtime as paths


MAX_CHECK_OUTPUT = 64 * 1024
MAX_POLICY = 8 * 1024


def _git(executable, environment, *arguments):
    completed = subprocess.run(
        [str(executable), *arguments], cwd=ROOT, env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=10, check=False,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    v.require(completed.returncode == 0 and not completed.stderr and
              len(completed.stdout) <= MAX_CHECK_OUTPUT,
              'Git policy preparation command failed')
    return completed.stdout


def _head_clean(executable, environment, revision):
    prefix = ('-c', 'core.fsmonitor=false', '-c', 'core.pager=cat',
              '-c', 'safe.directory=' + str(ROOT), '-C', str(ROOT))
    head = _git(executable, environment, *prefix, 'rev-parse', 'HEAD')
    v.require(head.strip() == revision.encode('ascii'),
              'Git policy preparation HEAD changed')
    status = _git(executable, environment, *prefix, 'status', '--porcelain')
    v.require(not status, 'Git policy preparation checkout is dirty')


def prepare_policy(*, expected_revision, output_root, git_executable=None):
    """Save one non-overwriting policy after two clean-HEAD observations."""
    owned_git.evidence._digest(expected_revision, 40)
    target = Path(output_root)
    v.require(target.is_absolute() and target.parent == ROOT / 'artifacts' and
              target.name not in ('', '.', '..'),
              'new Git policy root directly under artifacts')
    paths.regular_path(ROOT / 'artifacts', directory=True)
    paths.regular_path(target, directory=True, missing=True)
    v.require(not target.exists(), 'Git policy root already exists')

    name = 'git.exe' if os.name == 'nt' else 'git'
    if git_executable is None:
        selected = shutil.which(name, path=os.environ.get('PATH'))
        v.require(selected is not None and Path(selected).is_absolute(),
                  'PATH Git executable unavailable')
        executable = Path(selected)
    else:
        executable = Path(git_executable)
        v.require(executable.is_absolute() and
                  executable.name.casefold() == name,
                  'absolute named Git executable required')
    links = executable.lstat().st_nlink
    v.require(type(links) is int and 1 <= links <= 16,
              'Git executable hardlink count')
    executable = paths.regular_path(executable, links=links)
    before = owned_git.dependencies.file_observation(
        executable, native=True, maximum=owned_git.MAX_EXE)

    environment = dict(owned_git.FIXED_ENV)
    environment['PATH'] = str(executable.parent)
    if os.name == 'nt':
        for key in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP'):
            if os.environ.get(key):
                environment[key] = os.environ[key]
    policy = {'executable_path': str(executable),
              'executable_pin': before['pin'],
              'executable_links': links,
              'revision': expected_revision,
              'environment': environment}
    owned_git._policy(ROOT, policy)
    version = _git(executable, environment, '--version')
    v.require(re.fullmatch(rb'git version [^\r\n]+\r?\n?', version) is not None,
              'PATH program did not identify as Git')
    _head_clean(executable, environment, expected_revision)
    owned_git._policy(ROOT, policy)

    raw = io.json_bytes(policy)
    v.require(len(raw) <= MAX_POLICY, 'Git policy byte limit')
    target.mkdir()  # The attempt root is never reused or overwritten.
    path = target / 'policy.json'
    io._exclusive(path, raw)
    pin = observed._pin(raw)
    v.require(observed._file(path, MAX_POLICY) == raw,
              'saved Git policy raw changed')
    _head_clean(executable, environment, expected_revision)
    owned_git._policy(ROOT, policy)
    return {'status': 'input_policy_prepared',
            'policy_path': str(path), 'policy_pin': pin,
            'policy_bytes': pin['bytes'], 'policy_sha256': pin['sha256'],
            'source_revision': expected_revision,
            'scope': 'external-input-policy-only',
            'integration_pending': True, 'formal_permission': False,
            'source_closure_complete': False,
            'runtime_closure_complete': False,
            'execution_authenticated': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--git-executable', type=Path,
                        help='absolute Git binary to pin; defaults to PATH Git')
    args = parser.parse_args(argv)
    result = prepare_policy(expected_revision=args.revision,
                            output_root=args.output_root,
                            git_executable=args.git_executable)
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
