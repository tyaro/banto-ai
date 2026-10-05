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
