"""Owned Git calls for a future five-role fixture integration.

This helper is intentionally unused by the existing five-role entry.  It
attests only one direct Git executable and one owned call at a time.  Git's
own loaded code and descendants, other subprocesses, and the five-role runtime
remain outside this receipt.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_io as io
from . import _anomaly_v03_reader_dependencies as dependencies
from . import _anomaly_v03_runtime as paths


FORMAT = 'anomaly-v03-preformal-owned-git-v1'
MAX_EXE = 64 * 1024**2
MAX_STDERR = 64 * 1024
MAX_RECEIPT = 16 * 1024
MAX_OUTPUT = {'head': 128, 'status': 64 * 1024,
              'source_blob': 64 * 1024**2}
FIXED_ENV = {'GIT_CONFIG_NOSYSTEM': '1',
             'GIT_CONFIG_GLOBAL': os.devnull,
             'GIT_OPTIONAL_LOCKS': '0',
             'GIT_NO_LAZY_FETCH': '1',
             'GIT_TERMINAL_PROMPT': '0',
             'LC_ALL': 'C'}
PASSTHROUGH_ENV = {'PATH', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP'}


class UnreapedGit(RuntimeError):
    """Keep the still-owned process handle available for reconciliation."""

    def __init__(self, process, reason):
        self.process = process
        super().__init__(reason)


def _policy(root, policy, *, check_current=True):
    v.require(type(policy) is dict and set(policy) == {
        'executable_path', 'executable_pin', 'executable_links',
        'revision', 'environment'},
        'owned Git policy fields')
    v.require(type(policy['revision']) is str and
              re.fullmatch('[0-9a-f]{40}', policy['revision']) is not None,
              'owned Git revision')
    evidence._pin(policy['executable_pin'])
    v.require(type(policy['executable_links']) is int and
              1 <= policy['executable_links'] <= 16,
              'owned Git externally expected hardlink count')
    executable = Path(policy['executable_path'])
    v.require(executable.is_absolute() and executable.name.casefold() ==
              ('git.exe' if os.name == 'nt' else 'git'),
              'owned Git executable path')
    root = paths.regular_path(Path(root), directory=True)
    environment = policy['environment']
    v.require(type(environment) is dict and
              set(FIXED_ENV) <= set(environment) <=
              set(FIXED_ENV) | PASSTHROUGH_ENV and
              all(type(key) is str and type(value) is str and
                  '\x00' not in key + value and len(value) <= 32768
                  for key, value in environment.items()) and
              len(v.canonical_json(environment)) <= 4096 and
              all(environment[key] == value
                  for key, value in FIXED_ENV.items()) and
              type(environment.get('PATH')) is str and environment['PATH'],
              'owned Git exact environment')
    before = None
    if check_current:
        executable = paths.regular_path(executable,
                                        links=policy['executable_links'])
        resolved = shutil.which('git.exe' if os.name == 'nt' else 'git',
                                path=environment['PATH'])
        v.require(resolved is not None and
                  os.path.samefile(resolved, executable),
                  'Git PATH resolves to unexpected program')
        before = dependencies.file_observation(executable, native=True,
                                               maximum=MAX_EXE)
        v.require(before['pin'] == policy['executable_pin'] and
                  before['identity']['links'] == policy['executable_links'],
                  'externally pinned Git executable changed')
    return root, executable, dict(environment), before


def _command(policy, operation, source_path, expected_output_pin):
    v.require(operation in MAX_OUTPUT, 'owned Git operation allowlist')
    if operation == 'source_blob':
        v.safe_relative_path(source_path)
        v.require(type(source_path) is str and source_path.startswith('src/'),
                  'owned Git source path')
        evidence._pin(expected_output_pin)
        v.require(expected_output_pin['bytes'] <= MAX_OUTPUT[operation],
                  'owned Git expected blob size')
        command = ['show', policy['revision'] + ':' + source_path]
    else:
        v.require(source_path is None and expected_output_pin is None,
                  'owned Git nonblob arguments')
        command = (['rev-parse', 'HEAD'] if operation == 'head' else
                   ['status', '--porcelain'])
    return command


def _identity(process):
    if os.name == 'nt':
        return {**observed.creation_observation(process.pid, process._handle),
                'native_start_identity_authenticated': True}
    return {'pid': process.pid, 'start_token': None,
            'native_start_identity_authenticated': False}


def _pin_output(path, maximum):
    value = paths.regular_path(path)
    size = value.stat().st_size
    if size > maximum:
        return None, size
    raw = observed._file(value, maximum)
    return {'bytes': len(raw), 'sha256': observed._pin(raw)['sha256']}, size


def run_owned(*, root, policy, operation, receipt_root,
              source_path=None, expected_output_pin=None, timeout_seconds=10):
    """Run one allowlisted Git command; save its independent direct-handle facts.

    The executable pin and environment come from the caller.  A failed
    subprocess still gets a bounded receipt when its handle is reaped.
    """
    v.require(type(timeout_seconds) in (int, float) and
              0 < timeout_seconds <= 30, 'owned Git timeout')
    root, executable, environment, before = _policy(root, policy)
    command = _command(policy, operation, source_path, expected_output_pin)
    argv = [str(executable), '-c', 'core.fsmonitor=false',
            '-c', 'core.pager=cat', '-c', 'safe.directory=' + str(root),
            '-C', str(root), *command]
    target = Path(receipt_root)
    v.require(target.is_absolute(), 'owned Git receipt root absolute')
    paths.regular_path(target.parent, directory=True)
    paths.regular_path(target, directory=True, missing=True)
    target.mkdir()
    stdout_path, stderr_path = target / 'stdout.bin', target / 'stderr.bin'
    process = None
    identity = None
    exit_code = None
    reason = None
    process_error_type = None
    started = time.monotonic()
    try:
        with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
            try:
                process = subprocess.Popen(
                    argv, cwd=root, env=environment, stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, shell=False, close_fds=True,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                identity = _identity(process)
                deadline = started + timeout_seconds
                while process.poll() is None:
                    if (stdout_path.stat().st_size > MAX_OUTPUT[operation] or
                            stderr_path.stat().st_size > MAX_STDERR):
                        reason = 'output_limit'
                        break
                    if time.monotonic() >= deadline:
                        reason = 'time_limit'
                        break
                    time.sleep(0.025)
                if reason is not None and process.poll() is None:
                    process.kill()
                try:
                    exit_code = process.wait(timeout=5)
                except subprocess.TimeoutExpired as error:
                    raise UnreapedGit(process, 'owned Git did not exit') from error
            except UnreapedGit:
                raise
            except BaseException as error:
                reason = reason or 'spawn_or_observation_error'
                process_error_type = type(error).__name__
                if process is not None and process.poll() is None:
                    process.kill()
                    try:
                        exit_code = process.wait(timeout=5)
                    except subprocess.TimeoutExpired as timeout:
                        raise UnreapedGit(process, 'owned Git cleanup failed') from timeout
                if process is not None and exit_code is None:
                    exit_code = process.poll()
                if type(error) not in (OSError, ValueError, TypeError):
                    raise
    finally:
        elapsed = time.monotonic() - started
    prior_stop_reason = reason
    try:
        after = dependencies.file_observation(executable, native=True,
                                              maximum=MAX_EXE)
    except (OSError, ValueError) as error:
        after = {'observation_error_type': type(error).__name__}
        reason = 'executable_after_unavailable'
    stdout_pin, stdout_bytes = _pin_output(stdout_path, MAX_OUTPUT[operation])
    stderr_pin, stderr_bytes = _pin_output(stderr_path, MAX_STDERR)
    if reason != 'executable_after_unavailable' and after != before:
        reason = 'executable_changed'
    if reason is None:
        if stdout_pin is None or stderr_pin is None:
            reason = 'output_limit'
        elif exit_code != 0:
            reason = 'exit_nonzero'
        elif stderr_bytes != 0:
            reason = 'stderr_nonempty'
        elif operation == 'head' and stdout_path.read_bytes().strip() != \
                policy['revision'].encode('ascii'):
            reason = 'revision_mismatch'
        elif operation == 'status' and stdout_bytes != 0:
            reason = 'dirty_checkout'
        elif operation == 'source_blob' and stdout_pin != expected_output_pin:
            reason = 'blob_pin_mismatch'
    receipt = {'format': FORMAT, 'status': 'verified' if reason is None else 'failed',
               'reason': reason, 'prior_stop_reason': prior_stop_reason,
               'operation': operation,
               'source_path': source_path, 'revision': policy['revision'],
               'executable_path': str(executable),
               'executable_expected_pin': policy['executable_pin'],
               'executable_links_expected': policy['executable_links'],
               'executable_before': before, 'executable_after': after,
               'argv': argv, 'cwd': str(root), 'environment': environment,
               'process_identity': identity, 'exit_code': exit_code,
               'process_error_type': process_error_type,
               'direct_process_handle_exit_confirmed': exit_code is not None,
               'elapsed_seconds': elapsed, 'stdout_pin': stdout_pin,
               'stdout_bytes': stdout_bytes, 'stderr_pin': stderr_pin,
               'stderr_bytes': stderr_bytes,
               'expected_output_pin': expected_output_pin,
               'integration_pending': True, 'formal_permission': False,
               'source_closure_complete': False,
               'runtime_closure_complete': False,
               'execution_authenticated': False}
    raw = io.json_bytes(receipt)
    v.require(len(raw) <= MAX_RECEIPT, 'owned Git receipt size')
    io._exclusive(target / 'receipt.json', raw)
    receipt_pin = observed._pin(raw)
    verify_retained(target, receipt_pin, root=root, policy=policy)
    return {'receipt': receipt, 'receipt_pin': receipt_pin,
            'receipt_root': str(target),
            'stdout': (None if stdout_pin is None else stdout_path.read_bytes())}


def verify_retained(receipt_root, expected_receipt_pin, *, root, policy):
    """Recheck saved direct process facts and output without a new Git call."""
    target = Path(receipt_root)
    v.require(target.is_absolute(), 'retained Git receipt root')
    raw = observed._file(target / 'receipt.json', MAX_RECEIPT)
    evidence._raw(raw, expected_receipt_pin, 'retained owned Git receipt')
    receipt = v.strict_json(raw)
    changed_executable = receipt['reason'] in (
        'executable_changed', 'executable_after_unavailable')
    root, executable, environment, current = _policy(
        root, policy, check_current=not changed_executable)
    v.require(receipt['format'] == FORMAT and
              receipt['integration_pending'] is True and
              all(receipt[key] is False for key in (
                  'formal_permission', 'source_closure_complete',
                  'runtime_closure_complete', 'execution_authenticated')) and
              receipt['executable_path'] == str(executable) and
              receipt['executable_expected_pin'] == policy['executable_pin'] and
              receipt['executable_links_expected'] ==
              policy['executable_links'] and
              receipt['executable_before']['pin'] == policy['executable_pin'] and
              receipt['executable_before']['identity']['links'] ==
              policy['executable_links'] and
              receipt['environment'] == environment and
              receipt['cwd'] == str(root) and
              receipt['revision'] == policy['revision'],
              'retained owned Git boundary')
    if changed_executable:
        v.require(receipt['status'] == 'failed' and
                  receipt['executable_after'] != receipt['executable_before'],
                  'retained changed Git executable failure')
    else:
        v.require(receipt['executable_before'] ==
                  receipt['executable_after'] == current,
                  'retained owned Git executable')
    command = _command(policy, receipt['operation'], receipt['source_path'],
                       receipt['expected_output_pin'])
    v.require(receipt['argv'] == [str(executable), '-c', 'core.fsmonitor=false',
                                  '-c', 'core.pager=cat',
                                  '-c', 'safe.directory=' + str(root),
                                  '-C', str(root), *command],
              'retained owned Git argv')
    for name, maximum in (('stdout', MAX_OUTPUT[receipt['operation']]),
                          ('stderr', MAX_STDERR)):
        pin, size = _pin_output(target / (name + '.bin'), maximum)
        v.require(pin == receipt[name + '_pin'] and
                  size == receipt[name + '_bytes'],
                  'retained owned Git ' + name)
    if receipt['direct_process_handle_exit_confirmed'] is True:
        v.require(type(receipt['exit_code']) is int,
                  'retained owned Git exit code')
        if receipt['process_identity'] is None:
            v.require(receipt['status'] == 'failed' and
                      receipt['reason'] in (
                          'spawn_or_observation_error',
                          'executable_changed',
                          'executable_after_unavailable') and
                      type(receipt['process_error_type']) is str,
                      'retained owned Git identity observation failure')
        else:
            v.require(type(receipt['process_identity']) is dict and
                      type(receipt['process_identity'].get('pid')) is int and
                      receipt['process_identity']['pid'] > 0,
                      'retained owned Git process handle')
    else:
        v.require(receipt['status'] == 'failed' and
                  receipt['reason'] in (
                      'spawn_or_observation_error',
                      'executable_changed',
                      'executable_after_unavailable') and
                  receipt['exit_code'] is None and
                  type(receipt['process_error_type']) is str,
                  'retained owned Git unstarted failure')
    if receipt['status'] == 'verified':
        v.require(receipt['reason'] is None and receipt['exit_code'] == 0 and
                  receipt['prior_stop_reason'] is None and
                  receipt['process_error_type'] is None and
                  receipt['stderr_bytes'] == 0 and
                  receipt['stdout_pin'] is not None,
                  'retained owned Git successful exit')
        if receipt['operation'] == 'head':
            v.require((target / 'stdout.bin').read_bytes().strip() ==
                      policy['revision'].encode('ascii'),
                      'retained owned Git HEAD')
        elif receipt['operation'] == 'status':
            v.require(receipt['stdout_bytes'] == 0,
                      'retained owned Git clean status')
        else:
            v.require(receipt['stdout_pin'] == receipt['expected_output_pin'],
                      'retained owned Git blob pin')
    else:
        v.require(receipt['status'] == 'failed' and
                  type(receipt['reason']) is str,
                  'retained owned Git failure')
    return {'status': 'verified_retained', 'call_status': receipt['status'],
            'reason': receipt['reason'], 'formal_permission': False,
            'integration_pending': True}
