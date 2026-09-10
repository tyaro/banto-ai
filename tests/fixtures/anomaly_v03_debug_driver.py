"""Explicit diagnostic driver, with no CLI or import-time execution.

Only a new core fixture is used. Diagnostic fixtures are retained for inspection;
this driver closes handles but does not claim native acceptance or erase evidence.
Execution still requires the separately documented initial-probe decision.
"""

import ctypes as C
import shutil
import uuid

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_startup_preflight import StartupPreflight
from tests.fixtures.anomaly_v03_debug_tokens import DebugTokens
from tests.fixtures.anomaly_v03_debug_transport import DebugEventTransport, TransportError, need
from tests.fixtures.anomaly_v03_debug_stop import OwnedDebugStop
from tests.fixtures.anomaly_v03_debug_memory import DebugMemory
from tests.fixtures.anomaly_v03_debug_launch import SuspendedDebugLaunch
from tests.fixtures.anomaly_v03_debug_observer import DebugObserver
from tests.fixtures.anomaly_v03_debug_session import DebugSession
from tests.fixtures.anomaly_v03_debug_evidence import DebugEvidence, EvidenceFile
from tests.fixtures.anomaly_v03_debug_images import DebugImages
from tests.fixtures.anomaly_v03_debug_security import DebugSecurity
from tests.fixtures.anomaly_v03_debug_context import DebugContext
from tests.fixtures.anomaly_v03_debug_unload_entry import DebugUnloadEntry
from tests.fixtures.anomaly_v03_debug_init_return import DebugInitReturn
from tests.fixtures.anomaly_v03_debug_console_failure import DebugConsoleFailure
from tests.fixtures.anomaly_v03_debug_bootstrap import DebugBootstrap
from tests.fixtures.anomaly_v03_debug_init_failure import DebugInitFailure
from tests.fixtures.anomaly_v03_debug_bcrypt_failure import DebugBcryptFailure


class DriverResult(dict):
    def __init__(self, owner):
        super().__init__(status="not_started", resource_stop=False, teardown_status="not_started",
                         fixture_retention="not_created", native_accepted=False, formal_permission=False)
        self.private_owner = owner


class DebugDriver:
    MIN_FREE_DISK = 1024 * 1024 * 1024

    def __init__(self, *, unload_entry=False, init_return=False, console_failure=False,
                 detached_console=False, bootstrap=False, init_failure=False, bcrypt_failure=False):
        need(type(unload_entry) is bool, "entry_option")
        need(type(init_return) is bool and not (unload_entry and init_return), "return_option")
        need(type(console_failure) is bool and not (console_failure and (unload_entry or init_return)),
             "console_option")
        need(type(init_failure) is bool and not (init_failure and (unload_entry or init_return or console_failure)),
             "init_failure_option")
        need(type(bcrypt_failure) is bool and not (bcrypt_failure and
             (unload_entry or init_return or console_failure or init_failure)), "bcrypt_failure_option")
        need(type(detached_console) is bool and (not detached_console or init_return or unload_entry or init_failure or bcrypt_failure),
             "detached_option")
        self.detached_console = detached_console
        need(type(bootstrap) is bool and (not bootstrap or detached_console and (unload_entry or init_failure or bcrypt_failure)),
             "bootstrap_option")
        need(not init_failure or bootstrap and detached_console, "init_failure_bootstrap_option")
        need(not bcrypt_failure or bootstrap and detached_console, "bcrypt_bootstrap_option")
        self.preflight = StartupPreflight()
        self.api = self.tokens = self.fixture = self.transport = self.stop = None
        self.memory = self.launch = self.observer = self.session = None
        self.primary = self.secondary = None
        self.started = self.resource_stop = False
        self.request = self.request_raw = self.nonce = None
        self.teardown = w._Teardown()
        self.session_result = None
        self.token_resolved = True
        self.evidence = DebugEvidence()
        self.evidence_file = None
        self.images = DebugImages()
        self.bootstrap = DebugBootstrap(self.images) if bootstrap else None
        self.security = DebugSecurity()
        self.context = (DebugBcryptFailure(self.images, self.bootstrap) if bcrypt_failure else
                        DebugInitFailure(self.images, self.bootstrap) if init_failure else
                        DebugConsoleFailure(self.images) if console_failure else
                        DebugInitReturn(self.images) if init_return else
                        DebugContext(entry=DebugUnloadEntry() if unload_entry else None, images=self.images))
        self.result = DriverResult(self)

    def __repr__(self):
        return "DebugDriver(<private fixture, profiles and evidence>)"

    def _latch(self, error):
        self.resource_stop |= (w._resource_stop(error) or self.preflight.resource_stop
                               or self.teardown.resource_stop
                               or self.tokens is not None and self.tokens.resource_stop
                               or self.session is not None and self.session.resource_stop
                               or self.stop is not None and self.stop.resource_stop
                               or self.evidence.resource_stop
                               or self.security.resource_stop
                               or self.context.resource_stop
                               or self.bootstrap is not None and self.bootstrap.resource_stop
                               or self.evidence_file is not None and self.evidence_file.resource_stop)

    def _prepare(self):
        self.api = w._api()
        result = self.preflight.run()
        if result["status"] != "verified":
            raise self.preflight.primary or self.preflight.secondary or TransportError("driver_preflight")
        self.preflight._budget(self.api)
        free = shutil.disk_usage(w._temporary_path(self.api)).free
        need(type(free) is int and free >= self.MIN_FREE_DISK, "driver_disk_reserve")
        self.tokens = DebugTokens(self.api)
        self.tokens.prepare()
        if self.tokens.status != "prepared":
            raise self.tokens.primary or self.tokens.secondary or TransportError("driver_tokens")
        self.security.bind(self.api)
        for index in (0, 1):
            self.security.capture(index, self.tokens.buffers[index].value,
                                  lambda: self.preflight._budget(self.api))
        self.preflight._budget(self.api)
        self.fixture = w._Fixture(self.api, self.tokens.parent_profile["user"][0])
        self.fixture.create()
        self.fixture.freeze()
        self.fixture.file(w._REPLACE_TRACE_NAME, b"", "control")
        self.evidence_file = EvidenceFile(self.api)
        self.evidence_file.prepare(self.fixture)
        source = [row for row in result["sources"] if row["path"] in (
            "src/banto_ai/_anomaly_v03_windows.py", "tests/fixtures/anomaly_v03_native_child.py")]
        need(len(source) == 2, "driver_child_source")
        self.nonce = uuid.uuid4().hex
        self.request = {"version": "b1.2", "nonce": self.nonce, "objects": self.fixture.ledger,
                        "parent": self.tokens.parent_profile, "restricted": self.tokens.restricted_profile,
                        "source": source}
        self.request_raw = w._canonical(self.request)
        need(len(self.request_raw) <= w._LIMIT, "driver_request_size")
        self.fixture.file("control/request.json", self.request_raw, "private")
        self.preflight._budget(self.api)
        self.transport = DebugEventTransport(kernel=self.api.k, last_error=C.get_last_error)
        self.stop = OwnedDebugStop(self.transport)
        self.memory = DebugMemory(self.stop, self.api.p)
        self.observer = DebugObserver(self.stop, sample_memory=self.memory, images=self.images,
                                      context=self.context, bootstrap=self.bootstrap)
        self.launch = SuspendedDebugLaunch(self.api, self.tokens.buffers[1].value, self.fixture, self.stop,
                                          detached_console=self.detached_console)
        self.context.bind(self.stop, self.launch)
        if self.bootstrap is not None:
            self.bootstrap.bind(self.stop, self.launch)
            self.transport.bootstrap = self.bootstrap
        self.session = DebugSession(self.preflight, self.launch, self.observer,
                                    self.tokens.parent_profile, self.tokens.restricted_profile, security=self.security)

    def run(self):
        need(not self.started, "driver_retry")
        self.started = True
        try:
            self._prepare()
            self.session_result = self.session.run()
            if self.session_result["status"] != "observed":
                raise self.session.primary or self.session.secondary or TransportError("driver_session")
        except BaseException as error:
            self.primary = error
            self._latch(error)
        finally:
            # No path lookup, snapshot capture, ACL repair or deletion after a
            # failure/resource stop. Preserve the new fixture for diagnosis.
            if self.transport is not None:
                self.transport.state = "stopped"
            if self.launch is not None and self.launch.creation_state == "created" and not self.stop.started:
                self.teardown.attempt("driver_child_stop", lambda: self.stop.run(self.primary))
            if self.session is not None:
                self.teardown.attempt("driver_child_token_close", self.session._close_tokens)
            if self.fixture is not None:
                self.teardown.attempt("driver_fixture_close", lambda: self.fixture.close(teardown=self.teardown))
            if self.tokens is not None:
                try:
                    self.token_resolved = self.tokens.close()
                except BaseException as error:
                    self.token_resolved = False
                    self.secondary = error
                    self._latch(error)
        try:
            self._latch(self.secondary)
            child_clean = self.launch is None or self.launch.creation_state in ("not_started", "failed")
            if self.launch is not None and self.launch.creation_state == "created":
                child_clean = (self.stop.started and self.stop.result["teardown_status"] == "pass"
                               and self.stop.result["process_signaled"] and self.stop.result["debug_ownership_resolved"]
                               and all(handle is None for handle in self.stop.handles))
            clean = (self.token_resolved and self.teardown.count == 0 and child_clean
                     and (self.session is None or self.session.tokens_resolved()))
            self.result.update(status="observed" if self.primary is None and self.secondary is None
                               and clean and not self.resource_stop else "failed",
                               resource_stop=self.resource_stop, teardown_status="pass" if clean else "failed",
                               fixture_retention="unverified" if self.fixture is not None else "not_created")
        except BaseException as error:
            self.secondary = error
            self._latch(error)
            self.result["status"] = "report_failed"
            self.result["resource_stop"] = self.resource_stop
            self.result["teardown_status"] = "failed"
        # Use only already-owned local buffers and the prelaunch file handle.
        # No path lookup, readback, or cleanup is introduced after observation.
        try:
            if (self.evidence_file is not None and self.evidence_file.open_state == "prepared"
                    and self.transport is not None and self.stop is not None):
                self.evidence.capture(self)
                self._latch(self.evidence.primary)
                if self.evidence.capture_state == "captured":
                    self.evidence.write(self.api.k, self.evidence_file.handle)
                    self._latch(self.evidence.primary)
        except BaseException as error:
            self.secondary = error
            self._latch(error)
        finally:
            if self.evidence_file is not None:
                self.teardown.attempt("driver_evidence_close", self.evidence_file.close)
        try:
            self._latch(self.evidence.primary)
            saved = self.evidence.flush_state == "confirmed"
            evidence_closed = self.evidence_file is None or self.evidence_file.resolved()
            self.result["evidence_status"] = "flushed" if saved else self.evidence.capture_state
            self.result["evidence_write_state"] = self.evidence.write_state
            self.result["evidence_flush_state"] = self.evidence.flush_state
            self.result["evidence_file_closed"] = evidence_closed
            self.result["resource_stop"] = self.resource_stop
            if not evidence_closed or self.teardown.count:
                self.result["teardown_status"] = "failed"
            if (not saved or not evidence_closed or self.resource_stop or self.evidence.primary is not None
                    or self.secondary is not None or self.teardown.count):
                if self.result["status"] != "report_failed":
                    self.result["status"] = "failed"
        except BaseException as error:
            self.secondary = error
            self._latch(error)
            self.result["status"] = "report_failed"
            self.result["resource_stop"] = self.resource_stop
        return self.result
