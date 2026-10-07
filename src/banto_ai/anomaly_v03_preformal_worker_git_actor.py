"""Opt-in Git caller/lease/archive boundary; worker entry and ack are separate.

Only the new fixed inflight three files may be removed after saved readback.
An entry point must call keep_owner before allowing its owning Python to exit.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import anomaly_v03_preformal_worker_git_archive as archive

proof, tree = archive.proof, archive.proof.tree
v, io, observed, paths = archive.v, archive.io, archive.observed, archive.paths
keepers, owner = proof.keepers, tree.owner


class WorkerGitActor:
    def __init__(self, *, child, inventory_raw, inventory_pin, checkpoint):
        v.require(isinstance(child, proof.channel.ChildChannel) and callable(checkpoint),
                  'worker actor original child and common checkpoint')
        self.child, self.checkpoint = child, checkpoint
        self.pending = self.error = self.critical = self.keeper = self.saved = None
        self.verifier = proof.ProofVerifier(endpoint=child, inventory_raw=inventory_raw,
            inventory_pin=inventory_pin, read_evidence=self._read_original)
        self.inventory_raw, self.inventory_pin = inventory_raw, copy.deepcopy(inventory_pin)
        self.repository = Path(self.verifier.inventory['repository'])
        root = Path(child.request['budget_root'])
        self.inflight = root / 'worker-git-inflight'
        paths.regular_path(self.inflight, directory=True, missing=True)
        v.require(not self.inflight.exists(), 'worker actor exclusive unused inflight root')
        self.writer = archive.WorkerGitArchive(path=root/'worker-git.bin',
            verifier=self.verifier, checkpoint=checkpoint)
        self.leases = proof.VerifiedLeases(child=child, verifier=self.verifier)

    def probe(self):
        if self.error is not None or self.critical is not None:
            return 'worker_git_actor_stopped'
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
            result = tree.run_owned(root=self.repository, policy=self.child._policy(),
                operation=operation, source_path=source_path, expected_output_pin=expected_output_pin,
                receipt_root=self.inflight, timeout_seconds=10, stop_probe=self.probe,
                capture_quiescence=True)
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
                self.keeper = keepers.ChildGitKeeper(original, child=self.child,
                    lease=self.pending['lease'])
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
        v.require(self.critical is not None and isinstance(self.keeper, keepers.ChildGitKeeper),
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
