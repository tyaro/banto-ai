"""Cooperative, bounded resource monitor for one new fixture receipt directory.

No descendant discovery, foreign process termination, cleanup, or hard quota.
The thread latches the first stop; the caller checks before each bounded phase.
"""
from __future__ import annotations
import ctypes
import math
import os
from pathlib import Path
import shutil
import stat
import threading
import time

from . import _anomaly_v03_engineering_runtime as resources
from . import _anomaly_v03_io as io

DEFAULTS = {'wall_seconds':120,'parent_private_bytes':512*1024**2,'directory_bytes':32*1024**2,
            'directory_entries':256,'minimum_commit_headroom_bytes':2*1024**3,
            'minimum_free_ram_bytes':2*1024**3,'minimum_free_disk_bytes':5*1024**3}
INTERVAL = .25
RECEIPT_RESERVE = 64*1024


def limits(value=None):
    value = dict(DEFAULTS if value is None else value)
    if set(value) != set(DEFAULTS):raise ValueError('fixture budget fields')
    for key,cap in DEFAULTS.items():
        number = value[key]
        valid = type(number) in (int,float) and math.isfinite(number) if key == 'wall_seconds' else type(number) is int
        if not valid or number <= 0:raise ValueError('fixture budget positive finite limits')
        if (number < cap if key.startswith('minimum_') else number > cap):
            raise ValueError('fixture limits may only be tightened')
    return value


def system_snapshot(root):
    """System commit from GetPerformanceInfo (not process virtual-memory quota)."""
    kernel,w = resources._windows()
    class Performance(ctypes.Structure):
        _fields_ = [('cb',w.DWORD)]+[(n,ctypes.c_size_t) for n in
            ('commit','limit','peak_commit','physical','available','cache','kernel','paged','nonpaged','page_size')]+[
            ('handles',w.DWORD),('processes',w.DWORD),('threads',w.DWORD)]
    psapi = ctypes.WinDLL('psapi',use_last_error=True)
    psapi.GetPerformanceInfo.argtypes = [ctypes.POINTER(Performance),w.DWORD]
    psapi.GetPerformanceInfo.restype = w.BOOL
    value = Performance();value.cb = ctypes.sizeof(value)
    if not psapi.GetPerformanceInfo(ctypes.byref(value),value.cb):raise OSError('system commit observation failed')
    if not value.page_size or not value.limit:raise OSError('invalid system memory observation')
    return {'commit_total_bytes':value.commit*value.page_size,'commit_limit_bytes':value.limit*value.page_size,
        'commit_headroom_bytes':(value.limit-value.commit)*value.page_size,'free_ram_bytes':value.available*value.page_size,
        'free_disk_bytes':shutil.disk_usage(root).free,'parent_peak_private_bytes':resources.memory_bytes()['peak_private_bytes']}


def directory_snapshot(root, maximum):
    """Bounded metadata scan of this receipt only; never follow links/reparse nodes."""
    pending = [(Path(root),0)];entries = total = 0
    while pending:
        directory,depth = pending.pop()
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
            raise resources.ResourceStop('pipeline_unsafe_directory')
        if depth > 8:raise resources.ResourceStop('pipeline_directory_depth')
        with os.scandir(directory) as children:
            for child in children:
                entries += 1
                if entries > maximum:raise resources.ResourceStop('pipeline_inventory_limit')
                # Windows DirEntry's cached find-data stat reports st_nlink=0.
                # Query the path itself for the actual link count, without following it.
                info = Path(child.path).lstat()
                if getattr(info,'st_file_attributes',0)&0x400 or stat.S_ISLNK(info.st_mode):
                    raise resources.ResourceStop('pipeline_unsafe_directory')
                if stat.S_ISDIR(info.st_mode):pending.append((Path(child.path),depth+1))
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:total += info.st_size
                else:raise resources.ResourceStop('pipeline_unsafe_directory')
    return {'directory_bytes':total,'directory_entries':entries}


class UnclosedMonitor(RuntimeError):
    def __init__(self, monitor, report):
        self.monitor,self.report = monitor,report
        super().__init__('fixture resource monitor exit unconfirmed')


class FixtureBudget:
    def __init__(self, root, value=None, *, upstream=None):
        self.root = io.regular_path(Path(root),directory=True)
        self.limits = limits(value)
        if upstream is not None and (not isinstance(upstream,FixtureBudget) or self.root == upstream.root
                or not self.root.is_relative_to(upstream.root) or upstream._thread is None or upstream._stop.is_set()):
            raise ValueError('shared fixture budget must own a live enclosing root')
        self.upstream = upstream
        self.started = time.monotonic();self.reason = None;self.observation_error = None
        self.samples = 0;self.first = self.last = None;self.extrema = {}
        self._lock = threading.RLock();self._sampling = threading.Lock();self._stop = threading.Event();self._thread = None

    def _observe(self):
        with self._sampling:
            try:
                current = {**system_snapshot(self.root),**directory_snapshot(self.root,self.limits['directory_entries']),
                           'elapsed_seconds':time.monotonic()-self.started}
                expected = {'commit_total_bytes','commit_limit_bytes','commit_headroom_bytes','free_ram_bytes','free_disk_bytes','parent_peak_private_bytes','directory_bytes','directory_entries','elapsed_seconds'}
                if set(current) != expected or any(type(v) is not int or v < 0 for k,v in current.items() if k not in ('elapsed_seconds','commit_headroom_bytes')):
                    raise ValueError('invalid resource sample')
                if type(current['commit_headroom_bytes']) is not int or current['commit_headroom_bytes'] != current['commit_limit_bytes']-current['commit_total_bytes']:
                    raise ValueError('invalid commit headroom')
                checks = [('pipeline_wall_limit',current['elapsed_seconds']>self.limits['wall_seconds']),
                    ('pipeline_parent_memory_limit',current['parent_peak_private_bytes']>self.limits['parent_private_bytes']),
                    ('pipeline_directory_limit',current['directory_bytes']>self.limits['directory_bytes']),
                    ('pipeline_commit_headroom',current['commit_headroom_bytes']<self.limits['minimum_commit_headroom_bytes']),
                    ('pipeline_free_ram',current['free_ram_bytes']<self.limits['minimum_free_ram_bytes']),
                    ('pipeline_free_disk',current['free_disk_bytes']<self.limits['minimum_free_disk_bytes'])]
                with self._lock:
                    self.samples += 1;self.last = current
                    if self.first is None:self.first = current
                    for key,value in current.items():
                        if key not in self.extrema:self.extrema[key] = {'min':value,'max':value}
                        else:
                            self.extrema[key]['min'] = min(self.extrema[key]['min'],value)
                            self.extrema[key]['max'] = max(self.extrema[key]['max'],value)
                    self.reason = self.reason or next((name for name,stopped in checks if stopped),None)
            except resources.ResourceStop as error:
                with self._lock:self.reason = self.reason or error.reason
            except Exception as error:
                with self._lock:
                    self.reason = self.reason or 'pipeline_observation_error';self.observation_error = type(error).__name__

    def _run(self):
        try:
            while not self._stop.wait(INTERVAL):
                self._observe()
                if self.probe() is not None:break
        except BaseException as error:
            with self._lock:
                self.reason = self.reason or 'pipeline_monitor_failure';self.observation_error = type(error).__name__

    def start(self):
        if self._thread is not None:raise ValueError('fixture monitor already started')
        self.checkpoint()
        self._thread = threading.Thread(target=self._run,name='banto-fixture-budget',daemon=False)
        self._thread.start()

    def probe(self):
        outer = self.upstream.probe() if self.upstream is not None else None
        with self._lock:
            self.reason = self.reason or outer
            return self.reason

    def checkpoint(self):
        self._observe()
        reason = self.probe()
        if reason is not None:raise resources.ResourceStop(reason)

    def close(self):
        self._stop.set()
        if self._thread is not None:self._thread.join(timeout=2)
        confirmed = self._thread is None or not self._thread.is_alive()
        if confirmed:self._observe()
        self.probe()
        with self._lock:
            if not confirmed:self.reason = self.reason or 'pipeline_monitor_exit_unconfirmed'
            return {'format':'anomaly-v03-fixture-resource-budget-v1','scope':'one-fixture-call-and-new-receipt-directory',
                'limits':dict(self.limits),'poll_seconds':INTERVAL,'samples':self.samples,'first':self.first,'last':self.last,
                'shared_root':str(self.upstream.root) if self.upstream is not None else None,
                'extrema':{k:dict(v) for k,v in self.extrema.items()},'stop_reason':self.reason,'observation_error':self.observation_error,
                'monitor_exit_confirmed':confirmed,'passed':confirmed and self.reason is None,'receipt_reserve_bytes':RECEIPT_RESERVE,
                'enforcement':'sampled-and-cooperative-not-hard-quota','formal_permission':False}


def finish(monitor, target, result, owner_error=None):
    """Close/report even on an exception without losing an unreaped process owner."""
    try:report = monitor.close()
    except BaseException as error:
        error.resource_monitor = monitor
        if owner_error is not None:
            owner_error.resource_monitor = monitor
            raise owner_error
        raise
    result['resource_budget_passed'] = report['passed']
    if not report['passed']:result.update(status='failed',reason=report['stop_reason'])
    unclosed = None if report['monitor_exit_confirmed'] else UnclosedMonitor(monitor,report)
    try:
        raw = io.json_bytes(report)
        if len(raw) > RECEIPT_RESERVE//2:raise ValueError('budget receipt reserve exceeded')
        io._exclusive(Path(target)/'resource-budget.json',raw)
    finally:
        if owner_error is not None:
            if unclosed is not None:owner_error.resource_monitor = monitor
            raise owner_error
        if unclosed is not None:raise unclosed


def save_result(target, result):
    raw = io.json_bytes(result)
    if len(raw) > RECEIPT_RESERVE//2:raise resources.ResourceStop('pipeline_receipt_limit')
    io._exclusive(Path(target)/'result.json',raw)
