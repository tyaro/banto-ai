"""Explicit preflight only; never creates a fixture, restricted child or debugger.

Pins the fixed diagnostic inputs against the Git index using existing bounded
source readers. This verifies disk/index agreement, not loaded-code identity or
permission to run a probe. A future launcher must retain this result and enforce
its own remaining gates before process creation.
"""

import math
import os
import time

from banto_ai import _anomaly_v03_windows as w


SOURCES = (
    "src/banto_ai/__init__.py",
    "src/banto_ai/_anomaly_v03_windows.py",
    "tests/__init__.py",
    "tests/fixtures/anomaly_v03_native_child.py",
    "tests/fixtures/anomaly_v03_startup_events.py",
    "tests/fixtures/anomaly_v03_debug_transport.py",
    "tests/fixtures/anomaly_v03_debug_stop.py",
    "tests/fixtures/anomaly_v03_debug_observer.py",
    "tests/fixtures/anomaly_v03_debug_memory.py",
    "tests/fixtures/anomaly_v03_debug_launch.py",
    "tests/fixtures/anomaly_v03_debug_session.py",
    "tests/fixtures/anomaly_v03_debug_tokens.py",
    "tests/fixtures/anomaly_v03_debug_evidence.py",
    "tests/fixtures/anomaly_v03_debug_images.py",
    "tests/fixtures/anomaly_v03_debug_security.py",
    "tests/fixtures/anomaly_v03_debug_context.py",
    "tests/fixtures/anomaly_v03_debug_unload_entry.py",
    "tests/fixtures/anomaly_v03_debug_driver.py",
    "tests/fixtures/anomaly_v03_startup_preflight.py",
)


class PreflightResult(dict):
    def __init__(self, owner):
        super().__init__(status="not_started", source_scope="diagnostic-index-inputs",
                         sources=None, runtime=None, resource_stop=False,
                         execution_authenticated=False, launch_authorized=False,
                         native_accepted=False, formal_permission=False)
        self.private_owner = owner


class StartupPreflight:
    def __init__(self, *, clock=time.monotonic):
        self.clock = clock
        self.paths = tuple(w._ROOT / path for path in SOURCES)
        self.rows = [None] * len(SOURCES)
        self.count = 0
        self.source_bytes = 0
        self.runtime = None
        self.started = self.resource_stop = False
        self.primary = self.secondary = None
        self.origin = self.last_clock = None
        self.result = PreflightResult(self)

    def __repr__(self):
        return "StartupPreflight(<private failure evidence>)"

    def _time(self):
        now = self.clock()
        w._need(type(now) in (int, float) and math.isfinite(now), "preflight_clock")
        if self.origin is None:
            self.origin = self.last_clock = now
        w._need(now >= self.last_clock and now - self.origin < 30, "preflight_deadline")
        self.last_clock = now

    def _budget(self, api):
        w._need(not self.resource_stop, "preflight_resource_latched")
        self._time()
        own = api.resources(api.k.GetCurrentProcess())
        peak = own["peak_pagefile_bytes"]
        w._need(type(peak) is int and peak >= 0, "preflight_memory_sample")
        if peak >= w._MEMORY_LIMIT:
            self.resource_stop = True
            raise w._Failure("memory_budget")
        self._time()

    def run(self):
        w._need(not self.started, "preflight_retry")
        self.started = True
        try:
            self._time()
            api = w._api()
            self._budget(api)
            self.runtime = w._runtime()
            self._budget(api)
            environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1"}
            for index, path in enumerate(self.paths):
                self._budget(api)
                raw = w._source_bytes(api, path)
                w._need(type(raw) is bytes, "preflight_source_type")
                self.source_bytes += len(raw)
                if self.source_bytes > w._LIMIT:
                    self.resource_stop = True
                    raise w._Failure("source_size")
                # Retain bounded hash metadata before index IO; never retain
                # source bodies, environment values or absolute paths in JSON.
                self.rows[index] = {"path": SOURCES[index], "sha256": w._sha(raw), "bytes": len(raw)}
                self._budget(api)
                w._need(w._index_bytes(api, path, environment) == raw, "source_index_bytes")
                self.count += 1
                del raw
                self._budget(api)
            self.result.update(status="verified", sources=list(self.rows), runtime=self.runtime)
        except BaseException as error:
            self.primary = error
            self.resource_stop |= w._resource_stop(error)
            self.result["status"] = "failed"
        try:
            self.result["resource_stop"] = self.resource_stop
        except BaseException as error:
            self.secondary = error
            self.resource_stop |= w._resource_stop(error)
            self.result["status"] = "report_failed"
            self.result["resource_stop"] = self.resource_stop
        return self.result
