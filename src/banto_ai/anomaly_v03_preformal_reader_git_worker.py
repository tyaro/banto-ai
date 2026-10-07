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


def selected_source(repository, revision, source_pins, names):
    """Check fresh caller-held selected pins; the child later compares Git raw."""
    v.require(type(names) is tuple and len(names)==len(set(names)) and
        2*(len(names)+2) <= channel.MAX_JOBS and type(source_pins) is dict and
        set(source_pins)==set(names), 'reader exact bounded caller source inventory')
    actors.proof.evidence._digest(revision,40)
    root=paths.regular_path(Path(repository),directory=True)
    rows=[]
    for name in names:
        v.safe_relative_path(name); pin=source_pins[name]
        actors.proof.evidence._pin(pin)
        v.require(pin['bytes'] <= tree.direct.MAX_OUTPUT['source_blob'], 'reader selected source byte bound')
        raw=observed._file(root/name,max(1,pin['bytes']))
        actors.proof.evidence._raw(raw,pin,'reader fresh caller source pin')
        rows.append({'path':name,'pin':copy.deepcopy(pin)})
    return {'revision':revision,'selected_files':rows,
            'scope':'selected-working-git-raw-only-not-source-closure'}


def _pipe_raw_limits(limits, source_pins, names):
    """Validate caller-set failure maxima, independently of successful source sizes.

    This is not a parallel reservation or a whole-root capacity certificate.
    The admission later adds actual retained archive/control bytes and entries.
    """
    v.require(type(limits) is dict and set(limits)=={'head','status','source_blob'} and
        len(io.json_bytes(limits)) <= channel.MAX_CONTROL, 'reader exact bounded pipe raw allocation')
    v.require(type(source_pins) is dict and set(source_pins)==set(names),
              'reader allocation same caller source inventory')
    for pin in source_pins.values(): actors.proof.evidence._pin(pin)
    for operation, raw in limits.items():
        maximum={'receipt.json':tree.direct.MAX_RECEIPT,'stdout.bin':tree.direct.MAX_OUTPUT[operation],
                 'stderr.bin':tree.direct.MAX_STDERR,'partial-archive.bin':actors.archive.MAX_BYTES}
        v.require(type(raw) is dict and {'receipt.json','stdout.bin','stderr.bin'} <= set(raw) <= set(maximum)
            and all(type(n) is int and 0<n<=maximum[name] for name,n in raw.items()),
            'reader pipe allocation only original positive hard maxima')
        v.require(sum(raw.values())+tree.GitSinkAdmission.RESERVE <= tree.GitSinkAdmission.BYTE_LIMIT,
                  'reader raw allocation cannot fit even an empty original outer')
        if operation=='head':
            v.require(raw['stdout.bin']>41, 'reader head allocation includes its limit detection byte')
        if operation=='source_blob':
            v.require(all(pin['bytes']<raw['stdout.bin'] for pin in source_pins.values()),
                      'reader independent failure stdout maximum must hold normal source plus detection byte')
    return limits


class ReaderGitParent:
    """Opt-in composing caller; all sampler/clock owners remain with that caller."""
    @classmethod
    def create_native(cls, **request):
        """Refuse the limited native entry until its owned pipe is connected.

        The byte sink alone supplies no process/pipe lifetime or failure-raw
        guarantee. Keep this denial before channel/root/clock/worker creation.
        Existing protocol/default callers continue to use create().
        """
        raise monitor.resources.ResourceStop('reader_git_native_capture_not_connected')

    @classmethod
    def create(cls, *, root, revision, repository, policy, budget, source_pins, names, profile_pin,
               pipe_raw_limits=None):
        result=cls()
        result.original_source_pins, result.original_pipe_raw_limits = source_pins, pipe_raw_limits
        result.source_pins, result.pipe_raw_limits = copy.deepcopy(source_pins), copy.deepcopy(pipe_raw_limits)
        if pipe_raw_limits is not None:
            _pipe_raw_limits(result.pipe_raw_limits,result.source_pins,names)
        result.budget, result.shared = budget, getattr(budget,'outer',None)
        shared=result.shared
        v.require(shared is not None and getattr(budget,'stage',None)=='producer' and
            type(getattr(shared,'roots',None)) is dict and set(shared.roots)=={
                'outer','producer','saved-reader','publication'}, 'reader linked four-root producer budget required')
        shared.require_stage('producer',budget.root)
        target=Path(root).absolute()
        v.require(target.parent==Path(shared.roots['outer']), 'reader channel under original outer leaf')
        selected_source(repository,revision,result.source_pins,names)
        actors.proof.evidence._pin(profile_pin)
        result.repository, result.names = Path(repository), names
        result.profile_pin = copy.deepcopy(profile_pin)
        result.worker=result.error=None
        result.parent=channel.ParentChannel.create(root=target,revision=revision,policy=policy,
            budget=shared,verify_quiescent=lambda _raw,_count:False)
        result.clock=copy.deepcopy(result.parent.request['clock'])
        calls=[]
        for phase in ('pre','post'):
            for operation,name in [('head',None),('status',None),*[('source_blob',name) for name in names]]:
                calls.append({'lease':len(calls),'phase':phase,'operation':operation,'source_path':name,
                    'expected_output_pin':None if name is None else copy.deepcopy(result.source_pins[name]),
                    'raw_inventory':copy.deepcopy(result.pipe_raw_limits[operation])
                        if result.pipe_raw_limits is not None else {'receipt.json':tree.direct.MAX_RECEIPT,
                        'stdout.bin':tree.direct.MAX_OUTPUT[operation],'stderr.bin':tree.direct.MAX_STDERR,
                        'partial-archive.bin':actors.archive.MAX_BYTES}})
        request=result.parent.request
        inventory={'format':actors.proof.FORMAT+'-inventory','request_pin':result.parent.request_pin,
            **{name:copy.deepcopy(request[name]) for name in ('revision','root','root_identity','policy_pin')},
            'repository':str(result.repository),'calls':calls,'formal_permission':False}
        raw=io.json_bytes(inventory); pin=observed._pin(raw)
        result.verifier=ReaderGitArchiveVerifier(parent=result.parent,inventory_raw=raw,
            inventory_pin=pin,checkpoint=result.checkpoint)
        result.parent.verify_quiescent=result.verifier
        result.entry=prepare_entry(result.parent,inventory_raw=raw,inventory_pin=pin,names=names)
        result.checkpoint()
        return result

    def checkpoint(self):
        try:
            if self.error is not None:raise self.error
            shared=self.shared
            v.require(shared.started_at==self.clock['started_at'] and
                shared.limits['wall_seconds']==self.clock['wall_seconds'] and
                Path(shared.roots['outer'])==Path(self.parent.request['budget_root']),
                'reader original outer clock/root cannot be reset')
            shared.require_stage('producer',self.budget.root)
            # Repeated EnvelopeBudget producer checks do not append/reset the
            # inner budget's bounded phase log or create another sampler.
            shared.checkpoint('producer')
            reason=self.budget.probe()
            if reason is not None:raise monitor.resources.ResourceStop(reason)
            self.parent._live()
            root=paths.regular_path(Path(self.parent.request['budget_root']),directory=True)
            stat=root.lstat()
            v.require([stat.st_dev,stat.st_ino]==self.entry['budget_root_identity'],
                      'reader original measured outer identity changed')
        except BaseException as failure:
            if self.error is None:self.error=failure
            raise

    def source(self):
        self.checkpoint()
        return selected_source(self.repository,self.parent.request['revision'],self.source_pins,self.names)

    def bind(self, process):
        v.require(self.worker is None, 'reader original worker bind once')
        self.worker=process  # Before checkpoint, bind or native identity IO.
        self.parent.bind(process)
        binding,_=self.parent._binding()
        return copy.deepcopy(binding['worker_identity'])

    def fence(self, process):
        return self.parent.fence(process)


class ReaderGitWorker:
    def __init__(self, entry, *, revision, repository, names, pipe_io=None):
        # Native objects come from the retaining caller, never the JSON entry.
        self.original_pipe_io = pipe_io
        self.pipe_io = None if pipe_io is None else dict(pipe_io) if type(pipe_io) is dict else pipe_io
        self.clock = time.monotonic  # Same function for this checkpoint and the actor's call window.
        if pipe_io is not None:
            v.require(type(self.pipe_io) is dict and set(self.pipe_io) == {'kernel','stdin'},
                      'reader caller-held pipe kernel/stdin only')
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
        options = {} if self.pipe_io is None else {'pipe_io':{
            **self.pipe_io,'clock':self.clock,'root_identity':self.identity}}
        self.actor = actors.WorkerGitActor(child=self.child,inventory_raw=raw,
            inventory_pin=entry['inventory_pin'],checkpoint=self.checkpoint,**options)

    def checkpoint(self):
        # The parent sampler still measures all four roots and its original
        # reserves. This worker checks the same outer leaf/clock synchronously;
        # it does not start/reset a sampler or widen any existing limit.
        try:
            if self.error is not None:
                raise self.error
            self.child._live()
            clock = self.child.request['clock']; elapsed = self.clock()-clock['started_at']
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
