"""Sample one invented generator -> separate reader attempt under one budget.

The monitor owns only the caller's new attempt root and its parent process.
Each owned child is still stopped and reaped by its process supervisor, which
probes this monitor's latched reason.  Sampling is cooperative, not a quota or
formal campaign acceptance.  A separately prepared external pinset is outside
the measured root and time interval.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import threading
import time

from . import _anomaly_v03_fixture_budget as primitives
from . import _anomaly_v03_engineering_runtime as resources
from . import _anomaly_v03_runtime as paths
from . import anomaly_v03_registered_saved_attempt_fixture as fixture


ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-generated-two-role-outer-budget-v1'
INTERVAL = 0.25
REPORT_MAX_BYTES = 64 * 1024
RECEIPT_RESERVE_BYTES = 2 * REPORT_MAX_BYTES
RECEIPT_RESERVE_ENTRIES = 2
PHASES = ('preflight', 'generator', 'reader', 'postflight')
ROLES = ('generator', 'reader')
DEFAULTS = {
    'wall_seconds': 600,
    'parent_private_bytes': 512 * 1024**2,
    'directory_bytes': 192 * 1024**2,
    'directory_entries': 256,
    'directory_depth': 12,
    'minimum_commit_headroom_bytes': 2 * 1024**3,
    'minimum_free_ram_bytes': 2 * 1024**3,
    'minimum_free_disk_bytes': 5 * 1024**3,
}


def limits(value=None):
    """Permit tighter caller limits without silently widening this fixture."""
    result = dict(DEFAULTS if value is None else value)
    if set(result) != set(DEFAULTS):
        raise ValueError('generated outer budget fields')
    for key, baseline in DEFAULTS.items():
        number = result[key]
        valid = (type(number) in (int, float) and math.isfinite(number)
                 if key == 'wall_seconds' else type(number) is int)
        if not valid or number <= 0:
            raise ValueError('generated outer budget positive finite limits')
        if key.startswith('minimum_'):
            if number < baseline:
                raise ValueError('generated outer minimum reserve may only tighten')
        elif number > baseline:
            raise ValueError('generated outer limit may only tighten')
    return result


def _directory_snapshot(root, maximum_entries, maximum_depth, identity):
    """Metadata only; reject links, reparse points, hardlinks, or root replacement."""
    for attempt in range(2):
        try:
            pending = [(root, 0)]
            entries = total = depth = 0
            while pending:
                directory, level = pending.pop()
                metadata = directory.lstat()
                if (not stat.S_ISDIR(metadata.st_mode) or
                        getattr(metadata, 'st_file_attributes', 0) & 0x400):
                    raise resources.ResourceStop('generated_unsafe_directory')
                if directory == root and (metadata.st_dev, metadata.st_ino) != identity:
                    raise resources.ResourceStop('generated_root_changed')
                depth = max(depth, level)
                if depth > maximum_depth:
                    raise resources.ResourceStop('generated_directory_depth')
                with os.scandir(directory) as children:
                    for child in children:
                        entries += 1
                        if entries > maximum_entries:
                            raise resources.ResourceStop('generated_inventory_limit')
                        path = Path(child.path)
                        info = path.lstat()
                        if (stat.S_ISLNK(info.st_mode) or
                                getattr(info, 'st_file_attributes', 0) & 0x400):
                            raise resources.ResourceStop('generated_unsafe_directory')
                        if stat.S_ISDIR(info.st_mode):
                            pending.append((path, level + 1))
                        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                            total += info.st_size
                        else:
                            raise resources.ResourceStop('generated_unsafe_directory')
            return {'directory_bytes': total, 'directory_entries': entries,
                    'directory_depth': depth}
        except FileNotFoundError:
            if attempt:
                raise
    raise AssertionError('unreachable directory observation')


class PartitionedPublicationPreparation:
    """Retain future failure slots and current Python widths; no native admission.

    The measured object graph excludes the runtime/owner/native allocations.
    A directory snapshot is not an all-writer reservation or an exclusive lock.
    """
    FORMAT='anomaly-v03-partitioned-publication-preparation-v1'
    OUTER_BYTES,OUTER_ENTRIES,RESERVE,MEMORY_BYTES=1024**2,32,128*1024,321*1024**2

    def _retain_inputs(self, *, owner, checkpoint, archive_preparation, allocation, entry_raw, context_raw, parent_identity_raw):
        self.original_inputs=(owner,checkpoint,archive_preparation,allocation,entry_raw,context_raw,parent_identity_raw)
        self.owner,self.checkpoint,self.archive=owner,checkpoint,archive_preparation
        self.pending=self.error=self._failure=self._completed=None
        self._pending=None;self._returns=self._returns_anchor=();self._anchor=None;self.rejected=None
        self._observation_bindings=self._bindings_anchor=();self._observer=(_directory_snapshot,sys.getsizeof)
        self._completion_anchor=None;self._observing=False;self._observations=0

    def __init__(self, *, owner, checkpoint, archive_preparation, allocation, entry_raw, context_raw, parent_identity_raw):
        self._retain_inputs(owner=owner,checkpoint=checkpoint,archive_preparation=archive_preparation,
            allocation=allocation,entry_raw=entry_raw,context_raw=context_raw,parent_identity_raw=parent_identity_raw)
        try:
            previous=getattr(owner,'original_partitioned_publication',None)
            if previous is not None:
                previous.rejected=self;previous._failed(ValueError('partitioned publication original owner cannot be replaced'))
            owner.original_partitioned_publication=owner.partitioned_publication=self
            self.pending=self._pending={'inputs':self.original_inputs}
            from . import anomaly_v03_preformal_worker_git_archive as archive
            self.component=archive;v,io,evidence=archive.v,archive.io,archive.evidence
            v.require(type(archive_preparation) is archive.PartitionedArchivePreparation and
                archive_preparation.original_owner is owner and archive_preparation.original_checkpoint is checkpoint,
                'partitioned publication same original archive owner and clock')
            plan=archive_preparation.plan();self._retain_return(plan)
            self.archive_allocation_raw=archive_preparation._prepared[0]
            v.require(all(type(raw) is bytes and len(raw)<=archive.proof.channel.MAX_CONTROL for raw in
                (entry_raw,context_raw,parent_identity_raw)), 'partitioned publication original entry/context/identity bytes')
            v.require(v.strict_json(context_raw)==v.strict_json(archive_preparation._prepared[1]) and
                io.json_bytes(v.strict_json(context_raw))==context_raw,'partitioned publication exact held context raw')
            identity=v.strict_json(parent_identity_raw)
            v.require(type(identity) is dict and set(identity)=={'format','context_pin','identity','formal_permission'} and
                identity['format']==self.FORMAT+'-parent-identity' and identity['formal_permission'] is False and
                identity['context_pin']==archive.observed._pin(context_raw) and type(identity['identity']) is dict and
                set(identity['identity'])=={'pid','creation_time_100ns','start_token'} and
                all(type(identity['identity'][key]) is int and identity['identity'][key]>0 for key in ('pid','creation_time_100ns')),
                'partitioned publication declared parent identity bound to same context')
            evidence._digest(identity['identity']['start_token'],64)
            v.require(io.json_bytes(identity)==parent_identity_raw,'partitioned publication canonical original identity')
            v.require(type(allocation) is dict and set(allocation)=={'format','control_limits','call_raw_maxima',
                'parent_raw_maxima','diagnostic_maxima','native_buffer_payload_bytes','resident_extra_bytes'} and allocation['format']==self.FORMAT,
                'partitioned publication exact closed allocation')
            archive.ArchiveAppendAdmission.validate_controls(allocation['control_limits'])
            calls=allocation['call_raw_maxima'];parent=allocation['parent_raw_maxima'];diagnostics=allocation['diagnostic_maxima']
            v.require(type(calls) is list and len(calls)==plan['planned_calls'] and
                all(type(row) is dict and {'stdout.bin','stderr.bin','receipt.json'}<=set(row)<=set(archive.proof.RAW_LIMITS) and
                    all(type(n) is int and 0<n<=archive.proof.RAW_LIMITS[name] for name,n in row.items()) for row in calls),
                'partitioned publication all original call raw maxima')
            v.require(type(parent) is dict and {'stdout.bin','stderr.bin','receipt.json'}<=set(parent)<=set(archive.PublicationStorageAdmission.PARENT_MAX) and
                all(type(n) is int and 0<n<=archive.PublicationStorageAdmission.PARENT_MAX[name] for name,n in parent.items()) and
                type(diagnostics) is dict and set(diagnostics)=={'diagnostic.json','diagnostic.log'} and
                all(type(n) is int and 0<n<=REPORT_MAX_BYTES for n in diagnostics.values()),
                'partitioned publication independent parent failure and diagnostic maxima')
            v.require(type(allocation['native_buffer_payload_bytes']) is int and 0<=allocation['native_buffer_payload_bytes']<=131072 and
                type(allocation['resident_extra_bytes']) is int and 0<allocation['resident_extra_bytes']<=self.MEMORY_BYTES,
                'partitioned publication independent retained native payload and extra allowance')
            self.allocation_raw=io.json_bytes(allocation);self._retain_return(self.allocation_raw)
            v.require(len(self.allocation_raw)<=archive.proof.channel.MAX_CONTROL,'partitioned publication allocation raw bytes')
            self.context=v.strict_json(context_raw);self.root=Path(self.context['root']);self.identity=tuple(self.context['root_identity'])
            self._anchor=(self.original_inputs,self.archive_allocation_raw,self.allocation_raw)
            self.observe('prepare')
        except BaseException as error:self._failed(error)

    def _failed(self,error):
        if self._failure is None:self._failure=error
        self.error=self._failure
        if getattr(self.error,'partitioned_publication',None) is None:self.error.partitioned_publication=self
        if getattr(self.error,'reader_git_parent',None) is None:self.error.reader_git_parent=self.owner
        if getattr(self.owner,'error',None) is None:self.owner.error=self.error
        raise self.error

    def _retain_return(self,value):
        self._returns=self._returns_anchor=self._returns_anchor+(value,)

    def _bind_observation(self,value,raw):
        self._observation_bindings=self._bindings_anchor=self._bindings_anchor+((value,raw),)

    def _fixed(self, *, observation=True):
        if self._failure is not None:raise self._failure
        v,io=self.component.v,self.component.io
        owner,checkpoint,archive,allocation,entry,context,identity=self.original_inputs
        v.require(self.owner is owner and self.checkpoint is checkpoint and self.archive is archive and
            self.FORMAT=='anomaly-v03-partitioned-publication-preparation-v1' and
            (self.OUTER_BYTES,self.OUTER_ENTRIES,self.RESERVE,self.MEMORY_BYTES)==(1024**2,32,128*1024,321*1024**2) and
            (_directory_snapshot,sys.getsizeof)==self._observer and
            owner.original_partitioned_publication is owner.partitioned_publication is self and
            self._anchor[0] is self.original_inputs and archive._prepared[0] is self._anchor[1] and
            io.json_bytes(allocation)==self._anchor[2] and self.allocation_raw is self._anchor[2] and
            io.json_bytes(self.context)==context and self.root==Path(self.context['root']) and
            self.identity==tuple(self.context['root_identity']) and self.pending is self._pending,
            'partitioned publication original owner/input/snapshot metadata changed')
        v.require(self._completed is self._completion_anchor and self._returns is self._returns_anchor and
            self._observation_bindings is self._bindings_anchor,'partitioned publication original completion or returns replaced')
        if self._pending is not None:
            v.require(self._pending.get('inputs') is self.original_inputs,'partitioned publication original pending inputs hidden')
        for value,raw in self._observation_bindings:
            v.require(io.json_bytes(value)==raw,'partitioned publication original returned observation changed')
        plan=archive.plan()
        if observation and self._completed is not None:
            v.require(self.last_observation is self._completed[0] and io.json_bytes(self.last_observation)==self._completed[1] and
                io.json_bytes(plan)==self._completed[2], 'partitioned publication original observation cannot follow callbacks')
        return plan

    @staticmethod
    def _python_width(value):
        pending=[value];seen=set();total=0
        while pending:
            item=pending.pop();key=id(item)
            if key in seen:continue
            seen.add(key)
            if len(seen)>4096 or type(item) not in (dict,list,tuple,bytes,str,int,bool,type(None)):
                raise ValueError('partitioned publication bounded known Python payload graph')
            total+=sys.getsizeof(item)
            if type(item) is dict:pending.extend(item.keys());pending.extend(item.values())
            elif type(item) in (tuple,list):pending.extend(item)
        return total,len(seen)

    def observe(self,stage):
        if self._failure is not None:raise self._failure
        try:
            if self._observing or self._observations>=65:
                raise ValueError('partitioned publication pending or bounded observation cannot be replaced')
            self._observing=True;self._observations+=1
            plan=self._fixed(observation=False);self.pending=self._pending={'stage':stage,'inputs':self.original_inputs}
            self.checkpoint();self._fixed(observation=False)
            v,io=self.component.v,self.component.io
            v.require(type(stage) is str and len(stage.encode())<=64,'partitioned publication bounded observation stage')
            allocation=self.original_inputs[3]
            for original in self.archive._ledger:
                maxima=allocation['call_raw_maxima'][original[0]['lease']]
                v.require(all(raw is None or name in maxima and len(raw)<=maxima[name] for name,raw in original[5]['raw'].items()),
                    'partitioned publication retained actual raw exceeds independent call maximum')
            snapshot=self._observer[0](self.root,self.OUTER_ENTRIES,2,self.identity)
            self._retain_return(snapshot);self.pending['snapshot']=snapshot
            v.require(type(snapshot) is dict and set(snapshot)=={'directory_bytes','directory_entries','directory_depth'} and
                all(type(n) is int and n>=0 for n in snapshot.values()),'partitioned publication original directory snapshot')
            self._bind_observation(snapshot,io.json_bytes(snapshot))
            raw_bytes=sum(sum(row.values()) for row in allocation['call_raw_maxima'])
            future=sum(allocation['control_limits'].values())+raw_bytes+sum(allocation['parent_raw_maxima'].values())+\
                sum(allocation['diagnostic_maxima'].values())+sum(len(raw) for raw in self.original_inputs[4:])+plan['reserved_maxima_bytes']
            entries=len(allocation['control_limits'])+sum(len(row) for row in allocation['call_raw_maxima'])+\
                len(allocation['parent_raw_maxima'])+len(allocation['diagnostic_maxima'])+3+1
            # Do not walk API/native/Python owner objects or invoke their getters.
            graph=(self.original_inputs[3:],self._returns,self._observation_bindings,self.archive._returns,self.archive._bundle,
                tuple((prep._raw_returns,prep._record_bindings) for _,prep in self.archive._owners))
            self.pending['python_graph']=graph
            self.pending['python_width_return']=measured=self._python_width(graph);self._retain_return(measured)
            v.require(type(measured) is tuple and len(measured)==2 and all(type(n) is int and n>0 for n in measured),
                'partitioned publication original known Python width return')
            memory=future+allocation['native_buffer_payload_bytes']+allocation['resident_extra_bytes']+measured[0]
            row={'stage':stage,'allocation_pin':self.component.observed._pin(self.allocation_raw),'snapshot':snapshot,
                'future_bytes':future,'future_entries':entries,'remaining_bytes':self.OUTER_BYTES-self.RESERVE-snapshot['directory_bytes']-future,
                'remaining_entries':self.OUTER_ENTRIES-RECEIPT_RESERVE_ENTRIES-snapshot['directory_entries']-entries,
                'python_payload_graph_bytes':measured[0],'python_payload_graph_objects':measured[1],'memory_projection_bytes':memory,
                'entry_context_identity_bytes':sum(len(raw) for raw in self.original_inputs[4:]),'archive_growth_maxima_bytes':plan['reserved_maxima_bytes'],
                'all_call_raw_maxima_bytes':raw_bytes,'parent_failure_bytes':sum(allocation['parent_raw_maxima'].values()),
                'native_authorized':False,'atomic_reservation':False,'exclusive_root':False,'capacity_pass':False,
                'global_memory_measured':False,'rss_measured':False,'all_writers_registered':False,'parent_ack_authorized':False,'execution_authenticated':False}
            self.pending['projection']=row;self._retain_return(row)
            row_raw=io.json_bytes(row);self._bind_observation(row,row_raw)
            v.require(row['remaining_bytes']>=0 and row['remaining_entries']>=0 and memory<=self.MEMORY_BYTES,
                'partitioned publication all future disk entries/bytes and local memory projection')
            self.checkpoint();self._fixed(observation=False)
            self.last_observation=row;self._completed=self._completion_anchor=(row,row_raw,io.json_bytes(plan))
            self.pending=self._pending=None;self._observing=False;return self.view()
        except BaseException as error:self._failed(error)

    def view(self):
        try:self._fixed();return self.component.v.strict_json(self._completed[1])
        except BaseException as error:self._failed(error)

    def unresolved(self):return True  # No atomic/exclusive/native completion contract was issued.

    def execute(self):
        if self._failure is not None:raise self._failure
        raise ValueError('partitioned publication native/all-writer admission not prepared')


class GeneratedChainBudget:
    """One new root, one joined sampler, and one shared cooperative stop."""

    phase_names = PHASES
    role_names = ROLES

    def __init__(self, root, value=None):
        root = paths.regular_path(Path(root), directory=True)
        if (root.parent != ROOT / 'artifacts' or
                not root.name.startswith(fixture.PREFIX)):
            raise ValueError('dedicated invented generated-attempt root required')
        metadata = root.lstat()
        if metadata.st_ino == 0:
            raise ValueError('generated root identity unavailable')
        self.root = root
        self.root_identity = (metadata.st_dev, metadata.st_ino)
        self.limits = limits(value)
        self.started_at = time.monotonic()
        self.phase = 'preflight'
        self.phase_log = []
        self.roles = {}
        self.reason = None
        self.observation_error = None
        self.samples = 0
        self.first = self.last = None
        self.extrema = {}
        self._state_lock = threading.RLock()
        self._sampling_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._closed = None

    def _observe(self):
        with self._sampling_lock:
            try:
                current = {
                    **primitives.system_snapshot(self.root),
                    **self._directory_observation(),
                    'elapsed_seconds': time.monotonic() - self.started_at,
                }
                expected = {
                    'commit_total_bytes', 'commit_limit_bytes',
                    'commit_headroom_bytes', 'free_ram_bytes', 'free_disk_bytes',
                    'parent_peak_private_bytes', 'directory_bytes',
                    'directory_entries', 'directory_depth', 'elapsed_seconds',
                }
                if (set(current) != expected or
                        any(type(value) is not int or value < 0
                            for key, value in current.items()
                            if key not in ('elapsed_seconds', 'commit_headroom_bytes')) or
                        type(current['commit_headroom_bytes']) is not int or
                        current['commit_headroom_bytes'] !=
                        current['commit_limit_bytes'] - current['commit_total_bytes'] or
                        not math.isfinite(current['elapsed_seconds']) or
                        current['elapsed_seconds'] < 0):
                    raise ValueError('invalid generated outer budget sample')
                checks = (
                    ('generated_wall_limit',
                     current['elapsed_seconds'] > self.limits['wall_seconds']),
                    ('generated_parent_memory_limit',
                     current['parent_peak_private_bytes'] >
                     self.limits['parent_private_bytes']),
                    ('generated_directory_limit',
                     current['directory_bytes'] + RECEIPT_RESERVE_BYTES >
                     self.limits['directory_bytes']),
                    ('generated_inventory_limit',
                     current['directory_entries'] + RECEIPT_RESERVE_ENTRIES >
                     self.limits['directory_entries']),
                    ('generated_directory_depth',
                     current['directory_depth'] > self.limits['directory_depth']),
                    ('generated_commit_headroom',
                     current['commit_headroom_bytes'] <
                     self.limits['minimum_commit_headroom_bytes']),
                    ('generated_free_ram',
                     current['free_ram_bytes'] <
                     self.limits['minimum_free_ram_bytes']),
                    ('generated_free_disk',
                     current['free_disk_bytes'] <
                     self.limits['minimum_free_disk_bytes']),
                )
                with self._state_lock:
                    self.samples += 1
                    current['phase'] = self.phase
                    self.first = self.first or current
                    self.last = current
                    for key, value in current.items():
                        if key == 'phase':
                            continue
                        row = self.extrema.setdefault(key, {'min': value, 'max': value})
                        row['min'] = min(row['min'], value)
                        row['max'] = max(row['max'], value)
                    self.reason = self.reason or next(
                        (label for label, failed in checks if failed), None)
            except resources.ResourceStop as error:
                with self._state_lock:
                    self.reason = self.reason or error.reason
            except Exception as error:
                with self._state_lock:
                    self.reason = self.reason or 'generated_observation_error'
                    self.observation_error = self.observation_error or type(error).__name__

    def _run(self):
        try:
            while not self._stop.wait(INTERVAL):
                self._observe()
        except BaseException as error:
            with self._state_lock:
                self.reason = self.reason or 'generated_monitor_failure'
                self.observation_error = self.observation_error or type(error).__name__

    def _directory_observation(self):
        return _directory_snapshot(self.root, self.limits['directory_entries'],
                                   self.limits['directory_depth'], self.root_identity)

    def start(self):
        if self._thread is not None or self._closed is not None:
            raise ValueError('generated outer budget already started or closed')
        self._observe()
        self._thread = threading.Thread(target=self._run,
                                        name='banto-generated-two-role-budget',
                                        daemon=False)
        self._thread.start()
        return self

    def probe(self):
        with self._state_lock:
            return self.reason

    def checkpoint(self, phase):
        if (phase not in self.phase_names or self._thread is None or
                self._closed is not None or len(self.phase_log) >= 16):
            raise ValueError('invalid generated outer budget checkpoint')
        with self._state_lock:
            self.phase = phase
            self.phase_log.append({
                'phase': phase,
                'elapsed_seconds': time.monotonic() - self.started_at,
                'stop_before_sample': self.reason,
            })
        self._observe()
        reason = self.probe()
        if reason is not None:
            raise resources.ResourceStop(reason)

    def record_role(self, role, status, result_pin=None, pid=None,
                    exit_confirmed=None):
        valid_pin = (result_pin is None or
                     (type(result_pin) is dict and
                      set(result_pin) == {'bytes', 'sha256'} and
                      type(result_pin['bytes']) is int and
                      result_pin['bytes'] >= 0 and
                      type(result_pin['sha256']) is str and
                      re.fullmatch(r'[0-9a-f]{64}', result_pin['sha256'])))
        if (role not in self.role_names or type(status) is not str or not status or
                not valid_pin or
                (pid is not None and (type(pid) is not int or pid <= 0)) or
                (exit_confirmed is not None and
                 type(exit_confirmed) is not bool)):
            raise ValueError('generated outer budget role report')
        with self._state_lock:
            if (self._thread is None or self._closed is not None or
                    role in self.roles):
                raise ValueError('duplicate or late generated role report')
            self.roles[role] = {
                'status': status,
                'result_pin': dict(result_pin) if result_pin is not None else None,
                'worker_pid': pid,
                'worker_exit_confirmed': exit_confirmed,
                'reported_elapsed_seconds': time.monotonic() - self.started_at,
            }

    def close(self):
        """Stop and join the sampler before returning bounded receipt data."""
        if self._closed is not None:
            return self._closed
        if self._thread is None:
            raise ValueError('generated outer budget not started')
        self._stop.set()
        self._thread.join()
        self._observe()
        with self._state_lock:
            values = self.extrema
            summary = {
                'wall_seconds': time.monotonic() - self.started_at,
                'peak_parent_private_bytes': values.get(
                    'parent_peak_private_bytes', {}).get('max'),
                'minimum_commit_headroom_bytes': values.get(
                    'commit_headroom_bytes', {}).get('min'),
                'minimum_free_ram_bytes': values.get('free_ram_bytes', {}).get('min'),
                'minimum_free_disk_bytes': values.get('free_disk_bytes', {}).get('min'),
                'maximum_root_logical_bytes': values.get('directory_bytes', {}).get('max'),
                'maximum_root_entries': values.get('directory_entries', {}).get('max'),
                'maximum_root_depth': values.get('directory_depth', {}).get('max'),
            }
            report = {
                'format': FORMAT,
                'scope': 'invented-generated-attempt-to-separate-reader-only',
                'root': str(self.root),
                'root_identity': {'device': self.root_identity[0],
                                  'inode': self.root_identity[1]},
                'limits': dict(self.limits),
                'sample_interval_seconds': INTERVAL,
                'samples': self.samples,
                'first': self.first,
                'last': self.last,
                'extrema': {key: dict(value) for key, value in values.items()},
                'summary': summary,
                'phase_log': list(self.phase_log),
                'receipt_reserve_bytes': RECEIPT_RESERVE_BYTES,
                'receipt_reserve_entries': RECEIPT_RESERVE_ENTRIES,
                'root_measurement_scope':
                    'external prepared pins excluded; final budget and result reserved',
                'caller_reported_roles': {
                    key: dict(value) for key, value in self.roles.items()},
                'both_owned_exits_reported':
                    set(self.roles) == set(self.role_names) and all(
                        row['worker_exit_confirmed'] for row in self.roles.values()),
                'stop_reason': self.reason,
                'observation_error': self.observation_error,
                'sampler_exit_confirmed': not self._thread.is_alive(),
                'passed': self.reason is None and not self._thread.is_alive(),
                'stop_behavior': 'sampled; child-supervisor probes; not-hard-quota',
                'owned_child_reap_scope': 'caller-reported-exit-only',
                'formal_permission': False,
                'actual_registered_observations_read': False,
                'campaign_evaluations_credited': 0,
            }
            if len(json.dumps(report, sort_keys=True, separators=(',', ':'),
                              allow_nan=False).encode('utf-8')) > REPORT_MAX_BYTES:
                raise ValueError('generated outer budget report byte limit')
            self._closed = report
            return report
