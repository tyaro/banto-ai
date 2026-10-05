"""Opt-in Git containment; loaded code and individual descendant exits remain open."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
import time

from . import anomaly_v03_preformal_owned_git as direct
from . import anomaly_v03_preformal_job_tree_owner as owner

v, observed, dependencies, paths, io = (
    direct.v, direct.observed, direct.dependencies, direct.paths, direct.io)
JOB = 'anomaly-v03-preformal-git-job-v1'
_FIELDS = set('''format status reason prior_stop_reason operation source_path revision
    executable_path executable_expected_pin executable_links_expected executable_before
    executable_after argv cwd environment process_identity exit_code process_error_type
    direct_process_handle_exit_confirmed elapsed_seconds stdout_pin stdout_bytes
    stderr_pin stderr_bytes expected_output_pin integration_pending formal_permission
    source_closure_complete runtime_closure_complete execution_authenticated job'''.split())


def _execute(argv, root, environment, target, operation, timeout_seconds):
    """Retain native ownership until the root and its private Job are empty."""
    k = owner._kernel()
    job = process = thread = identity = exit_code = None
    accounting = memory = None
    assigned = resumed = False
    reason = error_type = critical = None
    errors = []
    started = time.monotonic()
    stdout_path, stderr_path = target/'stdout.bin', target/'stderr.bin'
    try:
        with open(os.devnull, 'rb') as stdin, stdout_path.open('xb') as stdout, \
                stderr_path.open('xb') as stderr:
            job, process, thread, pid = owner._spawn_cli(
                k, argv, root, stdin, stdout, stderr, environment=environment)
            assigned = True
            identity = direct._identity(SimpleNamespace(pid=pid, _handle=process))
            owner._need(k.ResumeThread(thread) == 1, 'ResumeThread Git')
            resumed = True
            while True:
                accounting = owner._accounting(k, job)
                exit_code = owner._root_exit(k, process)
                if exit_code is not None and exit_code != 0:
                    reason = 'exit_nonzero'
                    break
                if accounting['active_processes'] == 0 and exit_code is not None:
                    break
                if stdout_path.stat().st_size > direct.MAX_OUTPUT[operation] or \
                        stderr_path.stat().st_size > direct.MAX_STDERR:
                    reason = 'output_limit'
                    break
                if time.monotonic() - started >= timeout_seconds:
                    reason = 'time_limit'
                    break
                time.sleep(0.025)
    except (owner.UnreapedJob, owner.UnclosedHandles):
        raise  # A failed spawn owns its exact handles in the exception.
    except BaseException as error:
        reason = 'spawn_or_observation_error'
        error_type = type(error).__name__
        errors.append({'stage':'execution', 'error_type':error_type})
        if not isinstance(error, (OSError, ValueError, TypeError)):
            critical = error
    finally:
        if process is not None:
            try:
                # Any failed observation stops every member, including a root
                # that has not yet been resumed. Never close a live tree.
                if reason is not None:
                    owner._need(k.TerminateJobObject(job, 0xE007), 'TerminateJobObject Git')
                else:
                    accounting = owner._accounting(k, job)
                    exit_code = owner._root_exit(k, process)
                    if exit_code is None or accounting['active_processes'] != 0:
                        owner._need(k.TerminateJobObject(job, 0xE007), 'TerminateJobObject Git')
                accounting, exit_code = owner._wait_empty(
                    k, job, process, time.monotonic() + 5)
                owner._need(accounting['active_processes'] == 0 and exit_code is not None,
                            'owned Git Job empty')
            except BaseException as error:
                # A failed accounting query must still attempt to stop the
                # Job. Keep every handle when confirmation remains unavailable.
                try:
                    owner._need(k.TerminateJobObject(job, 0xE008), 'TerminateJobObject Git cleanup')
                except BaseException as stop_error:
                    error.git_stop_error = stop_error
                raise owner.UnreapedJob(job, process, thread, {
                    'status':'failed', 'phase':'git_reap',
                    'job_accounting':accounting, 'root_exit_code':exit_code,
                    'formal_permission':False}) from error
            try:
                memory = owner._job_memory(k, job)
            except BaseException as error:
                reason = reason or 'spawn_or_observation_error'
                error_type = error_type or type(error).__name__
                errors.append({'stage':'job_memory', 'error_type':type(error).__name__})
    fact = None if not assigned else {
        'format':JOB, 'assignment_confirmed':True, 'root_resumed':resumed,
        'accounting':accounting, 'memory':memory,
        'all_assigned_processes_exit_confirmed':True,
        'individual_descendant_exit_codes_authenticated':False,
        'loaded_code_authenticated':False, 'whole_tree_resource_budget_measured':False,
        'observation_errors':errors}
    owner._close_owned(k, job, process, thread, {
        'status':'failed' if reason is not None else 'complete',
        'stop_reason':reason, 'job':fact, 'formal_permission':False})
    if critical is not None:
        raise critical
    return identity, exit_code, reason, error_type, fact, time.monotonic() - started


def run_owned(*, root, policy, operation, receipt_root, source_path=None,
              expected_output_pin=None, timeout_seconds=10):
    v.require(type(timeout_seconds) in (int, float) and 0 < timeout_seconds <= 30,
              'owned Git timeout')
    root, executable, environment, before = direct._policy(root, policy)
    v.require(policy.get('process_ownership') == direct.JOB_OWNERSHIP,
              'owned Git Job opt-in required')
    if os.name != 'nt':
        raise OSError('owned Git private Job requires Windows')
    command = direct._command(policy, operation, source_path, expected_output_pin)
    argv = [str(executable), '-c', 'core.fsmonitor=false', '-c', 'core.pager=cat',
            '-c', 'safe.directory=' + str(root), '-C', str(root), *command]
    target = Path(receipt_root)
    v.require(target.is_absolute(), 'owned Git receipt root absolute')
    paths.regular_path(target.parent, directory=True)
    paths.regular_path(target, directory=True, missing=True)
    target.mkdir()
    identity, exit_code, reason, error_type, job, elapsed = _execute(
        argv, root, environment, target, operation, timeout_seconds)
    prior_stop_reason = reason
    try:
        after = dependencies.file_observation(executable, native=True, maximum=direct.MAX_EXE)
    except (OSError, ValueError) as error:
        after = {'observation_error_type':type(error).__name__}
        reason = 'executable_after_unavailable'
    stdout_pin, stdout_bytes = direct._pin_output(target/'stdout.bin', direct.MAX_OUTPUT[operation])
    stderr_pin, stderr_bytes = direct._pin_output(target/'stderr.bin', direct.MAX_STDERR)
    if reason != 'executable_after_unavailable' and after != before:
        reason = 'executable_changed'
    if reason is None:
        if stdout_pin is None or stderr_pin is None:
            reason = 'output_limit'
        elif exit_code != 0:
            reason = 'exit_nonzero'
        elif stderr_bytes != 0:
            reason = 'stderr_nonempty'
        elif operation == 'head' and (target/'stdout.bin').read_bytes().strip() != policy['revision'].encode():
            reason = 'revision_mismatch'
        elif operation == 'status' and stdout_bytes != 0:
            reason = 'dirty_checkout'
        elif operation == 'source_blob' and stdout_pin != expected_output_pin:
            reason = 'blob_pin_mismatch'
    receipt = {'format':direct.JOB_FORMAT, 'status':'verified' if reason is None else 'failed',
        'reason':reason, 'prior_stop_reason':prior_stop_reason, 'operation':operation,
        'source_path':source_path, 'revision':policy['revision'],
        'executable_path':str(executable), 'executable_expected_pin':policy['executable_pin'],
        'executable_links_expected':policy['executable_links'],
        'executable_before':before, 'executable_after':after, 'argv':argv, 'cwd':str(root),
        'environment':environment, 'process_identity':identity, 'exit_code':exit_code,
        'process_error_type':error_type, 'direct_process_handle_exit_confirmed':exit_code is not None,
        'elapsed_seconds':elapsed, 'stdout_pin':stdout_pin, 'stdout_bytes':stdout_bytes,
        'stderr_pin':stderr_pin, 'stderr_bytes':stderr_bytes,
        'expected_output_pin':expected_output_pin, 'job':job,
        'integration_pending':True, 'formal_permission':False, 'source_closure_complete':False,
        'runtime_closure_complete':False, 'execution_authenticated':False}
    raw = io.json_bytes(receipt)
    v.require(len(raw) <= direct.MAX_RECEIPT, 'owned Git receipt size')
    io._exclusive(target/'receipt.json', raw)
    pin = observed._pin(raw)
    direct.verify_retained(target, pin, root=root, policy=policy)
    return {'receipt':receipt, 'receipt_pin':pin, 'receipt_root':str(target),
            'stdout':None if stdout_pin is None else (target/'stdout.bin').read_bytes()}


def verify_job(receipt):
    """Validate saved containment facts, with no process or Job API calls."""
    v.require(set(receipt) == _FIELDS, 'retained owned Git Job receipt fields')
    job = receipt['job']
    if job is None:
        v.require(receipt['status'] == 'failed' and receipt['exit_code'] is None and
                  receipt['process_identity'] is None, 'retained unstarted Git Job')
        return
    v.require(type(job) is dict and set(job) == {
        'format','assignment_confirmed','root_resumed','accounting','memory',
        'all_assigned_processes_exit_confirmed','individual_descendant_exit_codes_authenticated',
        'loaded_code_authenticated','whole_tree_resource_budget_measured','observation_errors'} and
        job['format'] == JOB and job['assignment_confirmed'] is True and
        type(job['root_resumed']) is bool and job['all_assigned_processes_exit_confirmed'] is True and
        job['individual_descendant_exit_codes_authenticated'] is False and
        job['loaded_code_authenticated'] is False and job['whole_tree_resource_budget_measured'] is False,
        'retained Git Job scope')
    account = job['accounting']
    v.require(type(account) is dict and set(account) == {
        'total_processes','active_processes','limit_terminated_processes'} and
        all(type(n) is int and n >= 0 for n in account.values()) and
        account['total_processes'] >= 1 and account['active_processes'] == 0 and
        account['limit_terminated_processes'] <= account['total_processes'] and
        receipt['direct_process_handle_exit_confirmed'] is True,
        'retained Git Job empty accounting')
    errors = job['observation_errors']
    v.require(type(errors) is list and len(errors) <= 2 and all(
        type(row) is dict and set(row) == {'stage','error_type'} and
        row['stage'] in ('execution','job_memory') and type(row['error_type']) is str
        for row in errors), 'retained Git Job observation errors')
    if receipt['status'] == 'verified':
        v.require(job['root_resumed'] is True and not errors and
                  owner.valid_job_memory(job['memory']) and
                  account['limit_terminated_processes'] == 0 and
                  receipt['process_identity']['native_start_identity_authenticated'] is True,
                  'retained Git Job successful containment')
    else:
        v.require(job['memory'] is None or owner.valid_job_memory(job['memory']),
                  'retained failed Git Job memory')
        v.require(not errors or type(receipt['process_error_type']) is str,
                  'retained failed Git Job observation')
