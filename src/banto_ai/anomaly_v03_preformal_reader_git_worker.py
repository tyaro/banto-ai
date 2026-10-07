"""Opt-in initial-reader source actor entry; parent supervision is separate."""
from __future__ import annotations

import copy
from pathlib import Path
import time

from . import anomaly_v03_preformal_worker_git_terminal as terminal
from . import anomaly_v03_preformal_generated_chain_budget as monitor

actors, tree, v = terminal.actors, terminal.tree, terminal.v
channel, observed, paths, io = actors.proof.channel, actors.observed, actors.paths, actors.io
SOURCE_ADDITIONS = tuple('src/banto_ai/'+name+'.py' for name in (
    'anomaly_v03_preformal_reader_git_worker',
    'anomaly_v03_preformal_worker_git_actor','anomaly_v03_preformal_worker_git_terminal',
    'anomaly_v03_preformal_worker_git_archive','anomaly_v03_preformal_worker_git_proof',
    'anomaly_v03_preformal_worker_stop_channel','anomaly_v03_preformal_child_git_keeper',
    'anomaly_v03_preformal_owned_git_job','anomaly_v03_preformal_owned_git',
    'anomaly_v03_preformal_job_tree_owner','anomaly_v03_preformal_owned_source_git_session',
    'anomaly_v03_preformal_generated_chain_budget','_anomaly_v03_engineering_runtime',
    '_anomaly_v03_fixture_budget','anomaly_v03_reader_evidence','anomaly_v03_consumer_evidence'))
PROOF_FORMAT = 'anomaly-v03-preformal-reader-git-archive-proof-v1'


def publish_archive_ack(actor, manifest_raw, manifest_pin):
    """Publish the proof-linked manifest once, preserving every partial write."""
    v.require(isinstance(actor,actors.WorkerGitActor), 'reader original publication actor')
    pending = {'manifest_raw':manifest_raw,'manifest_pin':copy.deepcopy(manifest_pin),
               'proof_raw':None,'error':None}
    v.require(getattr(actor,'reader_publication',None) is None, 'reader publication cannot be retried')
    actor.reader_publication = pending  # Before validation, readback or publication IO.
    actor.child.stopped = True
    try:
        v.require(actor.leases.error is None and not actor.child.active and not actor.child.owners and
            actor.child.finished == len(actor.leases.records) > 0, 'reader no unresolved/zero-job publication')
        actors.proof.evidence._raw(manifest_raw,manifest_pin,'reader retained manifest pin')
        git_raw = actor.leases.verifier.proof(actor.leases.records)
        path = actor.child.root/'git-manifest.json'
        envelope = {'format':PROOF_FORMAT,'manifest':{'path':str(path),'pin':copy.deepcopy(manifest_pin)},
                    'git_proof':v.strict_json(git_raw),'formal_permission':False}
        pending['proof_raw'] = io.json_bytes(envelope)
        v.require(len(pending['proof_raw']) <= channel.MAX_CONTROL, 'reader linked proof byte bound')
        actor.checkpoint()
        actual = channel._write(path,v.strict_json(manifest_raw))
        v.require(actual == manifest_pin, 'reader published manifest raw pin')
        actor.checkpoint()
        proof_path = actor.child.root/'git-proof.json'
        pin = channel._write(proof_path,envelope)
        actor.checkpoint()
        return actor.child.acknowledge({'path':str(proof_path),'pin':pin})
    except BaseException as failure:
        pending['error'] = failure
        actor.leases._failed(failure)
        raise


class ReaderGitArchiveVerifier:
    """Parent-held inventory plus proof-linked manifest and full archive raw.

    The manifest pin is captured from this bound proof, not a pre-run external
    manifest adoption. Receipt/close consistency is not native authentication.
    """
    def __init__(self, *, parent, inventory_raw, inventory_pin, checkpoint):
        self.parent, self.inventory_raw = parent, inventory_raw
        self.inventory_pin = copy.deepcopy(inventory_pin)
        self.checkpoint, self.error, self.pending, self.saved = checkpoint, None, None, None
        v.require(isinstance(parent,channel.ParentChannel) and callable(checkpoint),
                  'reader original parent and shared checkpoint')
        actors.proof.ProofVerifier(endpoint=parent,inventory_raw=inventory_raw,
            inventory_pin=inventory_pin,read_evidence=lambda _:None)

    def __call__(self, raw, jobs_finished):
        if self.error is not None:
            raise self.error
        self.pending = {'proof_raw':raw,'manifest_raw':None,'manifest_pin':None}
        try:
            self.checkpoint(); self.parent._live()
            v.require(type(raw) is bytes and len(raw) <= channel.MAX_CONTROL and
                type(jobs_finished) is int and 0 < jobs_finished <= channel.MAX_JOBS,
                'reader bounded nonzero original finished count')
            envelope = v.strict_json(raw)
            v.require(type(envelope) is dict and set(envelope) == {
                'format','manifest','git_proof','formal_permission'} and
                envelope['format'] == PROOF_FORMAT and envelope['formal_permission'] is False and
                io.json_bytes(envelope) == raw, 'reader exact canonical linked archive proof')
            entry = envelope['manifest']; path = self.parent.root/'git-manifest.json'
            v.require(type(entry) is dict and set(entry) == {'path','pin'} and
                entry['path'] == str(path), 'reader fixed measured manifest path')
            self.pending['manifest_pin'] = copy.deepcopy(entry['pin'])
            manifest_raw = observed._file(path,channel.MAX_CONTROL)
            self.pending['manifest_raw'] = manifest_raw
            inventory_path = self.parent.root/'worker-inventory.json'
            actors.proof.evidence._raw(observed._file(inventory_path,channel.MAX_CONTROL),
                self.inventory_pin,'reader unchanged caller inventory file')
            saved = actors.archive.SavedWorkerGitArchive(endpoint=self.parent,
                manifest_raw=manifest_raw,manifest_pin=entry['pin'],inventory_raw=self.inventory_raw,
                inventory_pin=self.inventory_pin,checkpoint=self.checkpoint)
            self.saved = saved
            v.require(saved.verifier.verify(io.json_bytes(envelope['git_proof']),jobs_finished) is True,
                      'reader exact original raw/call/close proof')
            actors.proof.evidence._raw(observed._file(path,channel.MAX_CONTROL),entry['pin'],
                                      'reader manifest changed during verification')
            actors.proof.evidence._raw(observed._file(inventory_path,channel.MAX_CONTROL),
                self.inventory_pin,'reader inventory changed during verification')
            saved._current(); self.checkpoint(); self.parent._live()
            return True
        except BaseException as failure:
            self.error = failure
            raise


def source_names(base):
    return tuple(dict.fromkeys((*base,*SOURCE_ADDITIONS)))


def _plan(verifier, names):
    calls = verifier.inventory['calls']
    expected = [(phase,operation,name) for phase in ('pre','post')
        for operation,name in [('head',None),('status',None),*[('source_blob',name) for name in names]]]
    v.require([(c['phase'],c['operation'],c['source_path']) for c in calls] == expected,
              'initial reader exact fresh source/identity inventory')


def prepare_entry(parent, *, inventory_raw, inventory_pin, names):
    """Publish caller-held bytes in the measured channel, no launch or new clock."""
    v.require(isinstance(parent,channel.ParentChannel), 'reader original parent endpoint')
    parent._live()
    verifier = actors.proof.ProofVerifier(endpoint=parent, inventory_raw=inventory_raw,
        inventory_pin=inventory_pin, read_evidence=lambda _:None)
    _plan(verifier,names)
    path = parent.root/'worker-inventory.json'
    io._exclusive(path,inventory_raw)
    actors.proof.evidence._raw(observed._file(path,channel.MAX_CONTROL),inventory_pin,'reader inventory readback')
    root = paths.regular_path(Path(parent.request['budget_root']),directory=True)
    stat = root.lstat()
    return {'channel_root':str(parent.root),'request_pin':copy.deepcopy(parent.request_pin),
        'inventory_path':str(path),'inventory_pin':copy.deepcopy(inventory_pin),
        'budget_root_identity':[stat.st_dev,stat.st_ino]}


class ReaderGitWorker:
    def __init__(self, entry, *, revision, repository, names):
        v.require(type(entry) is dict and set(entry) == {'channel_root','request_pin',
            'inventory_path','inventory_pin','budget_root_identity'}, 'reader Git entry exact fields')
        self.child = channel.ChildChannel(entry['channel_root'],entry['request_pin'])
        self.root = paths.regular_path(Path(self.child.request['budget_root']),directory=True)
        identity = entry['budget_root_identity']
        v.require(type(identity) is list and len(identity)==2 and all(type(n) is int and n>=0 for n in identity)
            and identity[1]>0, 'reader caller-held budget root identity')
        self.identity = tuple(identity)
        self.error = None
        v.require(self.child.request['revision'] == revision, 'reader channel revision')
        path = Path(entry['inventory_path'])
        v.require(path == self.child.root/'worker-inventory.json','reader fixed measured inventory path')
        raw = observed._file(path,channel.MAX_CONTROL)
        verifier = actors.proof.ProofVerifier(endpoint=self.child,inventory_raw=raw,
            inventory_pin=entry['inventory_pin'],read_evidence=lambda _:None)
        _plan(verifier,names)
        v.require(verifier.inventory['repository'] == str(repository), 'reader original repository')
        self.names = names
        self.checkpoint()
        reason = self.child.wait_for_binding()
        if reason is not None:
            raise monitor.resources.ResourceStop(reason)
        self.actor = actors.WorkerGitActor(child=self.child,inventory_raw=raw,
            inventory_pin=entry['inventory_pin'],checkpoint=self.checkpoint)

    def checkpoint(self):
        # The parent sampler still measures all four roots and its original
        # reserves. This worker checks the same outer leaf/clock synchronously;
        # it does not start/reset a sampler or widen any existing limit.
        try:
            if self.error is not None:
                raise self.error
            self.child._live()
            clock = self.child.request['clock']; elapsed = time.monotonic()-clock['started_at']
            v.require(0 <= elapsed < clock['wall_seconds'], 'reader shared clock expired/moved backwards')
            snapshot = monitor._directory_snapshot(self.root,32,2,self.identity)
            v.require(snapshot['directory_bytes']+128*1024 <= 1024**2 and
                snapshot['directory_entries']+2 <= 32, 'reader original outer leaf reserve/entry cap')
        except BaseException as failure:
            self.child.stopped = True
            if self.error is None:self.error = failure
            raise

    def identity_bytes(self):
        calls = self.actor.verifier.inventory['calls']; index = len(self.actor.writer.rows)
        v.require(index < len(calls), 'reader planned identity phase')
        phase = calls[index]['phase']
        return {operation:self.actor.call(phase=phase,operation=operation) for operation in ('head','status')}

    def blob(self, *, revision, source_path, expected_output_pin):
        v.require(revision == self.child.request['revision'], 'reader original blob revision')
        calls = self.actor.verifier.inventory['calls']; index = len(self.actor.writer.rows)
        v.require(index < len(calls), 'reader planned blob phase')
        return self.actor.call(phase=calls[index]['phase'],operation='source_blob',
            source_path=source_path,expected_output_pin=expected_output_pin)

    def run(self, operation):
        return terminal.run_guarded(self.actor,operation,publish_ack=publish_archive_ack)
