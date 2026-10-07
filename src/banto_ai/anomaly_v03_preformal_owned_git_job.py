"""Opt-in Git containment; loaded code and individual descendant exits remain open."""
from __future__ import annotations

import os
import copy
from pathlib import Path
from types import SimpleNamespace
import time

from . import anomaly_v03_preformal_owned_git as direct
from . import anomaly_v03_preformal_job_tree_owner as owner

v, observed, dependencies, paths, io = (
    direct.v, direct.observed, direct.dependencies, direct.paths, direct.io)
JOB = 'anomaly-v03-preformal-git-job-v1'
QUIESCENCE = 'anomaly-v03-preformal-owned-git-quiescence-v1'
_FIELDS = set('''format status reason prior_stop_reason operation source_path revision
    executable_path executable_expected_pin executable_links_expected executable_before
    executable_after argv cwd environment process_identity exit_code process_error_type
    direct_process_handle_exit_confirmed elapsed_seconds stdout_pin stdout_bytes
    stderr_pin stderr_bytes expected_output_pin integration_pending formal_permission
    source_closure_complete runtime_closure_complete execution_authenticated job'''.split())


class BoundedSpoolFailure(RuntimeError):
    """Keep the original stream/block/error after uncertain output IO."""
    def __init__(self, spool, original_error):
        self.spool, self.original_error = spool, original_error
        super().__init__('bounded Git output IO is unconfirmed')


class BoundedGitSpool:
    """A byte sink for a future owned pipe reader, not a native transport.

    The last stored byte is an overflow sentinel. A caller must read at most
    next_read_size(), stop the original Job on output_limit, and retain this
    object with that native owner. EOF/stream close does not prove Job closure.
    No existing file-directed executor uses this component yet.
    """
    READ_BLOCK = 4096

    def __init__(self, stream, *, operation, output, maximum_stored_bytes,
                 checkpoint, sync):
        # Retain the caller's stream before validation or any fallible IO.
        self.stream, self.checkpoint, self.sync = stream, checkpoint, sync
        self.pending_raw = self.failure = None
        self.committed_bytes, self.stopped, self.closed = 0, False, False
        self.maximum_stored_bytes = maximum_stored_bytes
        try:
            v.require(operation in direct.MAX_OUTPUT and output in ('stdout', 'stderr'),
                      'bounded Git output operation/name')
            maximum = direct.MAX_OUTPUT[operation] if output == 'stdout' else direct.MAX_STDERR
            v.require(type(maximum_stored_bytes) is int and 0 < maximum_stored_bytes <= maximum,
                      'bounded Git output stays within existing cap')
            v.require(callable(checkpoint) and callable(sync) and
                      callable(getattr(stream, 'write', None)) and
                      callable(getattr(stream, 'flush', None)) and
                      callable(getattr(stream, 'close', None)),
                      'bounded Git original stream and shared IO callbacks')
        except BaseException as error:
            self._failed(error)

    def _failed(self, error):
        if self.failure is None:
            self.failure = BoundedSpoolFailure(self, error)
        self.stopped = True
        raise self.failure from self.failure.original_error

    def next_read_size(self):
        if self.failure is not None:
            raise self.failure
        if self.stopped or self.closed:
            return 0
        return min(self.READ_BLOCK, self.maximum_stored_bytes - self.committed_bytes)

    def append(self, raw):
        if self.failure is not None:
            raise self.failure
        # Keep even an invalid/overlong original block before diagnostics.
        self.pending_raw = raw
        try:
            amount = self.next_read_size()
            v.require(type(raw) is bytes and 0 < len(raw) <= amount,
                      'bounded Git pipe read exceeded original allowance')
            self.checkpoint()
            written = self.stream.write(raw)
            v.require(type(written) is int and written == len(raw),
                      'bounded Git short/unknown output write')
            self.committed_bytes += written
            self.stream.flush()
            self.sync()
            self.checkpoint()
            self.pending_raw = None
            if self.committed_bytes == self.maximum_stored_bytes:
                self.stopped = True
                return 'output_limit'
            return None
        except BaseException as error:
            self._failed(error)

    def finish_eof(self):
        if self.failure is not None:
            raise self.failure
        if self.closed:
            return
        try:
            v.require(not self.stopped and self.pending_raw is None,
                      'bounded Git stopped/uncertain stream is retained')
            self.checkpoint()
            self.stream.flush()
            self.sync()
            self.stream.close()
            v.require(getattr(self.stream, 'closed', None) is True,
                      'bounded Git original output close unconfirmed')
            self.closed = True
            self.checkpoint()
        except BaseException as error:
            self._failed(error)


class GitOutputOwnerFailure(RuntimeError):
    """Retain IO inputs even when the supplied native owner is invalid."""
    def __init__(self, output_owner, original_error):
        self.output_owner, self.original_error = output_owner, original_error
        super().__init__('Git output ownership is unconfirmed')


class GitOutputOwner:
    """Hold separate pipe readers/sinks with the original native exception.

    This boundary neither creates nor reads/closes a native pipe. A future
    adapter must retain each observed block here before fallible spool IO.
    ChildGitKeeper stops/reaps, but keeps core handles while this IO is held.
    No declaration on this object authorizes release, a lease or an ack.
    """
    def __init__(self, native_owner, *, read_handles, spools, checkpoint):
        self.native_owner = native_owner
        self.original_read_handles, self.original_spools = read_handles, spools
        self.read_handles, self.spools, self.checkpoint = read_handles, spools, checkpoint
        self.previous_owner = self.pending = self.rejected_raw = self.error = None
        try:
            v.require(type(native_owner) in (owner.UnreapedJob, owner.UnclosedHandles),
                      'Git output original native owner')
            self.previous_owner = getattr(native_owner, 'git_output_owner', None)
            native_owner.git_output_owner = self  # Before validation/clock/read/diagnostic IO.
            # Fix exact dict inputs even when a later validation rejects them.
            # Retain the original mappings too, before this potentially failing copy.
            if type(read_handles) is dict:
                self.read_handles = dict(read_handles)
            if type(spools) is dict:
                self.spools = dict(spools)
            v.require(self.previous_owner is None, 'Git output owner cannot be rebound')
            v.require(type(read_handles) is dict and set(read_handles) == {'stdout', 'stderr'} and
                      all(type(n) is int and 0 < n < 2**64 for n in read_handles.values()) and
                      len(set(read_handles.values())) == 2, 'Git output separate original read handles')
            core = (dict(native_owner.handles) if type(native_owner) is owner.UnclosedHandles else
                    {'job':native_owner.job,'process':native_owner.process,'thread':native_owner.thread,
                     **native_owner.extra_handles})
            v.require(not set(read_handles.values()) & set(core.values()),
                      'Git output read handles must not alias core/inherited handles')
            v.require(type(spools) is dict and set(spools) == {'stdout', 'stderr'} and
                      all(type(s) is BoundedGitSpool for s in spools.values()) and
                      spools['stdout'] is not spools['stderr'] and
                      spools['stdout'].stream is not spools['stderr'].stream and callable(checkpoint),
                      'Git output original separate sinks and shared checkpoint')
        except BaseException as error:
            self._failed(error)

    def _failed(self, error):
        if self.error is None:
            self.error = error
        if type(self.native_owner) in (owner.UnreapedJob, owner.UnclosedHandles):
            self.native_owner.git_output_error = self.error
            raise self.native_owner from self.error
        raise GitOutputOwnerFailure(self, self.error) from self.error

    def begin_read(self, output):
        if self.error is not None:
            self._failed(self.error)
        try:
            v.require(self.pending is None and output in ('stdout', 'stderr'),
                      'Git output no second read while original block is pending')
            self.pending = {'output':output,'handle':self.read_handles[output],
                            'spool':self.spools[output],'amount':None,'raw':None}
            self.pending['amount'] = self.spools[output].next_read_size()
            v.require(self.pending['amount'] > 0, 'Git output no read after limit/close')
            self.checkpoint()
            return self.pending['handle'], self.pending['amount']
        except BaseException as error:
            self._failed(error)

    def retain_read(self, raw):
        if self.error is not None:
            self._failed(self.error)
        try:
            if self.pending is None or self.pending['raw'] is not None:
                self.rejected_raw = raw  # Keep the new block without replacing an earlier one.
                v.require(False, 'Git output missing/duplicate original read observation')
            self.pending['raw'] = raw  # Before any validation or consumer IO.
            v.require(type(raw) is bytes and len(raw) <= self.pending['amount'],
                      'Git output observed read exceeded original allowance')
            return self.pending
        except BaseException as error:
            self._failed(error)


def _shared_stop(probe):
    stop = probe() if probe is not None else None
    v.require(stop is None or (type(stop) is str and 0 < len(stop) <= 128),
              'owned Git shared stop probe result')
    return stop


def _execute(argv, root, environment, target, operation, timeout_seconds, *, stop_probe=None,
             capture_quiescence=False):
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
            if _shared_stop(stop_probe) is not None:
                reason = 'shared_budget_stop'
            else:
                owner._need(k.ResumeThread(thread) == 1, 'ResumeThread Git')
                resumed = True
            while reason is None:
                if _shared_stop(stop_probe) is not None:
                    reason = 'shared_budget_stop'
                    break
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
                retained = owner.UnreapedJob(job, process, thread, {
                    'status':'failed', 'phase':'git_reap',
                    'job_accounting':accounting, 'root_exit_code':exit_code,
                    'formal_permission':False})
                retained.original_error = error
                try:
                    owner._need(k.TerminateJobObject(job, 0xE008), 'TerminateJobObject Git cleanup')
                except BaseException as stop_error:
                    retained.stop_error = stop_error
                raise retained from error
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
    closed = owner._close_owned(k, job, process, thread, {
        'status':'failed' if reason is not None else 'complete',
        'stop_reason':reason, 'job':fact, 'formal_permission':False})
    if critical is not None:
        raise critical
    result = (identity, exit_code, reason, error_type, fact, time.monotonic() - started)
    if capture_quiescence:
        # This event exists only after the original native close path returned.
        event = {'closed':closed, 'process_identity':copy.deepcopy(identity),
                 'exit_code':exit_code, 'accounting':copy.deepcopy(accounting)}
        return (*result, event)
    return result


def run_owned(*, root, policy, operation, receipt_root, source_path=None,
              expected_output_pin=None, timeout_seconds=10, stop_probe=None,
              capture_quiescence=False):
    v.require(type(timeout_seconds) in (int, float) and 0 < timeout_seconds <= 30,
              'owned Git timeout')
    v.require(stop_probe is None or callable(stop_probe), 'owned Git shared stop probe')
    v.require(type(capture_quiescence) is bool, 'owned Git explicit quiescence capture option')
    root, executable, environment, before = direct._policy(root, policy)
    v.require(policy.get('process_ownership') == direct.JOB_OWNERSHIP,
              'owned Git Job opt-in required')
    if os.name != 'nt':
        raise OSError('owned Git private Job requires Windows')
    command = direct._command(policy, operation, source_path, expected_output_pin)
    stop = _shared_stop(stop_probe)
    if stop is not None:
        raise owner.resources.ResourceStop(stop)
    argv = [str(executable), '-c', 'core.fsmonitor=false', '-c', 'core.pager=cat',
            '-c', 'safe.directory=' + str(root), '-C', str(root), *command]
    target = Path(receipt_root)
    v.require(target.is_absolute(), 'owned Git receipt root absolute')
    paths.regular_path(target.parent, directory=True)
    paths.regular_path(target, directory=True, missing=True)
    target.mkdir()
    execution = _execute(
        argv, root, environment, target, operation, timeout_seconds,
        **({'stop_probe': stop_probe} if stop_probe is not None else {}),
        **({'capture_quiescence':True} if capture_quiescence else {}))
    identity, exit_code, reason, error_type, job, elapsed = execution[:6]
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
    result = {'receipt':receipt, 'receipt_pin':pin, 'receipt_root':str(target),
              'stdout':None if stdout_pin is None else (target/'stdout.bin').read_bytes()}
    if capture_quiescence:
        event = execution[6]
        witness = {'format':QUIESCENCE, 'receipt_pin':pin, 'closed':event['closed'],
                   'process_identity':event['process_identity'], 'exit_code':event['exit_code'],
                   'accounting':event['accounting'], 'formal_permission':False}
        _verify_close_link(raw, pin, witness)  # Full retained verification just passed above.
        result['quiescence'] = witness
    return result


def verify_quiescence(receipt_raw, expected_receipt_pin, witness, *, root, policy,
                      stdout_raw, stderr_raw):
    """Verify retained receipt/output/policy and its linked post-close event.

    This consistency check does not authenticate loaded code or grant S4 credit.
    """
    direct.verify_raw(receipt_raw, expected_receipt_pin, stdout_raw=stdout_raw,
                      stderr_raw=stderr_raw, root=root, policy=policy)
    return _verify_close_link(receipt_raw, expected_receipt_pin, witness)


def _verify_close_link(receipt_raw, expected_receipt_pin, witness):
    direct.evidence._raw(receipt_raw, expected_receipt_pin, 'quiescent Git receipt pin')
    receipt = v.strict_json(receipt_raw)
    v.require(io.json_bytes(receipt) == receipt_raw and receipt['format'] == direct.JOB_FORMAT,
              'quiescent Git canonical private Job receipt')
    verify_job(receipt)
    v.require(type(witness) is dict and set(witness) == {
        'format','receipt_pin','closed','process_identity','exit_code','accounting','formal_permission'} and
        witness['format'] == QUIESCENCE and witness['receipt_pin'] == expected_receipt_pin and
        witness['formal_permission'] is False, 'quiescent Git exact witness')
    closed = witness['closed']
    v.require(type(closed) is dict and set(closed) == {'format','closed_handles'} and
        closed['format'] == 'anomaly-v03-owned-handles-closed-v1', 'quiescent Git close event')
    handles = closed['closed_handles']
    v.require(type(handles) is dict and set(handles) == {'thread','process','job'} and
        all(type(n) is int and 0 < n < 2**64 for n in handles.values()) and
        len(set(handles.values())) == 3, 'quiescent Git original distinct closed handles')
    identity = receipt['process_identity']
    v.require(type(identity) is dict and set(identity) == {
        'pid','creation_time_100ns','start_token','native_start_identity_authenticated'} and
        type(identity['pid']) is int and identity['pid'] > 0 and
        type(identity['creation_time_100ns']) is int and identity['creation_time_100ns'] > 0 and
        identity['native_start_identity_authenticated'] is True and
        identity['start_token'] == v.canonical_sha256({key:identity[key] for key in ('pid','creation_time_100ns')}),
        'quiescent Git original native identity')
    v.require(receipt['job'] is not None and type(receipt['exit_code']) is int and
        io.json_bytes(witness['process_identity']) == io.json_bytes(identity) and
        type(witness['exit_code']) is int and witness['exit_code'] == receipt['exit_code'] and
        io.json_bytes(witness['accounting']) == io.json_bytes(receipt['job']['accounting']),
        'quiescent Git receipt/event identity and empty Job')
    return True


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
