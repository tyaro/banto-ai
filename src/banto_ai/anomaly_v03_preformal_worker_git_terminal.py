"""Retained child terminal guard, for later opt-in worker entry wiring.

Quiescent Git ack is separate from successful business work. Zero-job and
incomplete successful prefixes remain closed. No native trial starts here.
"""
from __future__ import annotations

import time

from . import anomaly_v03_preformal_worker_git_actor as actors

v, tree, keepers = actors.v, actors.tree, actors.keepers


class ActorTerminal:
    def __init__(self, actor, publish_ack=None):
        v.require(isinstance(actor, actors.WorkerGitActor), 'terminal original Git actor')
        self.actor = actor
        self.publish_ack = publish_ack
        self.original_error = self.body_error = self.ack_error = None
        self.retention_error = self.sleep_error = self.unmatched_owner = self.unmatched_keeper = None
        self.original_control = getattr(actor,'control_publication',None)
        self.control_owners = []
        self.control_latch = self.control_error = None
        actor.terminal_guard = self  # Preserve this guard before any diagnostic IO.

    def _remember(self, name, failure):
        if getattr(self, name) is None:
            setattr(self, name, failure)

    def _pause(self):
        try:
            time.sleep(0.25)
        except BaseException as failure:
            self._remember('sleep_error', failure)

    def _recovery_ready(self):
        if self._control_pending():return False
        a = self.actor; keeper = a.keeper
        if not (isinstance(keeper, keepers.ChildGitKeeper) and keeper.original is a.critical and
            keeper.child is a.child and keeper.completion is not None and not keeper.remaining and
            keeper.closed == keeper.initial_handles and a.pending is not None and
            a.pending.get('finished') is True and keeper.lease == a.pending['lease'] and
            not a.child.active and not a.child.owners):
            return False
        v.require(not getattr(a.critical,'attribute_list_cleanup_pending',False) and
            not getattr(a.critical,'unknown_close_handles',()) and a.saved is not None and
            a.saved.read(keeper.lease) == a._read_original(keeper.lease) and
            a.saved.read(keeper.lease)['event'] == keeper.completion and
            a.leases.kept.get(keeper.lease) is keeper and a.leases.error is None,
            'terminal exact original recovery and saved failure raw')
        return True

    def _control_pending(self):
        """Keep original/rejected control objects before diagnostics; latch once."""
        if self.control_latch is not None:return True
        gate=getattr(self.actor,'control_publication',None)
        sidecar=getattr(self.actor,'control_publication_owner',None)
        attached=getattr(self.original_error,'control_publication_owner',None)
        for candidate in (self.original_control,gate,sidecar,attached):
            if candidate is not None and not any(candidate is held for held in self.control_owners):
                self.control_owners.append(candidate)
        if not self.control_owners:return False
        try:
            v.require(gate is self.original_control and type(gate) is actors.archive.ControlPublicationAdmission and
                gate.owner is self.actor and gate.endpoint is self.actor.child and
                sidecar is gate and
                gate.checkpoint is self.actor.checkpoint and gate.inventory_pin==self.actor.inventory_pin and
                (attached is None or attached is gate),
                'terminal original control publication owner')
            if gate.error is None and gate.pending is None and not gate.capture_pending():return False
            self.control_latch=gate
            self.control_error=gate.error
        except BaseException as error:
            self.control_latch=tuple(self.control_owners)
            self.control_error=error
        return True

    def retain_control(self):
        """No retry or invented Job/lease for failed control IO; keep Python."""
        if not self._control_pending():return
        self.actor.child.stopped=True
        while True:self._pause()

    def retain_owner(self):
        """Never leave this Python on keeper/diagnostic/sleep interruption."""
        a = self.actor
        a.child.stopped = True
        while True:
            try:
                if self._recovery_ready():
                    return
                a.keep_owner()
                if self._recovery_ready():
                    return
            except BaseException as failure:
                self._remember('retention_error', failure)
            self._pause()

    def retain_unmatched_owner(self, original):
        """Stop/hold an undeclared owner; no invented lease/raw/ack for it."""
        self.unmatched_owner = original  # Before child ledger/native/diagnostic IO.
        self.actor.child.stopped = True
        while True:
            try:
                if self.unmatched_keeper is None:
                    existing = getattr(original, 'child_keeper', None)
                    if isinstance(existing, keepers.ChildGitKeeper) and existing.original is original:
                        self.unmatched_keeper = existing
                    else:
                        try:
                            self.unmatched_keeper = keepers.ChildGitKeeper(
                                original, child=self.actor.child, lease=None)
                        except BaseException:
                            self.unmatched_keeper = getattr(original, 'child_keeper', None)
                            raise
                v.require(isinstance(self.unmatched_keeper, keepers.ChildGitKeeper) and
                    self.unmatched_keeper.original is original, 'terminal undeclared original keeper')
                def refuse(_):
                    raise original  # Not in the external call inventory: cannot grant ack.
                self.unmatched_keeper.keep(on_observation=refuse)
            except BaseException as failure:
                self._remember('retention_error', failure)
            self._pause()

    def acknowledge(self):
        a = self.actor; a.child.stopped = True
        v.require(not self._control_pending(),'terminal unresolved original control publication')
        v.require(self.unmatched_owner is None and not a.writer.failed and not a.child.active and
            not a.child.owners and a.child.finished == len(a.leases.records) == len(a.writer.rows) and
            a.child.finished > 0 and a.leases.error is None,
            'terminal no zero-job/active/unmatched/unverified acknowledgement')
        if a.critical is not None:
            v.require(self._recovery_ready(), 'terminal original owner still unresolved')
        if a.error is not None:
            v.require(a.pending is not None and a.pending.get('finished') is True and
                a.saved is not None and a.saved.statuses[-1] == 'failed' and
                a.saved.read(a.pending['lease']) == a._read_original(a.pending['lease']),
                'terminal failed call requires original retained raw; ordinary actor error denied')
        manifest, pin = a.writer.manifest()
        saved = actors.archive.SavedWorkerGitArchive(endpoint=a.child, manifest_raw=manifest,
            manifest_pin=pin, inventory_raw=a.inventory_raw, inventory_pin=a.inventory_pin,
            checkpoint=a.checkpoint)
        # Proof checks full inventory or the final failed prefix, never flags alone.
        saved.verifier.proof(a.leases.records)
        a.leases.verifier = saved.verifier
        if self.publish_ack is not None:
            v.require(callable(self.publish_ack), 'terminal bounded archive proof publisher')
            return self.publish_ack(a, manifest, pin)
        return a.leases.acknowledge()


def run_guarded(actor, operation, *, publish_ack=None):
    """Call only from the future worker entry before its reporting/exit catch."""
    guard = ActorTerminal(actor, publish_ack)
    result = None
    try:
        v.require(callable(operation), 'terminal worker operation callback')
        result = operation()
    except BaseException as failure:
        guard.body_error = guard.original_error = failure
    if guard.original_error is None and actor.error is not None:
        guard.original_error = actor.error
    if actor.critical is not None:
        guard.original_error = actor.critical
        guard.retain_owner()
    elif isinstance(guard.original_error, (tree.owner.UnreapedJob, tree.owner.UnclosedHandles)):
        guard.retain_unmatched_owner(guard.original_error)
    guard.retain_control()
    try:
        guard.acknowledge()
    except BaseException as failure:
        guard.ack_error = failure
        if guard._control_pending():
            if guard.original_error is None:guard.original_error=failure
            guard.retain_control()
        if guard.original_error is None:
            raise
    guard.retain_control()  # Even swallowed publication IO cannot reach reporting/exit.
    if guard.original_error is not None:
        raise guard.original_error
    return result
