"""Opt-in initial-reader source actor entry; parent supervision is separate."""
from __future__ import annotations

import copy
from pathlib import Path
from . import anomaly_v03_process_supervisor as parent_supervisor
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
APPEND_ENTRY_FORMAT = 'anomaly-v03-preformal-reader-git-append-entry-v2'
STORAGE_ENTRY_FORMAT = 'anomaly-v03-preformal-reader-git-storage-entry-v3'
PUBLICATION_LAUNCH_FORMAT = 'anomaly-v03-reader-publication-launch-context-v1'


def publish_archive_ack(actor, manifest_raw, manifest_pin):
    """Publish the proof-linked manifest once, preserving every partial write."""
    v.require(isinstance(actor,actors.WorkerGitActor), 'reader original publication actor')
    pending = {'manifest_raw':manifest_raw,'manifest_pin':copy.deepcopy(manifest_pin),
               'proof_raw':None,'error':None}
    v.require(getattr(actor,'reader_publication',None) is None, 'reader publication cannot be retried')
    actor.reader_publication = pending  # Before validation, readback or publication IO.
    actor.child.stopped = True
    try:
        gate=getattr(actor,'control_publication',None)
        pending['control_publication']=gate  # Before any publication/diagnostic IO.
        if gate is not None:
            v.require(type(gate) is actors.archive.ControlPublicationAdmission and
                gate.owner is actor and gate.endpoint is actor.child and gate.checkpoint is actor.checkpoint and
                gate.inventory_pin==actor.inventory_pin,'reader same original control publication owner')
        options={} if gate is None else {'publication_admission':gate}
        capture=None if gate is None else actors.archive.ChildPublicationCapture(gate=gate,actor=actor)
        pending['child_publication_capture']=capture
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
        actual = channel._write(path,v.strict_json(manifest_raw),**options)
        v.require(actual == manifest_pin, 'reader published manifest raw pin')
        actor.checkpoint()
        proof_path = actor.child.root/'git-proof.json'
        pin = channel._write(proof_path,envelope,**options)
        actor.checkpoint()
        ack_pin=pending['ack_pin']=actor.child.acknowledge({'path':str(proof_path),'pin':pin},**options)
        if gate is not None:
            pending['control_raw_pins']=gate.verify_publications(('git-manifest.json','git-proof.json','ack.json'))
            pending['local_capture']=capture.seal(pending['control_raw_pins'])
            carrier=getattr(gate,'original_publication_carrier',None)
            pending['publication_carrier']=carrier
            if carrier is not None:pending['carrier_return']=carrier.send(capture)
        return ack_pin
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


def prepare_entry(parent, *, inventory_raw, inventory_pin, names, append_control_limits=None,
                  publication_admission=None, publication_storage=None):
    """Publish caller-held bytes in the measured channel, no launch or new clock."""
    held_publication=publication_admission  # Keep the original caller gate before validation/root IO.
    held_storage=publication_storage
    controls=copy.deepcopy(append_control_limits)
    if append_control_limits is not None:
        actors.archive.ArchiveAppendAdmission.validate_controls(controls)
    v.require(isinstance(parent,channel.ParentChannel), 'reader original parent endpoint')
    if held_publication is not None:
        v.require(type(held_publication) is actors.archive.ControlPublicationAdmission and
            controls is not None and held_publication.endpoint is parent and
            isinstance(held_publication.owner,ReaderGitParent) and held_publication.owner.parent is parent and
            held_publication.owner.inventory_publication is held_publication and
            held_publication.control_limits==controls and held_publication.inventory_pin==inventory_pin,
            'reader original parent inventory publication context')
    if held_storage is not None:
        v.require(held_publication is not None and type(held_storage) is actors.archive.PublicationStoragePreparation and
            held_storage.owner is held_publication.owner and held_storage.endpoint is parent and
            held_storage.inventory_raw is inventory_raw and held_storage.inventory_pin==inventory_pin,
            'reader original issued storage preparation')
        held_storage._fixed()
    parent._live()
    verifier = actors.proof.ProofVerifier(endpoint=parent, inventory_raw=inventory_raw,
        inventory_pin=inventory_pin, read_evidence=lambda _:None)
    _plan(verifier,names)
    path = parent.root/'worker-inventory.json'
    if held_publication is None:io._exclusive(path,inventory_raw)
    else:channel._write(path,verifier.inventory,publication_admission=held_publication)
    actors.proof.evidence._raw(observed._file(path,channel.MAX_CONTROL),inventory_pin,'reader inventory readback')
    root = paths.regular_path(Path(parent.request['budget_root']),directory=True)
    stat = root.lstat()
    result={'channel_root':str(parent.root),'request_pin':copy.deepcopy(parent.request_pin),
        'inventory_path':str(path),'inventory_pin':copy.deepcopy(inventory_pin),
        'budget_root_identity':[stat.st_dev,stat.st_ino]}
    if append_control_limits is not None:
        value={'format':actors.archive.APPEND_PLAN_FORMAT,'revision':parent.request['revision'],
            'request_pin':copy.deepcopy(parent.request_pin),'inventory_pin':copy.deepcopy(inventory_pin),
            'budget_root':parent.request['budget_root'],'budget_root_identity':result['budget_root_identity'].copy(),
            'control_limits':controls,'formal_permission':False}
        raw=io.json_bytes(value)
        v.require(len(raw)<=channel.MAX_CONTROL,'reader bounded append context')
        result.update(format=APPEND_ENTRY_FORMAT,append_plan={'value':value,'pin':observed._pin(raw)})
    if held_storage is not None:
        value={'format':actors.archive.STORAGE_CONTEXT_FORMAT,'revision':parent.request['revision'],
            'request_pin':copy.deepcopy(parent.request_pin),'inventory_pin':copy.deepcopy(inventory_pin),
            'budget_root':parent.request['budget_root'],'budget_root_identity':result['budget_root_identity'].copy(),
            'clock':copy.deepcopy(parent.request['clock']),'allocation':copy.deepcopy(held_storage.allocation_entry),
            'formal_permission':False}
        raw=io.json_bytes(value);v.require(len(raw)<=channel.MAX_CONTROL,'reader bounded storage context')
        result.update(format=STORAGE_ENTRY_FORMAT,storage_plan={'value':value,'pin':observed._pin(raw)})
        held_storage._fixed()
    if held_publication is not None:
        held_publication.verify_publications(('worker-inventory.json',))
    return result


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
               pipe_raw_limits=None, append_control_limits=None, publication_storage=None):
        result=cls()
        result.error=None
        result.original_bootstrap_inputs=(root,revision,repository,policy,budget,source_pins,names,profile_pin,
            pipe_raw_limits,append_control_limits)+(() if publication_storage is None else (publication_storage,))
        result.original_storage_preparation=result.storage_preparation=None
        result.budget,result.shared=budget,None
        result.request_bootstrap_owner=None
        result.original_request_bootstrap=None
        result.inventory_publication=result.inventory_publication_error=result.inventory_pending_owner=None
        result.worker=None
        result.original_child_publication_denial=None
        try:
            result.shared=getattr(budget,'outer',None)
            if publication_storage is not None:
                actors.archive.PublicationStoragePreparation(root=root,revision=revision,budget=result.shared,
                    allocation=publication_storage,controls=append_control_limits,raw_limits=pipe_raw_limits,
                    source_pins=source_pins,names=names,checkpoint=result._storage_preparation_checkpoint,owner=result,
                    policy=policy,profile_pin=profile_pin,repository=repository)
                preparation=result.original_storage_preparation
                policy=preparation.policy;append_control_limits=preparation.controls
            if append_control_limits is not None:
                actors.archive.RequestBootstrapAdmission(root=root,revision=revision,policy=policy,budget=result.shared,
                    control_limits=append_control_limits,checkpoint=result._bootstrap_checkpoint,owner=result)
            return cls._create(result,root=root,revision=revision,repository=repository,policy=policy,budget=budget,
                source_pins=source_pins,names=names,profile_pin=profile_pin,pipe_raw_limits=pipe_raw_limits,
                append_control_limits=append_control_limits,publication_storage=publication_storage)
        except BaseException as failure:
            if publication_storage is not None:
                if result.error is None:result.error=failure
                failure.reader_git_parent=result
            preparation=result.original_storage_preparation
            if preparation is not None:preparation._failed(failure)
            gate=result.original_request_bootstrap
            if gate is not None:
                if result.error is None:result.error=failure
                failure.reader_git_parent=result
                gate._failed(failure)
            raise

    @classmethod
    def _create(cls, result, *, root, revision, repository, policy, budget, source_pins, names, profile_pin,
                pipe_raw_limits=None, append_control_limits=None, publication_storage=None):
        preparation=result.original_storage_preparation
        if preparation is not None:
            preparation._fixed()
            source_pins=preparation.source_pins;pipe_raw_limits=preparation.raw_limits
            append_control_limits=preparation.controls
            policy=preparation.policy;profile_pin=preparation.profile_pin;repository=preparation.repository
        result.original_source_pins, result.original_pipe_raw_limits = source_pins, pipe_raw_limits
        result.source_pins, result.pipe_raw_limits = copy.deepcopy(source_pins), copy.deepcopy(pipe_raw_limits)
        result.original_append_controls = append_control_limits
        result.append_controls = copy.deepcopy(append_control_limits)
        if append_control_limits is not None:
            v.require(pipe_raw_limits is not None,'reader append allocation requires explicit pipe raw maxima')
            actors.archive.ArchiveAppendAdmission.validate_controls(result.append_controls)
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
        result.inventory_publication = result.inventory_publication_error = None
        result.inventory_pending_owner = None
        result.rejected_inventory_publication = None
        bootstrap_options={} if result.request_bootstrap_owner is None else {'request_admission':result.request_bootstrap_owner}
        result.parent=channel.ParentChannel.create(root=target,revision=revision,policy=policy,
            budget=shared,verify_quiescent=lambda _raw,_count:False,**bootstrap_options)
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
        options={} if result.append_controls is None else {'append_control_limits':result.append_controls}
        if result.append_controls is not None:
            stat=paths.regular_path(Path(result.parent.request['budget_root']),directory=True).lstat()
            result.inventory_root_identity=(stat.st_dev,stat.st_ino)
            result.inventory_checkpoint=result.checkpoint  # Stable original bound callable; no new clock/sampler.
            result.inventory_publication=actors.archive.ControlPublicationAdmission(endpoint=result.parent,
                inventory_pin=pin,root_identity=result.inventory_root_identity,control_limits=result.append_controls,
                checkpoint=result.inventory_checkpoint,owner=result)
            result.parent.parent_publication_admission=result.inventory_publication  # Before inventory/channel IO.
            options['publication_admission']=result.inventory_publication
            if preparation is not None:
                preparation.bind(result.parent,raw,pin,result.inventory_checkpoint)
                options['publication_storage']=preparation
        try:
            result.entry=prepare_entry(result.parent,inventory_raw=raw,inventory_pin=pin,names=names,**options)
        except BaseException as failure:
            if result.inventory_publication is not None:
                result.error=result.inventory_publication_error=failure
                result.inventory_pending_owner=result.inventory_publication.pending
                failure.reader_git_parent=result  # Bootstrap Python/stream survives the failed return.
            raise
        result.checkpoint()
        return result

    def _storage_preparation_checkpoint(self):
        if self.error is not None:raise self.error
        v.require(self.budget is self.original_bootstrap_inputs[4] and self.shared is self.budget.outer and
            getattr(self.budget,'stage',None)=='producer','storage original linked producer budget')
        self.shared.require_stage('producer',self.budget.root)
        self.shared.checkpoint('producer')
        reason=self.budget.probe()
        if reason is not None:raise monitor.resources.ResourceStop(reason)

    def _bootstrap_checkpoint(self):
        """The original linked producer budget; no endpoint/inner phase reset."""
        gate=self.original_request_bootstrap
        if self.error is not None:raise self.error
        v.require(gate is not None and self.request_bootstrap_owner is gate and gate.owner is self and self.shared is gate.budget and
            self.budget is self.original_bootstrap_inputs[4] and Path(self.shared.roots['outer'])==gate.root and
            self.shared.started_at==gate.clock['started_at'] and
            self.shared.limits['wall_seconds']==gate.clock['wall_seconds'],
            'reader original bootstrap shared root, clock and budget')
        self.shared.require_stage('producer',self.budget.root)
        self.shared.checkpoint('producer')
        reason=self.budget.probe()
        if reason is not None:raise monitor.resources.ResourceStop(reason)

    def checkpoint(self):
        try:
            if self.error is not None:raise self.error
            preparation=getattr(self,'original_storage_preparation',None)
            if preparation is not None:
                try:preparation._fixed()
                except BaseException as error:preparation._failed(error)
            gate=getattr(self,'original_request_bootstrap',None)
            if gate is not None:
                self.rejected_request_bootstrap=(gate,getattr(self,'request_bootstrap_owner',None))
                v.require(type(gate) is actors.archive.RequestBootstrapAdmission and self.request_bootstrap_owner is gate,
                          'reader original request bootstrap sidecar retained')
                gate.verify_publications(('request.json',),cached=True)
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
            identity=self.entry['budget_root_identity'] if hasattr(self,'entry') else list(self.inventory_root_identity)
            v.require([stat.st_dev,stat.st_ino]==identity,
                      'reader original measured outer identity changed')
        except BaseException as failure:
            if self.error is None:self.error=failure
            raise

    def source(self):
        self._inventory_ready()
        self.checkpoint()
        return selected_source(self.repository,self.parent.request['revision'],self.source_pins,self.names)

    def bind(self, process):
        v.require(self.worker is None, 'reader original worker bind once')
        self.worker=process  # Before checkpoint, bind or native identity IO.
        try:
            self._inventory_ready()
            options={} if self.inventory_publication is None else {'publication_admission':self.inventory_publication}
            self.parent.bind(process,**options)
            binding,_=self.parent._binding()
            return copy.deepcopy(binding['worker_identity'])
        except BaseException as failure:
            self._remember_publication(failure)
            raise

    def fence(self, process):
        try:
            denied=self.original_child_publication_denial
            if denied is not None:
                if self.error is not None:raise self.error
                self.rejected_child_publication_fence=(denied,process)
                v.require(process is denied['process'] is self.worker,'reader original denied child Popen')
                return False
            self._inventory_ready()
            options={} if self.inventory_publication is None else {'publication_admission':self.inventory_publication}
            result=self.parent.fence(process,**options)
            self._inventory_ready()  # No true verdict while new control IO/raw remains unverified.
            return result
        except BaseException as failure:
            self._remember_publication(failure)
            raise

    def bind_publication_carrier(self, creator, *, frame_limit):
        """Bind a dedicated original read owner; native launcher remains closed."""
        self.publication_carrier_inputs=(creator,frame_limit,self.worker,self.parent,self.inventory_publication)
        try:
            carrier=actors.archive.PublicationCarrier(creator=creator,owner=self,
                checkpoint=self.inventory_checkpoint,frame_limit=frame_limit,sending=False,
                storage_admission=getattr(self,'original_publication_storage',None))
            held=self.publication_carrier_binding={'carrier':carrier,'process':self.worker,
                'endpoint':self.parent,'gate':self.inventory_publication,'original_inputs':self.publication_carrier_inputs}
            v.require(self.worker is self.parent.worker and self.worker is not None and self.inventory_publication is not None,
                'carrier exact original bound parent worker')
            held['process_handle']=self.worker._handle
            held['binding'],held['binding_pin']=self.parent._binding()
            held['creation']=observed.creation_observation(self.worker.pid,held['process_handle'])
            v.require(held['creation']==held['binding']['worker_identity'],'carrier original Popen HANDLE creation')
            held['context']={'request_pin':self.parent.request_pin,'inventory_pin':self.entry['inventory_pin'],
                'root_identity':self.entry['budget_root_identity'],'clock':self.clock,'root':str(self.parent.root),
                'revision':self.parent.request['revision'],'worker_identity':held['creation']}
            held['context_raw']=io.json_bytes(held['context'])
            v.require(len(held['context_raw'])<=channel.MAX_CONTROL,'carrier bounded parent context')
            self._inventory_ready()
            return carrier
        except BaseException as failure:
            carrier=getattr(self,'original_publication_carrier',None)
            if carrier is not None:carrier._failed(failure)
            self._remember_publication(failure);raise

    def arm_publication_storage(self,allocation):
        self.publication_storage_input=allocation
        return actors.archive.PublicationStorageAdmission(endpoint=self.parent,
            inventory_raw=self.verifier.inventory_raw,inventory_pin=self.entry['inventory_pin'],
            root_identity=tuple(self.entry['budget_root_identity']),allocation=allocation,
            checkpoint=self.inventory_checkpoint,owner=self)

    def prepare_partitioned_publication(self, *, archive_preparation, allocation, entry_raw, context_raw, parent_identity_raw):
        held=monitor.PartitionedPublicationPreparation.__new__(monitor.PartitionedPublicationPreparation)
        held._retain_inputs(owner=self,checkpoint=None,archive_preparation=archive_preparation,
            allocation=allocation,entry_raw=entry_raw,context_raw=context_raw,parent_identity_raw=parent_identity_raw)
        previous=getattr(self,'_partitioned_publication_owner',None)
        if previous is not None:
            previous.rejected=held;previous._failed(ValueError('reader original partitioned publication cannot be replaced'))
        self.partitioned_publication_inputs=(archive_preparation,allocation,entry_raw,context_raw,parent_identity_raw)
        self._partitioned_publication_owner=held
        try:
            held.__init__(owner=self,checkpoint=self.inventory_checkpoint,archive_preparation=archive_preparation,
                allocation=allocation,entry_raw=entry_raw,context_raw=context_raw,parent_identity_raw=parent_identity_raw)
            return held
        except BaseException as error:
            self._remember_publication(error);held._failed(error)

    def prepare_request_writers(self, *, publication, declaration, participants):
        held=monitor.RequestWriterPreparation.__new__(monitor.RequestWriterPreparation)
        held._retain_inputs(owner=self,checkpoint=None,publication=publication,
            declaration=declaration,participants=participants)
        previous=getattr(self,'_ReaderGitParent__request_writers_owner',None)
        if previous is not None:
            previous.rejected=held;previous._failed(ValueError('reader original request writers cannot be replaced'))
        self.__request_writers_owner=self._request_writers_owner=held
        try:
            checkpoint=self.inventory_checkpoint  # Original holder is attached before this getter.
            held.original_inputs=(self,checkpoint,publication,declaration,participants)
            held.checkpoint=checkpoint
            held.__init__(owner=self,checkpoint=checkpoint,publication=publication,
                declaration=declaration,participants=participants)
            return held
        except BaseException as error:held._failed(error)

    def prepare_publication_launch(self, *, pipe_io, creator):
        return ReaderPublicationLaunchPreparation(self,pipe_io,creator)

    def issue_publication_resources(self, issuer):
        self.original_publication_resource_input=issuer  # Before validation or storage/root IO.
        held=tree.owner.PublicationPipeResources.__new__(tree.owner.PublicationPipeResources)
        self.initializing_publication_resources=held
        try:
            held.__init__(issuer,checkpoint=self.inventory_checkpoint,owner=self)
            self._inventory_ready()
            v.require(self.entry['format']==STORAGE_ENTRY_FORMAT,'publication resources require fresh storage entry')
            self.original_publication_storage.view('before_publication_kernel_issue')
            self.publication_resource_return=held.issue()  # Original return before shared post-observation.
            self._inventory_ready()
            return held
        except BaseException as error:
            self._remember_publication(error)
            raise

    def observe_publication_carrier(self, process):
        self.publication_carrier_attempt=process  # Before any getter, clock or ReadFile.
        carrier=getattr(self,'original_publication_carrier',None)
        try:
            held=self.publication_carrier_binding
            current={'request_pin':self.parent.request_pin,'inventory_pin':self.entry['inventory_pin'],
                'root_identity':self.entry['budget_root_identity'],'clock':self.clock,'root':str(self.parent.root),
                'revision':self.parent.request['revision'],'worker_identity':held['creation']}
            v.require(process is self.worker is held['process'] and self.parent is held['endpoint'] and
                self.inventory_publication is held['gate'] and carrier is held['carrier'] and
                process._handle==held['process_handle'] and self.parent.binding_pin==held['binding_pin'] and
                io.json_bytes(held['context'])==held['context_raw']==io.json_bytes(current),
                'carrier fixed original parent binding')
            result=carrier.read_once()
            self.publication_carrier_return=result  # Actual return before candidate validation/readback.
            if result is None:return None
            if hasattr(self,'publication_carrier_candidate'):
                candidate=self.publication_carrier_candidate
                v.require(candidate['return'] is result and candidate['owner'] is self and candidate['process'] is process and
                    candidate['binding'] is held and candidate['payload_raw']==result['payload_raw'] and
                    all(candidate[key] is False for key in ('parent_ack_authorized','execution_authenticated','atomic_reservation')),
                    'carrier original cached parent return')
                actors.proof.evidence._raw(result['payload_raw'],candidate['payload_pin'],
                    'carrier cached original parent payload')
                return self.publication_carrier_candidate
            candidate=self.publication_carrier_candidate={'return':result,'owner':self,'process':process,
                'binding':held,'payload_raw':result['payload_raw'],'payload_pin':observed._pin(result['payload_raw']),
                'raw':{},'parent_ack_authorized':False,'execution_authenticated':False,'atomic_reservation':False}
            value=result['value']
            v.require(value['context']==held['context'] and value['binding_pin']==held['binding_pin'] and
                set(value['publications'])==set(actors.archive.ChildPublicationCapture.NAMES),
                'carrier candidate exact request/inventory/root/clock/revision/worker')
            total=0
            for name in actors.archive.ChildPublicationCapture.NAMES:
                row=value['publications'][name]
                actors.proof.evidence._keys(row,'pin fd file_identity python_close_return rename_return','carrier candidate row')
                v.require(type(row['fd']) is int and row['fd']>=0 and row['python_close_return'] is None and
                    row['rename_return'] is None and type(row['file_identity']) is list and len(row['file_identity'])==2,
                    'carrier candidate close fields cannot authenticate original owners')
                raw=observed._file(self.parent.root/name,channel.MAX_CONTROL)
                candidate['raw'][name]=raw  # Preserve mismatched/partial returned raw before pin/identity checks.
                actors.proof.evidence._raw(raw,row['pin'],'carrier original parent full raw pin')
                stat=paths.regular_path(self.parent.root/name).lstat()
                v.require([stat.st_dev,stat.st_ino]==row['file_identity'],'carrier original parent file identity')
                total+=len(raw)
            v.require(type(value['raw_bytes']) is int and total==value['raw_bytes'],'carrier separate full raw byte count')
            self._inventory_ready()
            candidate['post_checkpoint_raw']={}
            for name in actors.archive.ChildPublicationCapture.NAMES:
                raw=observed._file(self.parent.root/name,channel.MAX_CONTROL)
                candidate['post_checkpoint_raw'][name]=raw
                v.require(raw==candidate['raw'][name],'carrier raw changed during original shared checkpoint')
            return candidate  # A candidate remains false until the original child owner transport is authenticated.
        except BaseException as failure:
            if carrier is not None:carrier._failed(failure)
            self._remember_publication(failure);raise

    def _deny_child_publication(self, process, endpoint, observation):
        held={'owner':self,'process':process,'endpoint':endpoint,'observation':observation,
            'publication_admission':self.inventory_publication,'original_request':endpoint.request,
            'request_pin':endpoint.request_pin,'inventory_pin':self.entry['inventory_pin'],
            'root_identity':self.entry['budget_root_identity'],'clock':self.clock,
            'root':str(endpoint.root),'revision':endpoint.request['revision'],
            'binding_pin':observation['binding_pin'],'worker_identity':observation['binding']['worker_identity'],
            'child_close_rename_owner_observation':None,'parent_ack_authorized':False,
            'carrier_candidate':getattr(self,'publication_carrier_candidate',None),
            'execution_authenticated':False,'atomic_reservation':False}
        self.pending_child_publication_denial=held  # Preserve all original raw/owners before context validation.
        held['context_raw']=io.json_bytes({key:held[key] for key in ('request_pin','inventory_pin','root_identity','clock',
            'root','revision','binding_pin','worker_identity')})
        v.require(len(held['context_raw'])<=channel.MAX_CONTROL,'reader bounded original child IO denial context')
        v.require(self.original_child_publication_denial is None and process is self.worker and endpoint is self.parent and
            observation is endpoint.pending_child_publication and observation['process'] is process and
            observation['publication_admission'] is self.inventory_publication and observation['proof_verdict'] is True and
            observation['binding_pin']==endpoint.binding_pin and observation['binding']['worker_identity']==
                v.strict_json(observation['ack']['raw'])['worker_identity'] and
            self.inventory_publication.request_pin==held['request_pin'] and
            self.inventory_publication.inventory_pin==held['inventory_pin'],
            'reader exact original child publication denial context')
        self.original_child_publication_denial=endpoint.original_child_publication_denial=held
        return False  # Missing original child IO link cannot be supplied by flags/metadata or a True proof alone.

    def _remember_publication(self, failure):
        gate=self.inventory_publication
        if gate is None:return  # Existing default exception/owner behavior.
        if self.inventory_publication_error is None:self.inventory_publication_error=failure
        if self.error is None:self.error=failure
        if self.inventory_pending_owner is None:self.inventory_pending_owner=gate.pending
        failure.reader_git_parent=self

    def _inventory_ready(self):
        writers=getattr(self,'_ReaderGitParent__request_writers_owner',None)
        if writers is not None:
            try:
                writers._fixed();v.require(not writers.unresolved(),'reader request writer admission unresolved')
            except BaseException as error:writers._failed(error)
        partition=getattr(self,'_partitioned_publication_owner',None)
        if partition is not None:
            try:
                partition._fixed();v.require(not partition.unresolved(),'reader partitioned publication admission unresolved')
            except BaseException as error:partition._failed(error)
        resources=getattr(self,'original_publication_resources',None)
        if resources is not None:
            try:
                resources._fixed()
                v.require(not resources.unresolved() and not resources.close_started,
                    'reader publication resources pending or permanently closed')
            except BaseException as error:resources._failed(error)
        launch=getattr(self,'original_publication_launch',None)
        if launch is not None:
            try:launch._fixed()
            except BaseException as error:launch._failed(error)
        storage=getattr(self,'original_publication_storage',None)
        if storage is not None:
            if storage.original_error is not None:raise storage.original_error
            v.require(not storage.unresolved(),'reader original storage observation unresolved')
        carrier=getattr(self,'original_publication_carrier',None)
        if carrier is not None:
            v.require(not carrier.unresolved(),'reader original carrier IO unresolved')
        if getattr(self,'original_request_bootstrap',None) is not None and self.error is not None:raise self.error
        if self.inventory_publication_error is not None:
            raise self.inventory_publication_error  # Never overwrite the original rejected/pending owners.
        gate=getattr(self,'inventory_publication',None)
        sidecar=getattr(self,'control_publication_owner',None)
        if self.inventory_pending_owner is None and getattr(gate,'pending',None) is not None:
            self.inventory_pending_owner=gate.pending
        self.rejected_inventory_publication=(gate,sidecar)  # Keep rejected IO owners before diagnostics.
        if gate is None and sidecar is None:return
        try:
            if self.inventory_publication_error is not None:raise self.inventory_publication_error
            channel_error=getattr(self.parent,'parent_publication_error',None)
            if channel_error is not None:raise channel_error
            if gate.error is not None:raise gate.error
            v.require(type(gate) is actors.archive.ControlPublicationAdmission and sidecar is gate and
                gate.owner is self and gate.endpoint is self.parent and gate.checkpoint is self.inventory_checkpoint and
                gate.inventory_pin==self.entry['inventory_pin'] and gate.control_limits==self.append_controls and
                list(gate.identity)==self.entry['budget_root_identity'],
                'reader same original parent inventory gate, clock, context and root')
            v.require(gate.pending is None,'reader original inventory IO remains pending')
            allowed=('worker-inventory.json','binding.json','stop.json')
            names=tuple(name for name in allowed if name in gate.completed)
            v.require(names and names[0]=='worker-inventory.json' and set(names)==set(gate.completed),
                      'reader only its original inventory/binding/stop publications')
            for name in allowed:
                path=self.parent.root/name;paths.regular_path(path,missing=True)
                pending=path.with_name(name+'.pending');paths.regular_path(pending,missing=True)
                v.require(not pending.exists() and (name in gate.completed)==path.exists(),
                          'reader no unknown original parent control publication or pending')
            gate.verify_publications(names,cached=True,extended=len(names)>1)
        except BaseException as failure:
            if self.inventory_pending_owner is None and getattr(gate,'pending',None) is not None:
                self.inventory_pending_owner=gate.pending
            if self.inventory_publication_error is None:self.inventory_publication_error=failure
            if self.error is None:self.error=failure
            failure.reader_git_parent=self
            raise


class ParentPublicationRetention:
    """Retain Python publication owners; never retry IO or infer native recovery."""
    def __init__(self, parent, error, owners, caller_plan):
        self.parent, self.original_error, self.owners = parent, error, owners
        self.original_caller_plan = caller_plan
        self.pending = self.errors = ()
        self.original_inputs = parent.original_bootstrap_inputs
        self.worker = parent.worker
        self.endpoint = getattr(parent,'parent',None)
        self.existing_worker_error = self.pause_error = None
        parent.publication_retention = self
        parent.original_publication_retention = self
        error.parent_publication_retention = self
        try:
            for owner in owners:
                if owner is None:continue
                self.observing_owner=owner
                self.pending += (getattr(owner,'pending',None),)  # Preserve each result before the next fallible read.
                self.errors += (getattr(owner,'error',None),)
        except BaseException as failure:
            self.diagnostic_error=failure;error.reader_publication_diagnostic_error=failure

    def _pause(self):
        try:channel.time.sleep(0.25)
        except BaseException as failure:
            if self.pause_error is None:self.pause_error=failure

    def hold(self):
        # Unknown FileIO return/pending/raw cannot be repaired by a sleep,
        # closed metadata, caller report or a worker kill/wait declaration.
        while True:self._pause()

    def retain_worker(self, error):
        if hasattr(self,'original_worker_keeper_call'):
            self.rejected_worker_keeper_call=error
            self.hold()
            raise self.original_error
        held=self.original_worker_keeper_call={'error':error,'keeper':parent_supervisor.retain_until_exit,
            'return':None,'return_observed':False}  # Original callable/owner before keeper/native/diagnostic IO.
        try:
            v.require(error is self.existing_worker_error,'caller same original worker exception')
            held['return']=held['keeper'](error)
            held['return_observed']=True
        except BaseException as failure:self.worker_retention_error=failure
        self.hold()
        raise self.original_error  # Keeper return/interruption never resolves Python publication IO.


def retain_parent_publications(error, parent=None, *, caller_plan=None):
    """Before caller diagnostics/return, preserve the exact original IO owners.

    A supervisor's existing Unreaped/UnreconciledWorker keeps its own handle
    and fence path. Bootstrap has no process to kill, wait or close.
    """
    original=getattr(error,'reader_git_parent',None)
    if not isinstance(original,ReaderGitParent):original=getattr(getattr(error,'fence_error',None),'reader_git_parent',None)
    if not isinstance(original,ReaderGitParent):original=parent
    if not isinstance(original,ReaderGitParent):return False
    existing=getattr(original,'original_publication_retention',None)
    owners=(getattr(original,'original_request_bootstrap',None),
        getattr(original,'request_bootstrap_owner',None),getattr(original,'inventory_publication',None),
        getattr(original,'control_publication_owner',None),getattr(original,'original_publication_carrier',None),
        getattr(original,'publication_carrier',None),getattr(original,'original_publication_storage',None),
        getattr(original,'publication_storage',None),getattr(original,'original_storage_preparation',None),
        getattr(original,'storage_preparation',None),getattr(original,'original_publication_launch',None),
        getattr(original,'publication_launch',None),getattr(original,'original_publication_resources',None),
        getattr(original,'publication_resources',None))
    partition=(getattr(original,'_partitioned_publication_owner',None),getattr(original,'partitioned_publication',None))
    if any(owner is not None for owner in partition):owners+=partition
    writers=(getattr(original,'_ReaderGitParent__request_writers_owner',None),
        getattr(original,'_request_writers_owner',None),getattr(original,'request_writers',None),
        getattr(original,'original_request_writers',None))
    if any(owner is not None for owner in writers):owners+=writers
    storage_input=len(original.original_bootstrap_inputs)>10 and original.original_bootstrap_inputs[10] is not None
    if all(owner is None for owner in owners) and existing is None and not storage_input:return False
    rejected=(getattr(original,'rejected_request_bootstrap',None),
        getattr(original,'rejected_inventory_publication',None),getattr(owners[4],'rejected',None))
    error.reader_publication_owners=(original,owners,rejected,caller_plan)  # Before diagnosis/keeper entry.
    try:
        problem=(existing is not None or getattr(original,'error',None) is not None or
            any(getattr(owner,'error',None) is not None or getattr(owner,'pending',None) is not None
                for owner in owners if owner is not None) or
            owners[0] is not owners[1] or owners[2] is not owners[3] or owners[4] is not owners[5] or
            (owners[4] is not None and owners[4].unresolved()) or owners[6] is not owners[7] or
            (owners[6] is not None and owners[6].unresolved()) or owners[8] is not owners[9] or
            (owners[8] is not None and owners[8].unresolved()) or owners[10] is not owners[11] or
            (owners[10] is not None and owners[10].unresolved()) or owners[12] is not owners[13] or
            (owners[12] is not None and owners[12].unresolved()) or
            (any(owner is not None for owner in partition) and
                (partition[0] is not partition[1] or partition[0].unresolved())) or
            (any(owner is not None for owner in writers) and
                (any(owner is not writers[0] for owner in writers[1:]) or writers[0].unresolved())))
    except BaseException as failure:
        error.reader_publication_diagnostic_error=failure;problem=True
    if not problem:return False
    if existing is None:existing=ParentPublicationRetention(original,error,owners,caller_plan)
    error.parent_publication_retention=existing
    v.require(type(existing) is ParentPublicationRetention and existing.parent is original,
              'caller original retained Python publication owner')
    if getattr(original,'publication_retention',None) is not existing:
        existing.rejected_retention=(existing,getattr(original,'publication_retention',None))
    if isinstance(error,parent_supervisor.UnreapedWorker):
        if existing.existing_worker_error is not None and existing.existing_worker_error is not error:
            existing.rejected_worker_error=(existing.existing_worker_error,error)
            existing.hold()
            raise existing.original_error
        existing.existing_worker_error=error  # Link, never replace/recreate its original handle/fence keeper.
        return True
    existing.hold()
    raise existing.original_error  # An unexpected return is never a report/release authorization.


class ReaderPublicationLaunchPreparation:
    """Retain preissued local IO and the original Popen, without launching it.

    Options contain Python resources and cannot cross a process as JSON. A
    native issuer, explicit HANDLE inheritance and child-owner authentication
    remain separate gates; this preparation never creates or closes a handle.
    """
    def __init__(self,parent,pipe_io,creator):
        self.original_inputs=(parent,pipe_io,creator)
        self.parent,self.creator=parent,creator
        self.error=self.original_error=self.pending=self.process=self.options=None
        self.rejected=None
        try:
            self.previous=getattr(parent,'original_publication_launch',None)
            if self.previous is not None:
                self.previous.rejected=self
                self.previous._failed(ValueError('reader launch preparation cannot be replaced'))
            parent.original_publication_launch=parent.publication_launch=self
            self.pipe_io=dict(pipe_io) if type(pipe_io) is dict else pipe_io
            v.require(type(parent) is ReaderGitParent and type(self.pipe_io) is dict and
                set(self.pipe_io)=={'kernel','stdin'},'reader original local kernel/stdin')
            self.endpoint,self.storage,self.gate=parent.parent,parent.original_publication_storage,parent.inventory_publication
            self.checkpoint=parent.inventory_checkpoint
            self.entry_raw=io.json_bytes(parent.entry);self.entry_pin=observed._pin(self.entry_raw)
            v.require(parent.entry['format']==STORAGE_ENTRY_FORMAT and len(self.entry_raw)<=channel.MAX_CONTROL and
                type(self.storage) is actors.archive.PublicationStorageAdmission and parent.worker is None and
                type(creator) is tree.owner.NativeGitPipes and creator.kernel is self.pipe_io['kernel'] and
                creator.checkpoint is self.checkpoint and creator.result is True and creator.error is None and
                creator.spawn_io is None and creator.native.job is creator.native.process is creator.native.thread is None,
                'reader fresh storage entry and preissued dedicated original pipe owner')
            self.kernel,self.stdin=self.pipe_io['kernel'],self.pipe_io['stdin']
            creator.native.reader_publication_launch=self  # Before shared clock/root observations.
            resources=getattr(creator,'original_publication_resources',None)
            if resources is not None:resources.note_share(self)
            self._fixed();parent._inventory_ready();self.storage.view('reader_launch_preparation')
            self._fixed()
        except BaseException as error:self._failed(error)

    def _failed(self,error):
        if self.original_error is None:self.original_error=error
        self.error=self.original_error
        self.error.reader_publication_launch=self
        self.error.reader_git_parent=self.parent
        remember=getattr(self.parent,'_remember_publication',None)
        if callable(remember):remember(self.error)
        raise self.error

    def _fixed(self):
        if self.original_error is not None:raise self.original_error
        if self.error is not None:raise self.error
        buffers=getattr(self,'original_publication_native_buffers',None)
        if buffers is not None:buffers._fixed()
        native_process=getattr(self,'original_publication_native_process',None)
        if native_process is not None:native_process._fixed()
        inheritance=getattr(self,'original_publication_inheritance',None)
        if inheritance is not None:inheritance._fixed()
        self.rejected_binding=(getattr(self.parent,'publication_launch',None),self.parent.parent,
            getattr(self.parent,'original_publication_storage',None),self.parent.entry)
        v.require(self.parent.original_publication_launch is self.parent.publication_launch is self and
            self.parent.parent is self.endpoint and self.parent.original_publication_storage is self.storage and
            self.parent.inventory_publication is self.gate and self.parent.inventory_checkpoint is self.checkpoint and
            io.json_bytes(self.parent.entry)==self.entry_raw and self.pipe_io=={'kernel':self.kernel,'stdin':self.stdin} and
            self.creator is self.original_inputs[2] and self.creator.kernel is self.kernel and
            self.creator.checkpoint is self.checkpoint and self.creator.native.reader_publication_launch is self,
            'reader same original launch entry/resources/storage/clock/owner')
        if self.options is not None:
            v.require(self.options['pipe_io']==self.pipe_io and
                self.options['publication_io']['creator'] is self.creator and
                io.json_bytes(self.options['publication_io']['context'])==self.context_wrapper_raw,
                'reader issued launch options cannot follow callback changes')
        self.storage._fixed()

    def prepare_inheritance(self):
        held=tree.owner.PublicationPipeInheritance.__new__(tree.owner.PublicationPipeInheritance)
        self.initializing_publication_inheritance=held
        try:
            self._fixed()
            v.require(self.process is None and self.options is None,'reader inheritance preparation before original Popen')
            source=getattr(self.creator,'original_publication_resources',None)
            held.__init__(source,owner=self)
            self.parent._inventory_ready();self.storage.view('before_publication_inheritance')
            self.inheritance_return=held.prepare()
            self.parent._inventory_ready()
            return held
        except BaseException as error:self._failed(error)

    def offer_inheritance(self):
        try:
            self._fixed()
            held=self.original_publication_inheritance
            self.inheritance_offer_return=held.offer()
            return self.inheritance_offer_return
        except BaseException as error:self._failed(error)

    def prepare_handle_list(self, stdio, *, last_error):
        held=tree.owner.PublicationHandleListPreparation.__new__(tree.owner.PublicationHandleListPreparation)
        self.initializing_publication_handle_list=held  # Before argument validation, storage or API IO.
        try:
            self._fixed()
            v.require(self.process is None and self.options is None,'reader attribute preparation before Popen')
            held.__init__(self.original_publication_inheritance,stdio,owner=self,last_error=last_error)
            self.parent._inventory_ready();self.storage.view('before_publication_handle_list')
            self.handle_list_return=held.prepare()
            self.parent._inventory_ready()
            return held
        except BaseException as error:self._failed(error)

    def arm_native_buffers(self,allocation):
        held=tree.owner.PublicationNativeBufferAdmission.__new__(tree.owner.PublicationNativeBufferAdmission)
        held.caller_inputs=(self,allocation)
        self.initializing_publication_native_buffers=held
        try:
            self._fixed()
            v.require(self.process is None and self.options is None and
                getattr(self,'original_publication_handle_list',None) is None,
                'reader independent native buffer allocation before attributes')
            held.__init__(allocation,owner=self)
            self.native_buffer_admission_return=held.view()
            self.parent._inventory_ready();self.storage.view('before_publication_native_buffers')
            held._fixed();return held
        except BaseException as error:self._failed(error)

    def bind(self,process):
        self.rejected_process=process  # Before even Popen getters or identity IO.
        try:
            self._fixed()
            v.require(getattr(self,'original_publication_native_process',None) is None,
                'reader retained raw native owner cannot be replaced by a Popen bind')
            v.require(self.process is None,'reader launch original Popen bind once')
            self.process=process;self.pending={'process':process,'creator':self.creator,'storage':self.storage}
            held=self.pending
            held['process_handle']=process._handle
            inheritance=getattr(self,'original_publication_inheritance',None)
            if inheritance is not None:
                v.require(inheritance.offered is not None,'reader original inheritance offer required before Popen bind')
            held['creation_return']=self.parent.bind(process)
            self._fixed()
            held['carrier_return']=self.parent.bind_publication_carrier(self.creator,
                frame_limit=self.storage.allocation['frame_bytes'])
            binding=self.parent.publication_carrier_binding
            v.require(binding['process'] is process and binding['process_handle']==held['process_handle'] and
                binding['creation']==held['creation_return'],'reader original Popen HANDLE and returned creation')
            value={'format':PUBLICATION_LAUNCH_FORMAT,**copy.deepcopy(binding['context']),
                'binding_pin':copy.deepcopy(binding['binding_pin']),'entry_pin':copy.deepcopy(self.entry_pin),
                'formal_permission':False}
            raw=io.json_bytes(value);v.require(len(raw)<=channel.MAX_CONTROL,'reader bounded fresh local launch context')
            wrapper={'value':value,'pin':observed._pin(raw)}
            self.context_wrapper_raw=io.json_bytes(wrapper)
            self.options={'pipe_io':dict(self.pipe_io),'publication_io':{'creator':self.creator,'context':wrapper}}
            held['options_return']=self.options
            if inheritance is not None:
                held['inheritance_binding_return']=inheritance.bind_worker(process,held['process_handle'],
                    held['creation_return'],self.context_wrapper_raw)
            self._fixed();self.pending=None
            return self.options
        except BaseException as error:self._failed(error)

    def cached_options(self):
        try:
            self._fixed();v.require(self.options is not None and self.pending is None,'reader original issued local options')
            return self.options
        except BaseException as error:self._failed(error)

    def unresolved(self):
        try:self._fixed();return self.pending is not None or getattr(self,'original_publication_native_process',None) is not None
        except BaseException as error:
            if self.error is None:self.error=error
            return True


    def prepare_native_process(self,argv,cwd,job_owner):
        held=tree.owner.PublicationNativeProcessPreparation.__new__(tree.owner.PublicationNativeProcessPreparation)
        held.caller_inputs=(self,argv,cwd,job_owner)  # Before entry/storage/clock getters.
        self.initializing_publication_native_process=held
        try:
            self._fixed()
            v.require(self.process is None and self.options is None and cwd==str(self.endpoint.root),
                'reader raw native process preparation before process in the same root')
            held.__init__(self.original_publication_handle_list,argv,cwd,job_owner,owner=self,binding=self.entry_raw)
            self.parent._inventory_ready();self.storage.view('before_publication_native_process_preparation')
            self.native_process_preparation_return=held.prepare()
            self.parent._inventory_ready();held._fixed()
            return held
        except BaseException as error:self._failed(error)


class ReaderPublicationInputs:
    """Keep child-local borrowed resources before parse/copy/constructor IO."""
    def __init__(self,argv,pipe_io,publication_io):
        self.original_inputs=(argv,pipe_io,publication_io)
        self.worker=self.actor=self.error=self.original_error=self.pause_error=None

    def checked(self):
        try:
            if self.original_error is not None:raise self.original_error
            v.require(not hasattr(self,'checked_return'),'reader local input copy cannot be rearmed')
            pipe,publication=self.original_inputs[1:]
            self.pipe_io=dict(pipe) if type(pipe) is dict else pipe
            self.publication_io=dict(publication) if type(publication) is dict else publication
            v.require(type(self.pipe_io) is dict and set(self.pipe_io)=={'kernel','stdin'} and
                type(self.publication_io) is dict and set(self.publication_io)=={'creator','context'},
                'reader publication resources are local closed inputs')
            self.creator=self.publication_io['creator'];self.context=copy.deepcopy(self.publication_io['context'])
            v.require(type(self.context) is dict and set(self.context)=={'value','pin'},'reader fresh launch context pin')
            raw=io.json_bytes(self.context['value']);v.require(len(raw)<=channel.MAX_CONTROL,'reader local context bound')
            actors.proof.evidence._raw(raw,self.context['pin'],'reader local launch context pin')
            value=self.context['value']
            v.require(type(value) is dict and set(value)=={'format','request_pin','inventory_pin','root_identity','clock',
                'root','revision','worker_identity','binding_pin','entry_pin','formal_permission'} and
                value['format']==PUBLICATION_LAUNCH_FORMAT and value['formal_permission'] is False and
                type(self.creator) is tree.owner.NativeGitPipes and self.creator.kernel is self.pipe_io['kernel'] and
                self.creator.result is True and self.creator.error is None and self.creator.spawn_io is None and
                self.creator.native.job is self.creator.native.process is self.creator.native.thread is None,
                'reader original dedicated carrier and closed fresh context')
            self.context_raw=raw
            self.checked_return=self
            return self
        except BaseException as error:self.failed(error)

    def before_entry(self,pipe_io):
        try:
            if self.original_error is not None:raise self.original_error
            if self.error is not None:raise self.error
            v.require(getattr(self,'checked_return',None) is self and type(pipe_io) is dict and
                set(pipe_io)=={'kernel','stdin'} and pipe_io['kernel'] is self.pipe_io['kernel'] is self.creator.kernel and
                pipe_io['stdin'] is self.pipe_io['stdin'] and io.json_bytes(self.context['value'])==self.context_raw,
                'reader exact checked local resources before entry IO')
            actors.proof.evidence._raw(self.context_raw,self.context['pin'],'reader retained context before entry IO')
        except BaseException as error:self.failed(error)

    def attach(self,worker,entry):
        self.worker=worker  # Before binding readback or another callback.
        try:
            v.require(entry.get('format')==STORAGE_ENTRY_FORMAT,'reader publication requires fresh storage entry')
            actors.proof.evidence._raw(io.json_bytes(entry),self.context['value']['entry_pin'],
                'reader launch exact entry before actor IO')
            binding,pin=worker.child._binding()
            self.binding_return=(binding,pin)
            expected={'format':PUBLICATION_LAUNCH_FORMAT,'request_pin':worker.child.request_pin,
                'inventory_pin':entry['inventory_pin'],'root_identity':list(worker.identity),
                'clock':worker.child.request['clock'],'root':str(worker.child.root),'revision':worker.child.request['revision'],
                'worker_identity':worker.child.identity,'binding_pin':pin,'entry_pin':self.context['value']['entry_pin'],
                'formal_permission':False}
            v.require(io.json_bytes(expected)==self.context_raw and binding['worker_identity']==worker.child.identity,
                'reader launch original request/inventory/root/clock/binding/worker')
        except BaseException as error:self.failed(error)

    def arm(self,actor):
        self.actor=actor  # Before sender/storage/clock IO.
        try:
            v.require(self.error is None and actor is self.worker.actor and
                actor.pipe_io['kernel'] is self.pipe_io['kernel'] and actor.pipe_io['stdin'] is self.pipe_io['stdin'],
                'reader original borrowed IO to actor')
            self.carrier_return=actor.control_publication.arm_publication_carrier(self.creator,
                frame_limit=actor.original_publication_storage.allocation['frame_bytes'])
            return self.carrier_return
        except BaseException as error:self.failed(error)

    def fixed(self,actor):
        try:
            if self.original_error is not None:raise self.original_error
            if self.error is not None:raise self.error
            v.require(actor is self.actor is self.worker.actor and actor.publication_inputs is self and
                io.json_bytes(self.context['value'])==self.context_raw and
                actor.pipe_io['kernel'] is self.pipe_io['kernel'] is self.creator.kernel and
                actor.pipe_io['stdin'] is self.pipe_io['stdin'] and self.worker.publication_inputs is self,
                'reader original child launch resources/context cannot be hidden')
            actors.proof.evidence._raw(self.context_raw,self.context['pin'],'reader fixed launch context pin')
            self.carrier_return._fixed()
        except BaseException as error:self.failed(error)

    def failed(self,error):
        if self.original_error is None:self.original_error=error
        self.error=self.original_error
        self.error.reader_publication_inputs=self
        if self.worker is not None:self.error.reader_git_worker=self.worker
        if self.actor is not None:
            if self.actor.error is None:self.actor.error=self.error
            gate=getattr(self.actor,'control_publication',None)
            if gate is not None:gate._failed(self.error)
        raise self.error

    def _pause(self):
        try:channel.time.sleep(0.25)
        except BaseException as error:
            if self.pause_error is None:self.pause_error=error

    def hold(self):
        child=getattr(self.worker,'child',None)
        if child is not None:child.stopped=True
        while True:self._pause()


class ReaderInitializationRetention:
    def __init__(self,worker,error):
        self.worker,self.original_error=worker,error
        self.actor=worker.original_initializing_actor
        self.original_entry=worker.original_entry
        self.original_inputs=self.actor.original_constructor_inputs
        self.control=getattr(self.actor,'control_publication',None)
        self.storage=getattr(self.actor,'original_publication_storage',None)
        self.pause_error=None
        worker.original_initialization_retention=self
        error.reader_initialization_retention=self  # Before reporting or another fallible observation.

    def _pause(self):
        try:channel.time.sleep(0.25)
        except BaseException as error:
            if self.pause_error is None:self.pause_error=error

    def hold(self):
        self.worker.child.stopped=True
        while True:self._pause()


def retain_reader_initialization(error):
    inputs=getattr(error,'reader_publication_inputs',None)
    if type(inputs) is ReaderPublicationInputs:
        inputs.hold()
        raise inputs.error
    worker=getattr(error,'reader_git_worker',None)
    if not isinstance(worker,_ORIGINAL_READER_WORKER_CLASS) or not hasattr(worker,'original_initializing_actor'):return False
    actor=worker.original_initializing_actor
    if getattr(actor,'control_publication',None) is None and getattr(actor,'original_publication_storage',None) is None:return False
    held=getattr(worker,'original_initialization_retention',None)
    if held is None:held=ReaderInitializationRetention(worker,error)
    held.hold()
    raise held.original_error


class ReaderGitWorker:
    def __init__(self, entry, *, revision, repository, names, pipe_io=None, publication_io=None):
        self.original_publication_io=publication_io
        self.publication_inputs=None
        try:
            if publication_io is not None:
                self.publication_inputs=(publication_io if type(publication_io) is ReaderPublicationInputs else
                    ReaderPublicationInputs(None,pipe_io,publication_io).checked())
                self.publication_inputs.worker=self
                self.publication_inputs.before_entry(pipe_io)
            self._initialize(entry,revision=revision,repository=repository,names=names,pipe_io=pipe_io)
        except BaseException as error:
            if self.publication_inputs is not None:self.publication_inputs.failed(error)
            raise

    def _initialize(self, entry, *, revision, repository, names, pipe_io=None):
        # Native objects come from the retaining caller, never the JSON entry.
        self.original_pipe_io = pipe_io
        self.pipe_io = None if pipe_io is None else dict(pipe_io) if type(pipe_io) is dict else pipe_io
        self.original_entry = entry
        entry=copy.deepcopy(entry)  # Before any channel/source/clock observation.
        self.clock = time.monotonic  # Same function for this checkpoint and the actor's call window.
        if pipe_io is not None:
            v.require(type(self.pipe_io) is dict and set(self.pipe_io) == {'kernel','stdin'},
                      'reader caller-held pipe kernel/stdin only')
        storage=type(entry) is dict and entry.get('format')==STORAGE_ENTRY_FORMAT
        append=type(entry) is dict and entry.get('format') in (APPEND_ENTRY_FORMAT,STORAGE_ENTRY_FORMAT)
        fields={'channel_root','request_pin','inventory_path','inventory_pin','budget_root_identity'}
        v.require(type(entry) is dict and set(entry)==fields|({'format','append_plan'} if append else set())|
            ({'storage_plan'} if storage else set()),
            'reader Git entry exact fields')
        self.append_plan=copy.deepcopy(entry['append_plan']) if append else None
        self.storage_plan=copy.deepcopy(entry['storage_plan']) if storage else None
        if append:
            v.require(self.pipe_io is not None,'reader append entry requires caller-held pipe IO')
            v.require(type(self.append_plan) is dict and set(self.append_plan)=={'value','pin'},
                      'reader append entry exact context')
            actors.proof.evidence._raw(io.json_bytes(self.append_plan['value']),self.append_plan['pin'],
                                      'reader append context pin before channel IO')
        if storage:
            v.require(type(self.storage_plan) is dict and set(self.storage_plan)=={'value','pin'},
                'reader storage exact context before channel IO')
            raw=io.json_bytes(self.storage_plan['value'])
            v.require(len(raw)<=channel.MAX_CONTROL,'reader storage context bound before channel IO')
            actors.proof.evidence._raw(raw,self.storage_plan['pin'],'reader storage context pin before channel IO')
            actors.archive.checked_storage_allocation(self.storage_plan['value']['allocation'])
        self.child = channel.ChildChannel(entry['channel_root'],entry['request_pin'])
        self.root = paths.regular_path(Path(self.child.request['budget_root']),directory=True)
        identity = entry['budget_root_identity']
        v.require(type(identity) is list and len(identity)==2 and all(type(n) is int and n>=0 for n in identity)
            and identity[1]>0, 'reader caller-held budget root identity')
        self.identity = tuple(identity)
        if append:
            actors.archive.checked_append_plan(self.append_plan,request=self.child.request,
                request_pin=self.child.request_pin,inventory_pin=entry['inventory_pin'],root_identity=self.identity)
        if storage:
            actors.archive.checked_storage_plan(self.storage_plan,request=self.child.request,request_pin=self.child.request_pin,
                inventory_pin=entry['inventory_pin'],root_identity=self.identity)
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
        if self.publication_inputs is not None:self.publication_inputs.attach(self,entry)
        options = {} if self.pipe_io is None else {'pipe_io':{
            **self.pipe_io,'clock':self.clock,'root_identity':self.identity}}
        if append:options['append_plan']=copy.deepcopy(self.append_plan)
        if storage:
            options['storage_plan']=copy.deepcopy(self.storage_plan)
            if self.publication_inputs is not None:options['publication_inputs']=self.publication_inputs
            self.actor=actors.WorkerGitActor.__new__(actors.WorkerGitActor)  # Keep before constructor IO/return.
            self.original_initializing_actor=self.actor
            try:
                self.actor.__init__(child=self.child,inventory_raw=raw,inventory_pin=entry['inventory_pin'],
                    checkpoint=self.checkpoint,**options)
            except BaseException as error:
                self.error=error;error.reader_git_worker=self;raise
        else:
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


_ORIGINAL_READER_WORKER_CLASS=ReaderGitWorker
