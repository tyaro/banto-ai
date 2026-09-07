"""Low-level suspended launch/ownership adapter, with no CLI or auto-execution.

The future driver must finish preflight, token/fixture validation and allocation
before calling create(). This adapter does not grant permission or resume the
child. In particular, a successful suspended creation is not probe readiness.
"""

import ctypes as C
import os
import subprocess
import sys

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_transport import TransportError, need


class LaunchResult(dict):
    def __init__(self, owner):
        super().__init__(status="not_started", creation_state="not_started",
                         ownership_transferred=False, resource_stop=False,
                         native_accepted=False, formal_permission=False)
        self.private_owner = owner


class SuspendedDebugLaunch:
    FLAGS = 0x08000000 | 0x400 | 4 | 2  # NO_WINDOW, UNICODE_ENV, SUSPENDED, DEBUG_ONLY_THIS_PROCESS

    def __init__(self, api, token, fixture, stop):
        need(api.k is stop.kernel, "launch_kernel")
        self.api, self.stop, self.transport = api, stop, stop.transport
        self.fixture = fixture  # Borrowed; caller owns fixture/token teardown.
        self.startup, self.process = w._Startup(), w._Process()
        self.startup.cb = C.sizeof(self.startup)
        self.startup.desktop = ""
        self.startup_pointer, self.process_pointer = C.pointer(self.startup), C.pointer(self.process)
        arguments = [sys.executable, "-B", "-I", str(w._CHILD), str(fixture.root)]
        self.command = C.create_unicode_buffer(subprocess.list2cmdline(arguments))
        self.environment = C.create_unicode_buffer(
            "SystemRoot=" + os.environ["SystemRoot"] + "\0TEMP=" + str(fixture.root.parent)
            + "\0TMP=" + str(fixture.root.parent) + "\0\0")
        self.arguments = (token, sys.executable, self.command, None, None, False, self.FLAGS,
                          self.environment, str(fixture.root / "control"),
                          self.startup_pointer, self.process_pointer)
        self.started = self.resource_stop = self.transferred = False
        self.creation_state = "not_started"
        self.primary = self.secondary = None
        self.stop_result = None
        self.result = LaunchResult(self)
        self.stop.prepare_creation(self)

    def __repr__(self):
        return "SuspendedDebugLaunch(<private buffers and ownership>)"

    def _latch(self, error):
        self.resource_stop |= (w._resource_stop(error) or self.transport.resource_stop
                               or self.stop.resource_stop or self.stop.drain.resource_stop)
        self.transport.resource_stop |= self.resource_stop
        self.stop.resource_stop |= self.resource_stop

    def create(self):
        need(not self.started, "launch_retry")
        self.started = True
        try:
            self.transport._thread()
            need(not self.stop.started and self.transport.pid is None and self.stop.drain.pid is None
                 and self.transport.state == "idle" and self.transport.count == 0
                 and self.stop.creation_owner is self
                 and all(handle is None for handle in self.stop.handles), "launch_owner_state")
            self._latch(None)
            need(not self.resource_stop, "launch_resource_latched")
            need(type(self.arguments[0]) is int and self.arguments[0] > 0, "launch_token")
            # The output buffer and its result owner already exist. Any failure
            # between API entry and confirmed return retains uncertain output.
            self.creation_state = "uncertain"
            if not self.api.a.CreateProcessAsUserW(*self.arguments):
                self.creation_state = "failed"
                raise TransportError("restricted_debug_create", self.transport.last_error())
            self.creation_state = "created"
            need(self.process.pid != 0 and self.process.tid != 0, "launch_process_identity")
            self.transport.bind(self.process.pid)
            self.stop.adopt(self.process.process, self.process.thread)
            self.transferred = True
            self.result.update(status="suspended", creation_state=self.creation_state,
                               ownership_transferred=True)
        except BaseException as error:
            self.primary = error
            self._latch(error)
            self.transport.state = "stopped"
            if self.creation_state == "created":
                try:
                    self.stop_result = self.stop.run(error)
                except BaseException as secondary:
                    self.secondary = secondary
                    self._latch(secondary)
            # Failed/uncertain API output is not proof of valid owned handles.
            # Never guess, retry creation, or close arbitrary output values.
            self.result["status"] = "failed"
        try:
            self._latch(None)
            self.result.update(creation_state=self.creation_state,
                               ownership_transferred=self.transferred,
                               resource_stop=self.resource_stop)
        except BaseException as error:
            self.secondary = error
            self._latch(error)
            self.transport.state = "stopped"
            # If only final reporting failed after transfer, still attempt the
            # owned stop once. Never repeat an interrupted stop attempt.
            if self.creation_state == "created" and not self.stop.started:
                try:
                    self.stop_result = self.stop.run(self.primary or error)
                except BaseException as secondary:
                    self.secondary = secondary
                    self._latch(secondary)
            self._latch(None)
            self.result["status"] = "report_failed"
            self.result["resource_stop"] = self.resource_stop
        return self.result
