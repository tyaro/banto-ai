"""Opt-in Git caller/lease/archive boundary; worker entry and ack are separate.

Only the new fixed inflight three files may be removed after saved readback.
An entry point must call keep_owner before allowing its owning Python to exit.
"""
from __future__ import annotations

import copy
import time
from pathlib import Path

from . import anomaly_v03_preformal_worker_git_archive as archive

proof, tree = archive.proof, archive.proof.tree
v, io, observed, paths = archive.v, archive.io, archive.observed, archive.paths
keepers, owner = proof.keepers, tree.owner


class WorkerGitActor:
    def __init__(self, *, child, inventory_raw, inventory_pin, checkpoint, pipe_io=None, append_plan=None):
        # Keep caller-owned native IO before validating any opt-in descriptor.
        self.original_pipe_io = pipe_io
        self.pipe_io = None if pipe_io is None else dict(pipe_io) if type(pipe_io) is dict else pipe_io
        self.original_append_plan = append_plan
        self.append_plan = copy.deepcopy(append_plan)
        v.require(isinstance(child, proof.channel.ChildChannel) and callable(checkpoint),
                  'worker actor original child and common checkpoint')
        if pipe_io is not None:
            v.require(type(self.pipe_io) is dict and set(self.pipe_io) == {
                'kernel','stdin','clock','root_identity'} and callable(self.pipe_io['clock']),
                'worker actor explicit original pipe IO and shared clock')
            self.pipe_io['root_identity'] = copy.deepcopy(self.pipe_io['root_identity'])
        self.child, self.checkpoint = child, checkpoint
        self.pending = self.error = self.critical = self.keeper = self.saved = None
        self.verifier = proof.ProofVerifier(endpoint=child, inventory_raw=inventory_raw,
            inventory_pin=inventory_pin, read_evidence=self._read_original)
        self.inventory_raw, self.inventory_pin = inventory_raw, copy.deepcopy(inventory_pin)
        self.repository = Path(self.verifier.inventory['repository'])
        root = Path(child.request['budget_root'])
        self.append_admission = self.control_publication = None
        if append_plan is not None:
            v.require(self.pipe_io is not None,'worker append plan requires original pipe IO')
            controls=archive.checked_append_plan(self.append_plan,request=child.request,
                request_pin=child.request_pin,inventory_pin=self.inventory_pin,
                root_identity=self.pipe_io['root_identity'])
            self.append_admission=archive.ArchiveAppendAdmission(root=root,
                root_identity=self.pipe_io['root_identity'],revision=child.request['revision'],
                inventory_pin=self.inventory_pin,control_limits=controls,checkpoint=checkpoint)
            self.control_publication=archive.ControlPublicationAdmission(endpoint=child,
                root_identity=self.pipe_io['root_identity'],inventory_pin=self.inventory_pin,
                control_limits=controls,checkpoint=checkpoint,owner=self)
        self.inflight = root / 'worker-git-inflight'
        paths.regular_path(self.inflight, directory=True, missing=True)
        v.require(not self.inflight.exists(), 'worker actor exclusive unused inflight root')
        options={} if self.append_admission is None else {'append_admission':self.append_admission}
        self.writer = archive.WorkerGitArchive(path=root/'worker-git.bin',
            verifier=self.verifier, checkpoint=checkpoint,**options)
        self.leases = proof.VerifiedLeases(child=child, verifier=self.verifier)

    def _run_pipe(self, call):
        """Drive the retained transport; entry admission/native wall gates stay separate."""
        pending, held = self.pending, self.pipe_io
        pending['pipe_io'] = held
        pending['started_at'] = held['clock']()
        pending['admission'] = admission = tree.GitSinkAdmission(
            root=Path(self.child.request['budget_root']), root_identity=held['root_identity'],
            revision=self.child.request['revision'], call=call, checkpoint=self.checkpoint)
        admission.native.worker_git_actor=self  # Before keeper/transport IO, preserve this original caller.
        pending['transport'] = transport = tree.GitPipeTransport(admission,
            kernel=held['kernel'], stdin=held['stdin'], clock=held['clock'],
            started_at=pending['started_at'], repository=self.repository,
            policy=self.child._policy(), child=self.child, stop_probe=self.probe,
            normal_completion=True)
        try:
            transport.start()
            while True:
                pending['step'] = transport.step()
                if pending['step'] == 'close_ready':
                    break
                v.require(pending['step'] == 'pending', 'worker actor original transport step')
                time.sleep(0.025)
            transport.capture_receipt_inputs()  # Original Job is still open here.
            transport.close_once()
            return transport.publish_receipt()
        except (owner.UnreapedJob, owner.UnclosedHandles):
            raise
        except BaseException as failure:
            transport._abort(failure)  # Keep the original native even on caller sleep/IO interruption.

    def probe(self):
        if self.error is not None or self.critical is not None:
            return 'worker_git_actor_stopped'
        gate=self.control_publication
        if gate is not None and (gate.pending is not None or gate.error is not None):
            self.child.stopped=True
            return 'worker_git_control_publication_unresolved'
        self.checkpoint()
        return self.child.probe()

    def _fail(self, failure):
        self.child.stopped = True
        if self.error is None:
            self.error = failure

    def _read_original(self, lease):
        pending = self.pending
        v.require(pending is not None and lease == pending['lease'], 'worker actor original pending lease')
        call = self.verifier.inventory['calls'][lease]
        raw = {}
        for name, maximum in call['raw_inventory'].items():
            path = self.inflight / name
            paths.regular_path(path, missing=True)
            raw[name] = observed._file(path, maximum) if path.exists() else None
        return {'kind':pending['kind'], 'raw':raw, 'event':copy.deepcopy(pending['event'])}

    def _finish(self, *, keeper=None):
        lease = self.pending['lease']
        self.writer.append(lease)
        manifest, pin = self.writer.manifest()
        self.saved = archive.SavedWorkerGitArchive(endpoint=self.child, manifest_raw=manifest,
            manifest_pin=pin, inventory_raw=self.inventory_raw, inventory_pin=self.inventory_pin,
            checkpoint=self.checkpoint)
        v.require(self.saved.read(lease) == self._read_original(lease), 'worker actor original/saved readback')
        self.leases.verifier = self.saved.verifier
        row = self.leases.finish(lease, keeper=keeper)
        self.pending['finished'] = True
        return row

    def _cleanup_success(self):
        # The executor creates this root exclusively; no old root is eligible.
        v.require(self.pending['finished'] and self.saved.statuses[-1] == 'verified' and
            set(path.name for path in self.inflight.iterdir()) == {'receipt.json','stdout.bin','stderr.bin'},
            'worker actor exact new successful inflight inventory')
        self.checkpoint()
        v.require(self.saved.read(self.pending['lease']) == self._read_original(self.pending['lease']),
                  'worker actor raw changed before individual cleanup')
        for name in ('receipt.json','stdout.bin','stderr.bin'):
            path = self.inflight/name
            paths.regular_path(path)
            path.unlink()
        self.inflight.rmdir()
        self.checkpoint()
        self.pending = None

    def call(self, *, phase, operation, source_path=None, expected_output_pin=None):
        try:
            v.require(self.pending is None and self.error is None and self.critical is None and
                not self.writer.failed and self.probe() is None, 'worker actor no new work after stop/failure')
            lease = len(self.writer.rows)
            calls = self.verifier.inventory['calls']
            v.require(lease < len(calls) and self.child.finished == lease and not self.child.active and
                not self.child.owners and len(self.leases.records) == lease, 'worker actor exact next lease')
            call = calls[lease]
            v.require((phase,operation,source_path,expected_output_pin) == (
                call['phase'],call['operation'],call['source_path'],call['expected_output_pin']),
                'worker actor exact caller phase/operation/source/pin')
            self.verifier._live()
            paths.regular_path(self.inflight, directory=True, missing=True)
            v.require(not self.inflight.exists(), 'worker actor inflight remains exclusive')
            self.pending = {'lease':lease,'kind':'receipt','event':None,'finished':False}
            v.require(self.child.begin_job() == lease, 'worker actor native invocation lease')
            if self.pipe_io is None:
                result = tree.run_owned(root=self.repository, policy=self.child._policy(),
                    operation=operation, source_path=source_path, expected_output_pin=expected_output_pin,
                    receipt_root=self.inflight, timeout_seconds=10, stop_probe=self.probe,
                    capture_quiescence=True)
            else:
                result = self._run_pipe(call)
            self.pending['result'] = result  # Retain the original return before diagnostics/IO.
            self.pending['event'] = copy.deepcopy(result['quiescence'])
            packet = self._read_original(lease)
            v.require(result['receipt_root'] == str(self.inflight) and
                result['receipt_pin'] == observed._pin(packet['raw']['receipt.json']) and
                result['receipt'] == v.strict_json(packet['raw']['receipt.json']) and
                result['stdout'] == packet['raw']['stdout.bin'], 'worker actor original executor return/raw')
            self._finish()
            if self.saved.statuses[-1] != 'verified':
                raise owner.resources.ResourceStop('worker_git_failed_receipt')
            stdout = packet['raw']['stdout.bin']
            self._cleanup_success()
            return stdout
        except (owner.UnreapedJob, owner.UnclosedHandles) as original:
            # Retain native ownership before even child ledger/diagnostic IO.
            self.critical = original
            self._fail(original)
            original.worker_git_actor = self
            try:
                existing = getattr(original, 'child_keeper', None)
                self.keeper = existing  # Preserve cached observations/pending IO before ledger checks.
                lease = None if self.pending is None else self.pending['lease']
                if existing is not None:
                    v.require(isinstance(existing, keepers.ChildGitKeeper) and
                        existing.original is original and existing.child is self.child and
                        existing.lease == lease, 'worker actor same original pipe keeper')
                    existing.promote()
                else:
                    self.keeper = keepers.ChildGitKeeper(original, child=self.child, lease=lease)
            except BaseException:
                self.keeper = getattr(original, 'child_keeper', None)
                raise original
            raise
        except BaseException as failure:
            self._fail(failure)
            raise

    def keep_owner(self):
        """Retain this Python until original recovery/raw/lease all reconcile.

        Failed archive/ledger IO latches; callback retries cannot reappend or
        rerun native close. Unknown close/Delete owners remain held forever.
        Actual worker entry must use this path before ordinary error handling.
        """
        v.require(self.critical is not None and isinstance(self.keeper, keepers.ChildGitKeeper) and
            self.keeper.original is self.critical and self.keeper.child is self.child and
            self.pending is not None and self.keeper.lease == self.pending['lease'],
                  'worker actor original keeper required')
        def finish(event):
            if self.pending.get('recovery_attempted'):
                raise self.error
            self.pending['recovery_attempted'] = True
            self.pending['kind'], self.pending['event'] = 'recovery', copy.deepcopy(event)
            try:
                self._finish(keeper=self.keeper)
            except BaseException as failure:
                self.recovery_error = failure
                self._fail(failure)
                raise
        return self.keeper.keep(on_observation=finish)
