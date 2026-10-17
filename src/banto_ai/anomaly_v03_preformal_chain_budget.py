"""Continuous outer budget for one invented, preformal five-role chain.

This is an engineering fixture measurement, not the registered 50,000-draw
budget or S4 acceptance.  The sampler runs throughout the parent call and is
always joined by close().  The composed role supervisors probe its latched
stop while each owned child runs.  Sampling and termination are cooperative.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import re
import stat
import threading
import time

from . import _anomaly_v03_fixture_budget as primitives
from . import _anomaly_v03_engineering_runtime as resources


FORMAT = 'anomaly-v03-preformal-five-role-outer-budget-v1'
INTERVAL = 0.25
RECEIPT_RESERVE_BYTES = 128 * 1024  # Outer budget and result, each bounded to 64 KiB.
RECEIPT_RESERVE_ENTRIES = 2  # The same two files are written after the last sample.
DEFAULTS = {
    'wall_seconds': 240,
    'parent_private_bytes': 512 * 1024**2,
    'directory_bytes': 48 * 1024**2,
    'directory_entries': 256,
    'directory_depth': 8,
    'minimum_commit_headroom_bytes': 2 * 1024**3,
    'minimum_free_ram_bytes': 2 * 1024**3,
    'minimum_free_disk_bytes': 5 * 1024**3,
}
PHASES = ('preflight', 'producer', 'analysis', 'audit', 'writer', 'reader',
          'postflight')
ROLES = PHASES[1:6]


def limits(value=None):
    result = dict(DEFAULTS if value is None else value)
    if set(result) != set(DEFAULTS):
        raise ValueError('outer budget fields')
    for key, baseline in DEFAULTS.items():
        number = result[key]
        valid = (type(number) in (int, float) and math.isfinite(number)) if key == 'wall_seconds' else type(number) is int
        if not valid or number <= 0:
            raise ValueError('outer budget positive finite limits')
        if key.startswith('minimum_'):
            if number < baseline:
                raise ValueError('outer minimum reserve may only tighten')
        elif number > baseline:
            raise ValueError('outer limit may only tighten')
    return result


def _max_depth(root, maximum_entries, maximum_depth):
    """Measure directory depth after the bounded primitive's logical scan.

    The second scan can race an owned stage-to-payload rename; restart once.
    It never follows a reparse node or escapes the supplied root.
    """
    root = Path(root)
    for attempt in range(2):
        try:
            pending = [(root, 0)]
            entries = depth = 0
            while pending:
                directory, level = pending.pop()
                metadata = directory.lstat()
                if not stat.S_ISDIR(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
                    raise resources.ResourceStop('pipeline_unsafe_directory')
                depth = max(depth, level)
                if depth > maximum_depth:
                    raise resources.ResourceStop('pipeline_directory_depth')
                with os.scandir(directory) as children:
                    for child in children:
                        entries += 1
                        if entries > maximum_entries:
                            raise resources.ResourceStop('pipeline_inventory_limit')
                        path = Path(child.path)
                        info = path.lstat()
                        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                            raise resources.ResourceStop('pipeline_unsafe_directory')
                        if stat.S_ISDIR(info.st_mode):
                            pending.append((path, level + 1))
            return depth
        except FileNotFoundError:
            if attempt:
                raise
    raise AssertionError('unreachable depth observation')


class PreformalChainBudget(primitives.FixtureBudget):
    """One new root, one joined sampler, one latched engineering stop."""

    def __init__(self, root, value=None, *, publication_roots=()):
        # Initialize the adopted fixture monitor's ownership fields so nested
        # FixtureBudget(upstream=self) can share the live stop latch.  Only this
        # new preformal subclass uses the larger contiguous-chain caps below.
        super().__init__(root, publication_roots=publication_roots)
        self.limits = limits(value)
        self.started_at = self.started
        self.phase = 'preflight'
        self.phase_log = []
        self.roles = {}
        self._state_lock = self._lock
        self._sampling_lock = self._sampling
        self._closed = None

    def _observe(self):
        with self._sampling_lock:
            try:
                system = primitives.system_snapshot(self.root)
                tree = primitives.directory_snapshot(
                    self.root, self.limits['directory_entries'],
                    publication_roots=self.publication_roots)
                depth = _max_depth(self.root, self.limits['directory_entries'],
                                   self.limits['directory_depth'])
                current = {**system, **tree, 'directory_depth': depth,
                           'elapsed_seconds': time.monotonic() - self.started_at}
                expected = {'commit_total_bytes', 'commit_limit_bytes',
                            'commit_headroom_bytes', 'free_ram_bytes', 'free_disk_bytes',
                            'parent_peak_private_bytes', 'directory_bytes',
                            'directory_entries', 'directory_depth', 'elapsed_seconds'}
                if set(current) != expected or any(
                        type(v) is not int or v < 0 for k, v in current.items()
                        if k not in ('elapsed_seconds', 'commit_headroom_bytes')):
                    raise ValueError('invalid outer budget sample')
                if not math.isfinite(current['elapsed_seconds']) or current['elapsed_seconds'] < 0 or \
                        current['commit_headroom_bytes'] != current['commit_limit_bytes'] - current['commit_total_bytes']:
                    raise ValueError('invalid outer budget totals')
                checks = (
                    ('pipeline_wall_limit', current['elapsed_seconds'] > self.limits['wall_seconds']),
                    ('pipeline_parent_memory_limit', current['parent_peak_private_bytes'] > self.limits['parent_private_bytes']),
                    ('pipeline_directory_limit', current['directory_bytes'] +
                     RECEIPT_RESERVE_BYTES > self.limits['directory_bytes']),
                    ('pipeline_inventory_limit', current['directory_entries'] +
                     RECEIPT_RESERVE_ENTRIES > self.limits['directory_entries']),
                    ('pipeline_directory_depth', current['directory_depth'] > self.limits['directory_depth']),
                    ('pipeline_commit_headroom', current['commit_headroom_bytes'] < self.limits['minimum_commit_headroom_bytes']),
                    ('pipeline_free_ram', current['free_ram_bytes'] < self.limits['minimum_free_ram_bytes']),
                    ('pipeline_free_disk', current['free_disk_bytes'] < self.limits['minimum_free_disk_bytes']),
                )
                with self._state_lock:
                    self.samples += 1
                    current['phase'] = self.phase
                    self.first = self.first or current
                    self.last = current
                    for key, number in current.items():
                        if key == 'phase':
                            continue
                        if key not in self.extrema:
                            self.extrema[key] = {'min': number, 'max': number}
                        else:
                            row = self.extrema[key]
                            row['min'] = min(row['min'], number)
                            row['max'] = max(row['max'], number)
                    self.reason = self.reason or next((label for label, failed in checks if failed), None)
            except resources.ResourceStop as error:
                with self._state_lock:
                    self.reason = self.reason or error.reason
            except Exception as error:
                with self._state_lock:
                    self.reason = self.reason or 'pipeline_observation_error'
                    self.observation_error = self.observation_error or type(error).__name__

    def _run(self):
        try:
            while not self._stop.wait(INTERVAL):
                self._observe()
        except BaseException as error:
            with self._state_lock:
                self.reason = self.reason or 'pipeline_monitor_failure'
                self.observation_error = self.observation_error or type(error).__name__

    def start(self):
        if self._thread is not None or self._closed is not None:
            raise ValueError('outer budget already started or closed')
        self._observe()
        self._thread = threading.Thread(target=self._run,
                                        name='banto-preformal-five-role-budget',
                                        daemon=False)
        self._thread.start()
        return self

    def probe(self):
        with self._state_lock:
            return self.reason

    def checkpoint(self, phase=None):
        if (phase is not None and phase not in PHASES) or self._thread is None or self._closed is not None:
            raise ValueError('invalid outer budget checkpoint')
        if phase is not None:
            with self._state_lock:
                self.phase = phase
                self.phase_log.append({'phase': phase,
                                       'elapsed_seconds': time.monotonic() - self.started_at,
                                       'stop_before_sample': self.reason})
        self._observe()
        reason = self.probe()
        if reason is not None:
            raise resources.ResourceStop(reason)

    def record_role(self, role, status, result_pin=None, worker_pid=None, exit_confirmed=None):
        """Store caller-reported process completion; no foreign PID is queried."""
        valid_pin = (result_pin is None or
                     (type(result_pin) is dict and set(result_pin) == {'bytes', 'sha256'} and
                      type(result_pin['bytes']) is int and result_pin['bytes'] >= 0 and
                      type(result_pin['sha256']) is str and
                      re.fullmatch(r'[0-9a-f]{64}', result_pin['sha256'])))
        if role not in ROLES or type(status) is not str or not status or \
                not valid_pin or (exit_confirmed is not None and type(exit_confirmed) is not bool) or \
                (worker_pid is not None and (type(worker_pid) is not int or worker_pid <= 0)):
            raise ValueError('outer budget role report')
        with self._state_lock:
            if role in self.roles or self._closed is not None:
                raise ValueError('duplicate or late outer budget role report')
            self.roles[role] = {'worker_exit_confirmed': exit_confirmed,
                                'worker_pid': worker_pid, 'status': status,
                                'result_pin': dict(result_pin) if result_pin is not None else None,
                                'reported_elapsed_seconds': time.monotonic() - self.started_at}

    def close(self):
        """Stop and unconditionally join the sampler before returning evidence."""
        if self._closed is not None:
            return self._closed
        if self._thread is None:
            raise ValueError('outer budget not started')
        self._stop.set()
        self._thread.join()  # Local bounded scans; never return with a live sampler.
        self._observe()
        with self._state_lock:
            values = self.extrema
            summary = {
                'wall_seconds': time.monotonic() - self.started_at,
                'peak_parent_private_bytes': values.get('parent_peak_private_bytes', {}).get('max'),
                'minimum_commit_headroom_bytes': values.get('commit_headroom_bytes', {}).get('min'),
                'minimum_free_ram_bytes': values.get('free_ram_bytes', {}).get('min'),
                'minimum_free_disk_bytes': values.get('free_disk_bytes', {}).get('min'),
                'maximum_root_logical_bytes': values.get('directory_bytes', {}).get('max'),
                'maximum_root_entries': values.get('directory_entries', {}).get('max'),
                'maximum_root_depth': values.get('directory_depth', {}).get('max'),
            }
            report = {
                'format': FORMAT, 'scope': 'invented-preformal-five-role-engineering-fixture',
                'root': str(self.root), 'limits': dict(self.limits),
                'publication_roots': [str(p) for p in self.publication_roots],
                'sample_interval_seconds': INTERVAL, 'samples': self.samples,
                'first': self.first, 'last': self.last,
                'extrema': {k: dict(v) for k, v in self.extrema.items()},
                'summary': summary, 'phase_log': list(self.phase_log),
                'receipt_reserve_bytes': RECEIPT_RESERVE_BYTES,
                'receipt_reserve_entries': RECEIPT_RESERVE_ENTRIES,
                'root_measurement_scope':
                    'samples exclude outer resource-budget.json and result.json; bytes and entries reserved within limits',
                'caller_reported_roles': dict(self.roles),
                'caller_reported_all_five_exits':
                    set(self.roles) == set(ROLES) and all(
                        row['worker_exit_confirmed'] for row in self.roles.values()),
                'stop_reason': self.reason, 'observation_error': self.observation_error,
                'sampler_exit_confirmed': not self._thread.is_alive(),
                'passed': self.reason is None and not self._thread.is_alive(),
                'stop_behavior': 'sampled-continuously; checkpoints-and-owned-child-probes; not-hard-quota',
                'owned_child_reap_scope': 'caller-reported-exit-only; no foreign-process-query',
                'formal_permission': False, 'registered_data_read': False,
                'independent_s6_complete': False,
                'formal_50000_draw_budget_measured': False,
            }
            self._closed = report
            return report
