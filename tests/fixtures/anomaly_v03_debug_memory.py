"""Preallocated parent/owned-child memory sampler; no launch or handle adoption.

Reuse the production ABI and peak-commit budget metric. Native bindings are
supplied by an existing _Win instance; tests supply only a fake PSAPI function.
"""

import ctypes as C

from banto_ai._anomaly_v03_windows import _Memory
from tests.fixtures.anomaly_v03_debug_transport import TransportError, need


class DebugMemory:
    LIMIT = 512 * 1024 * 1024

    def __init__(self, stop, psapi):
        self.stop, self.transport, self.psapi = stop, stop.transport, psapi
        self.buffers = (_Memory(), _Memory())
        self.pointers = tuple(C.pointer(buffer) for buffer in self.buffers)
        for buffer in self.buffers:
            buffer.cb = C.sizeof(_Memory)
        self.state = "ready"
        self.resource_stop = False
        self.primary = None
        self.samples = 0
        self.process_commit_peaks = [0, 0]
        self.process_working_peaks = [0, 0]
        self.peak_commit = self.peak_working = 0

    def __repr__(self):
        return "DebugMemory(<private counters>)"

    def _ready(self):
        need(self.state == "ready" and not self.stop.started
             and not (self.resource_stop or self.transport.resource_stop
                      or self.stop.resource_stop or self.stop.drain.resource_stop), "memory_stopped")
        need(self.transport.state in ("idle", "pending", "exit_continued"), "memory_transport")

    def __call__(self):
        try:
            self._ready()
            self.transport._thread()
            process = self.stop.handles[0]
            need(process is not None and self.transport.pid is not None
                 and self.stop.drain.pid == self.transport.pid, "memory_owner")
            kernel = self.transport.kernel
            need(kernel.GetProcessId(process) == self.transport.pid, "memory_identity")
            parent = kernel.GetCurrentProcess()
            need(parent not in (None, 0), "memory_parent")
            # Slots are retained even if only one API writes before failure.
            for index, handle in enumerate((parent, process)):
                self._ready()
                self.state = "querying"
                if not self.psapi.GetProcessMemoryInfo(handle, self.pointers[index], C.sizeof(_Memory)):
                    raise TransportError("memory_query", self.transport.last_error())
                self.state = "ready"
                need(self.buffers[index].cb == C.sizeof(_Memory), "memory_size")
                # Lifetime peaks already confirmed for the other process are
                # still lower bounds. Stop as soon as their sum is conclusive,
                # before a second query can fail and mask the resource stop.
                self.process_commit_peaks[index] = max(self.process_commit_peaks[index],
                                                       self.buffers[index].peak_pagefile)
                self.process_working_peaks[index] = max(self.process_working_peaks[index],
                                                        self.buffers[index].peak_working)
                self.peak_commit = self.process_commit_peaks[0] + self.process_commit_peaks[1]
                self.peak_working = self.process_working_peaks[0] + self.process_working_peaks[1]
                if self.peak_commit >= self.LIMIT:
                    self.resource_stop = True
                    raise TransportError("memory_budget")
            self.samples += 1
            return self.peak_commit
        except BaseException as error:
            if self.primary is None:
                self.primary = error
            self.resource_stop |= (isinstance(error, MemoryError) or self.transport.resource_stop
                                   or self.stop.resource_stop or self.stop.drain.resource_stop)
            self.transport.resource_stop |= self.resource_stop
            self.transport.state = "stopped"
            self.state = "stopped"
            raise
