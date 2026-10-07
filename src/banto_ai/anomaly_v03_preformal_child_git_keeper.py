"""Retain original child Git ownership; lease/raw/proof completion is separate."""
from __future__ import annotations

import copy
import time

from . import anomaly_v03_preformal_owned_git_job as tree

owner, observed, v = tree.owner, tree.observed, tree.v


def _creation(process):
    kernel, types = observed.supervisor.resources._windows()
    kernel.GetProcessId.argtypes = [types.HANDLE]
    kernel.GetProcessId.restype = types.DWORD
    pid = int(kernel.GetProcessId(process))
    v.require(pid > 0, 'keeper original process handle PID')
    return observed.creation_observation(pid, process)


class ChildGitKeeper:
    def __init__(self, original, *, child, lease):
        v.require(isinstance(original, (owner.UnreapedJob, owner.UnclosedHandles)),
                  'keeper original native owner required')
        self.original, self.child, self.lease = original, child, lease
        self.ledger_error = None
        self.first_error = self.stop_error = self.callback_error = self.sleep_error = None
        self.close_owner = self.reaped = self.completion = None
        self.closed = {}
        self.blocked = isinstance(original, owner.UnclosedHandles)
        self.valid_extra_names = True
        if self.blocked:
            # The original Job handle may already be closed, or a close may
            # have happened without an observed return. Never blind reclose.
            self.remaining = dict(original.handles)
        else:
            self.valid_extra_names = set(original.extra_handles) <= {
                'inherited_0','inherited_1','inherited_2'}
            self.remaining = {'thread':original.thread,'process':original.process,'job':original.job,
                              **original.extra_handles}
        self.initial_handles = dict(self.remaining)
        # Retain the original, rather than propagating a plain IO/ledger error
        # that an entry point might treat as an ordinary terminal failure.
        try:
            child.stopped = True
            child.hold_owner(lease, original)
        except BaseException as failure:
            self.ledger_error = failure
            original.child_keeper = self
            raise original from failure

    def _remember(self, name, failure):
        if getattr(self, name) is None:
            setattr(self, name, failure)

    def reconcile_once(self):
        if self.completion is not None:
            return copy.deepcopy(self.completion)
        if self.blocked:
            return None
        try:
            v.require(self.valid_extra_names and {'thread','process','job'} <= set(self.initial_handles) and
                len(self.initial_handles) <= 6 and
                all(key in ('thread','process','job','inherited_0','inherited_1','inherited_2')
                    for key in self.initial_handles) and
                all(type(n) is int and 0 < n < 2**64 for n in self.initial_handles.values()) and
                len(set(self.initial_handles.values())) == len(self.initial_handles),
                'keeper bounded distinct original handles')
            kernel = owner._kernel()
            if self.reaped is None:
                try:
                    owner._need(kernel.TerminateJobObject(self.original.job, 0xE010),
                                'keeper TerminateJobObject')
                except BaseException as failure:
                    self._remember('stop_error', failure)
                # A partial spawn can own a suspended root outside the Job.
                if self.original.report.get('assignment_confirmed') is False:
                    try:
                        owner._need(kernel.TerminateProcess(self.original.process, 0xE011),
                                    'keeper TerminateProcess unassigned root')
                    except BaseException as failure:
                        self._remember('stop_error', failure)
                accounting, code = owner._wait_empty(
                    kernel, self.original.job, self.original.process, time.monotonic() + 5)
                v.require(type(accounting) is dict and set(accounting) == {
                    'total_processes','active_processes','limit_terminated_processes'} and
                    all(type(n) is int and n >= 0 for n in accounting.values()) and
                    accounting['active_processes'] == 0 and
                    accounting['limit_terminated_processes'] <= accounting['total_processes'] and
                    type(code) is int and 0 <= code < 2**32, 'keeper original Job/root empty')
                identity = _creation(self.original.process)
                v.require(type(identity) is dict and set(identity) == {
                    'pid','creation_time_100ns','start_token'} and
                    type(identity['pid']) is int and identity['pid'] > 0 and
                    type(identity['creation_time_100ns']) is int and identity['creation_time_100ns'] > 0 and
                    identity['start_token'] == v.canonical_sha256({
                        key:identity[key] for key in ('pid','creation_time_100ns')}),
                    'keeper original native creation identity')
                self.reaped = {'process_identity':copy.deepcopy(identity),'exit_code':code,
                               'accounting':copy.deepcopy(accounting)}
            attempted = dict(self.remaining)
            try:
                event = owner._close_handles(kernel, attempted,
                    {'status':'failed','phase':'git_keeper_close','formal_permission':False})
            except owner.UnclosedHandles as retained:
                self.close_owner = retained  # Keep the exact secondary owner too.
                self.blocked = True  # No native retry if the handoff bookkeeping fails.
                self.remaining = dict(retained.handles)
                self.closed.update({key:value for key,value in attempted.items() if key not in self.remaining})
                self.blocked = retained.close_error is not None
                return None
            self.blocked = True  # Native close succeeded; do not replay on bookkeeping failure.
            self.closed.update(event['closed_handles'])
            self.remaining = {}
            v.require(self.closed == self.initial_handles, 'keeper every original handle close witnessed')
            self.completion = {'format':'anomaly-v03-child-git-recovery-observation-v1',
                **self.reaped,'closed_handles':dict(self.closed),
                'call_status':'failed','formal_permission':False,'execution_authenticated':False,
                'lease_completed':False,'failure_raw_verified':False,'parent_ack_authorized':False}
            return copy.deepcopy(self.completion)
        except BaseException as failure:
            self._remember('first_error', failure)
            return None

    def keep(self, *, on_observation):
        """Keep Python ownership through callback/sleep failure; never grant ack.

        The caller must preserve raw and verify compact proof before separately
        finishing the lease. This component never deletes inflight/partial raw.
        """
        v.require(callable(on_observation), 'keeper bounded observation callback required')
        while True:
            try:
                observation = self.reconcile_once()
            except BaseException as failure:
                self._remember('first_error', failure)
                observation = None
            if observation is not None:
                try:
                    on_observation(copy.deepcopy(observation))
                    return observation
                except BaseException as failure:
                    self._remember('callback_error', failure)
            try:
                time.sleep(0.25)
            except BaseException as failure:
                self._remember('sleep_error', failure)
