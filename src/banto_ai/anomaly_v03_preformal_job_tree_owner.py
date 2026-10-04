"""Own one invented Windows CLI tree with a private Job Object.

This is a 26H2 engineering fixture, separate from the formal runner and the
existing one-process supervisor.  Job accounting confirms that every process
*in this job* has exited; it does not authenticate individual descendant exit
codes, processes created outside the job, or an S4 resource budget.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes as w
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

from . import anomaly_v03_platform_fixture_runtime as runtime


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'tests' / 'fixtures' / 'anomaly_v03_job_tree_child.py'
CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x00001000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102
STILL_ACTIVE = 259


class _BasicLimit(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64),
                ('PerJobUserTimeLimit', ctypes.c_int64),
                ('LimitFlags', w.DWORD),
                ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t),
                ('ActiveProcessLimit', w.DWORD),
                ('Affinity', ctypes.c_size_t),
                ('PriorityClass', w.DWORD),
                ('SchedulingClass', w.DWORD)]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in (
        'ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
        'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class _ExtendedLimit(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', _BasicLimit),
                ('IoInfo', _IoCounters),
                ('ProcessMemoryLimit', ctypes.c_size_t),
                ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t),
                ('PeakJobMemoryUsed', ctypes.c_size_t)]


class _BasicAccounting(ctypes.Structure):
    _fields_ = [('TotalUserTime', ctypes.c_int64),
                ('TotalKernelTime', ctypes.c_int64),
                ('ThisPeriodTotalUserTime', ctypes.c_int64),
                ('ThisPeriodTotalKernelTime', ctypes.c_int64),
                ('TotalPageFaultCount', w.DWORD),
                ('TotalProcesses', w.DWORD),
                ('ActiveProcesses', w.DWORD),
                ('TotalTerminatedProcesses', w.DWORD)]


class _StartupInfo(ctypes.Structure):
    _fields_ = [('cb', w.DWORD), ('lpReserved', w.LPWSTR),
                ('lpDesktop', w.LPWSTR), ('lpTitle', w.LPWSTR),
                ('dwX', w.DWORD), ('dwY', w.DWORD),
                ('dwXSize', w.DWORD), ('dwYSize', w.DWORD),
                ('dwXCountChars', w.DWORD), ('dwYCountChars', w.DWORD),
                ('dwFillAttribute', w.DWORD), ('dwFlags', w.DWORD),
                ('wShowWindow', w.WORD), ('cbReserved2', w.WORD),
                ('lpReserved2', ctypes.POINTER(w.BYTE)),
                ('hStdInput', w.HANDLE), ('hStdOutput', w.HANDLE),
                ('hStdError', w.HANDLE)]


class _ProcessInformation(ctypes.Structure):
    _fields_ = [('hProcess', w.HANDLE), ('hThread', w.HANDLE),
                ('dwProcessId', w.DWORD), ('dwThreadId', w.DWORD)]


class UnreapedJob(RuntimeError):
    """The caller retains native handles when all job members are unconfirmed."""

    def __init__(self, job, process, thread, report):
        self.job, self.process, self.thread, self.report = job, process, thread, report
        super().__init__('owned Job process exit could not be confirmed')


class UnclosedHandles(RuntimeError):
    """Preserve exact native handles if CloseHandle fails."""

    def __init__(self, handles, report):
        self.handles, self.report = dict(handles), report
        super().__init__('owned Job handles could not all be closed')


def _kernel():
    if os.name != 'nt':
        raise OSError('Windows Job fixture only')
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
    k.CreateJobObjectW.restype = w.HANDLE
    k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    k.SetInformationJobObject.restype = w.BOOL
    k.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                            w.DWORD, ctypes.POINTER(w.DWORD)]
    k.QueryInformationJobObject.restype = w.BOOL
    k.CreateProcessW.argtypes = [w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                                 w.BOOL, w.DWORD, ctypes.c_void_p, w.LPCWSTR,
                                 ctypes.POINTER(_StartupInfo),
                                 ctypes.POINTER(_ProcessInformation)]
    k.CreateProcessW.restype = w.BOOL
    k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    k.AssignProcessToJobObject.restype = w.BOOL
    k.IsProcessInJob.argtypes = [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)]
    k.IsProcessInJob.restype = w.BOOL
    k.ResumeThread.argtypes = [w.HANDLE]
    k.ResumeThread.restype = w.DWORD
    k.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
    k.WaitForSingleObject.restype = w.DWORD
    k.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
    k.GetExitCodeProcess.restype = w.BOOL
    k.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
    k.TerminateJobObject.restype = w.BOOL
    k.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
    k.TerminateProcess.restype = w.BOOL
    k.CloseHandle.argtypes = [w.HANDLE]
    k.CloseHandle.restype = w.BOOL
    return k


def _need(ok, label):
    if not ok:
        raise OSError(ctypes.get_last_error(), label)


def _new_job(k):
    job = k.CreateJobObjectW(None, None)  # Unnamed: no other process joins it.
    _need(job, 'CreateJobObjectW')
    try:
        limits = _ExtendedLimit()
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        _need(k.SetInformationJobObject(job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                                        ctypes.byref(limits), ctypes.sizeof(limits)),
              'SetInformationJobObject')
        observed = _ExtendedLimit()
        _need(k.QueryInformationJobObject(job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                                          ctypes.byref(observed), ctypes.sizeof(observed),
                                          None), 'QueryInformationJobObject limits')
        flags = observed.BasicLimitInformation.LimitFlags
        _need(flags & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE and
              not flags & (JOB_OBJECT_LIMIT_BREAKAWAY_OK |
                           JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK),
              'Job limits changed')
        return job
    except BaseException as error:
        if not k.CloseHandle(job):
            raise UnclosedHandles({'job': job},
                                  {'status': 'failed', 'phase': 'new_job',
                                   'observation_error_type': type(error).__name__,
                                   'formal_permission': False}) from error
        raise


def _accounting(k, job):
    value = _BasicAccounting()
    _need(k.QueryInformationJobObject(job, JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
                                      ctypes.byref(value), ctypes.sizeof(value), None),
          'QueryInformationJobObject accounting')
    return {'total_processes': int(value.TotalProcesses),
            'active_processes': int(value.ActiveProcesses),
            'limit_terminated_processes': int(value.TotalTerminatedProcesses)}


def _root_exit(k, process):
    result = k.WaitForSingleObject(process, 0)
    if result == WAIT_TIMEOUT:
        return None
    _need(result == WAIT_OBJECT_0, 'WaitForSingleObject root')
    code = w.DWORD()
    _need(k.GetExitCodeProcess(process, ctypes.byref(code)), 'GetExitCodeProcess')
    _need(code.value != STILL_ACTIVE, 'signaled root returned STILL_ACTIVE')
    return int(code.value)


def _wait_empty(k, job, process, deadline):
    """Wait for both empty Job accounting and the owned root process handle."""
    last = None
    while time.monotonic() < deadline:
        last = _accounting(k, job)
        exit_code = _root_exit(k, process)
        if last['active_processes'] == 0 and exit_code is not None:
            return last, exit_code
        time.sleep(0.025)
    last = _accounting(k, job)
    return last, _root_exit(k, process)


def _grandchild_started(evidence_dir, root_pid, accounting):
    """Check two bounded, post-exit fixture markers against Job accounting."""
    if root_pid is None or accounting is None or accounting['total_processes'] < 2:
        return False
    raws = []
    for name in ('parent-started.txt', 'grandchild-started.txt'):
        path = evidence_dir / name
        try:
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_size > 32 or
                    info.st_nlink != 1 or
                    getattr(info, 'st_file_attributes', 0) & 0x400):
                return False
            raws.append(path.read_bytes())
        except OSError:
            return False
    if re.fullmatch(rb'[1-9][0-9]{0,9}:[1-9][0-9]{0,9}', raws[0]) is None or \
            re.fullmatch(rb'[1-9][0-9]{0,9}', raws[1]) is None:
        return False
    parent, child = (int(value) for value in raws[0].split(b':'))
    return parent == root_pid and child == int(raws[1]) and child != root_pid


def run_fixture(evidence_dir, *, mode, wall_seconds=5.0,
                cleanup_seconds=5.0):
    """Run only the invented fixture; no arbitrary CLI or registered input.

    A new Job is configured before the suspended root is assigned and resumed.
    On timeout, a nonzero root exit, or any observation failure, terminate the
    Job and confirm ActiveProcesses==0 before returning a failed report.  If
    that cannot be confirmed, raise with all still-owned handles retained.
    """
    if mode not in ('success', 'timeout', 'parent-fail'):
        raise ValueError('invented Job fixture mode')
    if type(wall_seconds) not in (int, float) or not math.isfinite(wall_seconds) or wall_seconds <= 0:
        raise ValueError('positive finite Job fixture wall seconds')
    if type(cleanup_seconds) not in (int, float) or not math.isfinite(cleanup_seconds) or cleanup_seconds <= 0:
        raise ValueError('positive finite Job fixture cleanup seconds')
    evidence_dir = Path(evidence_dir).resolve(strict=True)
    if not evidence_dir.is_dir() or any(evidence_dir.iterdir()):
        raise ValueError('empty invented evidence directory required')
    if not FIXTURE.is_file():
        raise FileNotFoundError(FIXTURE)
    before = runtime.probe_runtime(ROOT)
    k = _kernel()
    job = _new_job(k)
    process = thread = None
    started = time.monotonic()
    root_pid = None
    root_resumed = assigned = False
    exit_code = None
    reason = None
    observation_error = None
    accounting = None
    try:
        args = [sys.executable, '-B', str(FIXTURE), 'parent', mode,
                str(evidence_dir)]
        startup = _StartupInfo()
        startup.cb = ctypes.sizeof(startup)
        created = _ProcessInformation()
        command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(args))
        _need(k.CreateProcessW(sys.executable, command_line, None, None,
                               False, CREATE_SUSPENDED | CREATE_NO_WINDOW,
                               None, str(ROOT), ctypes.byref(startup),
                               ctypes.byref(created)), 'CreateProcessW')
        process, thread, root_pid = created.hProcess, created.hThread, int(created.dwProcessId)
        _need(k.AssignProcessToJobObject(job, process), 'AssignProcessToJobObject')
        member = w.BOOL()
        _need(k.IsProcessInJob(process, job, ctypes.byref(member)) and member.value,
              'IsProcessInJob')
        assigned = True
        _need(k.ResumeThread(thread) == 1, 'ResumeThread')
        root_resumed = True
        while True:
            accounting = _accounting(k, job)
            exit_code = _root_exit(k, process)
            if exit_code is not None and exit_code != 0:
                reason = 'root_exit_nonzero'
                break
            if accounting['active_processes'] == 0:
                break
            if time.monotonic() - started >= wall_seconds:
                reason = 'wall_limit'
                break
            time.sleep(0.025)
        if reason is None:
            after = runtime.probe_runtime(ROOT)
            if after != before:
                reason = 'runtime_changed'
        if reason is not None:
            _need(k.TerminateJobObject(job, 0xE001), 'TerminateJobObject')
    except BaseException as error:
        reason = reason or 'observation_error'
        observation_error = type(error).__name__
        if process is not None:
            try:
                if assigned:
                    _need(k.TerminateJobObject(job, 0xE002), 'TerminateJobObject after error')
                else:
                    _need(k.TerminateProcess(process, 0xE003), 'TerminateProcess suspended root')
            except BaseException as stop_error:
                observation_error += ':' + type(stop_error).__name__
    finally:
        if process is not None:
            try:
                if assigned:
                    accounting, exit_code = _wait_empty(
                        k, job, process, time.monotonic() + cleanup_seconds)
                else:
                    wait = k.WaitForSingleObject(process, int(cleanup_seconds * 1000))
                    if wait == WAIT_OBJECT_0:
                        exit_code = _root_exit(k, process)
                    accounting = _accounting(k, job)
            except BaseException as error:
                observation_error = (observation_error + ':' if observation_error else '') + type(error).__name__
    elapsed = time.monotonic() - started
    confirmed = (process is None or
                 (exit_code is not None and accounting is not None and
                  accounting['active_processes'] == 0))
    tree_exit_confirmed = (assigned and exit_code is not None and
                           accounting is not None and
                           accounting['active_processes'] == 0)
    grandchild_started = (_grandchild_started(evidence_dir, root_pid, accounting)
                          if tree_exit_confirmed else False)
    if tree_exit_confirmed and exit_code == 0 and reason is None and not grandchild_started:
        reason = 'grandchild_start_unconfirmed'
    report = {'format': 'anomaly-v03-preformal-job-tree-owner-v1',
              'scope': 'invented-26h2-job-fixture-only',
              'mode': mode, 'status': 'complete' if
              (tree_exit_confirmed and root_resumed and grandchild_started and
               exit_code == 0 and
               reason is None and observation_error is None) else 'failed',
              'root_pid': root_pid, 'root_resumed': root_resumed,
              'job_assignment_confirmed': assigned,
              'root_exit_code': exit_code,
              'job_accounting': accounting,
              'job_all_assigned_processes_exit_confirmed': tree_exit_confirmed,
              'grandchild_started_confirmed': grandchild_started,
              'individual_descendant_exit_codes_authenticated': False,
              'stop_reason': reason, 'observation_error_type': observation_error,
              'elapsed_seconds': elapsed,
              'formal_permission': False, 'registered_data_read': False,
              'campaign_evaluations_credited': 0}
    if not confirmed:
        raise UnreapedJob(job, process, thread, report)
    unclosed = {}
    for name, handle in (('thread', thread), ('process', process), ('job', job)):
        if handle is not None:
            if not k.CloseHandle(handle):
                unclosed[name] = handle
    if unclosed:
        report['status'] = 'failed'
        report['observation_error_type'] = 'CloseHandle'
        report['unclosed_handles'] = sorted(unclosed)
        raise UnclosedHandles(unclosed, report)
    return report
