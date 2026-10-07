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
    def __init__(self, original, *, child, lease, normal_completion=False):
        v.require(isinstance(original, (owner.UnreapedJob, owner.UnclosedHandles)),
                  'keeper original native owner required')
        self.original, self.child, self.lease = original, child, lease
        self.normal_completion, self.normal_promoted = normal_completion, False
        self.ledger_error = None
        self.first_error = self.stop_error = self.callback_error = self.sleep_error = None
        self.close_owner = self.reaped = self.completion = None
        self.output_owner = None
        self.spawn_io_owner = None
        self.native_kernel = None
        self.io_close_adapter = self.previous_io_adapter = self.io_closed = None
        self.control_actor = getattr(original,'worker_git_actor',None)
        self.control_publication = getattr(self.control_actor,'control_publication',None)
        self.rejected_control_owner = None
        self.control_failure = None
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
            self.output_owner = getattr(original, 'git_output_owner', None)
            self.spawn_io_owner = getattr(original, 'spawn_io_owner', None)
            v.require(type(normal_completion) is bool, 'keeper explicit normal completion option')
            if normal_completion:
                original.child_keeper = self  # Retain before normal capture validation/IO.
                v.require(type(original) is owner.UnreapedJob and original.original_error is None and
                    lease in child.active and lease not in child.owners and not child.stopped and
                    self.output_owner is not None and self.output_owner.error is None,
                    'keeper original active normal call, no failed owner')
            else:
                child.stopped = True
                child.hold_owner(lease, original)
        except BaseException as failure:
            self.ledger_error = failure
            original.child_keeper = self
            if normal_completion is True:
                try:
                    self.promote()
                except BaseException as ledger_error:
                    self._remember('ledger_error',ledger_error)
            raise original from failure

    def _remember(self, name, failure):
        if getattr(self, name) is None:
            setattr(self, name, failure)

    def promote(self):
        """Latch failed normal ownership before ledger IO; never undo stop."""
        if self.normal_completion is not True or self.normal_promoted:
            return
        self.normal_promoted = True
        self.original.child_keeper = self
        self.child.stopped = True
        try:
            self.child.hold_owner(self.lease,self.original)
        except BaseException as failure:
            self._remember('ledger_error',failure)
            raise self.original from failure

    def bind_io_close(self, adapter):
        self.previous_io_adapter = self.io_close_adapter
        self.io_close_adapter = adapter  # Original keeper retains rejected bindings before diagnostics.
        self.original.child_keeper = self
        try:
            v.require(type(adapter) is tree.GitPipeClose and adapter.keeper is self and
                adapter.output_owner is self.output_owner and
                adapter.output_owner.native_owner is self.original and
                self.previous_io_adapter is None and self.completion is None,
                'keeper exact original IO close adapter, no rebind')
        except BaseException as failure:
            self._remember('first_error',failure)
            self.blocked=True
            raise self.original from failure

    def _control_pending(self):
        if self.control_failure is not None:return True
        actor=getattr(self.original,'worker_git_actor',None)
        gate=getattr(actor,'control_publication',None)
        sidecar=getattr(actor,'control_publication_owner',None)
        self.rejected_control_owner=(actor,gate,sidecar)  # Before pointer validation; keep rejected owners.
        if gate is None and self.control_publication is None and actor is self.control_actor:
            return False
        try:
            from .anomaly_v03_preformal_worker_git_archive import ControlPublicationAdmission
            v.require(actor is self.control_actor and gate is self.control_publication and
                type(gate) is ControlPublicationAdmission and gate.owner is actor and gate.endpoint is self.child and
                sidecar is gate and
                gate.checkpoint is actor.checkpoint and gate.inventory_pin==actor.inventory_pin,
                'keeper original caller control publication owner')
            if gate.error is not None:self.control_failure=gate.error
            return gate.pending is not None or self.control_failure is not None
        except BaseException as error:
            self._remember('first_error',error)
            self.control_failure=error
            return True

    def reconcile_once(self):
        if self.completion is not None:
            if getattr(self.original,'pending_pipe_receipt_owner',None) is not None or self._control_pending():
                return None  # Additional publication IO/raw remains owned, even after core close.
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
            kernel = self.native_kernel if self.reaped is not None else (self.spawn_io_owner.binding[0]
                if type(self.spawn_io_owner) is owner.SpawnIOOwner and
                   self.spawn_io_owner.entered and self.spawn_io_owner.binding is not None
                else owner._kernel())
            if self.reaped is None:
                self.native_kernel = kernel  # Keep the original observer for additional IO close.
                if self.normal_completion and not self.normal_promoted:
                    accounting = owner._accounting(kernel,self.original.job)
                    code = owner._root_exit(kernel,self.original.process)
                    v.require(accounting['active_processes'] == 0 and code == 0,
                              'keeper normal original Job/root must already be empty/exit0')
                else:
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
            if (getattr(self.original, 'attribute_list_cleanup_pending', False) or
                    getattr(self.original, 'unknown_close_handles', ())):
                # Stop/reap the original root, but never repeat a Delete/Close
                # whose completion was not observed. Keep its buffer and handles.
                self.blocked = True
                return None
            output_owner = getattr(self.original, 'git_output_owner', None)
            if self.output_owner is None and output_owner is not None:
                self.output_owner = output_owner
            if self.output_owner is not None:
                if self.io_close_adapter is None:
                    return None  # Close/EOF/metadata alone cannot authorize core close.
                v.require(type(self.io_close_adapter) is tree.GitPipeClose and
                    self.io_close_adapter.output_owner is self.output_owner and
                    self.io_close_adapter.keeper is self, 'keeper retained original IO adapter')
                self.io_closed = self.io_close_adapter.for_keeper(self)
            spawn_io_owner = getattr(self.original, 'spawn_io_owner', None)
            if self.spawn_io_owner is None and spawn_io_owner is not None:
                self.spawn_io_owner = spawn_io_owner
            if self.spawn_io_owner is not None and self.io_closed is None:
                # Additional read handles and original sink/write streams stay
                # held even after stdio duplicates/Job/root have finished.
                return None
            if getattr(self.original,'pending_pipe_receipt_owner',None) is not None or self._control_pending():
                return None  # Never turn partial/unknown receipt IO into recovered lease/ack.
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
                self.promote()
                return None
            self.blocked = True  # Native close succeeded; do not replay on bookkeeping failure.
            self.closed.update(event['closed_handles'])
            self.remaining = {}
            v.require(self.closed == self.initial_handles, 'keeper every original handle close witnessed')
            self.completion = {'format':'anomaly-v03-child-git-recovery-observation-v1',
                **self.reaped,'closed_handles':dict(self.closed),
                'call_status':'failed','formal_permission':False,'execution_authenticated':False,
                'lease_completed':False,'failure_raw_verified':False,'parent_ack_authorized':False}
            if self.io_closed is not None:
                self.completion['format']=tree.PIPE_RECOVERY
                self.completion['io_closed']=copy.deepcopy(self.io_closed)
            return copy.deepcopy(self.completion)
        except BaseException as failure:
            self._remember('first_error', failure)
            try:
                self.promote()
            except BaseException as ledger_error:
                self._remember('ledger_error',ledger_error)
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
