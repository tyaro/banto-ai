"""Bounded worker Git raw/event storage; no process launch or lease release.

Caller-held manifest/inventory pins bind the saved resolver to original raw.
Failed appends retain the partial archive and pending packet and forbid reuse.
Actual worker, owner lifetime, cache and common-budget wiring are separate.
"""
from __future__ import annotations

import base64
import copy
import gzip
import os
from pathlib import Path

from . import anomaly_v03_preformal_worker_git_proof as proof
from . import anomaly_v03_preformal_git_receipt_archive as bounds

v, io, observed, evidence, paths = proof.v, proof.io, proof.observed, proof.evidence, proof.tree.paths
FORMAT = 'anomaly-v03-preformal-worker-git-archive-v1'
MAGIC = b'WGA1'
MAX_BYTES, MAX_RECORD, MAX_RAW = bounds.MAX_BYTES, bounds.MAX_RECORD, bounds.MAX_RAW
APPEND_PLAN_FORMAT = 'anomaly-v03-preformal-worker-git-append-plan-v1'


class ArchiveAppendAdmission:
    """Opt-in frame growth and future control snapshot gate, not atomic reservation.

    Original recovery raw, including partial-archive.bin, stays in the measured
    root. Its raw inventory cap never supplies this new archive frame's bytes.
    Every control publisher must participate before this can authorize native.
    """
    CONTROL_NAMES = tuple(name+suffix for name in (
        'request.json','binding.json','stop.json','worker-inventory.json',
        'git-manifest.json','git-proof.json','ack.json') for suffix in ('','.pending'))
    BYTE_LIMIT, ENTRY_LIMIT, RESERVE = 1024**2, 32, 128*1024

    @classmethod
    def validate_controls(cls, value):
        v.require(type(value) is dict and set(value)==set(cls.CONTROL_NAMES) and
            all(type(n) is int and 0<n<=proof.channel.MAX_CONTROL for n in value.values()),
            'archive append all completed and pending control maxima')
        return value

    def __init__(self, *, root, root_identity, revision, inventory_pin, control_limits, checkpoint):
        self.original_root, self.original_identity, self.original_controls = root, root_identity, control_limits
        self.original_inventory_pin, self.checkpoint = inventory_pin, checkpoint
        self.writer = self.rejected_writer = self.pending = self.error = None
        self.completed = []
        self.root, self.identity = Path(root), copy.deepcopy(root_identity)
        self.revision, self.inventory_pin = revision, copy.deepcopy(inventory_pin)
        self.control_limits = copy.deepcopy(control_limits)
        v.require(self.root.is_absolute() and self.root == self.root.resolve() and
            type(self.identity) is tuple and len(self.identity)==2 and
            all(type(n) is int and n>=0 for n in self.identity) and callable(checkpoint),
            'archive append held root identity and shared checkpoint')
        evidence._digest(revision,40); evidence._pin(self.inventory_pin)
        self.validate_controls(self.control_limits)
        self.plan_raw=self._plan()

    def _plan(self):
        return io.json_bytes({'root':str(self.root),'root_identity':list(self.identity),
            'revision':self.revision,'inventory_pin':self.inventory_pin,'control_limits':self.control_limits})

    def _bound(self):
        writer=self.writer
        v.require(self._plan()==self.plan_raw and writer.checkpoint is self.checkpoint and
            writer.verifier.inventory_pin==self.inventory_pin and
            writer.verifier.endpoint.request['revision']==self.revision and
            Path(writer.verifier.endpoint.request['budget_root'])==self.root and writer.path.parent==self.root,
            'archive append held plan or original binding changed')
        if self.pending is not None:
            v.require(writer.raw is self.pending['before_raw'] and
                self.pending['lease']==len(self.completed)==len(writer.rows),
                'archive append original bytes or sequence changed')

    def _failed(self, failure):
        if self.error is None:self.error=failure
        raise self.error

    def bind(self, writer):
        if self.error is not None:raise self.error
        try:
            if self.writer is not None:
                self.rejected_writer=writer
                v.require(False,'archive append cannot rebind its original writer')
            self.writer=writer  # Before caller clock, root or verifier IO.
            v.require(type(writer) is WorkerGitArchive and writer.checkpoint is self.checkpoint and
                writer.verifier.inventory_pin==self.inventory_pin and
                writer.verifier.endpoint.request['revision']==self.revision and
                Path(writer.verifier.endpoint.request['budget_root'])==self.root and
                writer.path.parent==self.root, 'archive append exact inventory/revision/root/writer')
            self.checkpoint(); self._bound(); writer.verifier._live()
            info=paths.regular_path(self.root,directory=True).lstat()
            v.require((info.st_dev,info.st_ino)==self.identity,'archive append original root changed')
        except BaseException as failure:self._failed(failure)

    def _remaining(self, growth, stage):
        self.checkpoint(); self._bound(); self.writer.verifier._live()
        from . import anomaly_v03_preformal_generated_chain_budget as monitor
        snapshot=monitor._directory_snapshot(self.root,self.ENTRY_LIMIT,2,self.identity)
        held={'snapshot':snapshot,'controls':{}}
        self.pending[stage]=held  # Retain observations before subsequent IO.
        # Do not subtract a later per-control stat from an earlier root scan.
        # A concurrent publisher could otherwise shrink the purported future
        # reservation without its new bytes/entry appearing in the snapshot.
        # Count all slots again until every writer joins an atomic protocol.
        future_bytes=sum(self.control_limits.values())
        future_entries=len(self.control_limits)
        for name,maximum in self.control_limits.items():
            path=self.writer.verifier.endpoint.root/name
            paths.regular_path(path,missing=True)
            info=path.lstat() if path.exists() else None
            held['controls'][name]=None if info is None else {'bytes':info.st_size,'identity':(info.st_dev,info.st_ino)}
            size=0 if info is None else info.st_size
            v.require(size<=maximum,'archive append retained control exceeds held maximum')
        held.update(future_bytes=future_bytes,future_entries=future_entries,growth_bytes=growth)
        v.require(snapshot['directory_bytes']+future_bytes+growth+self.RESERVE<=self.BYTE_LIMIT and
            snapshot['directory_entries']+future_entries+2<=self.ENTRY_LIMIT,
            'archive append frame and future controls exceed original outer remaining budget')

    def reserve(self, writer, lease, frame):
        if self.error is not None:raise self.error
        try:
            v.require(writer is self.writer and self.pending is None and
                type(lease) is int and lease==len(self.completed)==len(writer.rows) and
                type(frame) is bytes and writer.pending['frame'] is frame,
                'archive append original ordered frame')
            self.pending={'lease':lease,'frame':frame,'before_raw':writer.raw}
            v.require(frame[:4]==MAGIC and len(frame)>=8 and
                int.from_bytes(frame[4:8],'big')==len(frame)-8 and len(frame)<=MAX_RECORD+8 and
                len(writer.raw)+len(frame)<=MAX_BYTES,'archive append unchanged frame and archive caps')
            self._remaining(len(frame),'before')
            v.require(observed._file(writer.path,MAX_BYTES)==writer.raw,'archive append original bytes changed')
        except BaseException as failure:self._failed(failure)

    def complete(self, writer):
        if self.error is not None:raise self.error
        try:
            v.require(writer is self.writer and self.pending is not None and
                self.pending['lease']==len(self.completed)==len(writer.rows),
                'archive append original pending completion')
            pending=self.pending
            raw=observed._file(writer.path,MAX_BYTES)
            pending['readback_raw']=raw
            v.require(raw==pending['before_raw']+pending['frame'],'archive append exact added frame readback')
            self._remaining(0,'after')
            row={'lease':pending['lease'],'before_pin':observed._pin(pending['before_raw']),
                'frame_pin':observed._pin(pending['frame']),'archive_pin':observed._pin(raw),
                'atomic_reservation':False,'lease_completed':False,'parent_ack_authorized':False,
                'execution_authenticated':False}
            self.completed.append(row); self.pending=None
        except BaseException as failure:self._failed(failure)


def checked_append_plan(entry, *, request, request_pin, inventory_pin, root_identity):
    """Only bind metadata to original caller pins; never authorize native work."""
    v.require(type(entry) is dict and set(entry)=={'value','pin'},'archive append exact pinned context')
    value=entry['value']; raw=io.json_bytes(value)
    v.require(len(raw)<=proof.channel.MAX_CONTROL,'archive append context byte bound')
    evidence._raw(raw,entry['pin'],'archive append held context pin')
    v.require(type(value) is dict and set(value)=={'format','revision','request_pin','inventory_pin',
        'budget_root','budget_root_identity','control_limits','formal_permission'} and
        value['format']==APPEND_PLAN_FORMAT and value['formal_permission'] is False and
        value['revision']==request['revision'] and value['request_pin']==request_pin and
        value['inventory_pin']==inventory_pin and value['budget_root']==request['budget_root'] and
        value['budget_root_identity']==list(root_identity), 'archive append original request/inventory/root link')
    ArchiveAppendAdmission.validate_controls(value['control_limits'])
    return copy.deepcopy(value['control_limits'])


class ControlPublicationAdmission:
    """Retained named control IO for an existing endpoint, not a shared lock.

    Request bootstrap and issuing this gate to all callers remain separate.
    Python FileIO.close evidence never substitutes for native owner recovery.
    """
    def __init__(self, *, endpoint, inventory_pin, root_identity, control_limits, checkpoint, owner):
        self.original_endpoint = self.endpoint = endpoint
        self.original_owner = self.owner = owner
        self.original_checkpoint = self.checkpoint = checkpoint
        self.original_identity, self.original_controls = root_identity, control_limits
        self.original_inventory_pin = inventory_pin
        self.pending = self.error = None
        self.completed = {}
        try:
            self.identity, self.control_limits = copy.deepcopy(root_identity), copy.deepcopy(control_limits)
            self.inventory_pin = copy.deepcopy(inventory_pin)
            v.require(isinstance(endpoint,proof.channel._Channel) and hasattr(owner,'__dict__') and callable(checkpoint),
                      'control original endpoint, retaining Python owner and checkpoint')
            self.previous_publication_owner=getattr(owner,'control_publication_owner',None)
            if self.previous_publication_owner is not None:
                self.previous_publication_owner.rejected_publication=self
                v.require(False,'control retaining owner cannot replace its original publication gate')
            owner.control_publication_owner=self  # Before checkpoint/file IO; do not replace a prior owner.
            self.request, self.request_pin = copy.deepcopy(endpoint.request), copy.deepcopy(endpoint.request_pin)
            self.root, self.channel_root = Path(self.request['budget_root']), endpoint.root
            v.require(type(self.identity) is tuple and len(self.identity)==2 and
                all(type(n) is int and n>=0 for n in self.identity) and self.identity[1]>0,
                'control original outer identity')
            evidence._pin(self.inventory_pin)
            ArchiveAppendAdmission.validate_controls(self.control_limits)
            self.plan_raw = self._plan()
        except BaseException as error:self._failed(error)

    def _plan(self):
        return io.json_bytes({'request_pin':self.request_pin,'inventory_pin':self.inventory_pin,
            'root':str(self.root),'channel_root':str(self.channel_root),'root_identity':list(self.identity),
            'control_limits':self.control_limits})

    def _failed(self, error):
        if self.error is None:self.error=error
        self.error.control_publication_owner=self  # Retain raw/streams even if the caller propagates this error.
        prior=getattr(self,'previous_publication_owner',None)
        if type(prior) is ControlPublicationAdmission and prior.error is None:
            prior.error=self.error  # A rejected rebind cannot leave the original publication owner armed.
        raise self.error

    def _view(self, stage):
        self.checkpoint()
        v.require(self._plan()==self.plan_raw and self.endpoint is self.original_endpoint and
            self.checkpoint is self.original_checkpoint and self.owner is self.original_owner and
            self.owner.control_publication_owner is self and self.endpoint.request==self.request and
            self.endpoint.request_pin==self.request_pin and self.endpoint.root==self.channel_root,
            'control held plan or original endpoint changed')
        self.endpoint._live()
        from . import anomaly_v03_preformal_generated_chain_budget as monitor
        snapshot=monitor._directory_snapshot(self.root,32,2,self.identity)
        held={'snapshot':snapshot,'controls':{}}
        self.pending[stage]=held
        for name,maximum in self.control_limits.items():
            path=self.channel_root/name
            paths.regular_path(path,missing=True)
            info=path.lstat() if path.exists() else None
            held['controls'][name]=None if info is None else {'bytes':info.st_size,
                'identity':(info.st_dev,info.st_ino)}
            v.require(info is None or info.st_size<=maximum,'control retained raw exceeds held maximum')
        # Keep every future slot, including already observed files. No discount
        # based on a later stat from a different publication instant.
        future_bytes, future_entries=sum(self.control_limits.values()),len(self.control_limits)
        held.update(future_bytes=future_bytes,future_entries=future_entries)
        v.require(snapshot['directory_bytes']+future_bytes+128*1024<=1024**2 and
            snapshot['directory_entries']+future_entries+2<=32,
            'control future frames exceed original outer byte/entry reserve')

    def _readback(self, path, stage):
        raw=observed._file(path,proof.channel.MAX_CONTROL)
        self.pending[stage]=raw
        evidence._raw(raw,self.pending['pin'],'control original raw readback')
        v.require(raw==self.pending['raw'],'control exact raw readback')
        return raw

    def publish(self, path, value):
        if self.error is not None:raise self.error
        try:
            v.require(self.pending is None,'control original publication already pending')
            self.pending={'path':path,'value':value,'owner':self.owner,'stream':None,'fd':None,
                'raw':None,'write_return':None,'close_return':None,'close_return_observed':False}
            pending=self.pending
            path=Path(path);name=path.name
            v.require(path==self.channel_root/name and name in self.control_limits and
                not name.endswith('.pending') and name not in self.completed,
                'control fixed completed name and exclusive publication')
            raw=io.json_bytes(value);pending['raw']=raw;pending['pin']=observed._pin(raw)
            v.require(type(value) is dict and len(raw)<=self.control_limits[name] and
                len(raw)<=self.control_limits[name+'.pending'] and len(raw)<=proof.channel.MAX_CONTROL,
                'control actual canonical raw within both caller slots')
            if name=='request.json':
                evidence._raw(raw,self.request_pin,'control original request pin')
            elif name=='worker-inventory.json':
                evidence._raw(raw,self.inventory_pin,'control original inventory pin')
            elif name=='git-manifest.json':
                v.require(value.get('inventory_pin')==self.inventory_pin,'control manifest inventory link')
            elif name in ('binding.json','stop.json','ack.json'):
                v.require(value.get('request_pin')==self.request_pin,'control original request link')
            self._view('before')
            staging=path.with_name(name+'.pending');pending['staging']=staging
            paths.regular_path(path,missing=True);paths.regular_path(staging,missing=True)
            v.require(not path.exists() and not staging.exists(),'control no overwrite or staging reuse')
            pending['file_factory']=proof.tree.file_io.FileIO
            stream=pending['stream']=pending['file_factory'](staging,'xb')
            fd=pending['fd']=stream.fileno()
            info=os.fstat(fd);pending['initial_file_identity']=(info.st_dev,info.st_ino)
            v.require(info.st_ino>0 and info.st_size==0 and
                pending['initial_file_identity']==(staging.stat().st_dev,staging.stat().st_ino),
                'control original exclusive empty fd/path')
            pending['write_attempted']=True
            pending['write_return']=stream.write(raw)
            v.require(type(pending['write_return']) is int and pending['write_return']==len(raw),
                      'control exact original write return')
            stream.flush();os.fsync(fd)
            info=os.fstat(fd);pending['written_file_identity']=(info.st_dev,info.st_ino)
            v.require(pending['written_file_identity']==pending['initial_file_identity'] and info.st_size==len(raw),
                      'control original fd/count after sync')
            self._readback(staging,'staging_raw')
            self._view('written')
            pending['close_attempted']=True
            pending['close_return']=stream.close()
            pending['close_return_observed']=True
            v.require(pending['close_return'] is None and stream.closed is True and stream.closefd is True,
                      'control observed Python owned fd close return')
            self._readback(staging,'closed_raw')
            pending['rename_attempted']=True
            pending['rename_return']=io._rename_no_replace(staging,path)
            v.require(pending['rename_return'] is None,'control observed no-replace publication return')
            self._readback(path,'published_raw')
            info=path.lstat();pending['published_file_identity']=(info.st_dev,info.st_ino)
            v.require(pending['published_file_identity']==pending['initial_file_identity'],
                      'control original file identity after publication')
            self._view('after')
            row={'pin':copy.deepcopy(pending['pin']),'file_identity':pending['published_file_identity'],
                'python_close_return':pending['close_return'],'atomic_reservation':False,
                'native_owner_recovered':False,'parent_ack_authorized':False,'execution_authenticated':False}
            self.completed[name]={'observation':row,'original':pending}
            self.pending=None
            return copy.deepcopy(row['pin'])
        except BaseException as error:self._failed(error)

    def verify_publications(self, names, *, cached=False, extended=False):
        """One final original close/raw check; no stream/native close or retry."""
        if self.error is not None:raise self.error
        try:
            v.require(type(cached) is bool and type(extended) is bool and (not extended or cached) and self.pending is None and
                (hasattr(self,'verification') if cached else not hasattr(self,'verification')),
                'control original completed verification or explicit cached readback')
            self.pending={'verification_names':names,'original_completed':self.completed,'raw':{},
                          'original_verification':getattr(self,'verification',None)}
            if cached:
                initial=self.verification['verification_names']
                v.require(type(names) is tuple and (names[:len(initial)]==initial if extended else initial==names),
                          'control cached original completed names or explicit extension')
            v.require(type(names) is tuple and set(names)==set(self.completed) and len(names)==len(set(names)),
                      'control final exact completed names')
            self._view('verify_before')
            for name in names:
                row=self.completed[name];original=row['original'];observation=row['observation']
                v.require(original['owner'] is self.owner and original['close_return_observed'] is True and
                    original['close_return'] is None and original['stream'].closed is True and
                    original['stream'].closefd is True and original['rename_return'] is None and
                    original['published_file_identity']==original['initial_file_identity']==observation['file_identity'],
                    'control original owned fd close and publication returns')
                path=self.channel_root/name;raw=observed._file(path,proof.channel.MAX_CONTROL)
                self.pending['raw'][name]=raw
                evidence._raw(raw,observation['pin'],'control final original published raw')
                info=path.lstat()
                v.require(raw==original['raw']==original['published_raw'] and
                    (info.st_dev,info.st_ino)==original['published_file_identity'],
                    'control final raw or original file identity changed')
            self._view('verify_after')
            if cached:self.cached_verification=self.pending
            else:self.verification=self.pending
            self.pending=None
            return {name:copy.deepcopy(self.completed[name]['observation']['pin']) for name in names}
        except BaseException as error:self._failed(error)


def _path(path, endpoint):
    path = Path(path)
    root = Path(endpoint.request['budget_root'])
    v.require(proof.channel._inside(path, root) and path.name == 'worker-git.bin' and
        len(path.relative_to(root).parts) <= 2, 'worker archive fixed measured path/depth')
    paths.regular_path(path.parent, directory=True)
    paths.regular_path(path, missing=True)
    return path


def _inventory(verifier):
    raw = io.json_bytes(verifier.inventory)
    evidence._raw(raw, verifier.inventory_pin, 'worker archive held inventory')
    calls = verifier.inventory['calls']
    v.require(all(call['raw_inventory']['stdout.bin'] <= bounds.MAX_STDOUT for call in calls) and
        not any(a['phase'] == 'post' and b['phase'] == 'pre' for a,b in zip(calls,calls[1:])),
        'worker archive existing stdout bound and ordered phases')
    return raw


def _append_frame(path, frame):
    with path.open('ab') as stream:
        written = stream.write(frame)
        v.require(written == len(frame), 'worker archive full append')
        stream.flush()
        os.fsync(stream.fileno())


class SavedWorkerGitArchive:
    def __init__(self, *, endpoint, manifest_raw, manifest_pin, inventory_raw,
                 inventory_pin, checkpoint):
        v.require(callable(checkpoint) and type(manifest_raw) is bytes and
            len(manifest_raw) <= proof.channel.MAX_CONTROL, 'worker archive bounded held manifest')
        evidence._raw(manifest_raw, manifest_pin, 'worker archive external manifest pin')
        manifest = v.strict_json(manifest_raw)
        v.require(io.json_bytes(manifest) == manifest_raw and type(manifest) is dict and
            set(manifest) == {'format','path','archive_pin','inventory_pin','rows','formal_permission'} and
            manifest['format'] == FORMAT+'-manifest' and manifest['formal_permission'] is False and
            manifest['inventory_pin'] == inventory_pin, 'worker archive exact manifest/context')
        self.endpoint, self.checkpoint, self.manifest = endpoint, checkpoint, manifest
        self.path = _path(manifest['path'], endpoint)
        rows = manifest['rows']
        v.require(type(rows) is list and 0 < len(rows) <= proof.channel.MAX_JOBS,
                  'worker archive bounded nonempty rows')
        self._packets = []
        self.verifier = proof.ProofVerifier(endpoint=endpoint, inventory_raw=inventory_raw,
            inventory_pin=inventory_pin, read_evidence=lambda lease:copy.deepcopy(self._packets[lease]))
        _inventory(self.verifier)
        v.require(len(rows) <= len(self.verifier.inventory['calls']), 'worker archive planned call count')
        raw = self._current(); offset = 0
        for lease,row in enumerate(rows):
            v.require(type(row) is dict and set(row) == {'lease','offset','bytes','sha256','evidence_pin'} and
                type(row['lease']) is int and row['lease'] == lease and type(row['offset']) is int and
                row['offset'] == offset and type(row['bytes']) is int and 8 <= row['bytes'] <= MAX_RECORD+8
                and offset+row['bytes'] <= len(raw), 'worker archive exact ordered frame coverage')
            frame = raw[offset:offset+row['bytes']]
            evidence._raw(frame, {'bytes':row['bytes'],'sha256':row['sha256']}, 'worker archive frame pin')
            v.require(frame[:4] == MAGIC and int.from_bytes(frame[4:8],'big') == len(frame)-8,
                      'worker archive magic/length')
            decoded = bounds._gunzip(frame[8:], MAX_RAW)
            record = v.strict_json(decoded)
            v.require(io.json_bytes(record) == decoded and type(record) is dict and set(record) == {
                'format','lease','inventory_pin','kind','raw_b64','event'} and record['format'] == FORMAT and
                type(record['lease']) is int and record['lease'] == lease and
                record['inventory_pin'] == inventory_pin, 'worker archive canonical bound record')
            call = self.verifier.inventory['calls'][lease]
            encoded = record['raw_b64']
            v.require(type(encoded) is dict and set(encoded) == set(call['raw_inventory']),
                      'worker archive exact original raw names')
            packet_raw = {name:None if value is None else bounds._decode(value,call['raw_inventory'][name])
                          for name,value in encoded.items()}
            self._packets.append({'kind':record['kind'],'raw':packet_raw,'event':record['event']})
            offset += row['bytes']
        v.require(offset == len(raw), 'worker archive no trailing/partial frame')
        identities, statuses = set(), []
        for lease,row in enumerate(rows):
            checked, identity, status, _ = self.verifier.record(lease)
            v.require(checked['evidence_pin'] == row['evidence_pin'] and
                identity['start_token'] not in identities, 'worker archive raw/event pin and unique original identity')
            identities.add(identity['start_token']); statuses.append(status)
        v.require(all(status == 'verified' for status in statuses[:-1]),
                  'worker archive no call after failed recovery/receipt')
        self.statuses = statuses
        self._current()
        self.verifier.read_evidence = self.read

    def _current(self):
        self.checkpoint(); self.endpoint._live()
        raw = observed._file(self.path, MAX_BYTES)
        evidence._raw(raw, self.manifest['archive_pin'], 'worker archive caller-held complete raw pin')
        self.checkpoint()
        return raw

    def read(self, lease):
        v.require(type(lease) is int and 0 <= lease < len(self._packets), 'worker archive saved lease')
        self._current()
        return copy.deepcopy(self._packets[lease])


class WorkerGitArchive:
    def __init__(self, *, path, verifier, checkpoint, append_admission=None):
        self.original_append_admission = self.append_admission = append_admission
        v.require(callable(checkpoint), 'worker archive shared budget checkpoint required')
        self.verifier, self.checkpoint = verifier, checkpoint
        self.inventory_raw = _inventory(verifier)
        self.path = _path(path, verifier.endpoint)
        v.require(not self.path.exists(), 'worker archive exclusive unused file')
        self.rows, self.raw, self.statuses = [], b'', []
        self.pending, self.failed = None, False
        if append_admission is not None:
            v.require(type(append_admission) is ArchiveAppendAdmission, 'worker archive explicit append admission')
            append_admission.bind(self)
        checkpoint(); verifier._live()
        io._exclusive(self.path, b'')
        checkpoint()

    def _manifest(self, raw, rows):
        result = {'format':FORMAT+'-manifest','path':str(self.path),'archive_pin':observed._pin(raw),
            'inventory_pin':self.verifier.inventory_pin,'rows':rows,'formal_permission':False}
        encoded = io.json_bytes(result)
        v.require(len(encoded) <= proof.channel.MAX_CONTROL, 'worker archive compact manifest byte bound')
        return encoded

    def append(self, lease):
        try:
            v.require(not self.failed and type(lease) is int and lease == len(self.rows) and
                len(self.rows) < proof.channel.MAX_JOBS and
                (not self.statuses or self.statuses[-1] == 'verified'), 'worker archive active ordered append')
            self.pending = {'lease':lease}
            self.checkpoint(); self.verifier._live()
            v.require(observed._file(self.path,MAX_BYTES) == self.raw, 'worker archive previous bytes changed')
            checked, _, status, _ = self.verifier.record(lease)
            packet = copy.deepcopy(self.verifier.read_evidence(lease))
            self.pending.update(packet=packet, evidence_pin=copy.deepcopy(checked['evidence_pin']))
            snapshot = proof.ProofVerifier(endpoint=self.verifier.endpoint, inventory_raw=self.inventory_raw,
                inventory_pin=self.verifier.inventory_pin, read_evidence=lambda _:packet)
            v.require(snapshot.record(lease)[0] == checked, 'worker archive original raw changed before append')
            record = {'format':FORMAT,'lease':lease,'inventory_pin':self.verifier.inventory_pin,
                'kind':packet['kind'],'event':packet['event'],'raw_b64':{
                    name:None if value is None else base64.b64encode(value).decode('ascii')
                    for name,value in packet['raw'].items()}}
            encoded = io.json_bytes(record)
            self.pending['encoded'] = encoded
            v.require(len(encoded) <= MAX_RAW, 'worker archive decoded record byte bound')
            compressed = gzip.compress(encoded,mtime=0)
            self.pending['compressed'] = compressed
            v.require(len(compressed) <= MAX_RECORD, 'worker archive compressed record byte bound')
            frame = MAGIC+len(compressed).to_bytes(4,'big')+compressed
            self.pending['frame'] = frame
            candidate = self.raw+frame
            self.pending['candidate'] = candidate
            v.require(len(candidate) <= MAX_BYTES, 'worker archive existing total byte bound')
            row = {'lease':lease,'offset':len(self.raw),**observed._pin(frame),
                   'evidence_pin':copy.deepcopy(checked['evidence_pin'])}
            rows = self.rows+[row]
            manifest = self._manifest(candidate,rows)
            self.pending['manifest'] = manifest
            if self.append_admission is not None:
                self.append_admission.reserve(self,lease,frame)
            self.failed = True  # No append retry after any uncertain write/readback.
            self.checkpoint(); _append_frame(self.path,frame)
            saved = SavedWorkerGitArchive(endpoint=self.verifier.endpoint,
                manifest_raw=manifest,manifest_pin=observed._pin(manifest),
                inventory_raw=self.inventory_raw,inventory_pin=self.verifier.inventory_pin,
                checkpoint=self.checkpoint)
            v.require(saved.read(lease) == packet and self.verifier.record(lease)[0] == checked,
                      'worker archive saved/original raw readback')
            self.checkpoint()
            if self.append_admission is not None:
                self.append_admission.complete(self)
            self.raw, self.rows = candidate, rows
            self.statuses.append(status)
            self.failed, self.pending = False, None
            return copy.deepcopy(checked)
        except BaseException:
            self.failed = True
            raise

    def manifest(self):
        v.require(not self.failed and self.rows, 'worker archive verified nonempty manifest')
        self.checkpoint(); self.verifier._live()
        v.require(observed._file(self.path,MAX_BYTES) == self.raw, 'worker archive final raw changed')
        raw = self._manifest(self.raw,self.rows)
        self.checkpoint()
        return raw, observed._pin(raw)
