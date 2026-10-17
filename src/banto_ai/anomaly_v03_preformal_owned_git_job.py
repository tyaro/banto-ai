"""Opt-in Git containment; loaded code and individual descendant exits remain open."""
from __future__ import annotations

import os
import copy
import hashlib
import io as file_io
from pathlib import Path
from types import SimpleNamespace
import time

from . import anomaly_v03_preformal_owned_git as direct
from . import anomaly_v03_preformal_job_tree_owner as owner

v, observed, dependencies, paths, io = (
    direct.v, direct.observed, direct.dependencies, direct.paths, direct.io)
JOB = 'anomaly-v03-preformal-git-job-v1'
QUIESCENCE = 'anomaly-v03-preformal-owned-git-quiescence-v1'
PIPE_QUIESCENCE = 'anomaly-v03-preformal-owned-git-pipe-quiescence-v1'
PIPE_CLOSE_LINK = 'anomaly-v03-preformal-git-pipe-close-link-v1'
PIPE_RECOVERY = 'anomaly-v03-child-git-pipe-recovery-observation-v1'
_FIELDS = set('''format status reason prior_stop_reason operation source_path revision
    executable_path executable_expected_pin executable_links_expected executable_before
    executable_after argv cwd environment process_identity exit_code process_error_type
    direct_process_handle_exit_confirmed elapsed_seconds stdout_pin stdout_bytes
    stderr_pin stderr_bytes expected_output_pin integration_pending formal_permission
    source_closure_complete runtime_closure_complete execution_authenticated job'''.split())


class BoundedSpoolFailure(RuntimeError):
    """Keep the original stream/block/error after uncertain output IO."""
    def __init__(self, spool, original_error):
        self.spool, self.original_error = spool, original_error
        super().__init__('bounded Git output IO is unconfirmed')


class BoundedGitSpool:
    """A byte sink for a future owned pipe reader, not a native transport.

    The last stored byte is an overflow sentinel. A caller must read at most
    next_read_size(), stop the original Job on output_limit, and retain this
    object with that native owner. EOF/stream close does not prove Job closure.
    No existing file-directed executor uses this component yet.
    """
    READ_BLOCK = 4096

    def __init__(self, stream, *, operation, output, maximum_stored_bytes,
                 checkpoint, sync):
        # Retain the caller's stream before validation or any fallible IO.
        self.stream, self.checkpoint, self.sync = stream, checkpoint, sync
        self.pending_raw = self.failure = None
        self.committed_bytes, self.stopped, self.closed = 0, False, False
        self.maximum_stored_bytes = maximum_stored_bytes
        try:
            v.require(operation in direct.MAX_OUTPUT and output in ('stdout', 'stderr'),
                      'bounded Git output operation/name')
            maximum = direct.MAX_OUTPUT[operation] if output == 'stdout' else direct.MAX_STDERR
            v.require(type(maximum_stored_bytes) is int and 0 < maximum_stored_bytes <= maximum,
                      'bounded Git output stays within existing cap')
            v.require(callable(checkpoint) and callable(sync) and
                      callable(getattr(stream, 'write', None)) and
                      callable(getattr(stream, 'flush', None)) and
                      callable(getattr(stream, 'close', None)),
                      'bounded Git original stream and shared IO callbacks')
        except BaseException as error:
            self._failed(error)

    def _failed(self, error):
        if self.failure is None:
            self.failure = BoundedSpoolFailure(self, error)
        self.stopped = True
        raise self.failure from self.failure.original_error

    def next_read_size(self):
        if self.failure is not None:
            raise self.failure
        if self.stopped or self.closed:
            return 0
        return min(self.READ_BLOCK, self.maximum_stored_bytes - self.committed_bytes)

    def append(self, raw):
        if self.failure is not None:
            raise self.failure
        # Keep even an invalid/overlong original block before diagnostics.
        self.pending_raw = raw
        try:
            amount = self.next_read_size()
            v.require(type(raw) is bytes and 0 < len(raw) <= amount,
                      'bounded Git pipe read exceeded original allowance')
            self.checkpoint()
            written = self.stream.write(raw)
            v.require(type(written) is int and written == len(raw),
                      'bounded Git short/unknown output write')
            self.committed_bytes += written
            self.stream.flush()
            self.sync()
            self.checkpoint()
            self.pending_raw = None
            if self.committed_bytes == self.maximum_stored_bytes:
                self.stopped = True
                return 'output_limit'
            return None
        except BaseException as error:
            self._failed(error)

    def finish_eof(self):
        if self.failure is not None:
            raise self.failure
        if self.closed:
            return
        try:
            v.require(not self.stopped and self.pending_raw is None,
                      'bounded Git stopped/uncertain stream is retained')
            self.checkpoint()
            self.stream.flush()
            self.sync()
            self.stream.close()
            v.require(getattr(self.stream, 'closed', None) is True,
                      'bounded Git original output close unconfirmed')
            self.closed = True
            self.checkpoint()
        except BaseException as error:
            self._failed(error)


class GitSinkAdmission:
    """Exclusive empty sinks admitted against the original measured outer leaf.

    This conservatively reserves every planned raw maximum, including partial
    archive/receipt bytes, before opening files. It creates no Job or pipe and
    does not substitute for the caller's global/memory/clock supervision.
    """
    BYTE_LIMIT, ENTRY_LIMIT, RESERVE = 1024**2, 32, 128 * 1024

    def __init__(self, *, root, root_identity, revision, call, checkpoint, publication_storage=None):
        self.original_root, self.original_identity, self.original_call = root, root_identity, call
        self.original_publication_storage=self.publication_storage=publication_storage
        self.publication_storage_input=(publication_storage,root,root_identity,call,checkpoint)
        self.shared_checkpoint, self.revision = checkpoint, revision
        self.native = owner.UnreapedJob(None, None, None, {
            'status':'pending', 'phase':'git_sink_admission', 'formal_permission':False})
        self.native.git_sink_admission = self
        self.bootstrap = self.native
        self.creator = self.spawn_io = self.output_owner = self.rejected_creator = None
        self.previous_native_admission = None
        self.native_bindings = []
        self.error = self.pending = self.snapshot = None
        self.streams, self.spools, self.file_identities, self.file_descriptors = {}, {}, {}, {}
        self.close_adapter = self.rejected_close_adapter = self.close_pending = None
        self.closed_observations = {}
        self.started = self.ready = False
        try:
            self.call, self.identity = copy.deepcopy(call), copy.deepcopy(root_identity)
            self.root = Path(root)
            v.require(self.root.is_absolute() and self.root == self.root.resolve() and
                type(self.identity) is tuple and len(self.identity) == 2 and
                all(type(n) is int and n >= 0 for n in self.identity) and callable(checkpoint),
                'Git sink original canonical root/identity/checkpoint')
            direct.evidence._digest(revision, 40)
            v.require(type(self.call) is dict and set(self.call) == {
                'lease','phase','operation','source_path','expected_output_pin','raw_inventory'} and
                type(self.call['lease']) is int and 0 <= self.call['lease'] < 64 and
                self.call['phase'] in ('pre','post'), 'Git sink exact planned call')
            direct._command({'revision':revision}, self.call['operation'],
                            self.call['source_path'], self.call['expected_output_pin'])
            self.limits = self.call['raw_inventory']
            maximum = {'receipt.json':direct.MAX_RECEIPT,
                'stdout.bin':direct.MAX_OUTPUT[self.call['operation']],
                'stderr.bin':direct.MAX_STDERR, 'partial-archive.bin':512 * 1024}
            v.require(type(self.limits) is dict and {'receipt.json','stdout.bin','stderr.bin'}
                <= set(self.limits) <= set(maximum) and all(type(n) is int and
                0 < n <= maximum[name] for name,n in self.limits.items()),
                'Git sink exact original raw maximums')
            self.inflight = self.root/'worker-git-inflight'
            self.paths = {name:self.inflight/(name+'.bin') for name in ('stdout','stderr')}
            if publication_storage is not None:
                from .anomaly_v03_preformal_worker_git_archive import PublicationStorageAdmission
                v.require(type(publication_storage) is PublicationStorageAdmission,'Git sink original typed publication storage')
                publication_storage.previous_sink=publication_storage.sink
                publication_storage.rejected_sink=self
                publication_storage.sink=self  # Keep original bootstrap before root/clock IO.
                v.require(publication_storage.root==self.root and publication_storage.identity==self.identity and
                    publication_storage.checkpoint is checkpoint and self.call in publication_storage.inventory['calls'],
                    'Git sink original same publication storage call/root')
                self.native.publication_storage=publication_storage
            self.checkpoint()
            paths.regular_path(self.inflight, directory=True, missing=True)
            v.require(not self.inflight.exists(), 'Git sink exclusive unused inflight')
        except BaseException as failure:
            self._failed(failure)

    def _failed(self, failure):
        if self.error is None:
            self.error = failure
        self.native.sink_error = self.error
        if self.native.original_error is None:
            self.native.original_error = self.error
        raise self.native from self.error

    def _retain_native(self, native):
        # Keep both bootstrap chains and the actual spawn before checkpoint IO.
        self.native_bindings.append((native, getattr(native, 'git_sink_admission', None)))
        v.require(type(native) is owner.UnreapedJob, 'Git sink original UnreapedJob')
        if native is self.native and getattr(native, 'git_sink_admission', None) is self:
            return
        self.native = native
        if self.publication_storage_input[0] is not None:
            native.publication_storage=self.publication_storage_input[0]  # Before any post-spawn checkpoint IO.
        self.previous_native_admission = getattr(native, 'git_sink_admission', None)
        native.git_sink_admission = self
        self.bootstrap.sink_successor = native
        v.require(self.previous_native_admission in (None,self),
                  'Git sink original native cannot have another admission')

    def bind_spawn(self, creator):
        """Hold original pipes/sinks with one spawn descriptor, without spawning."""
        if self.error is not None:
            raise self.native
        try:
            if self.creator is not None:
                self.rejected_creator = creator
                v.require(False, 'Git sink pipe creator cannot be rebound')
            self.creator = creator  # Before validation or original root/clock IO.
            if type(creator) is owner.NativeGitPipes:
                self._retain_native(creator.native)
            v.require(type(creator) is owner.NativeGitPipes and creator.error is None and
                creator.result is True and self.ready and self.pending is None,
                'Git sink original ready pipe creator/admission')
            self.checkpoint()
            self.spawn_io = creator.bind_spawn(self.streams)
            self._retain_native(self.spawn_io.native)
            self.spawn_io.git_sink_admission = self
            self.checkpoint()
            return self.spawn_io
        except BaseException as failure:
            if type(self.creator) is owner.NativeGitPipes and self.creator.spawn_io is not None:
                self.spawn_io = self.creator.spawn_io
                self._retain_native(self.spawn_io.native)
            self._failed(failure)

    def bind_output(self):
        """After the caller's spawn, keep the same core/streams/spools for IO."""
        if self.error is not None:
            raise self.native
        try:
            v.require(self.output_owner is None and type(self.spawn_io) is owner.SpawnIOOwner
                and self.spawn_io.native is self.native,
                'Git sink same original spawn, no output rebind')
            self.output_owner = GitOutputOwner.from_spawn(self.spawn_io,
                spools=self.spools, checkpoint=self.checkpoint)
            self.checkpoint()
            return self.output_owner
        except BaseException as failure:
            self._failed(failure)

    def bind_io_close(self, adapter):
        """Keep the original close adapter/keeper before any reconciliation IO."""
        if self.error is not None:
            raise self.native
        try:
            if self.close_adapter is not None:
                self.rejected_close_adapter = adapter
                v.require(False, 'Git admission close adapter cannot be rebound')
            self.close_adapter = adapter
            v.require(type(adapter) is GitPipeClose and adapter.output_owner is self.output_owner
                and adapter.keeper.original is self.native and
                adapter.keeper.output_owner is self.output_owner and
                self.output_owner.native_owner is self.native and
                self.output_owner.pipe_close is adapter and not adapter.started
                and adapter.error is None and all(adapter.streams[n] is s and not s.closed
                    for n,s in self.streams.items()), 'Git admission original close adapter/streams')
            adapter.keeper.bind_io_close(adapter)
            self.checkpoint()
        except BaseException as failure:
            self._failed(failure)

    def _closed_sink_size(self, name, stream, current):
        adapter = self.close_adapter
        self.close_pending = {'output':name,'stream':stream,'event':None,'raw':None}
        completed = None if type(adapter) is not GitPipeClose else adapter.keeper.completion
        # Successful core close deliberately freezes the keeper against replay.
        # Reconcile that state through its original event/raw link, not a flag.
        if completed is not None:
            self.close_pending['completion'] = completed
            v.require(adapter.keeper.remaining == {} and
                adapter.keeper.closed == adapter.keeper.initial_handles and
                adapter.keeper.close_owner is None and adapter.keeper.first_error is None and
                completed.get('closed_handles') == adapter.keeper.closed and
                completed.get('io_closed') == adapter.keeper.io_closed and
                all(completed.get(k) == value for k,value in adapter.keeper.reaped.items()),
                'Git admission original completed keeper/core close')
            raw = self.close_pending['completed_raw'] = {n:observed._file(
                self.paths[n],self.limits[n+'.bin']) for n in ('stdout','stderr')}
            verify_pipe_recovery(completed,stdout_raw=raw['stdout'],stderr_raw=raw['stderr'])
        v.require(type(adapter) is GitPipeClose and adapter.output_owner is self.output_owner
            and adapter.keeper.original is self.native and adapter.keeper.io_close_adapter is adapter
            and adapter.keeper.output_owner is self.output_owner
            and adapter.keeper.native_kernel is adapter.reader.kernel is self.spawn_io.binding[0]
            and adapter.keeper.reaped is not None and (not adapter.keeper.blocked or completed is not None)
            and adapter.error is None and self.output_owner.error is None
            and adapter.reader.failure is None and self.output_owner.pending is None
            and adapter.streams[name] is stream and adapter.started,
            'Git admission closed sink requires original confirmed adapter/keeper')
        event = self.close_pending['event'] = adapter.sink_events.get(name)
        spool = self.spools[name]
        v.require(type(event) is dict and set(event) == {'api','fd','return','file_identity','raw_pin'}
            and event['api'] == 'FileIO.close' and event['return'] is None
            and type(event['fd']) is int and event['fd'] == self.file_descriptors[name]
            and event['file_identity'] == {'device':current.st_dev,'inode':current.st_ino}
            and spool.closed and spool.stream is stream and spool.failure is None
            and spool.pending_raw is None and not spool.stopped
            and set(adapter.read_events) == {'stdout','stderr'} and all(
                row == {'api':'CloseHandle','handle':adapter.read_handles[n],'return':row['return']}
                and type(row['return']) is int and row['return'] > 0
                for n,row in adapter.read_events.items()), 'Git admission exact original sink/read close')
        raw = self.close_pending['raw'] = observed._file(self.paths[name], self.limits[name+'.bin'])
        v.require(observed._pin(raw) == event['raw_pin'] and len(raw) == spool.committed_bytes
            == current.st_size and hashlib.sha256(raw).digest() == adapter.reader.hashes[name].digest(),
            'Git admission closed sink original full raw witness')
        self.closed_observations[name] = self.close_pending
        return current.st_size

    def checkpoint(self):
        if self.error is not None:
            raise self.native
        try:
            if self.close_adapter is not None:
                for failure in (self.close_adapter.error, self.output_owner.error,
                                self.close_adapter.reader.failure):
                    if failure is not None:
                        self._failed(failure)
            self.shared_checkpoint()
            storage=self.publication_storage_input[0]
            if storage is not None:
                v.require(self.original_publication_storage is self.publication_storage is storage and
                    self.native.publication_storage is storage,'Git sink original publication storage sidecar')
                storage.view('sink_checkpoint')
            from . import anomaly_v03_preformal_generated_chain_budget as monitor
            self.snapshot = monitor._directory_snapshot(self.root, 32, 2, self.identity)
            stored = 0
            for name, stream in self.streams.items():
                current = paths.regular_path(self.paths[name]).lstat()
                v.require(self.file_identities[name] == (current.st_dev,current.st_ino) and
                    0 <= current.st_size <= self.limits[name+'.bin'],
                    'Git sink original file identity/count')
                if stream.closed:
                    stored += self._closed_sink_size(name, stream, current)
                else:
                    info = os.fstat(stream.fileno())
                    v.require(stream.fileno() == self.file_descriptors[name] and
                        (info.st_dev,info.st_ino) == self.file_identities[name] and
                        info.st_size == current.st_size, 'Git admission original open fd/count')
                    stored += info.st_size
            remaining = sum(self.limits.values()) - stored
            # Keep future receipt/partial files plus the existing diagnostic reserve.
            future_entries = len(self.limits) - len(self.streams) + (0 if self.started else 1)
            v.require(self.snapshot['directory_bytes'] + remaining + self.RESERVE <= self.BYTE_LIMIT
                and self.snapshot['directory_entries'] + future_entries + 2 <= self.ENTRY_LIMIT,
                'Git sink raw maxima exceed original remaining outer budget')
        except BaseException as failure:
            self._failed(failure)

    def create(self):
        if self.error is not None:
            raise self.native
        if self.ready:
            self.checkpoint()
            return self
        try:
            v.require(not self.started, 'Git sink cannot rearm partial creation')
            self.checkpoint()
            self.pending = {'operation':'mkdir','path':self.inflight}
            self.inflight.mkdir(exist_ok=False)
            self.started = True
            self.checkpoint()
            for name in ('stdout','stderr'):
                self.pending = {'operation':'FileIO','path':self.paths[name], 'stream':None}
                self.streams[name] = self.pending['stream'] = file_io.FileIO(self.paths[name], 'xb')
                self.file_descriptors[name] = self.streams[name].fileno()
                info = os.fstat(self.file_descriptors[name])
                self.file_identities[name] = (info.st_dev,info.st_ino)
                v.require(info.st_size == 0 and self.streams[name].closefd is True,
                          'Git sink original exclusive empty FileIO')
                stream = self.streams[name]
                self.spools[name] = BoundedGitSpool(stream, operation=self.call['operation'],
                    output=name, maximum_stored_bytes=self.limits[name+'.bin'],
                    checkpoint=self.checkpoint, sync=lambda s=stream:os.fsync(s.fileno()))
                self.checkpoint()
            self.ready, self.pending = True, None
            return self
        except BaseException as failure:
            self._failed(failure)


class GitOutputOwnerFailure(RuntimeError):
    """Retain IO inputs even when the supplied native owner is invalid."""
    def __init__(self, output_owner, original_error):
        self.output_owner, self.original_error = output_owner, original_error
        super().__init__('Git output ownership is unconfirmed')


class GitOutputOwner:
    """Hold separate pipe readers/sinks with the original native exception.

    This boundary neither creates nor reads/closes a native pipe. A future
    adapter must retain each observed block here before fallible spool IO.
    ChildGitKeeper stops/reaps, but keeps core handles while this IO is held.
    No declaration on this object authorizes release, a lease or an ack.
    """
    def __init__(self, native_owner, *, read_handles, spools, checkpoint):
        self.native_owner = native_owner
        self.original_read_handles, self.original_spools = read_handles, spools
        self.read_handles, self.spools, self.checkpoint = read_handles, spools, checkpoint
        self.previous_owner = self.pending = self.rejected_raw = self.error = None
        try:
            valid_native = type(native_owner) in (owner.UnreapedJob, owner.UnclosedHandles)
            if valid_native:
                self.previous_owner = getattr(native_owner, 'git_output_owner', None)
                native_owner.git_output_owner = self  # Before validation/copy/clock/read/diagnostic IO.
            # Fix exact dict inputs even when a later validation rejects them.
            # Retain the original mappings too, before this potentially failing copy.
            if type(read_handles) is dict:
                self.read_handles = dict(read_handles)
            if type(spools) is dict:
                self.spools = dict(spools)
            v.require(valid_native, 'Git output original native owner')
            v.require(self.previous_owner is None, 'Git output owner cannot be rebound')
            v.require(type(read_handles) is dict and set(read_handles) == {'stdout', 'stderr'} and
                      all(type(n) is int and 0 < n < 2**64 for n in read_handles.values()) and
                      len(set(read_handles.values())) == 2, 'Git output separate original read handles')
            core = (dict(native_owner.handles) if type(native_owner) is owner.UnclosedHandles else
                    {'job':native_owner.job,'process':native_owner.process,'thread':native_owner.thread,
                     **native_owner.extra_handles})
            v.require(not set(read_handles.values()) & set(core.values()),
                      'Git output read handles must not alias core/inherited handles')
            v.require(type(spools) is dict and set(spools) == {'stdout', 'stderr'} and
                      all(type(s) is BoundedGitSpool for s in spools.values()) and
                      spools['stdout'] is not spools['stderr'] and
                      spools['stdout'].stream is not spools['stderr'].stream and callable(checkpoint),
                      'Git output original separate sinks and shared checkpoint')
        except BaseException as error:
            self._failed(error)

    def _failed(self, error):
        if self.error is None:
            self.error = error
        if type(self.native_owner) in (owner.UnreapedJob, owner.UnclosedHandles):
            self.native_owner.git_output_error = self.error
            raise self.native_owner from self.error
        raise GitOutputOwnerFailure(self, self.error) from self.error

    @classmethod
    def from_spawn(cls, spawn_io, *, spools, checkpoint):
        """Bind sinks/readers to the same original spawn core, without release."""
        if type(spawn_io) is not owner.SpawnIOOwner:
            # The normal constructor keeps rejected inputs before reporting.
            return cls(spawn_io, read_handles={}, spools=spools, checkpoint=checkpoint)
        held = cls(spawn_io.native, read_handles=spawn_io.read_handles,
                   spools=spools, checkpoint=checkpoint)
        held.spawn_io_owner = spawn_io
        try:
            v.require(spawn_io.entered and spawn_io.binding is not None and
                      getattr(spawn_io.native, 'spawn_io_owner', None) is spawn_io and
                      all(held.spools[name].stream is spawn_io.sinks[name]
                          for name in ('stdout','stderr')), 'Git output uses original spawn sinks/core')
            return held
        except BaseException as error:
            held._failed(error)

    def begin_read(self, output):
        if self.error is not None:
            self._failed(self.error)
        try:
            v.require(self.pending is None and output in ('stdout', 'stderr'),
                      'Git output no second read while original block is pending')
            self.pending = {'output':output,'handle':self.read_handles[output],
                            'spool':self.spools[output],'amount':None,'raw':None}
            self.pending['amount'] = self.spools[output].next_read_size()
            v.require(self.pending['amount'] > 0, 'Git output no read after limit/close')
            self.checkpoint()
            return self.pending['handle'], self.pending['amount']
        except BaseException as error:
            self._failed(error)

    def retain_read(self, raw):
        if self.error is not None:
            self._failed(self.error)
        try:
            if self.pending is None or self.pending['raw'] is not None:
                self.rejected_raw = raw  # Keep the new block without replacing an earlier one.
                v.require(False, 'Git output missing/duplicate original read observation')
            self.pending['raw'] = raw  # Before any validation or consumer IO.
            v.require(type(raw) is bytes and len(raw) <= self.pending['amount'],
                      'Git output observed read exceeded original allowance')
            return self.pending
        except BaseException as error:
            self._failed(error)


class GitPipeReader:
    """One serial anonymous-pipe observation, with no spawn/close/ack authority.

    The caller supplies the original kernel and bounded disk readers for fresh
    exclusive sinks. Empty availability/zero-byte success is not EOF; only an
    observed broken pipe records EOF. This opt-in adapter is not an executor.
    """
    def __init__(self, output_owner, *, kernel, readback):
        self.output_owner, self.kernel = output_owner, kernel
        self.original_readback, self.readback = readback, readback
        self.previous_reader = self.failure = None
        self.stopped = False
        self.eof = {}
        self.hashes = {}
        self.streams = {}
        try:
            v.require(type(output_owner) is GitOutputOwner, 'pipe original IO owner')
            self.previous_reader = getattr(output_owner, 'pipe_reader', None)
            output_owner.pipe_reader = self  # Before validation, readback or native IO.
            self.streams = {name:spool.stream for name,spool in output_owner.spools.items()}
            if type(readback) is dict:
                self.readback = dict(readback)
            v.require(self.previous_reader is None and output_owner.error is None and
                      output_owner.pending is None, 'pipe reader cannot rebind/rearm')
            v.require(type(readback) is dict and set(readback) == {'stdout','stderr'} and
                      all(callable(fn) for fn in self.readback.values()) and
                      callable(getattr(kernel, 'PeekNamedPipe', None)) and
                      callable(getattr(kernel, 'ReadFile', None)), 'pipe original IO callbacks')
            v.require(all(s.committed_bytes == 0 and s.pending_raw is None and
                      s.failure is None and not s.closed and not s.stopped
                      for s in output_owner.spools.values()), 'pipe sinks start with no writes')
            self.hashes = {name:hashlib.sha256() for name in ('stdout','stderr')}
        except BaseException as error:
            self._failed(error)

    def _failed(self, error):
        if self.failure is None:
            self.failure = error
        self.stopped = True
        if type(self.output_owner) is GitOutputOwner:
            self.output_owner._failed(self.failure)
        raise GitOutputOwnerFailure(self, self.failure) from self.failure

    def _disk(self, pending, expected):
        # The callback must bound its actual read to this size. Keep its exact
        # return before validation, including mismatched/overlong failure raw.
        pending['readback_limit'] = pending['spool'].committed_bytes + 1
        pending['readback_raw'] = self.readback[pending['output']](pending['readback_limit'])
        raw = pending['readback_raw']
        v.require(type(raw) is bytes and len(raw) == pending['spool'].committed_bytes and
                  hashlib.sha256(raw).digest() == expected.digest(),
                  'pipe original disk readback differs from consumed blocks')

    def read_once(self, output):
        if self.failure is not None:
            self._failed(self.failure)
        held = self.output_owner
        try:
            v.require(not self.stopped and output not in self.eof,
                      'pipe no read after limit/observed EOF')
            v.require(output in self.streams and
                      held.spools[output].stream is self.streams[output],
                      'pipe original sink cannot be replaced')
            handle, allowance = held.begin_read(output)
            pending = held.pending
            pending['kernel'] = self.kernel
            self._disk(pending, self.hashes[output])  # Reject preexisting/changed sink before pipe IO.
            available = owner.w.DWORD()
            pending['available'] = available
            pending['api'] = 'PeekNamedPipe'
            held.checkpoint()
            pending['peek_result'] = self.kernel.PeekNamedPipe(
                handle, None, 0, None, owner.ctypes.byref(available), None)
            pending['peek_error'] = (0 if pending['peek_result'] else owner.ctypes.get_last_error())
            if not pending['peek_result']:
                v.require(pending['peek_error'] == 109, 'pipe PeekNamedPipe failed')
                held.retain_read(b'')
                self._disk(pending, self.hashes[output])
                held.checkpoint()
                self.eof[output] = {'handle':handle,'api':'PeekNamedPipe','error':109}
                held.pending = None
                return 'eof'  # Sinks/read handles remain owned; no native close or lease.
            if available.value == 0:
                held.checkpoint()
                held.pending = None
                return 'pending'
            pending['amount'] = amount = min(allowance, int(available.value))
            pending['buffer'] = buffer = owner.ctypes.create_string_buffer(amount)
            pending['bytes_read'] = count = owner.w.DWORD()
            pending['api'] = 'ReadFile'
            held.checkpoint()
            pending['read_result'] = self.kernel.ReadFile(
                handle, buffer, amount, owner.ctypes.byref(count), None)
            pending['read_error'] = (0 if pending['read_result'] else owner.ctypes.get_last_error())
            held.retain_read(buffer.raw[:count.value])  # Buffer/count survive API or copy failures too.
            v.require(count.value <= amount and bool(pending['read_result']),
                      'pipe ReadFile failed/returned an invalid count')
            if count.value == 0:
                self._disk(pending, self.hashes[output])
                held.checkpoint()
                held.pending = None
                return 'pending'  # A successful zero-byte pipe read is not EOF.
            expected = self.hashes[output].copy()
            expected.update(pending['raw'])
            pending['expected_digest'] = expected.hexdigest()
            pending['spool_result'] = pending['spool'].append(pending['raw'])
            self._disk(pending, expected)
            held.checkpoint()
            self.hashes[output] = expected
            result = pending['spool_result']
            if result == 'output_limit':
                self.stopped = True  # Caller must stop the original Job; no second pipe read.
            held.pending = None
            return result or 'data'
        except BaseException as error:
            self._failed(error)


class GitPipeClose:
    """Observe named read/sink closes; core/receipt/lease release is separate.

    FileIO owns its file descriptor: close it through that original object,
    never through CloseHandle as well. These observations do not authenticate
    the Windows ABI or supply the missing receipt/IO-release link.
    """
    def __init__(self, reader, *, keeper):
        self.reader, self.keeper = reader, keeper
        self.output_owner = getattr(reader, 'output_owner', None)
        self.previous = self.pending = self.error = self.result = None
        self.read_handles, self.streams, self.read_events, self.sink_events = {}, {}, {}, {}
        self.reaped = None
        self.started = False
        try:
            held = self.output_owner
            v.require(type(held) is GitOutputOwner, 'pipe close original output owner')
            self.previous = getattr(held, 'pipe_close', None)
            held.pipe_close = self  # Retain both owners before validation or IO.
            self.read_handles = dict(held.read_handles)
            self.streams = {name:spool.stream for name,spool in held.spools.items()}
            from .anomaly_v03_preformal_child_git_keeper import ChildGitKeeper
            v.require(type(reader) is GitPipeReader and type(keeper) is ChildGitKeeper and
                      keeper.original is held.native_owner and self.previous is None and
                      keeper.output_owner is held and held.pipe_reader is reader,
                      'pipe close same original reader/native/keeper, no rebind')
            v.require(type(getattr(held, 'spawn_io_owner', None)) is owner.SpawnIOOwner and
                      held.spawn_io_owner.native is held.native_owner and
                      held.spawn_io_owner.binding[0] is reader.kernel and
                      all(type(stream) is file_io.FileIO and stream.closefd is True and
                          not stream.closed and stream.writable()
                          for stream in self.streams.values()),
                      'pipe close original raw FileIO sinks and spawn kernel')
        except BaseException as error:
            self._failed(error)

    def _failed(self, error):
        if self.error is None:
            self.error = error
        if type(self.reader) is GitPipeReader:
            self.reader.stopped = True
        if type(self.output_owner) is GitOutputOwner:
            self.output_owner._failed(self.error)
        raise GitOutputOwnerFailure(self, self.error) from self.error

    def _readback(self):
        for name, stream in self.streams.items():
            spool = self.output_owner.spools[name]
            v.require(spool.stream is stream and self.reader.streams[name] is stream,
                      'pipe close original sink identity')
            self.pending = {'output':name, 'stream':stream, 'spool':spool, 'stage':'readback'}
            self.reader._disk(self.pending, self.reader.hashes[name])
            self.output_owner.checkpoint()

    def close_once(self):
        if self.error is not None:
            self._failed(self.error)
        try:
            held, reader, keeper = self.output_owner, self.reader, self.keeper
            if self.result is not None:
                self._readback()  # Raw may change; cached events never replay native close.
                return copy.deepcopy(self.result)
            v.require(not self.started and held.error is None and reader.failure is None and
                      not reader.stopped and held.pending is None and
                      held.read_handles == self.read_handles and
                      set(reader.eof) == {'stdout','stderr'} and all(
                          reader.eof[name] == {'handle':handle,'api':'PeekNamedPipe','error':109}
                          for name,handle in self.read_handles.items()) and all(
                          spool.failure is None and spool.pending_raw is None and
                          not spool.stopped and not spool.closed for spool in held.spools.values()),
                      'pipe close confirmed EOF, no pending/failed/limited output')
            spawn = held.spawn_io_owner
            v.require(spawn.writer_close_error is None and spawn.writer_close_result is not None and
                      set(spawn.writer_close_events) == {'stdout','stderr'} and all(
                          event['handle'] == spawn.native_write_handles[name] and
                          event['api'] == 'CloseHandle' and event['return'] > 0
                          for name,event in spawn.writer_close_events.items()),
                      'pipe close original parent writer close events')
            v.require(keeper.reaped is not None and keeper.native_kernel is reader.kernel and
                      not keeper.blocked and keeper.completion is None and
                      keeper.initial_handles == keeper.remaining and
                      not getattr(held.native_owner, 'attribute_list_cleanup_pending', False) and
                      not getattr(held.native_owner, 'unknown_close_handles', ()),
                      'pipe close original cached Job/root/creation, no uncertain cleanup')
            self.reaped = copy.deepcopy(keeper.reaped)
            self.started = True
            reader.stopped = True  # Freeze reads before the first close/flush/checkpoint.
            self._readback()
            for name, handle in self.read_handles.items():
                self.pending = {'output':name,'handle':handle,'kernel':reader.kernel,
                                'stage':'read_close','return':None}
                held.checkpoint()
                self.pending['return'] = result = reader.kernel.CloseHandle(handle)
                v.require(type(result) in (int,bool), 'pipe read close native return')
                if not result:
                    self.pending['last_error'] = owner.ctypes.get_last_error()
                    raise OSError(self.pending['last_error'], 'pipe read CloseHandle')
                self.read_events[name] = {'api':'CloseHandle','handle':handle,'return':int(result)}
                held.checkpoint()
            for name, stream in self.streams.items():
                spool = held.spools[name]
                self.pending = {'output':name,'stream':stream,'spool':spool,
                                'stage':'sink_close','return':'unobserved','fd':stream.fileno()}
                held.checkpoint()
                stream.flush()
                spool.sync()
                self.pending['file_stat'] = stat = os.fstat(self.pending['fd'])
                v.require(stat.st_size == spool.committed_bytes, 'pipe sink fstat/readback count')
                self.pending['return'] = result = stream.close()
                v.require(result is None and stream.closed, 'pipe original FileIO close return')
                self.sink_events[name] = {'api':'FileIO.close','fd':self.pending['fd'],
                    'return':None,'file_identity':{'device':stat.st_dev,'inode':stat.st_ino},
                    'raw_pin':{'bytes':spool.committed_bytes,'sha256':reader.hashes[name].hexdigest()}}
                spool.closed = True  # Only after the original close call returned successfully.
                held.checkpoint()
            self._readback()
            self.result = {'format':'anomaly-v03-git-pipe-io-close-observation-v1',
                'reaped':copy.deepcopy(self.reaped),'read_closed':copy.deepcopy(self.read_events),
                'sink_closed':copy.deepcopy(self.sink_events),'formal_permission':False,
                'execution_authenticated':False,'io_released':False,'parent_ack_authorized':False}
            return copy.deepcopy(self.result)
        except BaseException as error:
            self._failed(error)

    def for_keeper(self, keeper):
        """Fresh raw/event consistency for this exact retained opt-in owner."""
        try:
            v.require(keeper is self.keeper and keeper.original is self.output_owner.native_owner,
                      'pipe close exact original keeper')
            self.close_once()  # Original close returns, then raw reread; cached native IO is not replayed.
            v.require(self.result is not None and not self.error and
                      self.output_owner.error is None and self.output_owner.pending is None and
                      self.reader.failure is None and
                      set(self.read_events) == set(self.sink_events) == {'stdout','stderr'} and
                      all(spool.closed and spool.stream.closed
                          for spool in self.output_owner.spools.values()),
                      'pipe close original completed events, not release flags')
            link = {'format':PIPE_CLOSE_LINK, **copy.deepcopy(self.reaped),
                'core_handles':dict(keeper.initial_handles),
                'parent_write_closed':copy.deepcopy(self.output_owner.spawn_io_owner.writer_close_events),
                'eof':copy.deepcopy(self.reader.eof), 'read_closed':copy.deepcopy(self.read_events),
                'sink_closed':copy.deepcopy(self.sink_events),
                'formal_permission':False,'execution_authenticated':False}
            raw = {}
            self.pending = {'stage':'keeper_link','raw':raw,'link':link}
            for name in ('stdout','stderr'):
                raw[name]=self.reader.readback[name](self.output_owner.spools[name].committed_bytes+1)
            _verify_pipe_close_link(link, identity=keeper.reaped['process_identity'],
                exit_code=keeper.reaped['exit_code'], accounting=keeper.reaped['accounting'],
                core_handles=keeper.initial_handles, stdout_raw=raw['stdout'],stderr_raw=raw['stderr'])
            self.output_owner.checkpoint()
            return link
        except BaseException as error:
            self._failed(error)


class GitPipeTransport:
    """Opt-in single-call transport; receipt publication and entry admission stay separate.

    The caller keeps the original clock, child lease and stdin. A captured
    transport observation does not finish that lease or authorize a parent ack.
    Synchronous Peek/Read still requires a separately measured native wall gate.
    """
    def __init__(self, admission, *, kernel, repository, policy, stdin, child,
                 stop_probe, clock, started_at, normal_completion=False):
        self.admission, self.kernel, self.stdin, self.child = admission, kernel, stdin, child
        self.original_inputs = (repository, policy, stop_probe, clock, started_at)
        self.stop_probe, self.clock, self.started_at = stop_probe, clock, started_at
        self.normal_completion = normal_completion
        self.native = admission.native if type(admission) is GitSinkAdmission else owner.UnreapedJob(
            None, None, None, {'phase':'git_pipe_transport','formal_permission':False})
        self.owners = [self.native]
        self.native.pipe_transport = self  # Before validation, copying, policy or clock IO.
        self.previous_transport = getattr(admission, 'pipe_transport', None)
        self.creator = self.spawn_io = self.output = self.reader = self.keeper = self.closer = None
        self.pending = self.error = self.reason = self.result = self.stop_error = None
        self.spawn_return = self.resume_return = None
        self.receipt_capture_started = self.publication_started = False
        self.receipt_inputs = self.receipt_pending = self.published = None
        self.publication_stream = self.publication_pending = None
        self.started = self.stop_started = False
        try:
            v.require(type(admission) is GitSinkAdmission and self.previous_transport is None,
                      'transport original exclusive admission, no rebind')
            admission.pipe_transport = self
            v.require(type(normal_completion) is bool, 'transport explicit normal completion option')
            self.policy = copy.deepcopy(policy)
            v.require(callable(stop_probe) and callable(clock) and
                type(started_at) in (int,float) and 0 <= started_at < float('inf') and
                callable(getattr(child,'hold_owner',None)), 'transport original clock/stop/lease owner')
            self.repository, self.executable, self.environment, self.executable_before = direct._policy(
                repository, self.policy)
            self.executable_before = copy.deepcopy(self.executable_before)
            v.require(self.policy.get('process_ownership') == direct.JOB_OWNERSHIP and
                self.policy['revision'] == admission.revision, 'transport same private Job/revision')
            command = direct._command(self.policy, admission.call['operation'],
                admission.call['source_path'], admission.call['expected_output_pin'])
            self.argv = [str(self.executable), '-c','core.fsmonitor=false','-c','core.pager=cat',
                '-c','safe.directory='+str(self.repository),'-C',str(self.repository),*command]
        except BaseException as failure:
            self._failed(failure)

    def _retain(self, native):
        if native not in self.owners:
            self.owners.append(native)
        self.native = native
        native.pipe_transport = self

    def _failed(self, failure):
        if self.error is None:
            self.error = failure
        if isinstance(failure, (owner.UnreapedJob,owner.UnclosedHandles)):
            self._retain(failure)
        self.native.transport_error = self.error
        if getattr(self.native,'original_error',None) is None and self.error is not self.native:
            self.native.original_error = self.error
        if self.keeper is not None and self.keeper.normal_completion:
            try:
                self.keeper.promote()
            except BaseException as ledger_error:
                self.stop_error = ledger_error
        if self.error is self.native:
            raise self.native
        raise self.native from self.error

    def _abort(self, failure):
        # Retain the original failure and any secondary owner before stopping.
        if self.error is None:
            self.error = failure
        if isinstance(failure, (owner.UnreapedJob,owner.UnclosedHandles)):
            self._retain(failure)
        if not self.stop_started and type(self.native) is owner.UnreapedJob and all(
                type(h) is int and h > 0 for h in (self.native.job,self.native.process,self.native.thread)):
            try:
                self.stop_once()
            except BaseException as stop_error:
                self.stop_error = stop_error
        self._failed(failure)

    def _probe(self):
        self.admission.checkpoint()
        now = self.clock()
        v.require(type(now) in (int,float) and self.started_at <= now < float('inf'),
                  'transport original monotonic clock')
        self.pending = {'clock':now,'stop':None}
        self.pending['stop'] = stop = _shared_stop(self.stop_probe)
        return 'shared_budget_stop' if stop is not None else (
            'time_limit' if now-self.started_at >= 10 else None)

    def start(self):
        if self.error is not None:
            raise self.native
        try:
            v.require(not self.started, 'transport cannot restart original call')
            self.started = True
            reason = self._probe()
            if reason is not None:
                self.reason = reason
                raise owner.resources.ResourceStop(reason)  # Before pipe/Job creation.
            self.admission.create()
            self.creator = owner.NativeGitPipes(self.kernel, checkpoint=self.admission.checkpoint)
            self._retain(self.creator.native)
            self.creator.create()
            self.spawn_io = self.admission.bind_spawn(self.creator)
            self._retain(self.spawn_io.native)
            self.pending = {'stage':'spawn','return':None}
            self.pending['return'] = returned = owner._spawn_cli(self.kernel,self.argv,
                self.repository,self.stdin,self.creator.writers['stdout'],
                self.creator.writers['stderr'],environment=self.environment,spawn_io=self.spawn_io)
            self.spawn_return = returned  # Original API return before post-spawn IO.
            v.require(returned == (self.native.job,self.native.process,self.native.thread,returned[3]),
                      'transport original spawn return/core')
            self.spawn_io.close_parent_writers(checkpoint=self.admission.checkpoint)
            self.output = self.admission.bind_output()
            readers = {n:lambda limit,n=n:observed._file(self.admission.paths[n],limit)
                       for n in ('stdout','stderr')}
            self.reader = GitPipeReader(self.output,kernel=self.kernel,readback=readers)
            reason = self._probe()
            if reason is not None:
                self.reason = reason
                self.stop_once()
                raise owner.resources.ResourceStop(reason)
            self.pending = {'stage':'resume','return':None}
            self.pending['return'] = resumed = self.kernel.ResumeThread(self.native.thread)
            self.resume_return = resumed
            owner._need(resumed == 1, 'transport ResumeThread original Git root')
            self.pending = None
            return self
        except BaseException as failure:
            self._abort(failure)

    def stop_once(self):
        """Retain original keeper before its ledger/Terminate/wait; no IO release."""
        if self.stop_started:
            return None if self.keeper is None else copy.deepcopy(self.keeper.reaped)
        self.stop_started = True
        try:
            from .anomaly_v03_preformal_child_git_keeper import ChildGitKeeper
            self.keeper = ChildGitKeeper(self.native,child=self.child,lease=self.admission.call['lease'])
            self.native.child_keeper = self.keeper
            self.keeper.reconcile_once()
            return copy.deepcopy(self.keeper.reaped)
        except BaseException as failure:
            self.keeper = self.keeper or getattr(self.native,'child_keeper',None)
            self._failed(failure)

    def _normal_completion_once(self):
        """Capture actual empty/exit0/creation without stopping the child channel."""
        self.stop_started = True
        try:
            from .anomaly_v03_preformal_child_git_keeper import ChildGitKeeper
            self.keeper = ChildGitKeeper(self.native,child=self.child,
                lease=self.admission.call['lease'],normal_completion=True)
            self.keeper.reconcile_once()
            if self.keeper.first_error is not None:
                raise self.keeper.first_error
            v.require(self.keeper.reaped is not None and not self.keeper.normal_promoted,
                      'transport normal native completion unconfirmed')
            return copy.deepcopy(self.keeper.reaped)
        except BaseException as failure:
            self.keeper = self.keeper or getattr(self.native,'child_keeper',None)
            self._failed(failure)

    def step(self):
        if self.error is not None:
            raise self.native
        try:
            v.require(self.reader is not None and self.result is None and not self.stop_started,
                      'transport original running reader')
            reason = self._probe()
            if reason is None:
                for name in ('stdout','stderr'):
                    if name not in self.reader.eof:
                        self.pending = {'stage':'read','output':name,'return':None}
                        self.pending['return'] = value = self.reader.read_once(name)
                        if value == 'output_limit':
                            reason = 'output_limit'
                            break
                self.pending = {'stage':'native_observation','accounting':None,'exit_code':None}
                self.pending['accounting'] = accounting = owner._accounting(self.kernel,self.native.job)
                self.pending['exit_code'] = code = owner._root_exit(self.kernel,self.native.process)
                if code is not None and code != 0:
                    reason = reason or 'exit_nonzero'
                if reason is None and code is not None and accounting['active_processes'] == 0 and \
                        set(self.reader.eof) == {'stdout','stderr'}:
                    captured = (self._normal_completion_once() if self.normal_completion else self.stop_once())
                    v.require(captured is not None, 'transport original reap unconfirmed')
                    return 'close_ready'  # Root exit and EOF still do not release anything.
            if reason is not None:
                self.reason = reason
                self.stop_once()
                raise owner.resources.ResourceStop(reason)
            self.pending = None
            return 'pending'
        except BaseException as failure:
            self._abort(failure)

    def close_once(self):
        if self.error is not None:
            raise self.native
        try:
            v.require(self.stop_started and self.keeper is not None and self.keeper.reaped is not None
                and self.reader is not None, 'transport confirmed original stop/reap')
            if self.result is not None:
                self.closer.close_once()
                self.admission.checkpoint()
                return copy.deepcopy(self.result)
            self.closer = GitPipeClose(self.reader,keeper=self.keeper)
            self.admission.bind_io_close(self.closer)
            self.closer.close_once()
            recovery = self.keeper.reconcile_once()
            v.require(recovery is not None, 'transport every original IO/core close confirmed')
            raw = {n:observed._file(self.admission.paths[n],self.admission.limits[n+'.bin'])
                   for n in ('stdout','stderr')}
            self.pending = {'recovery':recovery,'raw':raw}
            verify_pipe_recovery(recovery,stdout_raw=raw['stdout'],stderr_raw=raw['stderr'])
            self.admission.checkpoint()
            self.result = {'recovery':recovery,'raw_pins':{n:observed._pin(b) for n,b in raw.items()},
                'formal_permission':False,'execution_authenticated':False,
                'lease_completed':False,'parent_ack_authorized':False}
            self.pending = None
            return copy.deepcopy(self.result)
        except BaseException as failure:
            self._failed(failure)

    def capture_receipt_inputs(self):
        """Observe memory/executable while the original Job handles are still open."""
        if self.error is not None:
            raise self.native
        try:
            v.require(not self.receipt_capture_started and self.normal_completion and
                self.keeper is not None and self.keeper.normal_completion and
                not self.keeper.normal_promoted and self.keeper.reaped is not None and
                self.keeper.completion is None and self.keeper.remaining == self.keeper.initial_handles and
                not self.keeper.blocked and self.closer is None and self.result is None and
                type(self.spawn_return) is tuple and self.spawn_return == (
                    self.native.job,self.native.process,self.native.thread,
                    self.keeper.reaped['process_identity']['pid']) and
                type(self.resume_return) is int and self.resume_return == 1 and
                self.native.report.get('assignment_confirmed') is True,
                'pipe receipt original normal return/identity before core close')
            self.receipt_capture_started = True
            self.receipt_pending = {'memory':None,'after':None,'raw':{},'reaped':None}
            reason = self._probe()
            if reason is not None:
                raise owner.resources.ResourceStop(reason)
            self.receipt_pending['memory'] = memory = owner._job_memory(self.kernel,self.native.job)
            v.require(owner.valid_job_memory(memory), 'pipe receipt original Job memory')
            self.receipt_pending['after'] = after = dependencies.file_observation(
                self.executable,native=True,maximum=direct.MAX_EXE)
            for name in ('stdout','stderr'):
                self.receipt_pending['raw'][name] = raw = observed._file(
                    self.admission.paths[name],self.admission.limits[name+'.bin'])
                v.require(len(raw) == self.output.spools[name].committed_bytes and
                    hashlib.sha256(raw).digest() == self.reader.hashes[name].digest(),
                    'pipe receipt original full output before close')
            self.receipt_pending['reaped'] = copy.deepcopy(self.keeper.reaped)
            self.admission.checkpoint()
            self.receipt_inputs = copy.deepcopy(self.receipt_pending)
            return copy.deepcopy(self.receipt_inputs)
        except BaseException as failure:
            self._abort(failure)

    def publish_receipt(self):
        """Publish one strict receipt from original observations; never finish a lease."""
        if self.error is not None:
            raise self.native
        prior_owner = getattr(self.native,'pending_pipe_receipt_owner',None)
        self.previous_publication_owner = prior_owner
        self.native.pending_pipe_receipt_owner = self  # Retain before validation/new file IO.
        try:
            v.require(prior_owner is None or prior_owner is self, 'pipe receipt same original publisher owner')
            v.require(self.receipt_inputs is not None and self.result is not None and
                self.keeper.completion is not None and not self.keeper.normal_promoted,
                'pipe receipt requires original pre-close inputs and complete close')
            self.admission.checkpoint()
            raw = {}
            self.publication_pending = {'raw_outputs':raw,'receipt_raw':None,'stream':self.publication_stream}
            for name in ('stdout','stderr'):
                raw[name] = observed._file(self.admission.paths[name],self.admission.limits[name+'.bin'])
                v.require(raw[name] == self.receipt_inputs['raw'][name],
                          'pipe receipt original output changed after close')
            if self.published is not None:
                self.publication_pending['receipt_raw'] = receipt_raw = observed._file(
                    self.admission.inflight/'receipt.json',direct.MAX_RECEIPT)
                v.require(receipt_raw == io.json_bytes(self.published['receipt']),
                          'pipe receipt cached original file changed')
                verify_quiescence(receipt_raw,self.published['receipt_pin'],self.published['quiescence'],
                    root=self.repository,policy=self.policy,stdout_raw=raw['stdout'],stderr_raw=raw['stderr'])
                self.native.pending_pipe_receipt_owner = None  # Only after original raw/witness verification.
                return copy.deepcopy(self.published)
            v.require(not self.publication_started, 'pipe receipt cannot retry partial publication')
            self.publication_started = True
            reaped = self.receipt_inputs['reaped']
            v.require(reaped == self.keeper.reaped and self.keeper.closed == self.keeper.initial_handles,
                      'pipe receipt original creation/exit/accounting/core close')
            identity = {**reaped['process_identity'],'native_start_identity_authenticated':True}
            reason = ('executable_changed' if self.receipt_inputs['after'] != self.executable_before else
                'job_limit_termination' if reaped['accounting']['limit_terminated_processes'] else
                'stderr_nonempty' if raw['stderr'] else None)
            call = self.admission.call
            output_pin = observed._pin(raw['stdout'])
            if reason is None:
                if call['operation'] == 'head' and raw['stdout'].strip() != self.policy['revision'].encode():
                    reason = 'revision_mismatch'
                elif call['operation'] == 'status' and raw['stdout']:
                    reason = 'dirty_checkout'
                elif call['operation'] == 'source_blob' and output_pin != call['expected_output_pin']:
                    reason = 'blob_pin_mismatch'
            if reason is not None:
                self.child.stopped = True  # A semantic failed receipt cannot rearm subsequent calls.
            self.publication_pending['clock'] = now = self.clock()
            v.require(type(now) in (int,float) and self.started_at <= now < self.started_at+10,
                      'pipe receipt original elapsed clock')
            fact = {'format':JOB,'assignment_confirmed':True,'root_resumed':True,
                'accounting':copy.deepcopy(reaped['accounting']),
                'memory':copy.deepcopy(self.receipt_inputs['memory']),
                'all_assigned_processes_exit_confirmed':True,
                'individual_descendant_exit_codes_authenticated':False,'loaded_code_authenticated':False,
                'whole_tree_resource_budget_measured':False,'observation_errors':[]}
            receipt = {'format':direct.JOB_FORMAT,'status':'verified' if reason is None else 'failed',
                'reason':reason,'prior_stop_reason':None,'operation':call['operation'],
                'source_path':call['source_path'],'revision':self.policy['revision'],
                'executable_path':str(self.executable),'executable_expected_pin':self.policy['executable_pin'],
                'executable_links_expected':self.policy['executable_links'],
                'executable_before':self.executable_before,'executable_after':self.receipt_inputs['after'],
                'argv':self.argv,'cwd':str(self.repository),'environment':self.environment,
                'process_identity':identity,'exit_code':reaped['exit_code'],'process_error_type':None,
                'direct_process_handle_exit_confirmed':True,'elapsed_seconds':now-self.started_at,
                'stdout_pin':output_pin,'stdout_bytes':len(raw['stdout']),
                'stderr_pin':observed._pin(raw['stderr']),'stderr_bytes':len(raw['stderr']),
                'expected_output_pin':call['expected_output_pin'],'job':fact,'integration_pending':True,
                'formal_permission':False,'source_closure_complete':False,'runtime_closure_complete':False,
                'execution_authenticated':False}
            receipt_raw = self.publication_pending['receipt_raw'] = io.json_bytes(receipt)
            v.require(len(receipt_raw) <= self.admission.limits['receipt.json'], 'pipe receipt admitted bytes')
            receipt_pin = observed._pin(receipt_raw)
            witness = {'format':PIPE_QUIESCENCE,'receipt_pin':receipt_pin,
                'closed':{'format':'anomaly-v03-owned-handles-closed-v1','closed_handles':dict(self.keeper.closed)},
                'process_identity':identity,'exit_code':reaped['exit_code'],
                'accounting':copy.deepcopy(reaped['accounting']),'formal_permission':False,
                'io_closed':copy.deepcopy(self.keeper.io_closed)}
            self.publication_pending['witness'] = witness
            verify_quiescence(receipt_raw,receipt_pin,witness,root=self.repository,policy=self.policy,
                              stdout_raw=raw['stdout'],stderr_raw=raw['stderr'])
            target = self.admission.inflight/'receipt.json'
            self.publication_stream = self.publication_pending['stream'] = file_io.FileIO(target,'xb')
            self.publication_pending['fd'] = fd = self.publication_stream.fileno()
            self.publication_pending['file_stat'] = info = os.fstat(fd)
            v.require(info.st_size == 0 and self.publication_stream.closefd is True,
                      'pipe receipt original exclusive empty file')
            self.publication_pending['write_return'] = written = self.publication_stream.write(receipt_raw)
            v.require(type(written) is int and written == len(receipt_raw), 'pipe receipt exact write')
            self.publication_stream.flush()
            os.fsync(fd)
            self.admission.checkpoint()
            current = paths.regular_path(target).lstat()
            v.require((info.st_dev,info.st_ino) == (current.st_dev,current.st_ino) and
                current.st_size == len(receipt_raw), 'pipe receipt original fd/path/count')
            self.publication_pending['close_return'] = closed = self.publication_stream.close()
            v.require(closed is None and self.publication_stream.closed, 'pipe receipt original FileIO close')
            self.publication_pending['readback'] = readback = observed._file(target,direct.MAX_RECEIPT)
            v.require(readback == receipt_raw, 'pipe receipt original disk readback')
            verify_quiescence(readback,receipt_pin,witness,root=self.repository,policy=self.policy,
                              stdout_raw=raw['stdout'],stderr_raw=raw['stderr'])
            self.admission.checkpoint()
            self.published = {'receipt':receipt,'receipt_pin':receipt_pin,'receipt_root':str(self.admission.inflight),
                              'stdout':raw['stdout'],'quiescence':witness}
            self.native.pending_pipe_receipt_owner = None
            return copy.deepcopy(self.published)
        except BaseException as failure:
            self._abort(failure)


def _verify_pipe_close_link(link, *, identity, exit_code, accounting, core_handles,
                            stdout_raw, stderr_raw):
    """Strict saved consistency; no native API, marker or release flag authority."""
    v.require(type(link) is dict and set(link) == {'format','process_identity','exit_code',
        'accounting','core_handles','parent_write_closed','eof','read_closed','sink_closed',
        'formal_permission','execution_authenticated'} and link['format'] == PIPE_CLOSE_LINK and
        link['formal_permission'] is False and link['execution_authenticated'] is False,
        'pipe close exact saved link')
    v.require(io.json_bytes(link['process_identity']) == io.json_bytes(identity) and
        link['exit_code'] == exit_code and type(link['exit_code']) is int and
        0 <= exit_code < 2**32 and type(identity) is dict and set(identity) == {
            'pid','creation_time_100ns','start_token'} and type(identity['pid']) is int and
        identity['pid'] > 0 and type(identity['creation_time_100ns']) is int and
        identity['creation_time_100ns'] > 0 and identity['start_token'] == v.canonical_sha256({
            key:identity[key] for key in ('pid','creation_time_100ns')}) and
        io.json_bytes(link['accounting']) == io.json_bytes(accounting) and
        type(accounting) is dict and set(accounting) == {'total_processes','active_processes',
            'limit_terminated_processes'} and all(type(n) is int and n >= 0 for n in accounting.values()) and
        accounting['active_processes'] == 0 and
        accounting['limit_terminated_processes'] <= accounting['total_processes'] and
        type(link['core_handles']) is dict and link['core_handles'] == core_handles and
        type(core_handles) is dict and
        {'thread','process','job'} <= set(core_handles) <= {
            'thread','process','job','inherited_0','inherited_1','inherited_2'} and
        all(type(n) is int and 0 < n < 2**64 for n in core_handles.values()) and
        len(set(core_handles.values())) == len(core_handles), 'pipe close original native link')
    handles = list(core_handles.values())
    for field in ('parent_write_closed','read_closed'):
        events=link[field]
        v.require(type(events) is dict and set(events) == {'stdout','stderr'},
                  'pipe close exact named native events')
        for event in events.values():
            v.require(type(event) is dict and set(event) == {'api','handle','return'} and
                event['api'] == 'CloseHandle' and type(event['handle']) is int and
                0 < event['handle'] < 2**64 and type(event['return']) is int and event['return'] > 0,
                'pipe close native return position')
            handles.append(event['handle'])
    v.require(len(set(handles)) == len(handles) and type(link['eof']) is dict and
        set(link['eof']) == {'stdout','stderr'} and all(link['eof'][name] == {
            'api':'PeekNamedPipe','handle':link['read_closed'][name]['handle'],'error':109}
            for name in ('stdout','stderr')), 'pipe close distinct handles and observed EOF')
    sinks=link['sink_closed']
    v.require(type(sinks) is dict and set(sinks) == {'stdout','stderr'}, 'pipe close exact sinks')
    for name,raw in (('stdout',stdout_raw),('stderr',stderr_raw)):
        event=sinks[name]
        v.require(type(event) is dict and set(event) == {'api','fd','return','file_identity','raw_pin'} and
            event['api'] == 'FileIO.close' and type(event['fd']) is int and event['fd'] >= 0 and
            event['return'] is None and type(event['file_identity']) is dict and
            set(event['file_identity']) == {'device','inode'} and
            all(type(n) is int and n >= 0 for n in event['file_identity'].values()) and
            type(raw) is bytes, 'pipe close original FileIO close observation')
        direct.evidence._raw(raw,event['raw_pin'],'pipe close full retained '+name)
    v.require(sinks['stdout']['fd'] != sinks['stderr']['fd'], 'pipe close distinct sink descriptors')
    return True


def verify_pipe_recovery(event, *, stdout_raw, stderr_raw):
    v.require(type(event) is dict and set(event) == {'format','process_identity','exit_code',
        'accounting','closed_handles','io_closed','call_status','formal_permission',
        'execution_authenticated','lease_completed','failure_raw_verified','parent_ack_authorized'} and
        event['format'] == PIPE_RECOVERY and event['call_status'] == 'failed' and all(
            event[name] is False for name in ('formal_permission','execution_authenticated',
                'lease_completed','failure_raw_verified','parent_ack_authorized')),
        'pipe recovery exact failed observation')
    return _verify_pipe_close_link(event['io_closed'], identity=event['process_identity'],
        exit_code=event['exit_code'], accounting=event['accounting'],
        core_handles=event['closed_handles'],stdout_raw=stdout_raw,stderr_raw=stderr_raw)


def _shared_stop(probe):
    stop = probe() if probe is not None else None
    v.require(stop is None or (type(stop) is str and 0 < len(stop) <= 128),
              'owned Git shared stop probe result')
    return stop


def _execute(argv, root, environment, target, operation, timeout_seconds, *, stop_probe=None,
             capture_quiescence=False):
    """Retain native ownership until the root and its private Job are empty."""
    k = owner._kernel()
    job = process = thread = identity = exit_code = None
    accounting = memory = None
    assigned = resumed = False
    reason = error_type = critical = None
    errors = []
    started = time.monotonic()
    stdout_path, stderr_path = target/'stdout.bin', target/'stderr.bin'
    try:
        with open(os.devnull, 'rb') as stdin, stdout_path.open('xb') as stdout, \
                stderr_path.open('xb') as stderr:
            job, process, thread, pid = owner._spawn_cli(
                k, argv, root, stdin, stdout, stderr, environment=environment)
            assigned = True
            identity = direct._identity(SimpleNamespace(pid=pid, _handle=process))
            if _shared_stop(stop_probe) is not None:
                reason = 'shared_budget_stop'
            else:
                owner._need(k.ResumeThread(thread) == 1, 'ResumeThread Git')
                resumed = True
            while reason is None:
                if _shared_stop(stop_probe) is not None:
                    reason = 'shared_budget_stop'
                    break
                accounting = owner._accounting(k, job)
                exit_code = owner._root_exit(k, process)
                if exit_code is not None and exit_code != 0:
                    reason = 'exit_nonzero'
                    break
                if accounting['active_processes'] == 0 and exit_code is not None:
                    break
                if stdout_path.stat().st_size > direct.MAX_OUTPUT[operation] or \
                        stderr_path.stat().st_size > direct.MAX_STDERR:
                    reason = 'output_limit'
                    break
                if time.monotonic() - started >= timeout_seconds:
                    reason = 'time_limit'
                    break
                time.sleep(0.025)
    except (owner.UnreapedJob, owner.UnclosedHandles):
        raise  # A failed spawn owns its exact handles in the exception.
    except BaseException as error:
        reason = 'spawn_or_observation_error'
        error_type = type(error).__name__
        errors.append({'stage':'execution', 'error_type':error_type})
        if not isinstance(error, (OSError, ValueError, TypeError)):
            critical = error
    finally:
        if process is not None:
            try:
                # Any failed observation stops every member, including a root
                # that has not yet been resumed. Never close a live tree.
                if reason is not None:
                    owner._need(k.TerminateJobObject(job, 0xE007), 'TerminateJobObject Git')
                else:
                    accounting = owner._accounting(k, job)
                    exit_code = owner._root_exit(k, process)
                    if exit_code is None or accounting['active_processes'] != 0:
                        owner._need(k.TerminateJobObject(job, 0xE007), 'TerminateJobObject Git')
                accounting, exit_code = owner._wait_empty(
                    k, job, process, time.monotonic() + 5)
                owner._need(accounting['active_processes'] == 0 and exit_code is not None,
                            'owned Git Job empty')
            except BaseException as error:
                # A failed accounting query must still attempt to stop the
                # Job. Keep every handle when confirmation remains unavailable.
                retained = owner.UnreapedJob(job, process, thread, {
                    'status':'failed', 'phase':'git_reap',
                    'job_accounting':accounting, 'root_exit_code':exit_code,
                    'formal_permission':False})
                retained.original_error = error
                try:
                    owner._need(k.TerminateJobObject(job, 0xE008), 'TerminateJobObject Git cleanup')
                except BaseException as stop_error:
                    retained.stop_error = stop_error
                raise retained from error
            try:
                memory = owner._job_memory(k, job)
            except BaseException as error:
                reason = reason or 'spawn_or_observation_error'
                error_type = error_type or type(error).__name__
                errors.append({'stage':'job_memory', 'error_type':type(error).__name__})
    fact = None if not assigned else {
        'format':JOB, 'assignment_confirmed':True, 'root_resumed':resumed,
        'accounting':accounting, 'memory':memory,
        'all_assigned_processes_exit_confirmed':True,
        'individual_descendant_exit_codes_authenticated':False,
        'loaded_code_authenticated':False, 'whole_tree_resource_budget_measured':False,
        'observation_errors':errors}
    closed = owner._close_owned(k, job, process, thread, {
        'status':'failed' if reason is not None else 'complete',
        'stop_reason':reason, 'job':fact, 'formal_permission':False})
    if critical is not None:
        raise critical
    result = (identity, exit_code, reason, error_type, fact, time.monotonic() - started)
    if capture_quiescence:
        # This event exists only after the original native close path returned.
        event = {'closed':closed, 'process_identity':copy.deepcopy(identity),
                 'exit_code':exit_code, 'accounting':copy.deepcopy(accounting)}
        return (*result, event)
    return result


def run_owned(*, root, policy, operation, receipt_root, source_path=None,
              expected_output_pin=None, timeout_seconds=10, stop_probe=None,
              capture_quiescence=False):
    v.require(type(timeout_seconds) in (int, float) and 0 < timeout_seconds <= 30,
              'owned Git timeout')
    v.require(stop_probe is None or callable(stop_probe), 'owned Git shared stop probe')
    v.require(type(capture_quiescence) is bool, 'owned Git explicit quiescence capture option')
    root, executable, environment, before = direct._policy(root, policy)
    v.require(policy.get('process_ownership') == direct.JOB_OWNERSHIP,
              'owned Git Job opt-in required')
    if os.name != 'nt':
        raise OSError('owned Git private Job requires Windows')
    command = direct._command(policy, operation, source_path, expected_output_pin)
    stop = _shared_stop(stop_probe)
    if stop is not None:
        raise owner.resources.ResourceStop(stop)
    argv = [str(executable), '-c', 'core.fsmonitor=false', '-c', 'core.pager=cat',
            '-c', 'safe.directory=' + str(root), '-C', str(root), *command]
    target = Path(receipt_root)
    v.require(target.is_absolute(), 'owned Git receipt root absolute')
    paths.regular_path(target.parent, directory=True)
    paths.regular_path(target, directory=True, missing=True)
    target.mkdir()
    execution = _execute(
        argv, root, environment, target, operation, timeout_seconds,
        **({'stop_probe': stop_probe} if stop_probe is not None else {}),
        **({'capture_quiescence':True} if capture_quiescence else {}))
    identity, exit_code, reason, error_type, job, elapsed = execution[:6]
    prior_stop_reason = reason
    try:
        after = dependencies.file_observation(executable, native=True, maximum=direct.MAX_EXE)
    except (OSError, ValueError) as error:
        after = {'observation_error_type':type(error).__name__}
        reason = 'executable_after_unavailable'
    stdout_pin, stdout_bytes = direct._pin_output(target/'stdout.bin', direct.MAX_OUTPUT[operation])
    stderr_pin, stderr_bytes = direct._pin_output(target/'stderr.bin', direct.MAX_STDERR)
    if reason != 'executable_after_unavailable' and after != before:
        reason = 'executable_changed'
    if reason is None:
        if stdout_pin is None or stderr_pin is None:
            reason = 'output_limit'
        elif exit_code != 0:
            reason = 'exit_nonzero'
        elif stderr_bytes != 0:
            reason = 'stderr_nonempty'
        elif operation == 'head' and (target/'stdout.bin').read_bytes().strip() != policy['revision'].encode():
            reason = 'revision_mismatch'
        elif operation == 'status' and stdout_bytes != 0:
            reason = 'dirty_checkout'
        elif operation == 'source_blob' and stdout_pin != expected_output_pin:
            reason = 'blob_pin_mismatch'
    receipt = {'format':direct.JOB_FORMAT, 'status':'verified' if reason is None else 'failed',
        'reason':reason, 'prior_stop_reason':prior_stop_reason, 'operation':operation,
        'source_path':source_path, 'revision':policy['revision'],
        'executable_path':str(executable), 'executable_expected_pin':policy['executable_pin'],
        'executable_links_expected':policy['executable_links'],
        'executable_before':before, 'executable_after':after, 'argv':argv, 'cwd':str(root),
        'environment':environment, 'process_identity':identity, 'exit_code':exit_code,
        'process_error_type':error_type, 'direct_process_handle_exit_confirmed':exit_code is not None,
        'elapsed_seconds':elapsed, 'stdout_pin':stdout_pin, 'stdout_bytes':stdout_bytes,
        'stderr_pin':stderr_pin, 'stderr_bytes':stderr_bytes,
        'expected_output_pin':expected_output_pin, 'job':job,
        'integration_pending':True, 'formal_permission':False, 'source_closure_complete':False,
        'runtime_closure_complete':False, 'execution_authenticated':False}
    raw = io.json_bytes(receipt)
    v.require(len(raw) <= direct.MAX_RECEIPT, 'owned Git receipt size')
    io._exclusive(target/'receipt.json', raw)
    pin = observed._pin(raw)
    direct.verify_retained(target, pin, root=root, policy=policy)
    result = {'receipt':receipt, 'receipt_pin':pin, 'receipt_root':str(target),
              'stdout':None if stdout_pin is None else (target/'stdout.bin').read_bytes()}
    if capture_quiescence:
        event = execution[6]
        witness = {'format':QUIESCENCE, 'receipt_pin':pin, 'closed':event['closed'],
                   'process_identity':event['process_identity'], 'exit_code':event['exit_code'],
                   'accounting':event['accounting'], 'formal_permission':False}
        _verify_close_link(raw, pin, witness)  # Full retained verification just passed above.
        result['quiescence'] = witness
    return result


def verify_quiescence(receipt_raw, expected_receipt_pin, witness, *, root, policy,
                      stdout_raw, stderr_raw):
    """Verify retained receipt/output/policy and its linked post-close event.

    This consistency check does not authenticate loaded code or grant S4 credit.
    """
    direct.verify_raw(receipt_raw, expected_receipt_pin, stdout_raw=stdout_raw,
                      stderr_raw=stderr_raw, root=root, policy=policy)
    if type(witness) is dict and witness.get('format') == PIPE_QUIESCENCE:
        v.require(set(witness) == {'format','receipt_pin','closed','process_identity',
            'exit_code','accounting','formal_permission','io_closed'}, 'pipe quiescent exact witness')
        base={key:value for key,value in witness.items() if key != 'io_closed'}
        base['format']=QUIESCENCE
        _verify_close_link(receipt_raw,expected_receipt_pin,base)
        return _verify_pipe_close_link(witness['io_closed'], identity={
            key:witness['process_identity'][key] for key in ('pid','creation_time_100ns','start_token')},
            exit_code=witness['exit_code'],accounting=witness['accounting'],
            core_handles=witness['closed']['closed_handles'],stdout_raw=stdout_raw,stderr_raw=stderr_raw)
    return _verify_close_link(receipt_raw, expected_receipt_pin, witness)


def _verify_close_link(receipt_raw, expected_receipt_pin, witness):
    direct.evidence._raw(receipt_raw, expected_receipt_pin, 'quiescent Git receipt pin')
    receipt = v.strict_json(receipt_raw)
    v.require(io.json_bytes(receipt) == receipt_raw and receipt['format'] == direct.JOB_FORMAT,
              'quiescent Git canonical private Job receipt')
    verify_job(receipt)
    v.require(type(witness) is dict and set(witness) == {
        'format','receipt_pin','closed','process_identity','exit_code','accounting','formal_permission'} and
        witness['format'] == QUIESCENCE and witness['receipt_pin'] == expected_receipt_pin and
        witness['formal_permission'] is False, 'quiescent Git exact witness')
    closed = witness['closed']
    v.require(type(closed) is dict and set(closed) == {'format','closed_handles'} and
        closed['format'] == 'anomaly-v03-owned-handles-closed-v1', 'quiescent Git close event')
    handles = closed['closed_handles']
    v.require(type(handles) is dict and set(handles) == {'thread','process','job'} and
        all(type(n) is int and 0 < n < 2**64 for n in handles.values()) and
        len(set(handles.values())) == 3, 'quiescent Git original distinct closed handles')
    identity = receipt['process_identity']
    v.require(type(identity) is dict and set(identity) == {
        'pid','creation_time_100ns','start_token','native_start_identity_authenticated'} and
        type(identity['pid']) is int and identity['pid'] > 0 and
        type(identity['creation_time_100ns']) is int and identity['creation_time_100ns'] > 0 and
        identity['native_start_identity_authenticated'] is True and
        identity['start_token'] == v.canonical_sha256({key:identity[key] for key in ('pid','creation_time_100ns')}),
        'quiescent Git original native identity')
    v.require(receipt['job'] is not None and type(receipt['exit_code']) is int and
        io.json_bytes(witness['process_identity']) == io.json_bytes(identity) and
        type(witness['exit_code']) is int and witness['exit_code'] == receipt['exit_code'] and
        io.json_bytes(witness['accounting']) == io.json_bytes(receipt['job']['accounting']),
        'quiescent Git receipt/event identity and empty Job')
    return True


def verify_job(receipt):
    """Validate saved containment facts, with no process or Job API calls."""
    v.require(set(receipt) == _FIELDS, 'retained owned Git Job receipt fields')
    job = receipt['job']
    if job is None:
        v.require(receipt['status'] == 'failed' and receipt['exit_code'] is None and
                  receipt['process_identity'] is None, 'retained unstarted Git Job')
        return
    v.require(type(job) is dict and set(job) == {
        'format','assignment_confirmed','root_resumed','accounting','memory',
        'all_assigned_processes_exit_confirmed','individual_descendant_exit_codes_authenticated',
        'loaded_code_authenticated','whole_tree_resource_budget_measured','observation_errors'} and
        job['format'] == JOB and job['assignment_confirmed'] is True and
        type(job['root_resumed']) is bool and job['all_assigned_processes_exit_confirmed'] is True and
        job['individual_descendant_exit_codes_authenticated'] is False and
        job['loaded_code_authenticated'] is False and job['whole_tree_resource_budget_measured'] is False,
        'retained Git Job scope')
    account = job['accounting']
    v.require(type(account) is dict and set(account) == {
        'total_processes','active_processes','limit_terminated_processes'} and
        all(type(n) is int and n >= 0 for n in account.values()) and
        account['total_processes'] >= 1 and account['active_processes'] == 0 and
        account['limit_terminated_processes'] <= account['total_processes'] and
        receipt['direct_process_handle_exit_confirmed'] is True,
        'retained Git Job empty accounting')
    errors = job['observation_errors']
    v.require(type(errors) is list and len(errors) <= 2 and all(
        type(row) is dict and set(row) == {'stage','error_type'} and
        row['stage'] in ('execution','job_memory') and type(row['error_type']) is str
        for row in errors), 'retained Git Job observation errors')
    if receipt['status'] == 'verified':
        v.require(job['root_resumed'] is True and not errors and
                  owner.valid_job_memory(job['memory']) and
                  account['limit_terminated_processes'] == 0 and
                  receipt['process_identity']['native_start_identity_authenticated'] is True,
                  'retained Git Job successful containment')
    else:
        v.require(job['memory'] is None or owner.valid_job_memory(job['memory']),
                  'retained failed Git Job memory')
        v.require(not errors or type(receipt['process_error_type']) is str,
                  'retained failed Git Job observation')
